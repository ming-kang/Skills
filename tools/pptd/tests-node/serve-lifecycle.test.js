import assert from "node:assert/strict";
import { once } from "node:events";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import {
  createEditorServer,
  createIdleWatchdog,
  findProjectManifest,
  removeLease,
  startEditorServer,
} from "../../../pptd/scripts/serve.mjs";

const PROJECT_YAML = `version: v2
title: 托管预览
size: [960, 540]
pages:
  - pages/01.page
`;

const PAGE_YAML = `pageType: content
background: {type: solid, color: "#FFFFFF"}
elements: []
`;

// undici keeps the fetch socket alive for ~3s; closing it explicitly keeps
// these lifecycle tests fast.
async function closeServer(server) {
  if (!server) return;
  server.closeAllConnections?.();
  server.close();
  await once(server, "close");
}

function makeProject() {
  const root = mkdtempSync(join(tmpdir(), "pptd-project-"));
  mkdirSync(join(root, "pages"), { recursive: true });
  mkdirSync(join(root, "media"), { recursive: true });
  writeFileSync(join(root, "deck.pptd"), PROJECT_YAML, "utf-8");
  writeFileSync(join(root, "pages", "01.page"), PAGE_YAML, "utf-8");
  writeFileSync(join(root, "media", "pixel.png"), "not-a-real-png", "utf-8");
  return root;
}

test("finds a manifest at the project top level and deeper", () => {
  const root = makeProject();
  try {
    assert.equal(findProjectManifest(root), "deck.pptd");
    rmSync(join(root, "deck.pptd"));
    mkdirSync(join(root, "nested"), { recursive: true });
    writeFileSync(join(root, "nested", "inner.pptd"), PROJECT_YAML, "utf-8");
    assert.equal(findProjectManifest(root), "nested/inner.pptd");
    assert.equal(findProjectManifest(join(root, "pages")), null);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("mounts a project read-only and blocks path escapes", async () => {
  const project = makeProject();
  const server = createEditorServer({ projectDirectory: project });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const manifest = await fetch(`${base}/project.json`);
    assert.equal(manifest.status, 200);
    assert.deepEqual(await manifest.json(), { manifest: "deck.pptd", title: "托管预览" });

    const page = await fetch(`${base}/project/pages/01.page`);
    assert.equal(page.status, 200);
    assert.match(page.headers.get("content-type"), /^text\/yaml/);
    assert.match(await page.text(), /pageType: content/);

    const media = await fetch(`${base}/project/media/pixel.png`);
    assert.equal(media.status, 200);

    // The editor assets are still served next to the mounted project.
    const index = await fetch(`${base}/`);
    assert.equal(index.status, 200);
    assert.match(await index.text(), /local-bridge\.js/);

    for (const escape of ["/project/../deck.pptd", "/project/..%2fdeck.pptd", "/project//etc/passwd"]) {
      const response = await fetch(`${base}${escape}`);
      assert.ok(response.status === 403 || response.status === 404, `${escape} → ${response.status}`);
    }
  } finally {
    await closeServer(server);
    rmSync(project, { recursive: true, force: true });
  }
});

test("answers a heartbeat ping so the idle watchdog stays quiet", async () => {
  const server = createEditorServer();
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  try {
    const response = await fetch(`http://127.0.0.1:${server.address().port}/__ping__`);
    assert.equal(response.status, 204);
  } finally {
    server.close();
    await once(server, "close");
  }
});

test("idle watchdog fires only after the idle window without a heartbeat", () => {
  let clock = 0;
  const activity = { lastActivityAt: 0 };
  let fired = 0;
  const watchdog = createIdleWatchdog({
    idleMs: 1_000,
    activity,
    now: () => clock,
    intervalMs: 10,
    onIdle: () => (fired += 1),
  });

  clock = 500;
  assert.equal(watchdog.isIdle(), false);
  activity.lastActivityAt = 900;
  clock = 1_100;
  assert.equal(watchdog.isIdle(), false, "a recent ping resets the idle window");
  clock = 2_000;
  assert.equal(watchdog.isIdle(), true);
  watchdog.stop();

  const disabled = createIdleWatchdog({ idleMs: 0, activity, now: () => 10_000_000 });
  assert.equal(disabled.isIdle(), false);
  disabled.stop();
});

test("reuses a live lease instead of failing with EADDRINUSE", async () => {
  const first = await startEditorServer({ port: 0, registerLease: true });
  try {
    assert.match(first.url, /^http:\/\/127\.0\.0\.1:\d+\/$/);
    const second = await startEditorServer({ port: 0, registerLease: true });
    try {
      assert.equal(second.reused, true, "a live lease for the same editor + project is reused");
      assert.equal(second.url, first.url);
      assert.equal(second.server, null);
      const response = await fetch(second.url);
      assert.equal(response.status, 200);
    } finally {
      second.server?.close();
    }
  } finally {
    await closeServer(first.server);
    removeLease(first.key, first.pid);
  }
});

test("drifts to a free port when the preferred one is taken", async () => {
  const blocker = createEditorServer();
  blocker.listen(0, "127.0.0.1");
  await once(blocker, "listening");
  const takenPort = blocker.address().port;
  try {
    const started = await startEditorServer({ port: takenPort, registerLease: false });
    try {
      assert.notEqual(started.port, takenPort, "EADDRINUSE must not kill the host");
      const response = await fetch(started.url);
      assert.equal(response.status, 200);
    } finally {
      await closeServer(started.server);
    }
  } finally {
    await closeServer(blocker);
  }
});
