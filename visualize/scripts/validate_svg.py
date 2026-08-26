#!/usr/bin/env python3
"""Robust, zero-dependency SVG validator for the visualize skill.

Run directly::

    python3 scripts/validate_svg.py [-q] file.svg [other.svg ...]

The same :class:`Validator` is loaded by ``svgkit.Diagram.save()``. Geometry
checks intentionally support the house-style subset. Unsupported positioned
``<tspan>`` content and transformed geometry are skipped with explicit warnings
rather than being measured at fictitious coordinates.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


Point = tuple[float, float]
TAU = math.tau
EPSILON = 1e-9

ANSI = {
    "red": "\033[0;31m",
    "green": "\033[0;32m",
    "yellow": "\033[1;33m",
    "blue": "\033[0;34m",
    "reset": "\033[0m",
}


def color(text: str, name: str, enabled: bool = True) -> str:
    if not enabled:
        return text
    return f"{ANSI[name]}{text}{ANSI['reset']}"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError:
        match = re.match(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", value.strip())
        return float(match.group(0)) if match else default


def parse_points(value: str | None) -> list[Point]:
    if not value:
        return []
    nums = [float(n) for n in re.findall(
        r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", value
    )]
    return list(zip(nums[::2], nums[1::2]))


def iter_with_ancestors(root: ET.Element) -> Iterable[tuple[ET.Element, list[str]]]:
    stack: list[tuple[ET.Element, list[str]]] = [(root, [])]
    while stack:
        element, ancestors = stack.pop()
        yield element, ancestors
        next_ancestors = ancestors + [local_name(element.tag)]
        for child in reversed(list(element)):
            stack.append((child, next_ancestors))


# ---------------------------------------------------------------------------
# Shared text measurement. Prefer a package-relative import, then accept a
# top-level svgkit only when it is the sibling file. Otherwise use the exact
# local implementation so a caller's unrelated ``svgkit`` module cannot win.
# ---------------------------------------------------------------------------
def _local_text_width(s: str, size: int = 14) -> float:
    latin = size * 8 / 14
    wide = size * 15 / 14
    return sum(wide if unicodedata.east_asian_width(ch) in ("W", "F") else latin
               for ch in s)


try:  # package import: visualize.scripts.validate_svg
    from .svgkit import text_width  # type: ignore
except (ImportError, ValueError):
    try:  # direct script import, but only trust the sibling module
        import svgkit as _svgkit  # type: ignore

        sibling = Path(__file__).resolve().with_name("svgkit.py")
        imported = Path(getattr(_svgkit, "__file__", "")).resolve()
        if imported != sibling:
            raise ImportError(f"top-level svgkit resolves to {imported}, not {sibling}")
        text_width = _svgkit.text_width
    except Exception:  # pragma: no cover - exercised in isolated/embedded callers
        text_width = _local_text_width


# The warm house palette (mirrors references/style.md). check_palette.py asserts
# that every family token in svgkit is present here.
WARM_PALETTE: set[str] = {
    "#f5f4ed", "#141413", "#3d3d3a", "#73726c",
    "#e1f5ee", "#0f6e56", "#085041", "#1d9e75",
    "#eeedfe", "#534ab7", "#3c3489", "#7f77dd",
    "#faece7", "#993c1d", "#712b13", "#c75b38",
    "#faeeda", "#854f0b", "#633806", "#ef9f27",
    "#fac775", "#f5c4b3", "#9fe1cb", "#cecbf6", "#f4c0d1", "#c0dd97", "#b5d4f4",
    "#f1efe8", "#5f5e5a", "#ffffff", "#000000", "#fff",
}
COLOR_KEYWORDS_OK = {"none", "transparent", "context-stroke", "currentcolor", "inherit"}


def normalize_hex(value: str) -> str | None:
    """Return lowercase ``#rrggbb``, expanding ``#rgb``; None for non-hex."""
    v = value.strip().lower()
    match = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", v)
    if not match:
        return None
    raw = match.group(1)
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    return "#" + raw


def is_cold_color(value: str) -> bool:
    hx = normalize_hex(value)
    if hx is None or hx in WARM_PALETTE:
        return False
    r = int(hx[1:3], 16)
    g = int(hx[3:5], 16)
    b = int(hx[5:7], 16)
    return b > r + 12 and b >= g - 4


@dataclass
class CheckResult:
    name: str
    status: str
    message: str = ""
    details: list[str] | None = None
    fix: str = ""


# ---------------------------------------------------------------------------
# Geometry engine (extracted to geometry.py for maintainability)
# ---------------------------------------------------------------------------
from geometry import (  # noqa: E402
    Point, TAU, EPSILON,
    Bounds, TextRun, PathSegment, PathData, ArcGeometry,
    parse_path, arc_geometry, path_bounds,
    path_outlines, parse_path_points,
    point_in_polygon, polygons_intersect, shapes_intersect,
    segment_crosses_polygon, segment_hits_aabb,
    overlap_area, rect_outline, ellipse_outline,
    _sample_path_subpaths,
)

# Backward-compatible private aliases used internally
_rect_outline = rect_outline
_ellipse_outline = ellipse_outline

def format_point(point: Point) -> str:
    return f"({point[0]:g},{point[1]:g})"


def format_bounds(bounds: Bounds) -> str:
    return f"[{bounds.left:g},{bounds.top:g},{bounds.right:g},{bounds.bottom:g}]"


