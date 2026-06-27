#!/usr/bin/env python3
"""Robust SVG validator for visualize.

Run directly: ``python3 scripts/validate_svg.py <file>``. The parsing-heavy
checks live in Python so they work consistently from Git Bash, macOS, Linux,
and CI.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


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
        match = re.match(r"-?\d+(?:\.\d+)?", value.strip())
        return float(match.group(0)) if match else default


def parse_points(value: str | None) -> list[tuple[float, float]]:
    if not value:
        return []
    nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", value)]
    return list(zip(nums[::2], nums[1::2]))


def iter_with_ancestors(root: ET.Element) -> Iterable[tuple[ET.Element, list[str]]]:
    stack: list[tuple[ET.Element, list[str]]] = [(root, [])]
    while stack:
        element, ancestors = stack.pop()
        yield element, ancestors
        next_ancestors = ancestors + [local_name(element.tag)]
        for child in reversed(list(element)):
            stack.append((child, next_ancestors))


# --------------------------------------------------------------------------- #
# Shared text measurement. svgkit.text_width is the single source of truth; this
# file is usually run as scripts/validate_svg.py so `import svgkit` resolves from
# the same directory. A local copy keeps the validator working if svgkit is gone.
# --------------------------------------------------------------------------- #
try:
    from svgkit import text_width  # type: ignore
except Exception:  # pragma: no cover - fallback mirrors svgkit.text_width
    def text_width(s: str, size: int = 14) -> float:
        import unicodedata
        latin = size * 8 / 14
        wide = size * 15 / 14
        return sum(wide if unicodedata.east_asian_width(ch) in ("W", "F") else latin
                   for ch in s)


# The warm house palette (mirrors references/style.md). Colors outside this set
# that read as cold (gray/blue) are flagged; warm custom tints are left alone.
WARM_PALETTE: set[str] = {
    # family fill / stroke / title / sub / line
    "#f5f4ed", "#141413", "#3d3d3a", "#73726c",
    "#e1f5ee", "#0f6e56", "#085041", "#1d9e75",
    "#eeedfe", "#534ab7", "#3c3489", "#7f77dd",
    "#faece7", "#993c1d", "#712b13", "#c75b38",
    "#faeeda", "#854f0b", "#633806", "#ef9f27",
    # decorative pastels — whitelisted because the warm-hue test would false-positive on them
    "#fac775", "#f5c4b3", "#9fe1cb", "#cecbf6", "#f4c0d1", "#c0dd97", "#b5d4f4",
    # alt neutrals + canvas + ink seen in the examples
    "#f1efe8", "#5f5e5a", "#ffffff", "#000000", "#fff",
}
COLOR_KEYWORDS_OK = {"none", "transparent", "context-stroke", "currentcolor", "inherit"}


def normalize_hex(value: str) -> str | None:
    """Return a 6-digit lowercase #rrggbb, expanding #rgb. None if not a hex color."""
    v = value.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", v)
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h


def is_cold_color(value: str) -> bool:
    """True for clearly cold (blue-dominant) hex colors not in the warm palette."""
    hx = normalize_hex(value)
    if hx is None or hx in WARM_PALETTE:
        return False
    r = int(hx[1:3], 16)
    g = int(hx[3:5], 16)
    b = int(hx[5:7], 16)
    # Cold = blue clearly above red and roughly tied with green (b > r+12 and
    # b >= g-4); catches Tailwind blue/slate/sky without flagging warm tints.
    return b > r + 12 and b >= g - 4


@dataclass
class CheckResult:
    name: str
    status: str
    message: str = ""
    details: list[str] | None = None
    fix: str = ""


@dataclass
class Bounds:
    left: float
    top: float
    right: float
    bottom: float
    element: str

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def area(self) -> float:
        return self.width * self.height


