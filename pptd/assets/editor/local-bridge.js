/**
 * NeoDeck Local bridge — no iframe, no cloud.
 * Official neo-ppt talks to us via window.__NEODECK_CONNECT__ instead of Penpal parent.
 */
import {
  basename,
  dirname,
  extractPagePaths,
  joinDeckPath,
  normalizeRelativePath,
  titleFromManifest,
} from "./lib.js";

const state = {
  editor: null, // methods exposed by official editor (setPPTD, ...)
  directoryHandle: null,
  fileIndex: new Map(),
  memoryFiles: new Map(),
  imageMap: Object.create(null), // path → data URL (export host / payload)
  manifestPath: "",
  manifestDirectory: "",
  manifestContent: "",
  deckTitle: "未打开文稿",
  imageCache: new Map(),
  readOnly: false,
  ready: false,
  exportMode: false,
  // Serve-host project mode (?ndProject=1): the deck is mounted read-only by
  // `node scripts/serve.mjs --project <dir>`, so no folder picker is needed.
  serverProject: false,
  projectBase: "",
  // Headless export host: media is served from the host instead of being
  // base64-inlined into payload.json (see open_local_editor in export_pptx.py).
  mediaBase: "",
};

/** Fetch a project file and cache it as a data URL; caches misses as "". */
// In-flight project/media fetches, so a host can wait until the editor has
// everything it needs before driving it (see wait_for_editor_media).
const pendingProjectFetches = { count: 0 };
window.__NEODECK_PENDING_PROJECT_FETCHES__ = () => pendingProjectFetches.count;

/**
 * The editor sometimes asks for an asset as "/media/x.png"; both the mounted
 * project and the export host expect a project-relative path. This is the
 * URL-side (never throws) variant — index keys go through the validating
 * normalizeRelativePath instead.
 */
function projectRelativePath(path) {
  return String(path)
    .replace(/^file:\/\/+/, "")
    .replace(/^\.\//, "")
    .replace(/^\/+/, "")
    .replaceAll("\\", "/");
}

async function dataUrlFromBase(baseUrl, path) {
  const cacheKey = `${baseUrl}${projectRelativePath(path)}`;
  if (state.imageCache.has(cacheKey)) return state.imageCache.get(cacheKey);
  let url = "";
  pendingProjectFetches.count += 1;
  try {
    const response = await fetch(`${baseUrl}${projectRelativePath(path)}`, { cache: "no-store" });
    if (response.ok) {
      const blob = await response.blob();
      url = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
      });
    }
  } catch (e) {
    console.warn("[neodeck] project file read failed", path, e);
  } finally {
    pendingProjectFetches.count -= 1;
  }
  state.imageCache.set(cacheKey, url);
  return url;
}

// Keep the host's idle watchdog happy while this page stays open: an SPA makes
// almost no requests after load, so request traffic is not a liveness signal.
function startHeartbeat() {
  // Export mode is a short-lived headless run driven by a Python host that has
  // no idle watchdog; pinging it would just add noise.
  if (state.exportMode) return;
  setInterval(() => {
    fetch("./__ping__", { cache: "no-store" }).catch(() => {});
  }, 60_000);
}
startHeartbeat();

const $ = (sel) => document.querySelector(sel);
const exportMode =
  new URL(location.href).searchParams.get("ndExport") === "1" ||
  new URL(location.href).searchParams.get("export") === "1";
state.exportMode = exportMode;
state.serverProject = new URL(location.href).searchParams.get("ndProject") === "1";
state.projectBase = state.serverProject ? "./project/" : "";
// Always publish a status, in every mode: this dataset is the only thing an
// automated host can observe, and leaving it undefined outside export mode is
// what let a blank editor look indistinguishable from a slow one.
document.documentElement.dataset.deckStatus = "booting";
if (exportMode) {
  document.documentElement.classList.add("nd-export-mode");
}

