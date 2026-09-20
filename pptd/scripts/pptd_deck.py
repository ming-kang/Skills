#!/usr/bin/env python3
"""PPTD deck loading: manifests, pages, payloads and local image maps.

This module owns "what is in a deck": finding the ``.pptd`` manifest, reading
YAML safely, keeping every referenced file inside the project directory, and
assembling the two hand-off shapes the exporters consume —

* ``build_payload``: the headless ``payload.json`` for the local editor host
  (consumed by ``assets/editor/local-bridge.js``);
* ``build_local_project``: the pre-parsed project for the Node WASM exporter
  (``scripts/local-export/export-pptd.mjs --json``).

Both parse here on purpose: PyYAML is the one Python dependency the skill
already requires, and the Node side has no guaranteed package tree. Both also
share ``read_validated_project``, so the two shapes cannot drift apart on what
a well-formed v2 deck is.
"""

from __future__ import annotations

import base64
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from pptd_common import ExportError, ensure_module, log

IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_EMBEDDED_MEDIA_BYTES = 200 * 1024 * 1024


def find_manifest(source: Path) -> Path:
    source = source.expanduser().resolve()
    if source.is_file():
        if source.suffix.lower() != ".pptd":
            raise ExportError(f"input must be a .pptd file or project directory: {source}")
        return source
    if not source.is_dir():
        raise ExportError(f"input does not exist: {source}")
    manifests = sorted(source.rglob("*.pptd"))
    if not manifests:
        raise ExportError(f"no .pptd manifest found under: {source}")
    if len(manifests) > 1:
        choices = "\n  ".join(str(path) for path in manifests[:20])
        raise ExportError(
            "multiple .pptd manifests found; pass one manifest explicitly:\n  " + choices
        )
    return manifests[0]


def read_yaml_mapping(path: Path) -> Tuple[str, Dict[str, Any]]:
    yaml = ensure_module("yaml", "pyyaml", "PyYAML is required to read PPTD YAML")
    text = path.read_text(encoding="utf-8")
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ExportError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExportError(f"expected a YAML mapping in {path}")
    return text, value


def safe_project_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ExportError("page path must be a non-empty string")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ExportError(f"project path escapes the PPTD directory: {relative}") from exc
    return candidate


def read_validated_project(
    manifest: Path,
) -> Tuple[str, Dict[str, Any], List[Tuple[str, str, Dict[str, Any]]]]:
    """Read and validate one v2 deck.

    Returns ``(manifest text, manifest mapping, [(page path, page text, page
    data)])``. The single definition of the deck contract, shared by both
    hand-off shapes so they cannot disagree about it.
    """
    manifest_text, manifest_data = read_yaml_mapping(manifest)
    if manifest_data.get("version") != "v2":
        raise ExportError("local PPTX export currently requires PPTD version: v2")
    page_paths = manifest_data.get("pages")
    if not isinstance(page_paths, list) or not page_paths:
        raise ExportError("PPTD manifest must contain a non-empty pages list")

    root = manifest.parent.resolve()
    pages: List[Tuple[str, str, Dict[str, Any]]] = []
    for entry in page_paths:
        page_path = safe_project_path(root, entry)
        if not page_path.is_file():
            raise ExportError(f"missing page file: {entry}")
        page_text, page_data = read_yaml_mapping(page_path)
        if not isinstance(page_data.get("elements"), list):
            raise ExportError(f"page elements must be an array: {entry}")
        pages.append((entry, page_text, page_data))
    return manifest_text, manifest_data, pages


def collect_image_sources(pages_data: Iterable[Dict[str, Any]]) -> List[str]:
    """Local image sources actually referenced by the deck, in first-seen order.

    Scanning the project directory instead would sweep up unrelated files —
    notably the page renders under .qa-images/, which the visual-QA loop writes
    into the project root and regenerates on every round.
    """
    sources: List[str] = []
    seen = set()

    def visit(holder: Any) -> None:
        if not isinstance(holder, dict):
            return
        src = holder.get("src")
        if not isinstance(src, str) or not src.strip():
            return
        if re.match(r"^(https?://|data:)", src, re.IGNORECASE):
            return
        if src in seen:
            return
        seen.add(src)
        sources.append(src)

    for page in pages_data:
        if not isinstance(page, dict):
            continue
        background = page.get("background")
        if isinstance(background, dict) and background.get("type") == "image":
            visit(background)
        elements = page.get("elements")
        if not isinstance(elements, list):
            continue
        for element in elements:
            if not isinstance(element, dict):
                continue
            if element.get("elementType") == "image":
                visit(element)
            fill = element.get("fill")
            if isinstance(fill, dict) and fill.get("type") == "image":
                visit(fill)
    return sources


def build_image_map(root: Path, pages_data: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    image_map: Dict[str, str] = {}
    total = 0
    for src in collect_image_sources(pages_data):
        path = safe_project_path(root, re.sub(r"^file://+", "", src))
        if not path.is_file():
            log(f"skip missing local image: {src}")
            continue
        suffix = path.suffix.lower()
        if suffix not in IMAGE_MIME:
            log(f"skip unsupported image type: {src}")
            continue
        size = path.stat().st_size
        if size > MAX_IMAGE_BYTES:
            log(f"skip local image over 20 MiB: {src}")
            continue
        if total + size > MAX_EMBEDDED_MEDIA_BYTES:
            raise ExportError(
                "local image payload exceeds 200 MiB; reduce media size or use remote URLs"
            )
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        image_map[src] = f"data:{IMAGE_MIME[suffix]};base64,{data}"
        total += size
    if image_map:
        log(f"prepared {len(image_map)} local image resource(s), {total} bytes")
    return image_map


def build_payload(manifest: Path, embed_media: bool = False) -> Dict[str, Any]:
    """Assemble the headless payload for the local editor.

    `embed_media=False` (the default) leaves `imageMap` empty: the deck's local
    media is served by the host that also serves the payload, so a deck with
    hundreds of high-resolution images no longer inflates the JSON (and the
    browser's memory) by a base64 factor. `embed_media=True` restores the old
    self-contained payload for hosts that cannot serve the project directory.
    """
    manifest = find_manifest(manifest)
    manifest_text, manifest_data, pages = read_validated_project(manifest)
    title = str(manifest_data.get("title") or manifest.stem)
    return {
        "id": f"local-export-{uuid.uuid4().hex}",
        "title": title,
        "manifestPath": manifest.name,
        "manifestContent": manifest_text,
        "pages": [{"path": entry, "content": text} for entry, text, _ in pages],
        "imageMap": build_image_map(manifest.parent, [data for _, _, data in pages])
        if embed_media
        else {},
    }


def build_local_project(manifest: Path) -> Dict[str, Any]:
    """Pre-parsed project for the local WASM exporter (`export-pptd.mjs --json`).

    The Node side has no guaranteed YAML package next to the skill, so the
    parsing happens here, where PyYAML is already a hard dependency.
    """
    manifest = find_manifest(manifest)
    _, manifest_data, pages = read_validated_project(manifest)
    return {
        "manifestPath": str(manifest),
        "manifest": manifest_data,
        "pages": [{"path": entry, "data": data} for entry, _, data in pages],
    }