class Validator:
    def __init__(self, svg_path: Path, no_color: bool = False) -> None:
        self.svg_path = svg_path
        self.no_color = no_color
        self.text = ""
        self.root: ET.Element | None = None
        self.failures = 0
        self.warnings = 0
        self.viewbox: tuple[float, float, float, float] | None = None

    def run(self) -> int:
        print(f"Validating SVG: {self.svg_path}")
        print("----------------------------------------")

        for result in self.check_file_and_xml():
            self.report(result)
            if result.status == "fail":
                print("----------------------------------------")
                print(color("Validation failed (XML parse error)", "red", not self.no_color))
                return 1

        checks = [
            self.check_svg_root,
            self.check_viewbox,
            self.check_renderer_compatibility,
            self.check_references,
            self.check_paint_order_occlusion,
            self.check_object_spacing,
            self.check_arrow_collisions,
            self.check_box_viewbox_overflow,
            self.check_text_overflow,
            self.check_text_collisions,
            self.check_type_scale,
            self.check_text_baseline,
            self.check_palette,
            self.check_filter_boundaries,
            self.check_closing_tag,
        ]

        for check in checks:
            self.report(check())

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
            return [CheckResult("Checking file", "fail", f"not found: {self.svg_path}", fix="Check the file path and ensure the SVG was generated")]

        try:
            self.text = self.svg_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            return [CheckResult("Reading UTF-8", "fail", str(exc), fix="Save the SVG as UTF-8 encoding")]

        try:
            self.root = ET.fromstring(self.text)
        except ET.ParseError as exc:
            return [
                CheckResult("Reading UTF-8", "pass"),
                CheckResult("Checking XML syntax", "fail", str(exc), fix="Check for unquoted attributes, unclosed tags, or stray characters. Regenerate with svgkit (scripts/svgkit.py)."),
            ]

        return [
            CheckResult("Reading UTF-8", "pass"),
            CheckResult("Checking XML syntax", "pass"),
        ]

    def check_svg_root(self) -> CheckResult:
        assert self.root is not None
        if local_name(self.root.tag) != "svg":
            return CheckResult("Checking SVG root", "fail", f"root tag is <{local_name(self.root.tag)}>", fix="Wrap content in an <svg> root element")
        return CheckResult("Checking SVG root", "pass")

    def check_viewbox(self) -> CheckResult:
        assert self.root is not None
        viewbox = self.root.get("viewBox")
        if not viewbox:
            return CheckResult("Checking viewBox", "fail", "missing viewBox", fix="Add viewBox='0 0 960 600' (or appropriate dimensions) to the <svg> element")
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", viewbox)]
        if len(nums) != 4 or nums[2] <= 0 or nums[3] <= 0:
            return CheckResult("Checking viewBox", "fail", f"invalid viewBox={viewbox!r}", fix="viewBox needs 4 numbers: 'min-x min-y width height' with positive width and height")
        self.viewbox = (nums[0], nums[1], nums[2], nums[3])
        return CheckResult("Checking viewBox", "pass", f"{nums[2]:g}x{nums[3]:g}")

    def check_renderer_compatibility(self) -> CheckResult:
        assert self.root is not None
        details: list[str] = []

        for element in self.root.iter():
            tag = local_name(element.tag)
            if tag == "style" and element.text:
                if "@import" in element.text:
                    details.append("<style> contains @import; renderers cannot fetch remote fonts")
                if re.search(r"url\(\s*['\"]?https?://", element.text):
                    details.append("<style> contains remote url(...); inline assets instead")
            for key, value in element.attrib.items():
                attr = local_name(key)
                if attr in {"href", "src"} and re.match(r"https?://|//", value):
                    details.append(f"<{tag}> has external {attr}={value!r}")

        if details:
            return CheckResult("Checking renderer-safe assets", "fail", details=details[:8], fix="Replace @import with inline <style> font stacks. Replace external url() with inline SVG. Remove external href/src references.")
        return CheckResult("Checking renderer-safe assets", "pass")

    def check_references(self) -> CheckResult:
        assert self.root is not None
        ids: dict[str, str] = {}
        marker_ids: set[str] = set()
        refs: list[tuple[str, str, str]] = []

        for element in self.root.iter():
            tag = local_name(element.tag)
            element_id = element.get("id")
            if element_id:
                ids[element_id] = tag
                if tag == "marker":
                    marker_ids.add(element_id)
            for attr, value in element.attrib.items():
                attr_name = local_name(attr)
                for ref_id in re.findall(r"url\(#([^)]+)\)", value):
                    refs.append((tag, attr_name, ref_id))

        missing: list[str] = []
        wrong_marker: list[str] = []
        for tag, attr, ref_id in refs:
            if ref_id not in ids:
                missing.append(f"<{tag}> {attr}=url(#{ref_id}) has no matching id")
            elif attr in {"marker-start", "marker-mid", "marker-end"} and ref_id not in marker_ids:
                wrong_marker.append(f"<{tag}> {attr}=url(#{ref_id}) points to <{ids[ref_id]}>")

        details = missing + wrong_marker
        if details:
            return CheckResult("Checking URL/marker references", "fail", details=details[:12], fix="Add missing id attributes to <defs> elements, or ensure marker-end references point to <marker> elements")
        return CheckResult("Checking URL/marker references", "pass", f"{len(refs)} reference(s)")

    def check_paint_order_occlusion(self) -> CheckResult:
        """Catch filled shapes painted after text, which visually block labels."""
        assert self.root is not None
        texts: list[tuple[int, Bounds, str]] = []
        occluders: list[tuple[int, Bounds, str]] = []

        for index, (element, ancestors) in enumerate(iter_with_ancestors(self.root)):
            if any(a in {"defs", "marker", "clipPath", "filter"} for a in ancestors):
                continue
            tag = local_name(element.tag)
            if tag == "text":
                bounds = self.text_bounds(element)
                label = text_content(element)
                if bounds is not None and label:
                    texts.append((index, bounds, label))
                continue
            if not self.is_filled_shape(element):
                continue
            bounds = self.shape_bounds(element)
            if bounds is None or bounds.width <= 0 or bounds.height <= 0:
                continue
            occluders.append((index, bounds, tag))

        issues: list[str] = []
        for shape_index, shape_bounds, tag in occluders:
            for text_index, text_bounds, label in texts:
                if text_index >= shape_index:
                    continue
                if not bounds_overlap_significant(shape_bounds, text_bounds):
                    continue
                issues.append(
                    f"<{tag}> painted later at {format_bounds(shape_bounds)} overlaps text "
                    f"{label!r} {format_bounds(text_bounds)}"
                )
                break
            if len(issues) >= 8:
                break

        if issues:
            return CheckResult(
                "Checking paint-order occlusion", "fail", details=issues,
                fix="Keep z-order back-to-front: containers → arrows → plates → boxes → box text → labels → legend. Move filled shapes before the text they support.",
            )
        return CheckResult("Checking paint-order occlusion", "pass")

    def check_object_spacing(self) -> CheckResult:
        """DRC-style box/shape clearance: no overlapping obstacles, 8px minimum air."""
        obstacles = self.collect_obstacles()
        overlaps: list[str] = []
        tight: list[str] = []
        min_gap = 8.0

        for i, first in enumerate(obstacles):
            for second in obstacles[i + 1:]:
                if bounds_contains(first, second) or bounds_contains(second, first):
                    continue
                area = bounds_intersection_area(first, second)
                if area > 1:
                    overlaps.append(
                        f"{first.element} {format_bounds(first)} overlaps "
                        f"{second.element} {format_bounds(second)}"
                    )
                else:
                    gap = bounds_gap(first, second)
                    if gap < min_gap:
                        tight.append(
                            f"{first.element} {format_bounds(first)} is {gap:.1f}px from "
                            f"{second.element} {format_bounds(second)}"
                        )
                if len(overlaps) >= 8 or len(tight) >= 8:
                    break
            if len(overlaps) >= 8 or len(tight) >= 8:
                break

        if overlaps:
            return CheckResult(
                "Checking object spacing", "fail", details=overlaps,
                fix="Move sibling boxes/shapes apart. Keep at least 8px of air; use panels only as containing parents, not overlapping peers.",
            )
        if tight:
            return CheckResult(
                "Checking object spacing", "warn", details=tight,
                fix="Increase clearance to at least 8px between solid obstacles; normal node gaps should stay 40–75px horizontally and 56–60px vertically.",
            )
        return CheckResult("Checking object spacing", "pass", f"{len(obstacles)} obstacle(s)")

    def check_arrow_collisions(self) -> CheckResult:
        assert self.root is not None
        obstacles = self.collect_obstacles()
        collisions: list[str] = []

        for element, ancestors in iter_with_ancestors(self.root):
            if any(a in {"defs", "marker", "clipPath", "filter"} for a in ancestors):
                continue
            if not self.is_arrow(element):
                continue

            points = self.arrow_points(element)
            if len(points) < 2:
                continue

            tag = local_name(element.tag)
            for p1, p2 in zip(points, points[1:]):
                for bounds in obstacles:
                    if self.segment_hits_bounds(p1, p2, bounds):
                        collisions.append(
                            f"<{tag}> segment {format_point(p1)}->{format_point(p2)} crosses {bounds.element} "
                            f"{format_bounds(bounds)}"
                        )
                        break
                if collisions and len(collisions) >= 12:
                    break
            if len(collisions) >= 12:
                break

        if collisions:
            return CheckResult("Checking arrow collisions", "fail", details=collisions, fix="Route arrows with orthogonal L-shaped paths around nodes. Anchor on component edges, not centers. Use polyline/path for multi-segment routes.")
        return CheckResult("Checking arrow collisions", "pass", f"{len(obstacles)} obstacle(s)")

    def collect_obstacles(self) -> list[Bounds]:
        assert self.root is not None
        obstacles: list[Bounds] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(a in {"defs", "marker", "clipPath", "filter"} for a in ancestors):
                continue
            bounds = self.shape_bounds(element)
            if bounds is None or self.is_non_obstacle(element, bounds):
                continue
            obstacles.append(bounds)
        return obstacles

    def shape_bounds(self, element: ET.Element) -> Bounds | None:
        tag = local_name(element.tag)
        if tag == "rect":
            x = parse_float(element.get("x"))
            y = parse_float(element.get("y"))
            width = parse_float(element.get("width"))
            height = parse_float(element.get("height"))
            return Bounds(x, y, x + width, y + height, "rect")
        if tag == "circle":
            r = parse_float(element.get("r"))
            cx = parse_float(element.get("cx"))
            cy = parse_float(element.get("cy"))
            return Bounds(cx - r, cy - r, cx + r, cy + r, "circle")
        if tag == "ellipse":
            rx = parse_float(element.get("rx"))
            ry = parse_float(element.get("ry"))
            cx = parse_float(element.get("cx"))
            cy = parse_float(element.get("cy"))
            return Bounds(cx - rx, cy - ry, cx + rx, cy + ry, "ellipse")
        if tag in {"polygon", "polyline"}:
            points = parse_points(element.get("points"))
            if not points:
                return None
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            return Bounds(min(xs), min(ys), max(xs), max(ys), tag)
        if tag == "path":
            points = parse_path_points(element.get("d"))
            if not points:
                return None
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            return Bounds(min(xs), min(ys), max(xs), max(ys), "path")
        return None

    def text_bounds(self, element: ET.Element) -> Bounds | None:
        label = text_content(element)
        if not label:
            return None
        x = parse_float(element.get("x"))
        y = parse_float(element.get("y"))
        size = parse_float(element.get("font-size"), 14.0)
        est = text_width(label, int(round(size)))
        letter_spacing = parse_float(element.get("letter-spacing"), 0.0)
        if letter_spacing and len(label) > 1:
            est += letter_spacing * (len(label) - 1)
        anchor = element.get("text-anchor", "start")
        if anchor == "middle":
            left, right = x - est / 2, x + est / 2
        elif anchor == "end":
            left, right = x - est, x
        else:
            left, right = x, x + est
        baseline = (element.get("dominant-baseline") or "").lower()
        line_h = size * 1.2
        if baseline in {"central", "middle", "mathematical"}:
            top, bottom = y - line_h / 2, y + line_h / 2
        else:
            top, bottom = y - size, y + size * 0.25
        return Bounds(left, top, right, bottom, "text")

    def text_host(self, element: ET.Element, bounds: Bounds, obstacles: list[Bounds]) -> Bounds | None:
        x = parse_float(element.get("x"))
        y = parse_float(element.get("y"))
        host = None
        for obstacle in obstacles:
            if not (obstacle.left <= x <= obstacle.right and obstacle.top - 2 <= y <= obstacle.bottom + 2):
                continue
            if host is None or obstacle.area < host.area:
                host = obstacle
        return host

    def is_filled_shape(self, element: ET.Element) -> bool:
        tag = local_name(element.tag)
        if tag not in {"rect", "circle", "ellipse", "polygon", "polyline", "path"}:
            return False
        fill = (element.get("fill") or "#000000").strip().lower()
        return fill not in {"none", "transparent"}

    def is_non_obstacle(self, element: ET.Element, bounds: Bounds) -> bool:
        """True for shapes the collision check should ignore: zero-size, dashed,
        hollow or stroke-only connectors, tiny (<70 wide or <30 tall), or
        near-full-canvas (>70% of the viewBox)."""
        if bounds.width <= 0 or bounds.height <= 0:
            return True
        tag = local_name(element.tag)
        fill = (element.get("fill") or "").strip().lower()
        if tag in {"line", "polyline", "path"} and fill in {"", "none", "transparent"}:
            return True
        if element.get("stroke-dasharray"):
            return True
        if fill in {"none", "transparent"} and not element.get("stroke"):
            return True
        if bounds.width < 70 or bounds.height < 30:
            return True
        if self.viewbox:
            _, _, vb_width, vb_height = self.viewbox
            if bounds.width > vb_width * 0.7 or bounds.height > vb_height * 0.7:
                return True
        return False

    def is_arrow(self, element: ET.Element) -> bool:
        tag = local_name(element.tag)
        if tag not in {"line", "polyline", "path"}:
            return False
        return any(
            element.get(attr)
            for attr in ("marker-start", "marker-mid", "marker-end")
        )

    def arrow_points(self, element: ET.Element) -> list[tuple[float, float]]:
        tag = local_name(element.tag)
        if tag == "line":
            return [
                (parse_float(element.get("x1")), parse_float(element.get("y1"))),
                (parse_float(element.get("x2")), parse_float(element.get("y2"))),
            ]
        if tag == "polyline":
            return parse_points(element.get("points"))
        if tag == "path":
            return parse_path_points(element.get("d"))
        return []

    def segment_hits_bounds(
        self,
        p1: tuple[float, float],
        p2: tuple[float, float],
        bounds: Bounds,
    ) -> bool:
        x1, y1 = p1
        x2, y2 = p2
        left, top, right, bottom = bounds.left, bounds.top, bounds.right, bounds.bottom
        eps = 1e-6

        if abs(y1 - y2) < eps:
            y = y1
            if not (top + eps < y < bottom - eps):
                return False
            seg_left = min(x1, x2)
            seg_right = max(x1, x2)
            overlap_left = max(seg_left, left)
            overlap_right = min(seg_right, right)
            if overlap_right - overlap_left <= eps:
                return False
            if point_near_edge(p1, bounds) or point_near_edge(p2, bounds):
                return False
            return True

        if abs(x1 - x2) < eps:
            x = x1
            if not (left + eps < x < right - eps):
                return False
            seg_top = min(y1, y2)
            seg_bottom = max(y1, y2)
            overlap_top = max(seg_top, top)
            overlap_bottom = min(seg_bottom, bottom)
            if overlap_bottom - overlap_top <= eps:
                return False
            if point_near_edge(p1, bounds) or point_near_edge(p2, bounds):
                return False
            return True

        return False

    def check_text_overflow(self) -> CheckResult:
        """Flag <text> that is wider than the box it sits in — the #1 failure."""
        assert self.root is not None
        obstacles = self.collect_obstacles()
        issues: list[str] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(a in {"defs", "marker", "clipPath", "filter"} for a in ancestors):
                continue
            if local_name(element.tag) != "text":
                continue
            label = text_content(element)
            if not label:
                continue
            bounds = self.text_bounds(element)
            if bounds is None:
                continue
            size = parse_float(element.get("font-size"), 14.0)
            host = self.text_host(element, bounds, obstacles)
            if host is None:
                continue
            pad = 6.0
            if bounds.left < host.left + pad - 1 or bounds.right > host.right - pad + 1:
                issues.append(
                    f'"{label}" (~{bounds.width:.0f}px @ {size:g}) overflows box '
                    f"{format_bounds(host)} (width {host.width:g})"
                )
            if len(issues) >= 8:
                break
        if issues:
            return CheckResult("Checking text fit", "warn", details=issues, fix="Size boxes from the text: boxWidth = max(line widths) + 32, line ~= latin*8 + cjk*15 at 14px. svgkit.node() does this automatically.")
        return CheckResult("Checking text fit", "pass")

    def check_text_collisions(self) -> CheckResult:
        """Treat each text run as a DRC object: it must not collide with peers, nodes, or uncovered arrows."""
        assert self.root is not None
        obstacles = self.collect_obstacles()
        texts: list[tuple[int, ET.Element, Bounds, str, Bounds | None]] = []
        arrow_segments: list[tuple[str, tuple[float, float], tuple[float, float]]] = []
        plates: list[Bounds] = []

        for index, (element, ancestors) in enumerate(iter_with_ancestors(self.root)):
            if any(a in {"defs", "marker", "clipPath", "filter"} for a in ancestors):
                continue
            tag = local_name(element.tag)
            if tag == "text":
                bounds = self.text_bounds(element)
                label = text_content(element)
                if bounds is not None and label:
                    texts.append((index, element, bounds, label, self.text_host(element, bounds, obstacles)))
                continue
            if self.is_arrow(element):
                points = self.arrow_points(element)
                arrow_segments.extend((tag, p1, p2) for p1, p2 in zip(points, points[1:]))
                continue
            if tag == "rect" and (element.get("fill") or "").strip().lower() in {"#fff", "#ffffff", "white"}:
                plate = self.shape_bounds(element)
                if plate is not None and plate.width < 140 and plate.height <= 24:
                    plates.append(plate)

        node_issues: list[str] = []
        text_issues: list[str] = []
        arrow_issues: list[str] = []

        for _, _, text_box, label, host in texts:
            for obstacle in obstacles:
                if host is obstacle:
                    continue
                if bounds_contains(obstacle, text_box) and host is not None:
                    continue
                if not bounds_overlap_significant(text_box, obstacle):
                    continue
                node_issues.append(
                    f"text {label!r} {format_bounds(text_box)} overlaps {obstacle.element} "
                    f"{format_bounds(obstacle)}"
                )
                break
            if len(node_issues) >= 6:
                break

        for i, (_, _, first_box, first_label, first_host) in enumerate(texts):
            for _, _, second_box, second_label, second_host in texts[i + 1:]:
                if first_host is not None and first_host is second_host:
                    continue
                if not bounds_overlap_significant(first_box, second_box):
                    continue
                text_issues.append(
                    f"text {first_label!r} {format_bounds(first_box)} overlaps text "
                    f"{second_label!r} {format_bounds(second_box)}"
                )
                break
            if len(text_issues) >= 6:
                break

        for _, _, text_box, label, host in texts:
            if host is not None or any(bounds_contains(plate, text_box) for plate in plates):
                continue
            expanded = expand_bounds(text_box, -1.0)
            for tag, p1, p2 in arrow_segments:
                if segment_intersects_bounds(p1, p2, expanded):
                    arrow_issues.append(
                        f"text {label!r} {format_bounds(text_box)} overlaps <{tag}> segment "
                        f"{format_point(p1)}->{format_point(p2)} without a white plate"
                    )
                    break
            if len(arrow_issues) >= 6:
                break

        details = node_issues + text_issues + arrow_issues
        if details:
            return CheckResult(
                "Checking text collisions", "warn", details=details[:12],
                fix="Move labels away from nodes/arrows, stagger overlapping labels by ~20px, shorten long labels, or add a small #FFFFFF plate behind an arrow label.",
            )
        return CheckResult("Checking text collisions", "pass", f"{len(texts)} text object(s)")

    def check_box_viewbox_overflow(self) -> CheckResult:
        """Flag box/diamond/circle whose bounds spill past the viewBox.

        svgkit sizes boxes from their text, but the builder places them. If a
        box is laid out past the viewBox edge, renderers (and downstream PDF /
        image exports) clip it — even when its inner text technically fits.
        text-overflow can't catch this because the host box it locates is
        already outside the canvas.
        """
        assert self.root is not None
        if not self.viewbox:
            return CheckResult("Checking box bounds vs viewBox", "warn", "skipped without viewBox")

        vb_x, vb_y, vb_w, vb_h = self.viewbox
        vb_right, vb_bottom = vb_x + vb_w, vb_y + vb_h
        issues: list[str] = []
        # Use the same obstacle set the other fit checks use — that already
        # filters the background canvas rect, dashed containers, and tiny
        # decorative chips we don't want to police here.
        for b in self.collect_obstacles():
            eps = 0.5
            spill_x_lo = b.left < vb_x - eps
            spill_x_hi = b.right > vb_right + eps
            spill_y_lo = b.top < vb_y - eps
            spill_y_hi = b.bottom > vb_bottom + eps
            if not (spill_x_lo or spill_x_hi or spill_y_lo or spill_y_hi):
                continue
            sides = []
            if spill_x_lo:
                sides.append(f"left={b.left:g} < {vb_x:g}")
            if spill_x_hi:
                sides.append(f"right={b.right:g} > {vb_right:g}")
            if spill_y_lo:
                sides.append(f"top={b.top:g} < {vb_y:g}")
            if spill_y_hi:
                sides.append(f"bottom={b.bottom:g} > {vb_bottom:g}")
            issues.append(
                f"{b.element} {format_bounds(b)} spills past viewBox "
                f"({vb_w:g}x{vb_h:g}): {', '.join(sides)}"
            )
            if len(issues) >= 8:
                break

        if issues:
            return CheckResult(
                "Checking box bounds vs viewBox", "fail", details=issues,
                fix="Resize the canvas (Diagram(w, h)) or reposition the element so its bounds stay inside the viewBox. The same failure mode as text-overflow, one level up.",
            )
        return CheckResult("Checking box bounds vs viewBox", "pass")

    def check_type_scale(self) -> CheckResult:
        """A locked scale reads as designed: 14 + 12, plus at most one 15-16 heading."""
        assert self.root is not None
        sizes: set[float] = set()
        heading_uses = 0
        for element in self.root.iter():
            raw = element.get("font-size")
            if raw is None:
                continue
            size = parse_float(raw)
            sizes.add(size)
            if size in (15.0, 16.0):
                heading_uses += 1
        if not sizes:
            return CheckResult("Checking type scale", "pass")
        allowed = {12.0, 14.0, 15.0, 16.0}
        offenders = sorted(s for s in sizes if s not in allowed)
        ordered = ", ".join(f"{s:g}" for s in sorted(sizes))
        if offenders:
            return CheckResult(
                "Checking type scale", "fail", f"off-size(s): {ordered}",
                fix="Use exactly two sizes — 14 (titles, weight 500) and 12 (everything else) — plus at most one 15-16 heading. See references/style.md.",
            )
        details: list[str] = []
        if heading_uses > 1:
            details.append(f"{heading_uses} elements at 15-16px (at most one heading allowed)")
        if len(sizes) > 3:
            details.append(f"{len(sizes)} distinct sizes (collapse to 14 + 12 + one optional 15-16)")
        if details:
            return CheckResult(
                "Checking type scale", "warn", "; ".join(details),
                fix="Collapse to 14 + 12 (+ one optional 15-16 heading). More than that reads as a ransom note.",
            )
        return CheckResult("Checking type scale", "pass", ordered)

    def check_text_baseline(self) -> CheckResult:
        """Warn on <text> without dominant-baseline (unpredictable vertical alignment).

        The house style sets ``dominant-baseline="central"`` everywhere; text
        missing it relies on each renderer's default (alphabetic), which drifts.
        Warn-only so deliberate one-offs still pass.
        """
        assert self.root is not None
        missing = 0
        for element in self.root.iter():
            if local_name(element.tag) != "text":
                continue
            if element.get("dominant-baseline") is None:
                missing += 1
        if missing:
            return CheckResult(
                "Checking text baseline", "warn",
                f"{missing} <text> without dominant-baseline",
                fix='Add dominant-baseline="central" for predictable vertical alignment. See references/style.md.',
            )
        return CheckResult("Checking text baseline", "pass")

    def check_palette(self) -> CheckResult:
        """Warn on cold gray/blue colors — the house palette is warm only."""
        assert self.root is not None
        cold: dict[str, int] = {}
        for element in self.root.iter():
            for attr in ("fill", "stroke"):
                value = element.get(attr)
                if not value or value.strip().lower() in COLOR_KEYWORDS_OK:
                    continue
                if is_cold_color(value):
                    key = normalize_hex(value) or value.strip().lower()
                    cold[key] = cold.get(key, 0) + 1
        if cold:
            details = [f"{c} (x{n})" for c, n in sorted(cold.items(), key=lambda kv: -kv[1])][:8]
            return CheckResult("Checking warm palette", "warn", details=details, fix="Replace cold gray/blue with the warm family fills/lines (e.g. #F5F4ED, #E1F5EE, #73726C). See references/style.md.")
        return CheckResult("Checking warm palette", "pass")

    def check_filter_boundaries(self) -> CheckResult:
        assert self.root is not None
        if not self.viewbox:
            return CheckResult("Checking filter boundaries", "warn", "skipped without viewBox")

        _, _, vb_width, vb_height = self.viewbox
        issues: list[str] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(a in {"defs", "marker", "clipPath", "filter"} for a in ancestors):
                continue
            if not element.get("filter"):
                continue
            bounds = self.shape_bounds(element)
            if bounds is None:
                continue
            margin = max(24.0, min(bounds.width, bounds.height) * 0.2)
            if (
                bounds.left < margin
                or bounds.top < margin
                or bounds.right > vb_width - margin
                or bounds.bottom > vb_height - margin
            ):
                issues.append(
                    f"filtered {bounds.element} {format_bounds(bounds)} is within {margin:g}px of viewBox edge"
                )

        if issues:
            return CheckResult("Checking filter boundaries", "warn", details=issues[:8], fix="Move filtered elements at least 30px away from viewBox edges, or enlarge the viewBox. Filters extend ~20% beyond the bounding box.")
        return CheckResult("Checking filter boundaries", "pass")

    def check_closing_tag(self) -> CheckResult:
        if re.search(r"</\s*svg\s*>\s*$", self.text, flags=re.I):
            return CheckResult("Checking closing tag", "pass")
        return CheckResult("Checking closing tag", "fail", "missing final </svg>", fix="Add </svg> at the end of the file. When using the Python list method, ensure lines.append('</svg>') is the last append.")


