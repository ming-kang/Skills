/**
 * The one test that opens the real editor in a real browser.
 *
 * Every other suite here exercises the host and the exporters, which is how a
 * CSP that blanked the editor could sit behind 57 green tests: the bridge still
 * reported progress, so nothing noticed the official bundle had never mounted.
 * These assertions are deliberately about the *page*, not about the bridge's
 * opinion of itself.
 *
 * Environment-dependent, like the browser suites in tests/: it skips itself
 * when Playwright's Chromium is not installed.
 */
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { startEditorServer } from "../../../pptd/scripts/serve.mjs";

const PROJECT_YAML = `version: v2
title: 浏览器冒烟
size: [960, 540]
pages:
  - pages/01.page
`;

const PAGE_YAML = `pageType: content
background: {type: solid, color: "#FFFFFF"}
elements:
  - elementId: title
    elementType: text
    bounds: [80, 96, 800, 80]
    content:
      align: [center, middle]
      text: |
        <p><span style="font-size:44px">浏览器冒烟</span></p>
`;

/** Playwright is a repo-root devDependency; treat a missing browser as "skip". */
async function loadChromium() {
  try {
    const { chromium } = await import("playwright");
    // executablePath() throws when the browser was never downloaded.
    chromium.executablePath();
    return chromium;
  } catch {
    return null;
  }
}

function makeProject() {
  const root = mkdtempSync(join(tmpdir(), "pptd-browser-"));
  mkdirSync(join(root, "pages"), { recursive: true });
  writeFileSync(join(root, "deck.pptd"), PROJECT_YAML, "utf-8");
  writeFileSync(join(root, "pages", "01.page"), PAGE_YAML, "utf-8");
  return root;
}

function isExternal(url) {
  try {
    const parsed = new URL(url);
    if (!parsed.protocol.startsWith("http")) return false;
    return parsed.hostname !== "127.0.0.1" && parsed.hostname !== "localhost";
  } catch {
    return false;
  }
}

test("the editor mounts, stays offline, and loads the mounted deck", async (t) => {
  const chromium = await loadChromium();
  if (!chromium) {
    t.skip("Playwright's Chromium is not installed");
    return;
  }

  const project = makeProject();
  // No lease: this test must get its own server, never reuse (or register) the
  // host a developer happens to have running. idleTimeoutMs 0 disables the
  // watchdog so nothing keeps the test process alive.
  const { server, url } = await startEditorServer({
    port: 0,
    projectDirectory: project,
    idleTimeoutMs: 0,
    registerLease: false,
  });
  const browser = await chromium.launch();
  const cspViolations = [];
  const externalResponses = [];
  const remoteFonts = [];

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.on("console", (message) => {
      if (/Content Security Policy/i.test(message.text())) cspViolations.push(message.text());
    });
    page.on("response", (response) => {
      if (isExternal(response.url())) externalResponses.push(`${response.status()} ${response.url()}`);
    });
    page.on("request", (request) => {
      if (isExternal(request.url()) && /\.woff2?($|\?)/.test(request.url())) remoteFonts.push(request.url());
    });

    await page.goto(`${url}?ndProject=1`, { waitUntil: "domcontentloaded" });
    // Wait for a *terminal* status, not for success: the bridge's handshake
    // watchdog publishes "failed" after 8s, so a broken editor reports itself
    // in seconds with a reason attached instead of burning a long timeout on
    // an unhelpful "waitForFunction exceeded".
    await page.waitForFunction(
      () => ["ready", "failed", "error"].includes(document.documentElement.dataset.deckStatus),
      undefined,
      { timeout: 60_000 },
    );

    const status = await page.evaluate(() => document.documentElement.dataset.deckStatus);
    const pageErrors = await page.evaluate(() => window.__ND_ERRORS__ ?? []);
    assert.equal(status, "ready", `deck status is "${status}" — page errors: ${pageErrors.join(" | ") || "none"}`);

    // The bundle only mounts if every module loaded. The bridge cannot see this:
    // it reports its own progress, not the editor's.
    const appSize = await page.evaluate(() => document.querySelector("#app")?.innerHTML.length ?? 0);
    assert.ok(appSize > 1_000, `the editor app did not mount (#app is ${appSize} chars)`);

    // Offline invariant. The fetch/XHR shim in index.html cannot see a <script>,
    // an @font-face or a sendBeacon, so the CSP is what actually holds this.
    assert.deepEqual(cspViolations, [], "the page reported CSP violations");
    assert.deepEqual(externalResponses, [], "the editor reached an external origin");
    assert.deepEqual(remoteFonts, [], "the editor requested a remote font");

    const title = await page.locator("#nd-title").textContent();
    assert.match(title ?? "", /浏览器冒烟/);
  } finally {
    await browser.close();
    server.closeAllConnections?.();
    await new Promise((resolve) => server.close(resolve));
    rmSync(project, { recursive: true, force: true });
  }
});