function toast(msg, kind = "info") {
  const el = $("#nd-toast");
  if (!el) return;
  el.hidden = false;
  el.dataset.kind = kind;
  el.textContent = msg;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => {
    el.hidden = true;
  }, 3200);
}

function setStatus(text) {
  const el = $("#nd-status");
  if (el) el.textContent = text;
}

function setTitle(text) {
  state.deckTitle = text;
  const el = $("#nd-title");
  if (el) el.textContent = text;
}

async function indexDirectory(directoryHandle) {
  const index = new Map();
  async function walk(handle, prefix = "") {
    for await (const [name, entry] of handle.entries()) {
      if (name === ".DS_Store") continue;
      const path = prefix ? `${prefix}/${name}` : name;
      if (entry.kind === "directory") await walk(entry, path);
      else index.set(normalizeRelativePath(path), entry);
    }
  }
  await walk(directoryHandle);
  return index;
}

function indexFallbackFiles(fileList) {
  const index = new Map();
  const files = [...fileList];
  const firstPath = files[0]?.webkitRelativePath || files[0]?.name || "";
  const rootName = firstPath.includes("/") ? firstPath.split("/")[0] : "";
  for (const file of files) {
    let path = file.webkitRelativePath || file.name;
    if (rootName && path.startsWith(`${rootName}/`)) path = path.slice(rootName.length + 1);
    index.set(normalizeRelativePath(path), { kind: "file", getFile: async () => file });
  }
  return index;
}

