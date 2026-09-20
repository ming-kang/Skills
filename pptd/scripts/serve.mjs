#!/usr/bin/env node
/**
 * Local editor host for the pptd skill: serves the offline neo-ppt mirror so a
 * Chromium-based browser can open, edit and export PPTD projects. It can also
 * mount one PPTD project read-only, so a preview needs no folder picker.
 *
 * Usage:
 *   node scripts/serve.mjs [--port 55173] [--open] [--project <dir>] [--idle-timeout <minutes>]
 *   node scripts/serve.mjs --status [--project <dir>]
 *   node scripts/serve.mjs --stop [--project <dir>]
 *
 * Lifecycle — the host is meant to be driven by an agent as well as a human:
 *   - Lease file: every running instance registers itself in the OS temp dir.
 *     A second launch for the same editor + project reuses the running URL
 *     instead of dying with EADDRINUSE.
 *   - Port drift: if the preferred port is held by a foreign process, the host
 *     binds a free port and reports the URL it actually got.
 *   - Idle watchdog: an open editor pings the host; when no heartbeat arrives
 *     for `--idle-timeout` minutes (default 120, 0 disables) the host exits and
 *     clears its lease, so a forgotten background process cannot linger.
 *   - --status / --stop print a single JSON line and are safe to call from a
 *     script or an agent tool call.
 *
 * Env:
 *   PPTD_EDITOR_DIR          override the editor directory (default: assets/editor)
 *                             (legacy alias OPEN_KIMI_PPT_EDITOR still honored)
 *   PPTD_SERVE_IDLE_MINUTES  default idle timeout in minutes (default: 120)
 */

import {
  createReadStream,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, extname, resolve, sep } from "node:path";
import { stdout as output } from "node:process";
import { fileURLToPath } from "node:url";

// The editor bridge's path/YAML helpers are the canonical implementations
// (and are unit-tested); the host reuses them instead of forking copies.
import { normalizeRelativePath, unquoteYamlScalar } from "../assets/editor/lib.js";

const SKILL_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_PORT = 55_173;
const DEFAULT_IDLE_MINUTES = 120;
const PROJECT_MOUNT = "/project/";
const PING_PATH = "/__ping__";

/**
 * The editor mirror directory: PPTD_EDITOR_DIR (legacy alias
 * OPEN_KIMI_PPT_EDITOR) when set, else the in-skill assets/editor copy.
 * The one definition of this policy — export_pptx.py's resolve_editor_root()
 * is its Python twin.
 */
function resolveEditorRoot() {
  return resolve(
    process.env.PPTD_EDITOR_DIR ??
      process.env.OPEN_KIMI_PPT_EDITOR ??
      resolve(SKILL_ROOT, "assets", "editor"),
  );
}

/**
 * Idle minutes from PPTD_SERVE_IDLE_MINUTES, falling back to the default
 * when unset or invalid. An invalid value used to become NaN, which the
 * watchdog reads as "disabled" — a forgotten background host that never
 * exits. Loud fallback instead of silent fail-open.
 */
function idleMinutesFromEnv() {
  const raw = process.env.PPTD_SERVE_IDLE_MINUTES;
  if (raw === undefined || raw === "") return DEFAULT_IDLE_MINUTES;
  const minutes = Number(raw);
  if (!Number.isFinite(minutes) || minutes < 0) {
    output.write(
      `pptd: ignoring invalid PPTD_SERVE_IDLE_MINUTES=${JSON.stringify(raw)}; using ${DEFAULT_IDLE_MINUTES}\n`,
    );
    return DEFAULT_IDLE_MINUTES;
  }
  return minutes;
}

const contentTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".wasm", "application/wasm"],
  [".pptd", "text/yaml; charset=utf-8"],
  [".page", "text/yaml; charset=utf-8"],
  [".yaml", "text/yaml; charset=utf-8"],
  [".yml", "text/yaml; charset=utf-8"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".gif", "image/gif"],
  [".webp", "image/webp"],
  [".ico", "image/x-icon"],
  [".woff", "font/woff"],
  [".woff2", "font/woff2"],
  [".ttf", "font/ttf"],
  [".otf", "font/otf"],
  [".fntdata", "application/octet-stream"],
]);

function respond(response, statusCode, message) {
  response.writeHead(statusCode, {
    "Content-Type": "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  response.end(message);
}

/* ------------------------------------------------------------------ *
 * Project mounting (read-only preview)
 * ------------------------------------------------------------------ */

/**
 * Map a /project/... pathname to a file inside the project, or null when it
 * escapes. The path rules are the editor bridge's normalizeRelativePath —
 * one canonical implementation (no absolute, no drive, no ".."), reused here
 * so host and bridge cannot disagree about what a project path is.
 */
function resolveProjectPath(projectRoot, pathname) {
  let relative;
  try {
    // The editor asks for some assets with a leading slash ("media/x.png").
    relative = normalizeRelativePath(pathname.replace(/^\/+/, ""));
  } catch {
    return null;
  }
  const candidate = resolve(projectRoot, relative);
  return candidate === projectRoot || candidate.startsWith(`${projectRoot}${sep}`) ? candidate : null;
}

/** Locate the deck manifest inside a mounted project (top level first). */
export function findProjectManifest(projectRoot, maxDepth = 4) {
  let entries;
  try {
    entries = readdirSync(projectRoot, { withFileTypes: true });
  } catch {
    return null;
  }
  const isManifest = (entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".pptd");
  const topLevel = entries.filter(isManifest).map((entry) => entry.name).sort();
  if (topLevel.length) return topLevel[0];

  const queue = entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => ({ name: entry.name, depth: 1 }));
  while (queue.length) {
    const current = queue.shift();
    if (current.depth > maxDepth) continue;
    let children;
    try {
      children = readdirSync(resolve(projectRoot, current.name), { withFileTypes: true });
    } catch {
      continue;
    }
    const found = children.filter(isManifest).map((entry) => `${current.name}/${entry.name}`).sort();
    if (found.length) return found[0];
    for (const child of children) {
      if (child.isDirectory()) queue.push({ name: `${current.name}/${child.name}`, depth: current.depth + 1 });
    }
  }
  return null;
}

function projectTitle(manifestPath, manifestText) {
  if (!manifestText) return null;
  const match = manifestText.match(/^title\s*:\s*(.+?)\s*$/m);
  if (!match) return null;
  const title = unquoteYamlScalar(match[1]);
  return title || (manifestPath ? manifestPath.split("/").pop().replace(/\.pptd$/i, "") : null);
}

/* ------------------------------------------------------------------ *
 * HTTP server
 * ------------------------------------------------------------------ */

export function createEditorServer({
  editorDirectory = resolveEditorRoot(),
  projectDirectory = null,
} = {}) {
  const root = resolve(editorDirectory);
  const rootPrefix = `${root}${sep}`;
  const projectRoot = projectDirectory ? resolve(projectDirectory) : null;
  // Heartbeat source for the idle watchdog: every request counts, and the
  // editor page itself pings PING_PATH while it stays open.
  const activity = { lastActivityAt: Date.now() };

  const server = createServer((request, response) => {
    activity.lastActivityAt = Date.now();
    handleRequest(request, response);
  });

  function handleRequest(request, response) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      respond(response, 405, "Method Not Allowed");
      return;
    }

    let pathname;
    try {
      pathname = decodeURIComponent(new URL(request.url ?? "/", "http://localhost").pathname);
    } catch {
      respond(response, 400, "Bad Request");
      return;
    }

    if (pathname === PING_PATH) {
      response.writeHead(204, { "Cache-Control": "no-store" });
      response.end();
      return;
    }

    if (projectRoot && (pathname === "/project.json")) {
      serveProjectManifest(request, response, projectRoot);
      return;
    }

    if (projectRoot && pathname.startsWith(PROJECT_MOUNT)) {
      const filePath = resolveProjectPath(projectRoot, pathname.slice(PROJECT_MOUNT.length));
      if (!filePath) {
        respond(response, 403, "Forbidden");
        return;
      }
      serveFile(request, response, filePath);
      return;
    }

    if (pathname.endsWith("/")) pathname += "index.html";
    const filePath = resolve(root, `.${pathname}`);
    if (filePath !== root && !filePath.startsWith(rootPrefix)) {
      respond(response, 403, "Forbidden");
      return;
    }
    serveFile(request, response, filePath);
  }

  function serveProjectManifest(request, response, root_) {
    const manifest = findProjectManifest(root_);
    if (!manifest) {
      respond(response, 404, "No .pptd manifest in the mounted project");
      return;
    }
    let title = null;
    try {
      title = projectTitle(manifest, readFileSync(resolve(root_, manifest), "utf-8"));
    } catch {
      /* the manifest is also served under /project/; title is optional */
    }
    const body = JSON.stringify({ manifest, title });
    response.writeHead(200, {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Length": Buffer.byteLength(body),
      "Cache-Control": "no-store",
    });
    response.end(request.method === "HEAD" ? undefined : body);
  }

  function serveFile(request, response, filePath) {
    let stats;
    try {
      stats = statSync(filePath);
    } catch {
      respond(response, 404, "Not Found");
      return;
    }
    if (!stats.isFile()) {
      respond(response, 404, "Not Found");
      return;
    }

    response.writeHead(200, {
      "Content-Type": contentTypes.get(extname(filePath).toLowerCase()) ?? "application/octet-stream",
      "Content-Length": stats.size,
      "Cache-Control": "no-store",
    });

    if (request.method === "HEAD") {
      response.end();
      return;
    }

    const stream = createReadStream(filePath);
    stream.on("error", () => response.destroy());
    stream.pipe(response);
  }

  // Exposed for the idle watchdog and for tests.
  server.activity = activity;
  server.projectRoot = projectRoot;
  return server;
}