def text_content(element: ET.Element) -> str:
    return "".join(element.itertext()).strip()


def bounds_intersection_area(a: Bounds, b: Bounds) -> float:
    width = min(a.right, b.right) - max(a.left, b.left)
    height = min(a.bottom, b.bottom) - max(a.top, b.top)
    if width <= 0 or height <= 0:
        return 0.0
    return width * height


def bounds_overlap_significant(
    a: Bounds,
    b: Bounds,
    min_axis_overlap: float = 2.0,
    min_area: float = 8.0,
) -> bool:
    width = min(a.right, b.right) - max(a.left, b.left)
    height = min(a.bottom, b.bottom) - max(a.top, b.top)
    return width >= min_axis_overlap and height >= min_axis_overlap and width * height >= min_area


def bounds_contains(outer: Bounds, inner: Bounds, tolerance: float = 1.0) -> bool:
    return (
        outer.left - tolerance <= inner.left
        and outer.top - tolerance <= inner.top
        and outer.right + tolerance >= inner.right
        and outer.bottom + tolerance >= inner.bottom
    )


def bounds_gap(a: Bounds, b: Bounds) -> float:
    if a.right < b.left:
        dx = b.left - a.right
    elif b.right < a.left:
        dx = a.left - b.right
    else:
        dx = 0.0
    if a.bottom < b.top:
        dy = b.top - a.bottom
    elif b.bottom < a.top:
        dy = a.top - b.bottom
    else:
        dy = 0.0
    return math.hypot(dx, dy)


