from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from typing import Any

from pptd_common import ExportError

ELEMENT_TYPES = {"text", "shape", "line", "image", "icon", "table", "chart"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}


def find_manifest(source: Path) -> Path:
    source = Path(source).expanduser().resolve()
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


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise ExportError(
            f"PyYAML is required; install it with: {sys.executable} -m pip install PyYAML"
        ) from exc
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeError) as exc:
        raise ExportError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExportError(f"expected a YAML mapping in {path}")
    return value


def safe_project_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ExportError("project path must be a non-empty string")
    root = root.resolve()
    candidate = (root / relative.replace("\\", "/")).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ExportError(f"project path escapes the PPTD directory: {relative}") from exc
    return candidate


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _dimensions(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 4 or not all(_number(item) for item in value):
        raise ExportError(f"{label} must be [x, y, width, height] with finite numbers")
    if value[2] <= 0 or value[3] <= 0:
        raise ExportError(f"{label} width and height must be positive")
    return value


def _media_holders(page: dict[str, Any]):
    background = page.get("background")
    if isinstance(background, dict) and background.get("type") == "image":
        yield background
    for element in page.get("elements", []):
        if element.get("elementType") == "image":
            yield element
        fill = element.get("fill")
        if isinstance(fill, dict) and fill.get("type") == "image":
            yield fill


def _validate_media(root: Path, page_path: str, page: dict[str, Any]) -> None:
    for holder in _media_holders(page):
        src = holder.get("src")
        if not isinstance(src, str) or not src.strip():
            raise ExportError(f"{page_path}: image source must be a non-empty string")
        if re.match(r"^(https?://|data:)", src, re.IGNORECASE):
            continue
        relative = re.sub(r"^file://+", "", src)
        path = safe_project_path(root, relative)
        if not path.is_file():
            raise ExportError(f"{page_path}: missing local image: {src}")
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ExportError(f"{page_path}: unsupported local image type: {src}")


def _validate_elements(
    root: Path, size: list[float], page_path: str, page: dict[str, Any]
) -> list[str]:
    warnings: list[str] = []
    seen_ids: set[str] = set()
    for index, element in enumerate(page["elements"]):
        label = f"{page_path}: elements[{index}]"
        if not isinstance(element, dict):
            raise ExportError(f"{label} must be a mapping")
        element_id = element.get("elementId")
        if not isinstance(element_id, str) or not element_id.strip():
            raise ExportError(f"{label}.elementId must be a non-empty string")
        if element_id in seen_ids:
            raise ExportError(f"{page_path}: duplicate elementId: {element_id}")
        seen_ids.add(element_id)
        if element.get("elementType") not in ELEMENT_TYPES:
            raise ExportError(f"{label}.elementType is invalid: {element.get('elementType')!r}")
        bounds = _dimensions(element.get("bounds"), f"{label}.bounds")
        if (
            bounds[0] < 0
            or bounds[1] < 0
            or bounds[0] + bounds[2] > size[0]
            or bounds[1] + bounds[3] > size[1]
        ):
            warnings.append(f"{label} ({element_id}) extends beyond the slide canvas")
        if element["elementType"] == "text":
            content = element.get("content")
            if not isinstance(content, dict) or not isinstance(content.get("text"), str):
                raise ExportError(f"{label}.content.text must be a string for text elements")
    _validate_media(root, page_path, page)
    return warnings


def build_local_project(source: Path) -> dict[str, Any]:
    manifest_path = find_manifest(source)
    manifest = read_yaml_mapping(manifest_path)
    if manifest.get("version") != "v2":
        raise ExportError("only PPTD version: v2 is supported")
    size = manifest.get("size")
    if (
        not isinstance(size, list)
        or len(size) != 2
        or not all(_number(item) and item > 0 for item in size)
    ):
        raise ExportError("manifest.size must contain two positive finite numbers")
    page_paths = manifest.get("pages")
    if not isinstance(page_paths, list) or not page_paths:
        raise ExportError("manifest.pages must be a non-empty array")
    if not all(isinstance(entry, str) and entry.strip() for entry in page_paths):
        raise ExportError("every manifest.pages entry must be a non-empty string")
    if len(set(page_paths)) != len(page_paths):
        raise ExportError("manifest.pages contains duplicate paths")

    root = manifest_path.parent.resolve()
    pages: list[dict[str, Any]] = []
    warnings: list[str] = []
    for entry in page_paths:
        page_path = safe_project_path(root, entry)
        if not page_path.is_file():
            raise ExportError(f"missing page file: {entry}")
        page = read_yaml_mapping(page_path)
        if not isinstance(page.get("elements"), list):
            raise ExportError(f"page elements must be an array: {entry}")
        warnings.extend(_validate_elements(root, size, entry, page))
        pages.append({"path": entry, "data": page})

    return {
        "manifestPath": str(manifest_path),
        "manifest": manifest,
        "pages": pages,
        "warnings": warnings,
    }


def validation_summary(project: dict[str, Any]) -> dict[str, Any]:
    pages = project["pages"]
    return {
        "valid": True,
        "manifest": project["manifestPath"],
        "title": project["manifest"].get("title"),
        "slides": len(pages),
        "elements": sum(len(page["data"]["elements"]) for page in pages),
        "warnings": project.get("warnings", []),
    }