/* ------------------------------------------------------------------ *
 * Idle watchdog
 * ------------------------------------------------------------------ */

/**
 * Calls `onIdle` once when `activity.lastActivityAt` has not advanced for
 * `idleMs`. `now` is injectable so tests do not have to wait in real time.
 */
export function createIdleWatchdog({ idleMs, activity, onIdle, now = () => Date.now(), intervalMs = 15_000 }) {
  const disabled = !Number.isFinite(idleMs) || idleMs <= 0;
  if (disabled) {
    return { stop: () => {}, isIdle: () => false };
  }
  // Check often enough for short timeouts (tests, manual --idle-timeout).
  const interval = Math.max(100, Math.min(intervalMs, idleMs));
  const timer = setInterval(() => {
    if (now() - activity.lastActivityAt >= idleMs) {
      stop();
      onIdle?.();
    }
  }, interval);
  // Never keep the process alive just for the watchdog.
  timer.unref?.();
  const stop = () => clearInterval(timer);
  return { stop, isIdle: () => now() - activity.lastActivityAt >= idleMs };
}

/* ------------------------------------------------------------------ *
 * Lease registry (OS temp dir)
 * ------------------------------------------------------------------ */

const LEASE_DIRECTORY = resolve(tmpdir(), "pptd-serve");

function leaseKey({ editorRoot, projectRoot }) {
  return createHash("sha1").update(`${editorRoot}\n${projectRoot ?? ""}`).digest("hex").slice(0, 16);
}

function leaseFile(key) {
  return resolve(LEASE_DIRECTORY, `${key}.json`);
}

function readLease(key) {
  try {
    const value = JSON.parse(readFileSync(leaseFile(key), "utf-8"));
    return value && typeof value === "object" ? value : null;
  } catch {
    return null;
  }
}