async function textFromIndexed(path) {
  const key = normalizeRelativePath(path);
  if (state.memoryFiles.has(key)) return state.memoryFiles.get(key);
  const entry = state.fileIndex.get(key);
  if (!entry) throw new Error(`找不到文件：${path}`);
  return (await entry.getFile()).text();
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

/** Common media layouts decks use, most specific first. */
const IMAGE_LAYOUT_DIRECTORIES = ["media", "assets", "images"];

function lookupImageMap(path) {
  if (!path || !state.imageMap) return "";
  if (state.imageMap[path]) return state.imageMap[path];
  // The payload's keys are the deck's own src strings; the editor may ask
  // with a different spelling ("media/x.png" vs "/media/x.png"). Accept a
  // path-suffix match, never a bare-basename match — that would let any a.png
  // satisfy a request for b/a.png.
  const keys = Object.keys(state.imageMap);
  const hit = keys.find((key) => path.endsWith(`/${key}`) || key.endsWith(`/${path}`));
  return hit ? state.imageMap[hit] : "";
}

/**
 * Where an image reference may live inside the deck's own files, most
 * specific first. The last step is the only fuzzy one and is labeled as such:
 * any indexed file whose path ends with the requested path, which covers
 * decks that nest their media one level deeper than the manifest says.
 */
function imageCandidates(path) {
  const candidates = [];
  const add = (p) => {
    if (p && !candidates.includes(p)) candidates.push(p);
  };
  add(path);
  if (state.manifestDirectory) {
    try {
      add(joinDeckPath(state.manifestDirectory, path));
    } catch {
      /* ignore */
    }
  }
  const base = path.split("/").pop();
  if (base) {
    for (const directory of IMAGE_LAYOUT_DIRECTORIES) {
      add(`${directory}/${base}`);
      if (state.manifestDirectory) {
        try {
          add(joinDeckPath(state.manifestDirectory, `${directory}/${base}`));
        } catch {
          /* ignore */
        }
      }
    }
  }
  for (const key of state.fileIndex.keys()) {
    if (key.endsWith(`/${path}`)) add(key);
  }
  return candidates;
}

/** Read the first candidate that exists in the deck's files, as a data URL. */
async function readIndexedImage(candidates) {
  for (const candidate of candidates) {
    if (!state.fileIndex.has(candidate) && !state.memoryFiles.has(candidate)) continue;
    if (!state.imageCache.has(candidate)) {
      // memoryFiles holds text (manifests/pages), never image bytes.
      if (!state.fileIndex.has(candidate)) continue;
      try {
        const file = await state.fileIndex.get(candidate).getFile();
        state.imageCache.set(candidate, await fileToDataUrl(file));
      } catch (e) {
        console.warn("[neodeck] image read failed", candidate, e);
        continue;
      }
    }
    const url = state.imageCache.get(candidate);
    if (url) return url;
  }
  return "";
}

/**
 * Resolve an image reference to something the editor can render: a named
 * fallback chain, most specific first. Each step is either a host fetch or a
 * deck-file lookup, and a total miss reports the exact candidates that were
 * tried — no interleaved fuzzy scoring to reason about.
 */
async function resolveImage(requestedPath) {
  if (requestedPath == null || requestedPath === "") return "";
  const raw = String(requestedPath);
  if (/^(?:data:image\/|https?:\/\/|blob:)/i.test(raw)) return raw;

  let path;
  try {
    path = normalizeRelativePath(raw.replace(/^file:\/\/+/, "").replace(/^\.\//, ""));
  } catch {
    path = raw.replace(/^file:\/\/+/, "").replace(/^\.\//, "").replaceAll("\\", "/");
  }

  // 1. embedded payload imageMap (only populated in embed_media mode).
  const mapped = lookupImageMap(path);
  if (mapped) return mapped;

  // 2. host-served media: the mounted project (preview) and the export
  //    host's media mount. The host only sets mediaBase when it can serve
  //    the project directory.
  if (state.serverProject) {
    const url = await dataUrlFromBase(state.projectBase, path);
    if (url) return url;
  }
  if (state.mediaBase) {
    const url = await dataUrlFromBase(state.mediaBase, path);
    if (url) return url;
  }

  // 3. the deck's own files.
  const candidates = imageCandidates(path);
  const url = await readIndexedImage(candidates);
  if (url) return url;

  console.warn("[neodeck] image not found", requestedPath, "tried", candidates.slice(0, 8));
  return "";
}

async function getImages(payload = {}) {
  // Official contract: { chatId, filePath: string[] } -> string[] (data URLs / public URLs)
  let paths = payload?.filePath;
  if (paths == null) paths = [];
  if (!Array.isArray(paths)) paths = [paths];
  const out = [];
  for (const p of paths) {
    try {
      out.push(await resolveImage(p));
    } catch (e) {
      console.warn("[neodeck] getImages item failed", p, e);
      out.push("");
    }
  }
  return out;
}

async function writeIndexedFile(path, content) {
  if (state.readOnly || !state.directoryHandle) {
    state.memoryFiles.set(path, content);
    return;
  }
  const parts = path.split("/");
  let dir = state.directoryHandle;
  for (let i = 0; i < parts.length - 1; i++) {
    dir = await dir.getDirectoryHandle(parts[i], { create: true });
  }
  const handle = await dir.getFileHandle(parts[parts.length - 1], { create: true });
  const writable = await handle.createWritable();
  await writable.write(content);
  await writable.close();
  state.fileIndex.set(path, handle);
  state.memoryFiles.set(path, content);
}

async function onSave(payload) {
  const changes = payload?.changes || payload?.files || [];
  const list = Array.isArray(changes) ? changes : [];
  setStatus("正在保存…");
  try {
    for (const change of list) {
      if (!change?.path) continue;
      const path = normalizeRelativePath(change.path);
      if (!/\.(?:pptd|page)$/i.test(path)) continue;
      await writeIndexedFile(path, change.content ?? "");
    }
    setStatus(state.readOnly ? "只读 · 已存内存" : "已保存到本地");
  } catch (e) {
    setStatus("保存失败");
    toast(`保存失败：${e.message || e}`, "error");
    throw e;
  }
}

// The official bundle is expected to call __NEODECK_CONNECT__ once it mounts.
// If it never does, this bridge would otherwise sit on "等待编辑器…" forever —
// the exact symptom of a CSP that blocks the bundle's module loader. Time the
// handshake out and say what actually went wrong instead.
// A healthy load reaches deckStatus "ready" in ~300ms against the local host
// (measured on a cold browser), so this is a ~25x margin: it will not fire on a
// slow machine, only on an editor that is genuinely never coming.
const HANDSHAKE_TIMEOUT_MS = 8000;
let handshakeWatchdog = setTimeout(() => {
  if (state.ready) return;
  document.documentElement.dataset.deckStatus = "failed";
  const [firstError] = window.__ND_ERRORS__ ?? [];
  setStatus("编辑器内核未加载");
  const detail = firstError ? `：${firstError}` : "（无 JS 错误，检查编辑器资源是否完整）";
  console.error(`[neodeck] editor never connected within ${HANDSHAKE_TIMEOUT_MS}ms${detail}`);
  toast(`编辑器内核未加载${detail}`, "error");
}, HANDSHAKE_TIMEOUT_MS);

/** Called by patched official editor instead of Penpal connect */
window.__NEODECK_CONNECT__ = function neoDeckConnect(options) {
  clearTimeout(handshakeWatchdog);
  const methods = options?.methods;
  if (!methods || typeof methods !== "object") {
    // A half-connected editor is worse than none: it would report ready and
    // then fail on the first setPPTD. Treat it as a failed handshake.
    document.documentElement.dataset.deckStatus = "failed";
    setStatus("编辑器握手异常");
    console.error("[neodeck] __NEODECK_CONNECT__ called without methods", options);
    toast("编辑器握手异常：未提供接口", "error");
    const failure = Promise.reject(new Error("no editor methods"));
    failure.catch(() => {}); // the caller may never attach a handler
    return { promise: failure, destroy() {} };
  }
  state.editor = methods;
  state.ready = true;
  setStatus("编辑器就绪");
  // Force light chrome immediately (official default is system → OS dark FOUC).
  Promise.resolve(
    methods.setSlideConfig?.({ editable: true, locale: "zh-CN", theme: "light" }),
  ).catch((e) => console.warn("[neodeck] setSlideConfig", e));
  // host methods the editor will call via connection.promise
  const host = {
    close() {
      toast("本地模式无需关闭");
    },
    reenter() {},
    async toggleFullScreen(want) {
      try {
        const el = document.documentElement;
        const isFs = Boolean(document.fullscreenElement);
        if (want === true || (want !== false && !isFs)) {
          if (!isFs && el.requestFullscreen) await el.requestFullscreen();
        } else if (want === false || isFs) {
          if (isFs && document.exitFullscreen) await document.exitFullscreen();
        }
      } catch (e) {
        console.warn("[neodeck] fullscreen", e);
      }
      return Boolean(document.fullscreenElement);
    },
    showFeedback() {},
    sendPrompt() {
      toast("本地模式已禁用 AI", "warning");
    },
    showMessage(payload) {
      const message = typeof payload === "string" ? payload : payload?.message || payload?.content;
      if (message) toast(String(message));
    },
    hideMessage() {},
    onSave,
    getImages,
    setAnnotationMode() {},
    setAnnotationCurrentPage() {},
    upsertAnnotation() {},
    removeAnnotation() {},
    clearAnnotations() {},
  };

  if (state.exportMode) {
    loadExportPayload().catch((error) => {
      console.error("[neodeck] export payload failed", error);
      document.documentElement.dataset.deckStatus = "error";
      window.exportHostError = String(error?.stack || error);
      setStatus("导出载荷加载失败");
    });
  } else if (state.serverProject) {
    loadProjectFromServer().catch((error) => {
      console.error("[neodeck] server project failed", error);
      document.documentElement.dataset.deckStatus = "error";
      setStatus("项目载入失败");
      toast(`项目载入失败：${error.message || error}`, "error");
    });
  } else {
    // Auto-open demo if nothing loaded after a beat
    setTimeout(() => {
      if (!state.manifestPath) openDemo().catch((e) => console.error(e));
    }, 400);
  }

  return {
    promise: Promise.resolve(host),
    destroy() {
      state.editor = null;
      state.ready = false;
    },
  };
};

/** Serve-host project mode: load the mounted deck from ./project/ (read-only). */
/** Clear every per-deck field. Every load path starts here, so a new deck can never inherit the previous one's files, images or media mount. */
function resetDeckState() {
  state.directoryHandle = null;
  state.readOnly = false;
  state.fileIndex = new Map();
  state.memoryFiles = new Map();
  state.imageCache = new Map();
  state.imageMap = Object.create(null);
  state.mediaBase = "";
}

/**
 * Hand a fully loaded deck to the editor core.
 *
 * The single place that decides how a deck becomes visible: all three load
 * paths (mounted project, export payload, folder/upload/demo) go through it,
 * so the manifest bookkeeping, the light-theme forcing and the setPPTD
 * contract exist once instead of three times.
 */
async function presentDeck({
  id,
  title,
  pptdContent,
  pages,
  pptdPath,
  readOnly = false,
  editable = true,
  statusText,
}) {
  state.manifestPath = pptdPath;
  state.manifestDirectory = dirname(pptdPath);
  state.manifestContent = pptdContent;
  state.readOnly = readOnly;
  setTitle(title);
  if (statusText) setStatus(statusText);
  // Force light chrome immediately (official default is system → OS dark FOUC).
  await state.editor.setSlideConfig?.({
    editable,
    locale: "zh-CN",
    theme: "light",
    ...(id ? { slideId: id } : {}),
  });
  // isCreate:true leaves the official UI in a "generating / loading" state and
  // disables export / present until generate_end — use false for local opens.
  await state.editor.setPPTD(id ?? `local-${Date.now()}`, {
    pptdContent,
    pages,
    basePath: "",
    pptdPath,
    isCreate: false,
  });
  await state.editor.setEditable?.(editable);
}

async function loadProjectFromServer() {
  document.documentElement.dataset.deckStatus = "loading";
  setStatus("载入本地项目…");
  const info = await fetch("./project.json", { cache: "no-store" }).then((response) => {
    if (!response.ok) throw new Error(`project.json HTTP ${response.status}`);
    return response.json();
  });
  if (!state.editor?.setPPTD) throw new Error("编辑器尚未就绪");

  const manifestPath = info.manifest;
  if (!manifestPath) throw new Error("挂载目录中没有 .pptd 清单");
  const projectUrl = (relative) => `${state.projectBase}${projectRelativePath(relative)}`;

  const manifestContent = await fetch(projectUrl(manifestPath), { cache: "no-store" }).then((response) => {
    if (!response.ok) throw new Error(`manifest HTTP ${response.status}`);
    return response.text();
  });

  const manifestDirectory = dirname(manifestPath);
  const pagePaths = extractPagePaths(manifestContent);
  const pages = [];
  const missing = [];
  for (const pagePath of pagePaths.slice(0, 500)) {
    try {
      const content = await fetch(projectUrl(joinDeckPath(manifestDirectory, pagePath)), {
        cache: "no-store",
      }).then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.text();
      });
      pages.push({ path: pagePath, content });
    } catch {
      missing.push(pagePath);
    }
  }
  if (missing.length) throw new Error(`缺少页面：${missing.slice(0, 5).join(", ")}`);

  resetDeckState();
  const title = info.title || titleFromManifest(manifestContent, basename(manifestPath));
  await presentDeck({
    id: null,
    title,
    pptdContent: manifestContent,
    pages,
    pptdPath: manifestPath,
    readOnly: true,
    statusText: `${title} · 预览（只读）`,
  });
  toast(`已载入「${title}」· ${pages.length} 页 · 挂载目录只读`);
  document.documentElement.dataset.deckStatus = "ready";
}

/**
 * Headless / agent-browser export: load deck from ./payload.json (no folder picker).
 *
 * The payload shape is owned by `build_payload()` in scripts/pptd_deck.py —
 * its docstring is the single definition of the contract; keep this reader
 * and that writer in sync through it, not through copies of the field list.
 */
async function loadExportPayload() {
  document.documentElement.dataset.deckStatus = "loading";
  setStatus("载入导出载荷…");
  const response = await fetch("./payload.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`payload HTTP ${response.status}`);
  const payload = await response.json();
  if (!state.editor?.setPPTD) throw new Error("编辑器尚未就绪");

  resetDeckState();
  for (const [key, value] of Object.entries(payload.imageMap || {})) {
    try {
      state.imageMap[normalizeRelativePath(key)] = value;
    } catch {
      state.imageMap[String(key).replaceAll("\\", "/")] = value;
    }
    state.imageCache.set(key, value);
  }
  // Media the host serves instead of inlining into the payload. Empty when the
  // host could not serve the project directory, in which case imageMap is the
  // only source and resolveImage falls through to it.
  state.mediaBase = typeof payload.mediaBase === "string" ? payload.mediaBase : "";

  const manifestPath = payload.manifestPath || "deck.pptd";
  const manifestContent = payload.manifestContent || "";
  state.memoryFiles.set(normalizeRelativePath(manifestPath), manifestContent);
  for (const page of payload.pages || []) {
    if (!page?.path) continue;
    state.memoryFiles.set(normalizeRelativePath(page.path), page.content ?? "");
  }

  const title = payload.title || titleFromManifest(manifestContent, basename(manifestPath));
  await presentDeck({
    id: payload.id,
    title,
    pptdContent: manifestContent,
    pages: payload.pages || [],
    pptdPath: manifestPath,
    readOnly: true,
    statusText: `导出模式 · ${title}`,
  });

  window.exportRemote = state.editor;
  try {
    window.exportSlideStatus = await state.editor.getSlideStatus?.();
  } catch {
    window.exportSlideStatus = null;
  }
  document.documentElement.dataset.deckStatus = "ready";
}

async function loadDeckFromIndex(manifestPath, sourceLabel, options = {}) {
  const readOnly = Boolean(options.readOnly);
  const editable = options.editable !== false;
  if (!state.editor?.setPPTD) throw new Error("编辑器尚未就绪");
  const manifestContent = await textFromIndexed(manifestPath);
  const pagePaths = extractPagePaths(manifestContent);
  const pages = [];
  const missing = [];
  const manifestDirectory = dirname(manifestPath);
  for (const pagePath of pagePaths.slice(0, 500)) {
    const indexedPath = joinDeckPath(manifestDirectory, pagePath);
    try {
      pages.push({ path: pagePath, content: await textFromIndexed(indexedPath) });
    } catch {
      missing.push(pagePath);
    }
  }
  if (missing.length) throw new Error(`缺少页面：${missing.slice(0, 5).join(", ")}`);
  const title = titleFromManifest(manifestContent, basename(manifestPath));
  await presentDeck({
    id: null,
    title,
    pptdContent: manifestContent,
    pages,
    pptdPath: manifestPath,
    readOnly,
    editable,
    statusText: sourceLabel,
  });
  toast(`已载入「${title}」· ${pages.length} 页`);
}

async function openDemo() {
  resetDeckState();
  const manifest = JSON.stringify({
    version: "v2",
    title: "PPT Design",
    size: [960, 540],
    pages: ["pages/01.page"],
  });
  const page1 = JSON.stringify({
    pageType: "content",
    background: { color: "#f7f8fc" },
    elements: [
      {
        elementId: "title",
        elementType: "text",
        bounds: [80, 96, 800, 80],
        content: {
          text: '<p><span style="font-size:44px;color:#171923;font-weight:700">PPT Design</span></p>',
        },
      },
      {
        elementId: "sub",
        elementType: "text",
        bounds: [80, 192, 800, 50],
        content: {
          text: '<p><span style="font-size:18px;color:#667085">点击左上角「打开项目文件夹」，选择包含 .pptd 清单与 pages/ 的项目目录</span></p>',
        },
      },
      {
        elementId: "steps",
        elementType: "text",
        bounds: [80, 268, 800, 190],
        content: {
          text: '<p><span style="font-size:20px;color:#3a4251;line-height:2">①  打开项目文件夹（.pptd + pages/ + media/）</span></p><p><span style="font-size:20px;color:#3a4251;line-height:2">②  在画布中编辑页面、元素与样式</span></p><p><span style="font-size:20px;color:#3a4251;line-height:2">③  导出 PPTX 或页面图片</span></p>',
        },
      },
    ],
  });
  state.memoryFiles.set("presentation.pptd", manifest);
  state.memoryFiles.set("pages/01.page", page1);
  // synthetic index for demo
  for (const [path, content] of state.memoryFiles) {
    state.fileIndex.set(path, {
      kind: "file",
      getFile: async () => new File([content], basename(path), { type: "text/plain" }),
    });
  }
  // Editable in UI; readOnly only means "don't write to disk" (saves stay in memory).
  await loadDeckFromIndex("presentation.pptd", "内置示例 · 内存", {
    readOnly: true,
    editable: true,
  });
}

async function openDirectoryHandle(handle) {
  setStatus("扫描文件夹…");
  resetDeckState();
  state.directoryHandle = handle;
  state.fileIndex = await indexDirectory(handle);
  const manifests = [...state.fileIndex.keys()].filter((p) => p.toLowerCase().endsWith(".pptd"));
  if (!manifests.length) throw new Error("文件夹内没有 .pptd");
  const manifestPath = manifests.length === 1 ? manifests[0] : manifests.sort()[0];
  await loadDeckFromIndex(manifestPath, `${handle.name} · 可写`, {
    readOnly: false,
    editable: true,
  });
}

async function openFallbackFiles(fileList) {
  setStatus("读取上传…");
  resetDeckState();
  state.readOnly = true;
  state.fileIndex = indexFallbackFiles(fileList);
  const manifests = [...state.fileIndex.keys()].filter((p) => p.toLowerCase().endsWith(".pptd"));
  if (!manifests.length) throw new Error("没有 .pptd");
  await loadDeckFromIndex(manifests.sort()[0], "上传 · 只读", {
    readOnly: true,
    editable: true,
  });
}

function wireUi() {
  if (state.serverProject) {
    // The deck is mounted by the host; a folder picker would only confuse.
    const openButton = $("#nd-open");
    if (openButton) openButton.hidden = true;
  }
  $("#nd-open")?.addEventListener("click", async () => {
    try {
      if (window.showDirectoryPicker) {
        const handle = await window.showDirectoryPicker({ mode: "readwrite" });
        await openDirectoryHandle(handle);
      } else {
        $("#nd-folder")?.click();
      }
    } catch (e) {
      if (e?.name === "AbortError") return;
      toast(e.message || String(e), "error");
    }
  });
  $("#nd-folder")?.addEventListener("change", async (ev) => {
    const files = ev.target.files;
    if (!files?.length) return;
    try {
      await openFallbackFiles(files);
    } catch (e) {
      toast(e.message || String(e), "error");
    }
    ev.target.value = "";
  });
}

// Force sdk query params so official app enters ppt-editor external mode
(function forceSdkQuery() {
  const url = new URL(location.href);
  let changed = false;
  const params = {
    sdkMode: "ppt-editor",
    pptPlatform: "neodeck-local",
    functional: JSON.stringify({
      fullscreen: true,
      present: true,
      export: true,
      close: false,
      annotation: false,
      feedback: false,
      share: false,
      versionHistory: false,
    }),
    sdkSaveMode: "external",
    sdkImageMode: "external",
  };
  for (const [k, v] of Object.entries(params)) {
    if (url.searchParams.get(k) !== v) {
      url.searchParams.set(k, v);
      changed = true;
    }
  }
  if (changed) history.replaceState(null, "", url);
})();

wireUi();
setStatus("等待编辑器…");
