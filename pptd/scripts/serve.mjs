#!/usr/bin/env node
/**
 * Local editor host for the pptd skill: serves the offline neo-ppt mirror so
 * a Chromium-based browser can open, edit and export PPTD projects.
 *
 * Usage:
 *   node scripts/serve.mjs [--port 55173] [--open]
 *
 * Env:
 *   PPTD_EDITOR_DIR        override the editor directory (default: assets/editor)
 *                           (legacy alias OPEN_KIMI_PPT_EDITOR still honored)
 */

import { spawn } from "node:child_process";
import { createReadStream, statSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, extname, resolve, sep } from "node:path";
import { stdin as input, stdout as output } from "node:process";
import { fileURLToPath } from "node:url";

const SKILL_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_PORT = 55_173;

const contentTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".wasm", "application/wasm"],
]);

function respond(response, statusCode, message) {
  response.writeHead(statusCode, {
    "Content-Type": "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  response.end(message);
}

export function createEditorServer({ editorDirectory = resolve(SKILL_ROOT, "assets", "editor") } = {}) {
  const root = resolve(editorDirectory);
  const rootPrefix = `${root}${sep}`;

  return createServer((request, response) => {
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

    if (pathname.endsWith("/")) pathname += "index.html";
    const filePath = resolve(root, `.${pathname}`);
    if (filePath !== root && !filePath.startsWith(rootPrefix)) {
      respond(response, 403, "Forbidden");
      return;
    }

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
  });
}

export function startEditorServer({
  host = "127.0.0.1",
  port = DEFAULT_PORT,
  editorDirectory,
} = {}) {
  const directory = editorDirectory ?? process.env.PPTD_EDITOR_DIR ?? process.env.OPEN_KIMI_PPT_EDITOR;
  const server = createEditorServer(
    directory ? { editorDirectory: resolve(directory) } : {},
  );

  return new Promise((resolvePromise, reject) => {
    const onError = (error) => reject(error);
    server.once("error", onError);
    server.listen(port, host, () => {
      server.off("error", onError);
      const address = server.address();
      const actualPort = typeof address === "object" && address ? address.port : port;
      resolvePromise({ server, url: `http://${host}:${actualPort}/` });
    });
  });
}

function printHelp() {
  output.write(`Local pptd editor host.

Usage:
  node scripts/serve.mjs [options]

Options:
  --port <number>  HTTP port (default: ${DEFAULT_PORT})
  --open           Open the editor in the default browser
  -h, --help       Show this help
`);
}

function openBrowser(url) {
  const command = process.platform === "darwin" ? "open" : process.platform === "win32" ? "cmd" : "xdg-open";
  const args = process.platform === "win32" ? ["/c", "start", "", url] : [url];
  const child = spawn(command, args, { detached: true, stdio: "ignore" });
  child.on("error", (error) => console.warn(`Could not open the browser: ${error.message}`));
  child.unref();
}

function parseServeArguments(args) {
  const options = { port: DEFAULT_PORT, open: false, help: false };
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--port") {
      const port = Number(args[(index += 1)]);
      if (!Number.isInteger(port) || port < 1 || port > 65_535) {
        throw new Error("--port must be an integer between 1 and 65535");
      }
      options.port = port;
      continue;
    }
    if (argument === "--open") {
      options.open = true;
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

// Only run the server when invoked directly, not when imported by tests.
const invokedDirectly =
  process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
  const options = parseServeArguments(process.argv.slice(2));
  if (options.help) {
    printHelp();
  } else {
    startEditorServer({ port: options.port }).then(({ server, url }) => {
      console.log(`pptd local editor is running at ${url}`);
      console.log("Press Ctrl+C to stop the server.");
      if (options.open) openBrowser(url);
      const shutdown = () => server.close(() => process.exit(0));
      process.once("SIGINT", shutdown);
      process.once("SIGTERM", shutdown);
    }).catch((error) => {
      console.error(`Error: ${error.message}`);
      process.exitCode = 1;
    });
  }
}