function writeLease(key, lease) {
  try {
    mkdirSync(LEASE_DIRECTORY, { recursive: true });
    writeFileSync(leaseFile(key), `${JSON.stringify(lease, null, 2)}\n`, "utf-8");
  } catch {
    /* the lease is an optimization; losing it must not break serving */
  }
}

export function removeLease(key, pid) {
  try {
    const current = readLease(key);
    // Only clear a lease we still own: a newer instance may have replaced it.
    if (current && pid != null && current.pid !== pid) return;
    rmSync(leaseFile(key), { force: true });
  } catch {
    /* ignore */
  }
}

function listLeases() {
  try {
    return readdirSync(LEASE_DIRECTORY)
      .filter((name) => name.endsWith(".json"))
      .map((name) => {
        const file = resolve(LEASE_DIRECTORY, name);
        try {
          // The key is the file name: carry it so consumers never rebuild it
          // from lease contents (which drifts when the lease shape changes).
          return { file, key: name.replace(/\.json$/, ""), lease: JSON.parse(readFileSync(file, "utf-8")) };
        } catch {
          return null;
        }
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

function processAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    // EPERM means the process exists but belongs to another user.
    return error.code === "EPERM";
  }
}

async function httpOk(url, timeoutMs = 2_000) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) });
    return response.ok;
  } catch {
    return false;
  }
}

function stopProcess(pid) {
  if (!processAlive(pid)) return true;
  if (process.platform === "win32") {
    // /T takes the browser-opener child too; fall back to force.
    if (spawnSync("taskkill", ["/pid", String(pid), "/T"], { stdio: "ignore" }).status !== 0) {
      spawnSync("taskkill", ["/pid", String(pid), "/T", "/F"], { stdio: "ignore" });
    }
  } else {
    try {
      process.kill(pid, "SIGTERM");
    } catch {
      /* already gone */
    }
  }
  const deadline = Date.now() + 5_000;
  while (Date.now() < deadline) {
    if (!processAlive(pid)) return true;
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 200);
  }
  return !processAlive(pid);
}

/* ------------------------------------------------------------------ *
 * Server lifecycle
 * ------------------------------------------------------------------ */

export async function startEditorServer({
  host = "127.0.0.1",
  port = DEFAULT_PORT,
  editorDirectory,
  projectDirectory = null,
  idleTimeoutMs = idleMinutesFromEnv() * 60_000,
  registerLease = true,
} = {}) {
  const editorRoot = resolve(editorDirectory ?? resolveEditorRoot());
  const projectRoot = projectDirectory ? resolve(projectDirectory) : null;
  const key = leaseKey({ editorRoot, projectRoot });

  // Another live instance for the same editor + project: reuse its URL.
  if (registerLease) {
    const lease = readLease(key);
    if (lease && processAlive(lease.pid)) {
      const url = `http://${lease.host ?? host}:${lease.port}/`;
      if (await httpOk(url)) {
        return { server: null, url, port: lease.port, pid: lease.pid, reused: true, projectRoot, editorRoot, key };
      }
    }
  }

  const requestedPort = Number.isInteger(port) && port >= 0 && port <= 65_535 ? port : DEFAULT_PORT;
  const server = createEditorServer(projectRoot ? { editorDirectory: editorRoot, projectDirectory: projectRoot } : { editorDirectory: editorRoot });

  return new Promise((resolvePromise, reject) => {
    // A single "error" listener: EADDRINUSE drifts to a free port, anything
    // else rejects. Registering two listeners would consume the event first.
    const onError = (error) => {
      if (error?.code === "EADDRINUSE") {
        // Foreign process on the preferred port: drift instead of dying.
        output.write(`pptd: port ${requestedPort} is in use; trying a free port\n`);
        listen(0);
        return;
      }
      reject(error);
    };
    server.once("error", onError);

    const listen = (candidatePort) =>
      server.listen(candidatePort, host, () => {
        server.off("error", onError);
        const address = server.address();
        const actualPort = typeof address === "object" && address ? address.port : candidatePort;
        const url = `http://${host}:${actualPort}/`;
        const pid = process.pid;
        const lease = {
          pid,
          port: actualPort,
          host,
          url,
          editorRoot,
          projectRoot,
          startedAt: new Date().toISOString(),
        };
        if (registerLease) writeLease(key, lease);

        const watchdog = createIdleWatchdog({
          idleMs: idleTimeoutMs,
          activity: server.activity,
          onIdle: () => {
            output.write(`pptd local editor exited after ${idleTimeoutMs / 60_000} idle minutes\n`);
            shutdown(0);
          },
        });

        const shutdown = (code) => {
          watchdog.stop();
          server.close(() => {
            if (registerLease) removeLease(key, pid);
            process.exit(code);
          });
          // Do not hang on keep-alive sockets.
          setTimeout(() => process.exit(code), 1_000).unref();
        };
        server.shutdown = shutdown;

        resolvePromise({
          server,
          url,
          port: actualPort,
          pid,
          reused: false,
          projectRoot,
          editorRoot,
          key,
          watchdog,
          shutdown,
        });
      });

    listen(requestedPort);
  });
}