def _parse_inline_style(value: str | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    priorities: dict[str, int] = {}
    for declaration in (value or "").split(";"):
        if ":" not in declaration:
            continue
        key, raw = declaration.split(":", 1)
        name = key.strip().lower()
        important = bool(re.search(r"\s*!important\s*$", raw, flags=re.I))
        normalized = re.sub(r"\s*!important\s*$", "", raw, flags=re.I).strip()
        priority = 1 if important else 0
        # CSS: !important beats a later normal declaration; declarations at
        # equal priority retain normal last-one-wins ordering.
        if name not in parsed or priority >= priorities[name]:
            parsed[name] = normalized
            priorities[name] = priority
    return parsed


class Validator:
    def __init__(self, svg_path: Path, no_color: bool = False) -> None:
        self.svg_path = svg_path
        self.no_color = no_color
        self._reset()

    def _reset(self) -> None:
        self.text = ""
        self.root: ET.Element | None = None
        self.viewbox: tuple[float, float, float, float] | None = None
        self.failures = 0
        self.warnings = 0
        self.parent_map: dict[ET.Element, ET.Element] = {}
        self._obstacles: list[Bounds] | None = None
        self._labels: list[TextRun] | None = None
        self._unsupported_text: list[str] = []
        self._unsupported_transforms: list[str] = []
        self._unsupported_paths: list[str] = []

    def collect(self) -> list[CheckResult]:
        """Run all checks from a fresh parse and return structured results."""
        self._reset()
        results = self.check_file_and_xml()
        if any(result.status == "fail" for result in results):
            return results

        checks = [
            self.check_svg_root,
            self.check_viewbox,
            self.check_accessibility,
            self.check_renderer_compatibility,
            self.check_marker_contract,
            self.check_references,
            self.check_white_background,
            self.check_flat_style,
            self.check_box_overlap,
            self.check_arrow_collisions,
            self.check_box_viewbox_overflow,
            self.check_text_overflow,
            self.check_label_vs_box,
            self.check_label_vs_label,
            self.check_unsupported_text_geometry,
            self.check_unsupported_transforms,
            self.check_type_scale,
            self.check_text_baseline,
            self.check_palette,
            self.check_closing_tag,
        ]
        results.extend(check() for check in checks)
        return results

    def run(self, quiet: bool = False) -> int:
        results = self.collect()
        if quiet:
            problems = [result for result in results if result.status != "pass"]
            if not problems:
                return 0
            print(f"Validating SVG: {self.svg_path}")
            for result in problems:
                self.report(result)
            if self.failures:
                print(color(f"Validation failed ({self.failures} error(s))", "red", not self.no_color))
                return 1
            return 0

        print(f"Validating SVG: {self.svg_path}")
        print("----------------------------------------")
        for result in results:
            self.report(result)
        print("----------------------------------------")
        if self.failures == 0:
            suffix = f" ({self.warnings} warning(s))" if self.warnings else ""
            print(f"Validation complete{suffix}")
            return 0
        print(color(f"Validation failed ({self.failures} error(s))", "red", not self.no_color))
        return 1

    def report(self, result: CheckResult) -> None:
        if result.status == "pass":
            status = color("✓ Pass", "green", not self.no_color)
        elif result.status == "warn":
            status = color("⚠ Warning", "yellow", not self.no_color)
            self.warnings += 1
        else:
            status = color("✗ Fail", "red", not self.no_color)
            self.failures += 1
        message = f" ({result.message})" if result.message else ""
        print(f"{result.name}... {status}{message}")
        for detail in result.details or []:
            print(f"  - {detail}")
        if result.fix and result.status != "pass":
            print(f"  Fix: {result.fix}")

    def check_file_and_xml(self) -> list[CheckResult]:
        if not self.svg_path.is_file():
            return [CheckResult(
                "Checking file", "fail", f"not found: {self.svg_path}",
                fix="Check the path and ensure the SVG was generated.",
            )]
        try:
            self.text = self.svg_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            return [CheckResult(
                "Reading UTF-8", "fail", str(exc), fix="Save the SVG as UTF-8.",
            )]
        try:
            self.root = ET.fromstring(self.text)
        except ET.ParseError as exc:
            self.root = None
            return [
                CheckResult("Reading UTF-8", "pass"),
                CheckResult(
                    "Checking XML syntax", "fail", str(exc),
                    fix="Check for unquoted attributes, unclosed tags, or stray characters.",
                ),
            ]
        self.parent_map = {child: parent for parent in self.root.iter() for child in parent}
        return [CheckResult("Reading UTF-8", "pass"), CheckResult("Checking XML syntax", "pass")]

    def check_svg_root(self) -> CheckResult:
        assert self.root is not None
        if local_name(self.root.tag) != "svg":
            return CheckResult(
                "Checking SVG root", "fail", f"root tag is <{local_name(self.root.tag)}>",
                fix="Wrap content in an <svg> root element.",
            )
        return CheckResult("Checking SVG root", "pass")

    def check_viewbox(self) -> CheckResult:
        assert self.root is not None
        viewbox = self.root.get("viewBox")
        if not viewbox:
            return CheckResult(
                "Checking viewBox", "fail", "missing viewBox",
                fix="Add viewBox='0 0 W H' with positive width and height.",
            )
        nums = [float(value) for value in re.findall(
            r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", viewbox
        )]
        if len(nums) != 4 or nums[2] <= 0 or nums[3] <= 0:
            return CheckResult(
                "Checking viewBox", "fail", f"invalid viewBox={viewbox!r}",
                fix="viewBox needs four numbers: min-x min-y width height.",
            )
        self.viewbox = nums[0], nums[1], nums[2], nums[3]
        return CheckResult("Checking viewBox", "pass", f"{nums[2]:g}x{nums[3]:g}")

    def check_accessibility(self) -> CheckResult:
        assert self.root is not None
        children = list(self.root)
        details: list[str] = []
        if len(children) < 2 or [local_name(child.tag) for child in children[:2]] != ["title", "desc"]:
            details.append("the first two element children must be <title> then <desc>")
        else:
            if not "".join(children[0].itertext()).strip():
                details.append("<title> must be non-empty")
            if not "".join(children[1].itertext()).strip():
                details.append("<desc> must be non-empty")
        if details:
            return CheckResult(
                "Checking accessibility", "fail", details=details,
                fix="Make non-empty <title> and <desc> the first two children of <svg>.",
            )
        return CheckResult("Checking accessibility", "pass")

    def check_renderer_compatibility(self) -> CheckResult:
        assert self.root is not None
        details: list[str] = []

        def embedded_or_local(target: str) -> bool:
            normalized = target.strip().strip("\"'").lower()
            return normalized.startswith("#") or normalized.startswith("data:")

        def inspect_urls(context: str, value: str) -> None:
            for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", value, re.I):
                target = match.group(2).strip()
                if target and not embedded_or_local(target):
                    detail = f"{context} contains external url({target})"
                    if detail not in details:
                        details.append(detail)

        for processing_instruction in re.finditer(
            r"<\?xml-stylesheet\b.*?\?>", self.text, re.I | re.S
        ):
            details.append(
                "document contains an xml-stylesheet processing instruction; inline styles instead"
            )

        for element in self.root.iter():
            tag = local_name(element.tag)
            if tag == "style" and element.text:
                if "@import" in element.text.lower():
                    details.append("<style> contains @import")
                inspect_urls("<style>", element.text)
            for key, value in element.attrib.items():
                attr = local_name(key).lower()
                if attr in {"href", "src"}:
                    target = value.strip()
                    if target and not embedded_or_local(target):
                        details.append(f"<{tag}> has external {attr}={value!r}")
                inspect_urls(f"<{tag}> {attr}", value)
        if details:
            return CheckResult(
                "Checking renderer-safe assets", "fail", details=details[:12],
                fix="Use inline data assets or local #id fragments; remove imports and external/relative references.",
            )
        return CheckResult("Checking renderer-safe assets", "pass")

    def check_marker_contract(self) -> CheckResult:
        assert self.root is not None
        id_counts: dict[str, int] = {}
        markers: list[ET.Element] = []
        marker_refs: list[tuple[str, str, str]] = []
        stylesheet_markers: list[str] = []
        mixed_marker_properties: list[str] = []
        marker_names = ("marker", "marker-start", "marker-mid", "marker-end")
        for element in self.root.iter():
            tag = local_name(element.tag)
            element_id = element.get("id")
            if element_id:
                id_counts[element_id] = id_counts.get(element_id, 0) + 1
            if tag == "marker":
                markers.append(element)
            values = {attr: self._presentation_value(element, attr) for attr in marker_names}
            shorthand = values["marker"]
            if shorthand is not None and any(
                values[attr] is not None for attr in ("marker-start", "marker-mid", "marker-end")
            ):
                mixed_marker_properties.append(
                    f"<{tag}> mixes marker shorthand with longhands; use one form"
                )
            for attr, value in values.items():
                if value and value.strip().lower() != "none":
                    marker_refs.append((tag, attr, value))
            if tag == "style" and element.text:
                for attr, value in re.findall(
                    r"(marker(?:-(?:start|mid|end))?)\s*:\s*([^;}]+)", element.text, re.I
                ):
                    stylesheet_markers.append(attr.lower())
                    if value.strip().lower() != "none":
                        marker_refs.append(("style", attr.lower(), value.strip()))

        details = [f"duplicate id={value!r} appears {count} times"
                   for value, count in sorted(id_counts.items()) if count > 1]
        if len(markers) != 1 or markers[0].get("id") != "arrow":
            ids = [marker.get("id") for marker in markers]
            details.append(f"expected exactly one <marker id='arrow'>; found marker ids {ids}")
        for tag, attr, value in marker_refs:
            if value.strip() != "url(#arrow)":
                details.append(f"<{tag}> {attr} must be url(#arrow), got {value!r}")
        details.extend(mixed_marker_properties)
        if stylesheet_markers:
            names = ", ".join(sorted(set(stylesheet_markers)))
            details.append(
                f"stylesheet marker properties cannot be resolved to elements ({names}); "
                "use presentation attributes or inline style"
            )
        if details:
            return CheckResult(
                "Checking marker contract", "fail", details=details[:12],
                fix="Keep one marker#arrow; use element/inline marker properties targeting url(#arrow), not stylesheet rules.",
            )
        return CheckResult("Checking marker contract", "pass", f"{len(marker_refs)} marker reference(s)")

    def check_references(self) -> CheckResult:
        assert self.root is not None
        ids = {element.get("id"): local_name(element.tag)
               for element in self.root.iter() if element.get("id")}
        refs: list[tuple[str, str, str]] = []
        for element in self.root.iter():
            tag = local_name(element.tag)
            values = [(local_name(attr).lower(), value) for attr, value in element.attrib.items()]
            if tag == "style" and element.text:
                values.append(("css", element.text))
            for attr, value in values:
                stripped = value.strip()
                if attr in {"href", "src"} and stripped.startswith("#") and len(stripped) > 1:
                    refs.append((tag, attr, stripped[1:]))
                for match in re.finditer(
                    r"url\(\s*['\"]?#([^)\s'\"]+)['\"]?\s*\)", value, re.I
                ):
                    refs.append((tag, attr, match.group(1)))
        missing = [f"<{tag}> {attr} references #{ref_id} with no matching id"
                   for tag, attr, ref_id in refs if ref_id not in ids]
        if missing:
            return CheckResult(
                "Checking URL/marker references", "fail", details=missing[:12],
                fix="Add the referenced local id or correct the #id fragment.",
            )
        return CheckResult("Checking URL/marker references", "pass", f"{len(refs)} reference(s)")

    def _presentation_value(self, element: ET.Element, name: str,
                            default: str | None = None) -> str | None:
        current: ET.Element | None = element
        while current is not None:
            style = _parse_inline_style(current.get("style"))
            value = style.get(name.lower(), current.get(name))
            if value is not None and value.strip().lower() != "inherit":
                return value.strip()
            current = self.parent_map.get(current)
        return default

    @staticmethod
    def _alpha_value(value: str | None, default: float = 1.0) -> float:
        if value is None:
            return default
        raw = value.strip()
        try:
            number = float(raw[:-1]) / 100.0 if raw.endswith("%") else float(raw)
        except ValueError:
            return default
        return max(0.0, min(1.0, number))

    def _effective_opacity(self, element: ET.Element) -> float:
        opacity = 1.0
        current: ET.Element | None = element
        while current is not None:
            style = _parse_inline_style(current.get("style"))
            raw = style.get("opacity", current.get("opacity"))
            if raw is not None and raw.strip().lower() != "inherit":
                opacity *= self._alpha_value(raw)
            current = self.parent_map.get(current)
        return opacity

    def _is_hidden(self, element: ET.Element) -> bool:
        current: ET.Element | None = element
        while current is not None:
            style = _parse_inline_style(current.get("style"))
            display = style.get("display", current.get("display"))
            if display is not None and display.strip().lower() == "none":
                return True
            current = self.parent_map.get(current)
        visibility = (self._presentation_value(element, "visibility", "visible") or "visible").lower()
        return visibility in {"hidden", "collapse"} or self._effective_opacity(element) <= EPSILON

    @classmethod
    def _color_alpha(cls, value: str) -> float:
        raw = value.strip().lower()
        if raw.startswith("#"):
            digits = raw[1:]
            if len(digits) == 4:
                return int(digits[-1] * 2, 16) / 255.0
            if len(digits) == 8:
                return int(digits[-2:], 16) / 255.0
            return 1.0
        match = re.fullmatch(r"(?:rgb|rgba|hsl|hsla)\((.*)\)", raw, re.I)
        if not match:
            return 1.0
        contents = match.group(1).strip()
        if "/" in contents:
            return cls._alpha_value(contents.rsplit("/", 1)[1].strip())
        parts = [part.strip() for part in contents.split(",")]
        if len(parts) == 4:
            return cls._alpha_value(parts[-1])
        return 1.0

    def _paint_is_visible(self, element: ET.Element, paint: str) -> bool:
        if self._is_hidden(element):
            return False
        default = "black" if paint == "fill" else "none"
        color_value = (self._presentation_value(element, paint, default) or default).strip().lower()
        if color_value in {"none", "transparent"}:
            return False
        alpha = self._alpha_value(self._presentation_value(element, f"{paint}-opacity", "1"))
        return self._effective_opacity(element) * alpha * self._color_alpha(color_value) > EPSILON

    def _stylesheet_has_transform(self) -> bool:
        assert self.root is not None
        return any(
            local_name(element.tag) == "style"
            and bool(element.text)
            and bool(re.search(
                r"(?<![-\w])(?:transform|translate|rotate|scale)\s*:",
                element.text or "", re.I,
            ))
            for element in self.root.iter()
        )

    def _has_transform(self, element: ET.Element) -> bool:
        current: ET.Element | None = element
        transform_names = ("transform", "translate", "rotate", "scale")
        while current is not None:
            style = _parse_inline_style(current.get("style"))
            for name in transform_names:
                value = style.get(name, current.get(name))
                if value is not None and value.strip().lower() not in {"", "none"}:
                    return True
            current = self.parent_map.get(current)
        return False

    def check_white_background(self) -> CheckResult:
        assert self.root is not None
        if not self.viewbox:
            return CheckResult("Checking white background", "fail", "cannot check without a viewBox")

        non_painting = {"title", "desc", "style", "defs", "metadata"}
        painted = [child for child in self.root if local_name(child.tag) not in non_painting]
        if not painted or local_name(painted[0].tag) != "rect":
            first = local_name(painted[0].tag) if painted else "none"
            return CheckResult(
                "Checking white background", "fail",
                f"the first painted root child is <{first}>, not the canvas background rect",
                fix="Put a full-canvas white <rect> immediately after <defs>, before all diagram content.",
            )

        element = painted[0]
        if self._has_transform(element):
            return CheckResult(
                "Checking white background", "fail", "the canvas background rect is transformed",
                fix="Use an untransformed full-canvas white rect as the first painted root child.",
            )
        if self._is_hidden(element):
            return CheckResult(
                "Checking white background", "fail", "the canvas background rect is hidden or transparent",
                fix="Use a visible opaque full-canvas white rect as the first painted root child.",
            )
        vb_x, vb_y, vb_w, vb_h = self.viewbox
        vb_right, vb_bottom = vb_x + vb_w, vb_y + vb_h
        fill = normalize_hex(self._presentation_value(element, "fill", "black") or "")
        x = parse_float(element.get("x"), 0.0)
        y = parse_float(element.get("y"), 0.0)
        width = parse_float(element.get("width"))
        height = parse_float(element.get("height"))
        opacity = self._effective_opacity(element)
        fill_opacity = self._alpha_value(self._presentation_value(element, "fill-opacity", "1"))
        covers = (
            x <= vb_x + 0.5 and y <= vb_y + 0.5
            and x + width >= vb_right - 0.5 and y + height >= vb_bottom - 0.5
        )
        if fill == "#ffffff" and covers and opacity >= 0.999 and fill_opacity >= 0.999:
            return CheckResult("Checking white background", "pass")
        return CheckResult(
            "Checking white background", "fail",
            "the first painted root child is not an opaque white rect covering the full viewBox",
            fix="Put an opaque full-canvas <rect> with fill='#FFFFFF' immediately after <defs>.",
        )

    def check_flat_style(self) -> CheckResult:
        assert self.root is not None
        details: list[str] = []
        forbidden_tags = {"lineargradient", "radialgradient", "filter"}
        for element in self.root.iter():
            tag = local_name(element.tag)
            lowered = tag.lower()
            if lowered in forbidden_tags or lowered.startswith("fe"):
                details.append(f"forbidden <{tag}> element")
            style = element.get("style", "")
            if element.get("filter") is not None or re.search(r"(?:^|;)\s*filter\s*:", style, re.I):
                details.append(f"<{tag}> uses filter")
            if re.search(r"(?:^|;)\s*(?:box-|text-)?shadow\s*:", style, re.I):
                details.append(f"<{tag}> uses shadow CSS")
            if tag == "style" and element.text:
                if re.search(r"(?:filter|box-shadow|text-shadow)\s*:", element.text, re.I):
                    details.append("<style> contains filter/shadow CSS")
        if details:
            return CheckResult(
                "Checking flat style", "fail", details=details[:12],
                fix="Remove gradients, filters, blur, and shadows; the house style is completely flat.",
            )
        return CheckResult("Checking flat style", "pass")

    def collect_obstacles(self) -> list[Bounds]:
        assert self.root is not None
        if self._obstacles is not None:
            return self._obstacles
        if self._stylesheet_has_transform():
            detail = "<style> transform rules are unresolved; all obstacle geometry is skipped"
            if detail not in self._unsupported_transforms:
                self._unsupported_transforms.append(detail)
            self._obstacles = []
            return self._obstacles
        obstacles: list[Bounds] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(name in {"defs", "marker", "clipPath", "filter"} for name in ancestors):
                continue
            if self._has_transform(element):
                detail = f"<{local_name(element.tag)}> transform is not included in geometry checks"
                if detail not in self._unsupported_transforms:
                    self._unsupported_transforms.append(detail)
                continue
            bounds = self.shape_bounds(element)
            if bounds is None or self.is_non_obstacle(element, bounds):
                continue
            obstacles.append(bounds)
        self._obstacles = obstacles
        return obstacles

    def shape_bounds(self, element: ET.Element) -> Bounds | None:
        tag = local_name(element.tag)
        role = element.get("data-role")
        if tag == "rect":
            x, y = parse_float(element.get("x")), parse_float(element.get("y"))
            width, height = parse_float(element.get("width")), parse_float(element.get("height"))
            return Bounds(x, y, x + width, y + height, tag, role,
                          _rect_outline(x, y, x + width, y + height), source=element)
        if tag == "circle":
            radius = parse_float(element.get("r"))
            cx, cy = parse_float(element.get("cx")), parse_float(element.get("cy"))
            return Bounds(cx - radius, cy - radius, cx + radius, cy + radius, tag, role,
                          _ellipse_outline(cx, cy, radius, radius), source=element)
        if tag == "ellipse":
            rx, ry = parse_float(element.get("rx")), parse_float(element.get("ry"))
            cx, cy = parse_float(element.get("cx")), parse_float(element.get("cy"))
            return Bounds(cx - rx, cy - ry, cx + rx, cy + ry, tag, role,
                          _ellipse_outline(cx, cy, rx, ry), source=element)
        if tag == "polygon":
            points = parse_points(element.get("points"))
            if len(points) < 3:
                return None
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            return Bounds(min(xs), min(ys), max(xs), max(ys), tag, role,
                          tuple(points), source=element)
        if tag == "path":
            if self.is_arrow(element):
                return None
            if not self._paint_is_visible(element, "fill"):
                return None
            try:
                data = parse_path(element.get("d"))
                raw_bounds = path_bounds(data)
            except ValueError as exc:
                self._unsupported_paths.append(f"<path> geometry skipped: {exc}")
                return None
            if raw_bounds is None:
                return None
            outlines = path_outlines(data)
            outline = outlines[0] if len(outlines) == 1 else None
            return Bounds(*raw_bounds, tag, role, outline, len(outlines) != 1, element)
        return None

    def is_non_obstacle(self, element: ET.Element, bounds: Bounds) -> bool:
        if bounds.width <= 0 or bounds.height <= 0:
            return True
        if not self._paint_is_visible(element, "fill") and not self._paint_is_visible(element, "stroke"):
            return True
        dash = (self._presentation_value(element, "stroke-dasharray", "") or "").strip().lower()
        if dash and dash != "none":
            return True
        if bounds.width < 70 or bounds.height < 30:
            return True
        if self.viewbox:
            _, _, vb_width, vb_height = self.viewbox
            if bounds.width > vb_width * 0.7 or bounds.height > vb_height * 0.7:
                return True
        return False

    def is_arrow(self, element: ET.Element) -> bool:
        if local_name(element.tag) not in {"line", "polyline", "path"}:
            return False
        shorthand = self._presentation_value(element, "marker")
        if shorthand is not None:
            return shorthand.strip().lower() != "none"
        for attr in ("marker-start", "marker-mid", "marker-end"):
            value = self._presentation_value(element, attr)
            if value and value.strip().lower() != "none":
                return True
        return False

    def arrow_segments(self, element: ET.Element) -> list[tuple[Point, Point]]:
        tag = local_name(element.tag)
        if tag == "line":
            points = [(parse_float(element.get("x1")), parse_float(element.get("y1"))),
                      (parse_float(element.get("x2")), parse_float(element.get("y2")))]
            return list(zip(points, points[1:]))
        if tag == "polyline":
            points = parse_points(element.get("points"))
            return list(zip(points, points[1:]))
        if tag == "path":
            try:
                data = parse_path(element.get("d"))
            except ValueError as exc:
                detail = f"<path> arrow geometry skipped: {exc}"
                if detail not in self._unsupported_paths:
                    self._unsupported_paths.append(detail)
                return []
            segments: list[tuple[Point, Point]] = []
            for subpath in _sample_path_subpaths(data):
                segments.extend(zip(subpath, subpath[1:]))
            return segments
        return []

    def check_box_overlap(self) -> CheckResult:
        boxes = self.collect_obstacles()
        failures: list[str] = []
        candidates: list[str] = []
        container_roles = {"panel", "container"}
        for index, first in enumerate(boxes):
            for second in boxes[index + 1:]:
                if ((first.role in container_roles and first.contains(second))
                        or (second.role in container_roles and second.contains(first))):
                    continue
                intersects = shapes_intersect(first, second)
                if intersects is True:
                    failures.append(
                        f"{first.element} {format_bounds(first)} overlaps {second.element} {format_bounds(second)}"
                    )
                elif intersects is None:
                    ox, oy = overlap_area(first, second)
                    if ox > 1 and oy > 1:
                        candidates.append(
                            f"uncertain path overlap candidate: {first.element} {format_bounds(first)} vs "
                            f"{second.element} {format_bounds(second)}"
                        )
                if len(failures) + len(candidates) >= 12:
                    break
            if len(failures) + len(candidates) >= 12:
                break
        if failures:
            return CheckResult(
                "Checking box overlap", "fail", details=failures + candidates,
                fix="Move nodes apart. Only explicit data-role='panel'/'container' may contain nodes.",
            )
        if candidates:
            return CheckResult(
                "Checking box overlap", "warn", details=candidates,
                fix="Inspect complex path candidates visually or simplify them to a supported single outline.",
            )
        return CheckResult("Checking box overlap", "pass", f"{len(boxes)} box(es)")

    def check_arrow_collisions(self) -> CheckResult:
        assert self.root is not None
        obstacles = self.collect_obstacles()
        failures: list[str] = []
        candidates: list[str] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(name in {"defs", "marker", "clipPath", "filter"} for name in ancestors):
                continue
            if not self.is_arrow(element):
                continue
            if not self._paint_is_visible(element, "stroke"):
                continue
            if self._has_transform(element):
                # collect_obstacles() records the explicit unsupported-transform
                # warning. Do not hard-check untransformed coordinates.
                continue
            for start, end in self.arrow_segments(element):
                for obstacle in obstacles:
                    if obstacle.role in {"panel", "container"}:
                        continue
                    if obstacle.outline is not None:
                        hit = segment_crosses_polygon(start, end, obstacle.outline)
                        uncertain = False
                    else:
                        hit = segment_hits_aabb(start, end, obstacle)
                        uncertain = hit
                    if not hit:
                        continue
                    detail = (
                        f"<{local_name(element.tag)}> segment {format_point(start)}->{format_point(end)} "
                        f"crosses {obstacle.element} {format_bounds(obstacle)}"
                    )
                    (candidates if uncertain else failures).append(detail)
                    break
                if len(failures) + len(candidates) >= 12:
                    break
            if len(failures) + len(candidates) >= 12:
                break
        if failures:
            return CheckResult(
                "Checking arrow collisions", "fail", details=failures + candidates,
                fix="Route arrows around nodes with orthogonal paths and anchor endpoints on edges.",
            )
        if candidates:
            return CheckResult(
                "Checking arrow collisions", "warn", details=candidates,
                fix="Inspect the complex path candidate; its AABB intersects the arrow but its outline is ambiguous.",
            )
        return CheckResult("Checking arrow collisions", "pass", f"{len(obstacles)} obstacle(s)")

    def collect_labels(self) -> list[TextRun]:
        assert self.root is not None
        if self._labels is not None:
            return self._labels
        if self._stylesheet_has_transform():
            detail = "<style> transform rules are unresolved; all text geometry is skipped"
            if detail not in self._unsupported_transforms:
                self._unsupported_transforms.append(detail)
            self._labels = []
            return self._labels
        obstacles = self.collect_obstacles()
        runs: list[TextRun] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(name in {"defs", "marker", "clipPath", "filter"} for name in ancestors):
                continue
            if local_name(element.tag) != "text":
                continue
            if not self._paint_is_visible(element, "fill") and not self._paint_is_visible(element, "stroke"):
                continue
            if self._has_transform(element):
                detail = "<text> transform is not included in geometry checks"
                if detail not in self._unsupported_transforms:
                    self._unsupported_transforms.append(detail)
                continue
            descendants = list(element.iter())[1:]
            if descendants:
                tags = ", ".join(sorted({local_name(child.tag) for child in descendants}))
                self._unsupported_text.append(
                    f"nested/positioned <tspan> or child text content skipped ({tags}); "
                    "runs are not flattened into a synthetic line"
                )
                continue
            label = (element.text or "").strip()
            if not label:
                continue
            x, y = parse_float(element.get("x")), parse_float(element.get("y"))
            size = parse_float(self._presentation_value(element, "font-size", "14"), 14.0)
            estimated = text_width(label, int(round(size)))
            anchor = (self._presentation_value(element, "text-anchor", "start") or "start").lower()
            if anchor == "middle":
                left, right = x - estimated / 2, x + estimated / 2
            elif anchor == "end":
                left, right = x - estimated, x
            else:
                left, right = x, x + estimated
            half = size * 0.5
            bounds = Bounds(left, y - half, right, y + half, "text",
                            element.get("data-role"), _rect_outline(left, y - half, right, y + half),
                            source=element)
            containing = sorted(
                (obstacle for obstacle in obstacles if obstacle.contains_point((x, y), 2.0)),
                key=lambda obstacle: obstacle.area,
            )
            role = element.get("data-role")
            panels = [obstacle for obstacle in containing if obstacle.role in {"panel", "container"}]
            nodes = [obstacle for obstacle in containing if obstacle.role not in {"panel", "container"}]
            if role == "node-text":
                host = nodes[0] if nodes else None
                # Some generated box_text (notably actor labels) has no obstacle
                # host. Keep it in free-label collision checks instead of hiding it.
                free = host is None
            elif role in {"arrow-label", "legend-label"}:
                host, free = None, True
            elif role == "container-label":
                host, free = (panels[0] if panels else None), True
            elif nodes:
                host, free = nodes[0], False
            else:
                # Legacy hand-written SVG: a broad explicit panel must not capture
                # every caption as node text. Keep the panel as an ignorable host.
                host, free = (panels[0] if panels else None), True
            runs.append(TextRun(label, size, bounds, host, role, free))
        self._labels = runs
        return runs

    def check_text_overflow(self) -> CheckResult:
        issues: list[str] = []
        for run in self.collect_labels():
            if run.host is None or run.free:
                continue
            pad = 6.0
            if run.bounds.left < run.host.left + pad - 1 or run.bounds.right > run.host.right - pad + 1:
                issues.append(
                    f'"{run.label}" (~{run.bounds.width:.0f}px @ {run.size:g}) overflows '
                    f"{run.host.element} {format_bounds(run.host)}"
                )
        if issues:
            return CheckResult(
                "Checking text fit", "warn", details=issues[:12],
                fix="Size the box from its text; svgkit.node() does this automatically.",
            )
        return CheckResult("Checking text fit", "pass")

    def check_label_vs_box(self) -> CheckResult:
        obstacles = self.collect_obstacles()
        issues: list[str] = []
        for run in self.collect_labels():
            if not run.free:
                continue
            for obstacle in obstacles:
                if obstacle.role in {"panel", "container"}:
                    continue
                intersects = shapes_intersect(run.bounds, obstacle, tolerance=2.0)
                if intersects is True or intersects is None:
                    issues.append(
                        f'"{run.label}" (~{run.bounds.width:.0f}px @ {run.size:g}) overlaps '
                        f"{obstacle.element} {format_bounds(obstacle)}"
                    )
                    break
        if issues:
            return CheckResult(
                "Checking label vs box", "warn", details=issues[:12],
                fix="Shorten the label, widen the gap, or flip label_offset to the emptier side.",
            )
        return CheckResult("Checking label vs box", "pass")

    def check_label_vs_label(self) -> CheckResult:
        runs = [run for run in self.collect_labels() if run.free]
        issues: list[str] = []
        for index, first in enumerate(runs):
            for second in runs[index + 1:]:
                ox, oy = overlap_area(first.bounds, second.bounds)
                if ox > 2.0 and oy > 2.0:
                    issues.append(
                        f'"{first.label}" {format_bounds(first.bounds)} overlaps '
                        f'"{second.label}" {format_bounds(second.bounds)}'
                    )
        if issues:
            return CheckResult(
                "Checking label vs label", "warn", details=issues[:12],
                fix="Nudge label_offset or stagger neighboring labels by about 20px.",
            )
        return CheckResult("Checking label vs label", "pass")

    def check_unsupported_text_geometry(self) -> CheckResult:
        # collect_labels populates this list; force collection even when no other text check did.
        self.collect_labels()
        if self._unsupported_text:
            return CheckResult(
                "Checking unsupported text geometry", "warn",
                details=sorted(set(self._unsupported_text)),
                fix="Use separate plain <text> elements for positioned lines; <tspan> geometry is skipped.",
            )
        return CheckResult("Checking unsupported text geometry", "pass")

    def check_unsupported_transforms(self) -> CheckResult:
        self.collect_obstacles()
        self.collect_labels()
        details = sorted(set(self._unsupported_transforms + self._unsupported_paths))
        if details:
            return CheckResult(
                "Checking unsupported transforms", "warn", details=details,
                fix="Flatten transforms/complex paths before relying on collision checks; skipped geometry is not guessed.",
            )
        return CheckResult("Checking unsupported transforms", "pass")

    def check_box_viewbox_overflow(self) -> CheckResult:
        if not self.viewbox:
            return CheckResult("Checking box bounds vs viewBox", "warn", "skipped without viewBox")
        vb_x, vb_y, vb_w, vb_h = self.viewbox
        right, bottom = vb_x + vb_w, vb_y + vb_h
        issues: list[str] = []
        for bounds in self.collect_obstacles():
            sides: list[str] = []
            if bounds.left < vb_x - 0.5:
                sides.append(f"left={bounds.left:g} < {vb_x:g}")
            if bounds.right > right + 0.5:
                sides.append(f"right={bounds.right:g} > {right:g}")
            if bounds.top < vb_y - 0.5:
                sides.append(f"top={bounds.top:g} < {vb_y:g}")
            if bounds.bottom > bottom + 0.5:
                sides.append(f"bottom={bounds.bottom:g} > {bottom:g}")
            if sides:
                issues.append(f"{bounds.element} {format_bounds(bounds)}: {', '.join(sides)}")
        if issues:
            return CheckResult(
                "Checking box bounds vs viewBox", "fail", details=issues[:12],
                fix="Grow Diagram(w, h) or reposition the element inside the viewBox.",
            )
        return CheckResult("Checking box bounds vs viewBox", "pass")

    def check_type_scale(self) -> CheckResult:
        assert self.root is not None
        sizes: set[float] = set()
        headings = 0
        for element in self.root.iter():
            raw = self._presentation_value(element, "font-size")
            if local_name(element.tag) != "text" or raw is None:
                continue
            size = parse_float(raw)
            sizes.add(size)
            if size in {15.0, 16.0}:
                headings += 1
        if not sizes:
            return CheckResult("Checking type scale", "pass")
        allowed = {12.0, 14.0, 15.0, 16.0}
        offenders = sorted(sizes - allowed)
        rendered = ", ".join(f"{size:g}" for size in sorted(sizes))
        if offenders:
            return CheckResult(
                "Checking type scale", "fail", f"off-size(s): {rendered}",
                fix="Use 14 for titles, 12 for all other text, and at most one 15-16 heading.",
            )
        if headings > 1 or len(sizes) > 3:
            return CheckResult(
                "Checking type scale", "warn",
                f"{headings} heading-size elements; sizes={rendered}",
                fix="Keep at most one 15-16 heading and collapse the rest to 14/12.",
            )
        return CheckResult("Checking type scale", "pass", rendered)

    def check_text_baseline(self) -> CheckResult:
        assert self.root is not None
        missing = sum(
            1 for element in self.root.iter()
            if local_name(element.tag) == "text" and element.get("dominant-baseline") is None
        )
        if missing:
            return CheckResult(
                "Checking text baseline", "warn", f"{missing} <text> without dominant-baseline",
                fix='Add dominant-baseline="central" for predictable vertical alignment.',
            )
        return CheckResult("Checking text baseline", "pass")

    def check_palette(self) -> CheckResult:
        assert self.root is not None
        cold: dict[str, int] = {}
        for element in self.root.iter():
            for attr in ("fill", "stroke"):
                value = self._presentation_value(element, attr)
                if not value or value.strip().lower() in COLOR_KEYWORDS_OK:
                    continue
                if is_cold_color(value):
                    key = normalize_hex(value) or value.strip().lower()
                    cold[key] = cold.get(key, 0) + 1
        if cold:
            details = [f"{value} (x{count})" for value, count in sorted(cold.items())]
            return CheckResult(
                "Checking warm palette", "warn", details=details[:12],
                fix="Replace cold gray/blue with the warm family fills and lines.",
            )
        return CheckResult("Checking warm palette", "pass")

    def check_closing_tag(self) -> CheckResult:
        if re.search(r"</\s*svg\s*>\s*$", self.text, flags=re.I):
            return CheckResult("Checking closing tag", "pass")
        return CheckResult(
            "Checking closing tag", "fail", "missing final </svg>",
            fix="Add </svg> as the final non-whitespace content.",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated SVG diagrams.")
    parser.add_argument("svg_file", type=Path, nargs="+", help="SVG file(s) to validate")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="stay silent for clean files; print only warnings and failures",
    )
    args = parser.parse_args()

    worst = 0
    for index, path in enumerate(args.svg_file):
        if not args.quiet and index:
            print()
        worst = max(worst, Validator(path, no_color=args.no_color).run(quiet=args.quiet))
    return worst


if __name__ == "__main__":
    sys.exit(main())