def expand_bounds(bounds: Bounds, amount: float) -> Bounds:
    left = bounds.left - amount
    top = bounds.top - amount
    right = bounds.right + amount
    bottom = bounds.bottom + amount
    if right < left:
        mid = (left + right) / 2
        left = right = mid
    if bottom < top:
        mid = (top + bottom) / 2
        top = bottom = mid
    return Bounds(left, top, right, bottom, bounds.element)


def point_in_bounds(point: tuple[float, float], bounds: Bounds) -> bool:
    x, y = point
    return bounds.left <= x <= bounds.right and bounds.top <= y <= bounds.bottom


def segments_intersect(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    def orientation(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

    def on_segment(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> bool:
        return (
            min(p[0], r[0]) - 1e-6 <= q[0] <= max(p[0], r[0]) + 1e-6
            and min(p[1], r[1]) - 1e-6 <= q[1] <= max(p[1], r[1]) + 1e-6
        )

    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)

    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    eps = 1e-6
    return (
        abs(o1) <= eps and on_segment(a1, b1, a2)
        or abs(o2) <= eps and on_segment(a1, b2, a2)
        or abs(o3) <= eps and on_segment(b1, a1, b2)
        or abs(o4) <= eps and on_segment(b1, a2, b2)
    )


def segment_intersects_bounds(
    p1: tuple[float, float],
    p2: tuple[float, float],
    bounds: Bounds,
) -> bool:
    if p1 == p2:
        return point_in_bounds(p1, bounds)
    if point_in_bounds(p1, bounds) or point_in_bounds(p2, bounds):
        return True
    if max(p1[0], p2[0]) < bounds.left or min(p1[0], p2[0]) > bounds.right:
        return False
    if max(p1[1], p2[1]) < bounds.top or min(p1[1], p2[1]) > bounds.bottom:
        return False
    corners = [
        (bounds.left, bounds.top),
        (bounds.right, bounds.top),
        (bounds.right, bounds.bottom),
        (bounds.left, bounds.bottom),
    ]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    return any(segments_intersect(p1, p2, edge1, edge2) for edge1, edge2 in edges)


def point_near_edge(point: tuple[float, float], bounds: Bounds, tolerance: float = 2.0) -> bool:
    x, y = point
    inside_x = bounds.left - tolerance <= x <= bounds.right + tolerance
    inside_y = bounds.top - tolerance <= y <= bounds.bottom + tolerance
    if not (inside_x and inside_y):
        return False
    return (
        abs(x - bounds.left) <= tolerance
        or abs(x - bounds.right) <= tolerance
        or abs(y - bounds.top) <= tolerance
        or abs(y - bounds.bottom) <= tolerance
    )


def format_point(point: tuple[float, float]) -> str:
    return f"({point[0]:g},{point[1]:g})"


def format_bounds(bounds: Bounds) -> str:
    return f"[{bounds.left:g},{bounds.top:g},{bounds.right:g},{bounds.bottom:g}]"


def parse_path_points(d: str | None) -> list[tuple[float, float]]:
    """Extract a best-effort point list from common SVG path commands.

    The collision check only treats horizontal/vertical segments as blocking.
    That keeps curved arrows from creating false positives while still checking
    the orthogonal route segments this skill recommends.
    """

    if not d:
        return []
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", d)
    points: list[tuple[float, float]] = []
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    command = ""
    index = 0

    def next_number() -> float | None:
        nonlocal index
        if index >= len(tokens) or re.match(r"[A-Za-z]", tokens[index]):
            return None
        value = float(tokens[index])
        index += 1
        return value

    def read_pair(relative: bool) -> tuple[float, float] | None:
        x = next_number()
        y = next_number()
        if x is None or y is None:
            return None
        if relative:
            return (current[0] + x, current[1] + y)
        return (x, y)

    while index < len(tokens):
        token = tokens[index]
        if re.match(r"[A-Za-z]", token):
            command = token
            index += 1

        if not command:
            break

        cmd = command
        lower = cmd.lower()
        relative = cmd.islower()

        if lower == "m":
            pair = read_pair(relative)
            if pair is None:
                break
            current = pair
            start = pair
            points.append(current)
            command = "l" if relative else "L"
        elif lower == "l":
            pair = read_pair(relative)
            if pair is None:
                break
            current = pair
            points.append(current)
        elif lower == "h":
            x = next_number()
            if x is None:
                break
            current = (current[0] + x, current[1]) if relative else (x, current[1])
            points.append(current)
        elif lower == "v":
            y = next_number()
            if y is None:
                break
            current = (current[0], current[1] + y) if relative else (current[0], y)
            points.append(current)
        elif lower in {"c", "s", "q", "t", "a"}:
            # Curves are sampled only by their endpoint. Orthogonal collision
            # checks will ignore the resulting diagonal segment unless the curve
            # begins/ends on the same x or y.
            counts = {"c": 6, "s": 4, "q": 4, "t": 2, "a": 7}
            needed = counts[lower]
            values: list[float] = []
            for _ in range(needed):
                value = next_number()
                if value is None:
                    return points
                values.append(value)
            if lower == "a":
                end = (values[5], values[6])
            else:
                end = (values[-2], values[-1])
            current = (current[0] + end[0], current[1] + end[1]) if relative else end
            points.append(current)
        elif lower == "z":
            current = start
            points.append(current)
        else:
            break

        if index < len(tokens) and re.match(r"[A-Za-z]", tokens[index]):
            continue

    # Drop repeated points so zero-length path fragments do not confuse checks.
    deduped: list[tuple[float, float]] = []
    for point in points:
        if not deduped or math.dist(deduped[-1], point) > 1e-6:
            deduped.append(point)
    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated SVG diagram.")
    parser.add_argument("svg_file", type=Path, help="SVG file to validate")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    args = parser.parse_args()

    return Validator(args.svg_file, no_color=args.no_color).run()


if __name__ == "__main__":
    sys.exit(main())