/* ------------------------------------------------------------------ *
 * CLI
 * ------------------------------------------------------------------ */

function printHelp() {
  output.write(`Local pptd editor host.

Usage:
  node scripts/serve.mjs [options]        start (or reuse) the editor host
  node scripts/serve.mjs --status         show running instances as JSON
  node scripts/serve.mjs --stop           stop a running instance

Options:
  --port <number>        HTTP port (default: ${DEFAULT_PORT}; 0 picks a free port)
  --project <dir>        mount a PPTD project read-only for instant preview
  --open                 open the editor in the default browser
  --idle-timeout <min>   exit after this many idle minutes (default: 120; 0 disables)
  --status               print running instances as JSON and exit
  --stop                 stop the instance for the same editor + project
  -h, --help             show this help

The instance registers itself in a lease file under the OS temp dir, so a second
launch reuses the running URL instead of failing with EADDRINUSE. An open editor
pings the host; when the pings stop, the host exits after the idle timeout.
`);
}

function openBrowser(url) {
  const command = process.platform === "darwin" ? "open" : process.platform === "win32" ? "cmd" : "xdg-open";
  const args = process.platform === "win32" ? ["/c", "start", "", url] : [url];
  const child = spawn(command, args, { detached: true, stdio: "ignore" });
  child.on("error", (error) => output.write(`Could not open the browser: ${error.message}\n`));
  child.unref();
}

function parseServeArguments(args) {
  const options = {
    port: DEFAULT_PORT,
    open: false,
    help: false,
    status: false,
    stop: false,
    project: null,
    idleTimeoutMinutes: idleMinutesFromEnv(),
  };
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--port") {
      const port = Number(args[(index += 1)]);
      if (!Number.isInteger(port) || port < 0 || port > 65_535) {
        throw new Error("--port must be an integer between 0 and 65535 (0 picks a free port)");
      }
      options.port = port;
      continue;
    }
    if (argument === "--project") {
      const project = args[(index += 1)];
      if (!project) throw new Error("--project needs a directory");
      options.project = resolve(project);
      continue;
    }
    if (argument === "--idle-timeout") {
      const minutes = Number(args[(index += 1)]);
      if (!Number.isFinite(minutes) || minutes < 0) {
        throw new Error("--idle-timeout must be a non-negative number of minutes");
      }
      options.idleTimeoutMinutes = minutes;
      continue;
    }
    if (argument === "--open") {
      options.open = true;
      continue;
    }
    if (argument === "--status") {
      options.status = true;
      continue;
    }
    if (argument === "--stop") {
      options.stop = true;
      continue;
    }
    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }
    throw new Error(`unknown argument: ${argument}`);
  }
  return options;
}

