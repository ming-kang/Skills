#!/usr/bin/env node
/**
 * Browser smoke test for the pptd local editor host.
 *
 * Verifies the two host modes against a real headless Chromium:
 *   1. --project <dir> mounts a deck server-side (no folder picker needed) and
 *      the bridge loads it to deckStatus "ready";
 *   2. the heartbeat endpoint answers, and the editor keeps the host alive.
 *
 * Not part of `npm test` (it needs Playwright's Chromium); run it manually:
 *   node tools/pptd/smoke_editor.mjs [--project <dir>]
 */

import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import readline from "node:readline";

const SKILL_ROOT = resolve(import.meta.dirname, "..", "..", "pptd");
const SERVE_SCRIPT = join(SKILL_ROOT, "scripts", "serve.mjs");

const FIXTURE = `version: v2
title: 冒烟测试文稿
size: [960, 540]
pages:
  - pages/01.page
`;

const FIXTURE_PAGE = `pageType: content
background: {type: solid, color: "#FFFFFF"}
elements:
  - elementId: title
    elementType: text
    bounds: [80, 96, 800, 80]
    content:
      align: [center, middle]
      text: |
        <p><span style="font-size:44px;color:#111827;font-weight:700">挂载预览标题</span></p>
  - elementId: shot
    elementType: image
    bounds: [380, 230, 200, 120]
    src: media/shot.png
    fit: {mode: contain}
`;

/** True for any http(s) URL that is not the local host we started. */
function isExternal(url) {
  try {
    const parsed = new URL(url);
    if (!parsed.protocol.startsWith("http")) return false;
    return parsed.hostname !== "127.0.0.1" && parsed.hostname !== "localhost";
  } catch {
    return false;
  }
}

function makeProject() {
  const root = mkdtempSync(join(tmpdir(), "pptd-smoke-"));
  mkdirSync(join(root, "pages"), { recursive: true });
  mkdirSync(join(root, "media"), { recursive: true });
  writeFileSync(join(root, "deck.pptd"), FIXTURE, "utf-8");
  writeFileSync(join(root, "pages", "01.page"), FIXTURE_PAGE, "utf-8");
  // 1x1 transparent PNG, referenced by the page above.
  writeFileSync(
    join(root, "media", "shot.png"),
    Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==",
      "base64",
    ),
  );
  return root;
}

function startHost(project) {
  const child = spawn(process.execPath, [SERVE_SCRIPT, "--port", "0", "--project", project, "--idle-timeout", "10"], {
    stdio: ["ignore", "pipe", "pipe"],
  });
  return new Promise((resolvePromise, reject) => {
    const timeout = setTimeout(() => reject(new Error("host did not report a URL")), 20_000);
    const onLine = (line) => {
      if (!line.startsWith("{")) return;
      clearTimeout(timeout);
      try {
        resolvePromise({ child, info: JSON.parse(line) });
      } catch (error) {
        reject(error);
      }
    };
    readline.createInterface({ input: child.stdout }).on("line", onLine);
    child.on("exit", (code) => reject(new Error(`host exited early: ${code}`)));
  });
}

async function main() {
  const argument = process.argv[2];
  const project = argument === "--project" ? resolve(process.argv[3]) : makeProject();
  const { chromium } = await import("playwright");
  const { child, info } = await startHost(project);
  const failures = [];

  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const consoleLines = [];
    const requested = [];
    // Anything that reached an origin other than the host is an offline leak.
    const externalResponses = [];
    page.on("console", (message) => consoleLines.push(message.text()));
    page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
    page.on("request", (request) => requested.push(request.url()));
    page.on("response", (response) => {
      if (isExternal(response.url())) externalResponses.push(`${response.status()} ${response.url()}`);
    });

    await page.goto(`${info.url}?ndProject=1`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(
      () => document.documentElement.dataset.deckStatus === "ready",
      undefined,
      { timeout: 90_000 },
    );
    await page.waitForTimeout(2_000);

    const title = await page.locator("#nd-title").textContent();
    if (!title?.includes("冒烟测试文稿") && !title?.includes(project.split(/[\\/]/).pop())) {
      failures.push(`unexpected deck title: ${title}`);
    }
    if (!(await page.locator("#nd-open").isHidden())) {
      failures.push("the folder-picker button should be hidden in project mode");
    }
    const missingImages = consoleLines.filter((line) => line.includes("image not found"));
    if (missingImages.length) {
      failures.push(`image resolution failed: ${missingImages[0]}`);
    }
    // The mounted manifest, page and media must all be fetched through the host.
    for (const fragment of ["/project.json", "/project/deck.pptd", "/project/pages/01.page", "media/shot.png"]) {
      if (!requested.some((url) => url.includes(fragment))) {
        failures.push(`the editor never requested ${fragment}`);
      }
    }

    // The host must answer the heartbeat the bridge sends every 60s.
    const ping = await page.evaluate(() => fetch("./__ping__", { cache: "no-store" }).then((r) => r.status));
    if (ping !== 204) failures.push(`heartbeat returned ${ping}`);

    // The official bundle only mounts if every module loaded. A CSP that is too
    // strict (script-src without `data:`) blocks its loader and leaves a blank
    // page behind a bridge that still reports "ready" — assert the DOM instead.
    const appSize = await page.evaluate(() => document.querySelector("#app")?.innerHTML.length ?? 0);
    if (appSize < 1_000) failures.push(`the editor app did not mount (#app is ${appSize} chars)`);

    // Offline invariant: no CSP violation, and nothing answered from off-host.
    // The fetch/XHR shim cannot see a <script>, an @font-face or a sendBeacon,
    // so the policy is what actually holds the line here.
    const violations = consoleLines.filter((line) => /Content Security Policy/i.test(line));
    if (violations.length) failures.push(`CSP violation: ${violations[0].slice(0, 200)}`);
    if (externalResponses.length) {
      failures.push(`the editor reached an external origin: ${externalResponses.join(", ").slice(0, 300)}`);
    }

    // Fonts must come from the local fonts/ directory, never a remote host.
    const remoteFonts = requested.filter((url) => isExternal(url) && /\.woff2?($|\?)/.test(url));
    if (remoteFonts.length) failures.push(`remote font requested: ${remoteFonts[0]}`);
  } finally {
    await browser.close();
    child.kill();
  }

  if (failures.length) {
    console.error(`FAIL\n${failures.map((line) => `  - ${line}`).join("\n")}`);
    process.exitCode = 1;
    return;
  }
  console.log(`OK  editor loaded the mounted project (${info.url}?ndProject=1)`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