async function reportStatus(options) {
  const editorRoot = resolveEditorRoot();
  const entries = options.project
    ? [
        {
          file: leaseFile(leaseKey({ editorRoot, projectRoot: options.project })),
          lease: readLease(leaseKey({ editorRoot, projectRoot: options.project })),
        },
      ].filter((entry) => entry.lease)
    : listLeases();
  const servers = [];
  for (const { file, lease } of entries) {
    const alive = processAlive(lease?.pid);
    const responding = alive && lease?.url ? await httpOk(lease.url) : false;
    servers.push({
      running: Boolean(responding),
      pid: lease?.pid ?? null,
      url: lease?.url ?? null,
      project: lease?.projectRoot ?? null,
      editor: lease?.editorRoot ?? null,
      startedAt: lease?.startedAt ?? null,
      leaseFile: file,
    });
  }
  output.write(`${JSON.stringify({ event: "status", servers }, null, 2)}\n`);
  return servers.some((entry) => entry.running) ? 0 : 1;
}

function stopInstances(options) {
  const editorRoot = resolveEditorRoot();
  const key = options.project ? leaseKey({ editorRoot, projectRoot: options.project }) : null;
  const entries = key
    ? [{ file: leaseFile(key), key, lease: readLease(key) }].filter((entry) => entry.lease)
    : listLeases();
  const stopped = [];
  for (const { key: leaseKeyName, lease } of entries) {
    const pid = lease?.pid;
    if (!processAlive(pid)) {
      removeLease(leaseKeyName, pid);
      stopped.push({ pid, stopped: false, reason: "not running" });
      continue;
    }
    stopped.push({ pid, url: lease?.url, stopped: stopProcess(pid) });
    removeLease(leaseKeyName, pid);
  }
  output.write(`${JSON.stringify({ event: "stop", stopped }, null, 2)}\n`);
  return 0;
}

// Only run the CLI when invoked directly, not when imported by tests.
const invokedDirectly =
  process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
  let options;
  try {
    options = parseServeArguments(process.argv.slice(2));
  } catch (error) {
    output.write(`Error: ${error.message}\n`);
    process.exitCode = 1;
    options = null;
  }

  if (options) {
    if (options.help) {
      printHelp();
    } else if (options.status) {
      reportStatus(options).then((code) => process.exit(code));
    } else if (options.stop) {
      process.exit(stopInstances(options));
    } else {
      startEditorServer({
        port: options.port,
        projectDirectory: options.project,
        idleTimeoutMs: options.idleTimeoutMinutes * 60_000,
      })
        .then(({ url, port, pid, reused, shutdown, server, projectRoot }) => {
          if (reused) {
            output.write(`pptd local editor is already running at ${url}\n`);
          } else {
            output.write(`pptd local editor is running at ${url}\n`);
            output.write(server.projectRoot ? `Read-only project: ${server.projectRoot}\n` : "");
            output.write(
              options.idleTimeoutMinutes > 0
                ? `Open the URL in a Chromium-based browser; the host exits after ${options.idleTimeoutMinutes} idle minutes (or Ctrl+C).\n`
                : "Open the URL in a Chromium-based browser; press Ctrl+C to stop the host.\n",
            );
          }
          if (options.open) openBrowser(url);
          output.write(
            `${JSON.stringify({
              event: reused ? "reuse" : "listening",
              url,
              port,
              pid,
              project: projectRoot ?? null,
              idleTimeoutMinutes: options.idleTimeoutMinutes,
              reused,
            })}\n`,
          );
          // Keep the process referenced so a background launch is not reaped.
          if (shutdown) {
            process.once("SIGINT", () => shutdown(0));
            process.once("SIGTERM", () => shutdown(0));
          }
        })
        .catch((error) => {
          output.write(`Error: ${error.message}\n`);
          process.exitCode = 1;
        });
    }
  }
}
