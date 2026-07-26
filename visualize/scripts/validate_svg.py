#!/usr/bin/env python3
"""Robust SVG validator for visualize.

Run directly: ``python3 scripts/validate_svg.py <file>``.
Agent-friendly summary: ``python3 scripts/validate_svg.py -q <file>`` (one-line
OK/FAIL; failures and warnings still print with fix hints).

The parsing-heavy checks live in Python so they work consistently from Git Bash,
macOS, Linux, and CI.
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
    "#f1efe8", "#dad8cf", "#5f5e5a", "#ffffff", "#000000", "#fff",
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
    # Saturation filter: near-grays (all channels close) are not cold even if
    # slightly blue-dominant — avoids false-positives on light warm grays.
    if max(r, g, b) - min(r, g, b) <= 15:
        return False
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


class Validator:
    def __init__(self, svg_path: Path, no_color: bool = False,
                 quiet: bool = False) -> None:
        self.svg_path = svg_path
        self.no_color = no_color
        self.quiet = quiet
        self.text = ""
        self.root: ET.Element | None = None
        self.failures = 0
        self.warnings = 0
        self.viewbox: tuple[float, float, float, float] | None = None

    def run(self) -> int:
        if not self.quiet:
            print(f"Validating SVG: {self.svg_path}")
            print("----------------------------------------")

        for result in self.check_file_and_xml():
            self.report(result)
            if result.status == "fail":
                if self.quiet:
                    print(color(f"FAIL {self.svg_path} (XML parse error)", "red", not self.no_color))
                else:
                    print("----------------------------------------")
                    print(color("Validation failed (XML parse error)", "red", not self.no_color))
                return 1

        checks = [
            self.check_svg_root,
            self.check_viewbox,
            self.check_accessibility,
            self.check_renderer_compatibility,
            self.check_flat_style,
            self.check_references,
            self.check_arrow_collisions,
            self.check_box_overlaps,
            self.check_box_viewbox_overflow,
            self.check_text_overflow,
            self.check_label_overhang,
            self.check_type_scale,
            self.check_text_baseline,
            self.check_palette,
            self.check_filter_boundaries,
            self.check_legend_overlap,
            self.check_closing_tag,
        ]

        for check in checks:
            self.report(check())

        if self.quiet:
            if self.failures == 0:
                warn = f" ({self.warnings} warning(s))" if self.warnings else ""
                print(color(f"OK {self.svg_path}{warn}", "green", not self.no_color))
                return 0
            print(color(f"FAIL {self.svg_path} ({self.failures} error(s))", "red", not self.no_color))
            return 1

        print("----------------------------------------")
        if self.failures == 0:
            suffix = f" ({self.warnings} warning(s))" if self.warnings else ""
            print(f"Validation complete{suffix}")
            return 0

        print(color(f"Validation failed ({self.failures} error(s))", "red", not self.no_color))
        return 1

    def report(self, result: CheckResult) -> None:
        if result.status == "pass":
            if self.quiet:
                return
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

    def check_accessibility(self) -> CheckResult:
        """Require non-empty title/desc as the first two element children."""
        assert self.root is not None
        children = list(self.root)
        names = [local_name(child.tag) for child in children[:2]]
        issues: list[str] = []
        if names != ["title", "desc"]:
            issues.append(f"first children are {names!r}, expected ['title', 'desc']")
        for name in ("title", "desc"):
            matches = [e for e in children if local_name(e.tag) == name]
            if len(matches) != 1:
                issues.append(f"expected exactly one <{name}>, found {len(matches)}")
            elif not "".join(matches[0].itertext()).strip():
                issues.append(f"<{name}> is empty")
        if self.root.get("role") != "img":
            issues.append("root is missing role='img'")
        if issues:
            return CheckResult(
                "Checking accessibility metadata", "fail", details=issues,
                fix="Put one non-empty <title> then <desc> first inside <svg>, and add role='img'.",
            )
        return CheckResult("Checking accessibility metadata", "pass")

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

    def check_flat_style(self) -> CheckResult:
        """Enforce the house-style invariants that XML validity cannot express."""
        assert self.root is not None
        issues: list[str] = []
        marker_count = 0
        for element, ancestors in iter_with_ancestors(self.root):
            tag = local_name(element.tag)
            if tag in {"linearGradient", "radialGradient", "filter"}:
                issues.append(f"<{tag}> is forbidden by the flat style")
            if element.get("filter"):
                issues.append(f"<{tag}> uses filter={element.get('filter')!r}")
            if element.get("id") == "arrow" and tag == "marker":
                marker_count += 1
            if tag == "marker" and element.get("id") != "arrow":
                issues.append(f"unexpected marker id={element.get('id')!r}; use only 'arrow'")
            if tag in {"rect", "ellipse", "polygon", "path", "circle"}:
                sw = parse_float(element.get("stroke-width"), 0.0)
                fill = (element.get("fill") or "").strip().lower()
                # Filled component shapes use a 0.5 hairline. Ignore background,
                # marker art, dots, and raw data cells without a stroke.
                if (fill not in {"", "none", "transparent", "#ffffff", "#fff"}
                        and element.get("stroke") and not any(a in {"defs", "marker"} for a in ancestors)
                        and sw not in {0.5, 0.75}):
                    issues.append(f"<{tag}> filled shape has stroke-width={sw:g}; expected 0.5")
            if len(issues) >= 12:
                break
        if marker_count != 1:
            issues.append(f"expected exactly one <marker id='arrow'>, found {marker_count}")
        if issues:
            return CheckResult(
                "Checking flat house style", "fail", details=issues[:12],
                fix="Remove gradients/filters and extra markers; use 0.5px component strokes and the single open-chevron marker.",
            )
        return CheckResult("Checking flat house style", "pass")

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

    def check_arrow_collisions(self) -> CheckResult:
        assert self.root is not None
        obstacles = self.collect_obstacles()
        collisions: list[str] = []

        for element, ancestors in iter_with_ancestors(self.root):
            if any(a in {"defs", "marker", "clipPath", "filter"} for a in ancestors):
                continue
            if not self.is_arrow(element):
                continue

            points, curve_flags = self.arrow_segments(element)
            if len(points) < 2:
                continue

            tag = local_name(element.tag)
            for (p1, p2), from_curve in zip(zip(points, points[1:]), curve_flags):
                if from_curve:
                    # A bezier's straight chord is not the drawn line; skip it.
                    continue
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
        if tag == "polygon":
            points = parse_points(element.get("points"))
            if not points:
                return None
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            return Bounds(min(xs), min(ys), max(xs), max(ys), "polygon")
        if tag == "path" and element.get("fill", "none") not in {"none", "transparent"}:
            # Best-effort bounds for svgkit cylinders and other filled path shapes.
            # Path commands' numeric pairs include arc radii/flags, so prefer
            # sampled endpoints; cylinder bodies still expose their four corners.
            points = parse_path_points(element.get("d"))
            if points:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                return Bounds(min(xs), min(ys), max(xs), max(ys), "path")
        return None

    def is_non_obstacle(self, element: ET.Element, bounds: Bounds) -> bool:
        """True for shapes the collision check should ignore: zero-size, dashed,
        hollow (fill=none with no stroke), tiny (<70 wide or <30 tall), or
        near-full-canvas (>70% of the viewBox)."""
        if bounds.width <= 0 or bounds.height <= 0:
            return True
        if element.get("stroke-dasharray"):
            return True
        if element.get("fill") in {"none", "transparent"} and not element.get("stroke"):
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
        return self.arrow_segments(element)[0]

    def arrow_segments(
        self, element: ET.Element
    ) -> tuple[list[tuple[float, float]], list[bool]]:
        """Points plus a per-gap flag: True when that segment is a curve chord."""
        tag = local_name(element.tag)
        if tag == "line":
            points = [
                (parse_float(element.get("x1")), parse_float(element.get("y1"))),
                (parse_float(element.get("x2")), parse_float(element.get("y2"))),
            ]
            return points, [False]
        if tag == "polyline":
            points = parse_points(element.get("points"))
            return points, [False] * max(len(points) - 1, 0)
        if tag == "path":
            return parse_path_segments(element.get("d"))
        return [], []

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

        # General segment-vs-rectangle test (Liang–Barsky). Endpoints attached
        # to an obstacle edge are valid; only a positive interior run collides.
        if point_near_edge(p1, bounds) or point_near_edge(p2, bounds):
            # Do not blanket-ignore: a segment may leave one edge and cross the
            # entire box to another edge. Sample its midpoint first.
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if not (left + eps < mx < right - eps and top + eps < my < bottom - eps):
                return False
        dx, dy = x2 - x1, y2 - y1
        p = (-dx, dx, -dy, dy)
        q = (x1 - left, right - x1, y1 - top, bottom - y1)
        t0, t1 = 0.0, 1.0
        for pi, qi in zip(p, q):
            if abs(pi) < eps:
                if qi < 0:
                    return False
                continue
            r = qi / pi
            if pi < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return False
        return t1 - t0 > eps

    def check_box_overlaps(self) -> CheckResult:
        """Warn when distinct solid component boxes overlap materially."""
        boxes = self.collect_obstacles()
        issues: list[str] = []
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                overlap_w = min(a.right, b.right) - max(a.left, b.left)
                overlap_h = min(a.bottom, b.bottom) - max(a.top, b.top)
                if overlap_w <= 2 or overlap_h <= 2:
                    continue
                # Nested/sub-shapes are intentional: panel header/body, entity
                # divider geometry, cylinder cap over body.
                if ((a.left <= b.left and a.top <= b.top and a.right >= b.right and a.bottom >= b.bottom)
                        or (b.left <= a.left and b.top <= a.top and b.right >= a.right and b.bottom >= a.bottom)):
                    continue
                if overlap_w * overlap_h < min(a.width * a.height, b.width * b.height) * 0.08:
                    continue
                issues.append(f"{a.element} {format_bounds(a)} overlaps {b.element} {format_bounds(b)}")
                if len(issues) >= 8:
                    break
            if len(issues) >= 8:
                break
        if issues:
            return CheckResult(
                "Checking box overlaps", "warn", details=issues,
                fix="Separate solid nodes by at least 8px. Nested panel/header and cylinder parts may overlap intentionally.",
            )
        return CheckResult("Checking box overlaps", "pass")

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
            label = (element.text or "").strip()
            if not label:
                continue
            x = parse_float(element.get("x"))
            y = parse_float(element.get("y"))
            size = parse_float(element.get("font-size"), 14.0)
            est = text_width(label, int(round(size)))
            anchor = element.get("text-anchor", "start")
            if anchor == "middle":
                lo, hi = x - est / 2, x + est / 2
            elif anchor == "end":
                lo, hi = x - est, x
            else:
                lo, hi = x, x + est
            # Smallest box whose vertical band contains the text baseline.
            host = None
            for b in obstacles:
                if b.left <= x <= b.right and b.top - 2 <= y <= b.bottom + 2:
                    if host is None or b.width * b.height < host.width * host.height:
                        host = b
            if host is None:
                continue
            pad = 6.0
            if lo < host.left + pad - 1 or hi > host.right - pad + 1:
                issues.append(
                    f'"{label}" (~{est:.0f}px @ {size:g}) overflows box '
                    f"{format_bounds(host)} (width {host.width:g})"
                )
            if len(issues) >= 8:
                break
        if issues:
            return CheckResult("Checking text fit", "fail", details=issues, fix="Size boxes from the text: boxWidth = max(line widths) + 32, line ~= latin*8 + cjk*15 at 14px. svgkit.node() does this automatically.")
        return CheckResult("Checking text fit", "pass")

    def check_label_overhang(self) -> CheckResult:
        """Warn when an arrow label is much wider than the arrow it rides.

        A long label on a short gap spills into neighbouring boxes. Prefer a
        shorter wording or a wider gap (layout-best-practices §3).

        Multi-segment paths are scored by their *longest* segment so a short
        bend stub does not false-positive against a label on the long run.
        """
        assert self.root is not None
        # Each arrow → (longest_seg_len, midpoints for proximity matching).
        arrows: list[tuple[float, list[tuple[float, float]]]] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(a in {"defs", "marker", "clipPath", "filter"} for a in ancestors):
                continue
            if not self.is_arrow(element):
                continue
            pts = self.arrow_points(element)
            if len(pts) < 2:
                continue
            longest = 0.0
            mids: list[tuple[float, float]] = []
            for p1, p2 in zip(pts, pts[1:]):
                seg_len = abs(p2[0] - p1[0]) + abs(p2[1] - p1[1])
                longest = max(longest, seg_len)
                mids.append(((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2))
            # Also accept the overall path midpoint for curved / long routes.
            mids.append(((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2))
            arrows.append((longest, mids))

        if not arrows:
            return CheckResult("Checking arrow label length", "pass", "no arrows")

        issues: list[str] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(a in {"defs", "marker", "clipPath", "filter"} for a in ancestors):
                continue
            if local_name(element.tag) != "text":
                continue
            label = (element.text or "").strip()
            if not label:
                continue
            # Skip box titles (font-weight 500 / size 14) — only captions on arrows.
            size = parse_float(element.get("font-size"), 14.0)
            weight = element.get("font-weight", "400")
            if size >= 14 or weight in {"500", "600", "700", "bold"}:
                continue
            x = parse_float(element.get("x"))
            y = parse_float(element.get("y"))
            est = text_width(label, int(round(size)))
            # Nearest arrow within 28px of any of its segment midpoints.
            best_len = None
            best_dist = 28.0
            for longest, mids in arrows:
                for mx, my in mids:
                    dist = abs(mx - x) + abs(my - y)
                    if dist < best_dist:
                        best_dist = dist
                        best_len = longest
            if best_len is None:
                continue
            # Require a clear overhang (label > segment + 20px) so slightly
            # snug labels that still read cleanly do not warn.
            if best_len > 0 and est > best_len + 20:
                issues.append(
                    f'"{label}" (~{est:.0f}px) wider than its arrow '
                    f"(longest segment {best_len:g}px)"
                )
            if len(issues) >= 6:
                break

        if issues:
            return CheckResult(
                "Checking arrow label length", "warn", details=issues,
                fix="Shorten the label (≤3 words) or widen the gap so the arrow carries it. See references/svg-layout-best-practices.md §3.",
            )
        return CheckResult("Checking arrow label length", "pass")

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

    def check_legend_overlap(self) -> CheckResult:
        """Warn if obstacles reach within 40px of the viewBox bottom — no
        room for a clean legend row at the default ``y = height - 20``."""
        assert self.root is not None
        if not self.viewbox:
            return CheckResult("Checking legend space", "warn", "skipped without viewBox")
        _, _, _, vb_h = self.viewbox
        obstacles = self.collect_obstacles()
        lowest = max((b.bottom for b in obstacles), default=0.0)
        margin = vb_h - lowest
        if margin < 40:
            return CheckResult(
                "Checking legend space", "warn",
                f"bottom-most node at y={lowest:g} leaves only {margin:g}px "
                f"(need \u226540px for a legend row)",
                fix="Grow the canvas (Diagram(w, h)) by ~40px so the legend gets "
                    "its own clear row, or pass an explicit ``y`` to ``legend()``.",
            )
        return CheckResult("Checking legend space", "pass")

    def check_closing_tag(self) -> CheckResult:
        if re.search(r"</\s*svg\s*>\s*$", self.text, flags=re.I):
            return CheckResult("Checking closing tag", "pass")
        return CheckResult("Checking closing tag", "fail", "missing final </svg>", fix="Add </svg> at the end of the file. When using the Python list method, ensure lines.append('</svg>') is the last append.")


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
    """Backward-compatible wrapper around ``parse_path_segments``."""
    return parse_path_segments(d)[0]


def parse_path_segments(
    d: str | None,
) -> tuple[list[tuple[float, float]], list[bool]]:
    """Extract points from common SVG path commands, flagging curve chords.

    Straight line/H/V/L segments (orthogonal or diagonal) are checked exactly
    by the collision test. Curves are sampled by endpoint only, and the flag
    marks their straight chord so the checker can skip it (a bezier arcing
    around a box must not false-positive on its chord).
    """

    if not d:
        return [], []
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", d)
    points: list[tuple[float, float]] = []
    curve_flags: list[bool] = []  # parallel to the gaps between points
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    command = ""
    index = 0

    def push(point: tuple[float, float], from_curve: bool) -> None:
        nonlocal current
        if points and math.dist(points[-1], point) <= 1e-6:
            current = point
            return
        if points:
            curve_flags.append(from_curve)
        points.append(point)
        current = point

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
            start = pair
            push(pair, from_curve=False)
            command = "l" if relative else "L"
        elif lower == "l":
            pair = read_pair(relative)
            if pair is None:
                break
            push(pair, from_curve=False)
        elif lower == "h":
            x = next_number()
            if x is None:
                break
            target = (current[0] + x, current[1]) if relative else (x, current[1])
            push(target, from_curve=False)
        elif lower == "v":
            y = next_number()
            if y is None:
                break
            target = (current[0], current[1] + y) if relative else (current[0], y)
            push(target, from_curve=False)
        elif lower in {"c", "s", "q", "t", "a"}:
            counts = {"c": 6, "s": 4, "q": 4, "t": 2, "a": 7}
            needed = counts[lower]
            values: list[float] = []
            for _ in range(needed):
                value = next_number()
                if value is None:
                    return points, curve_flags
                values.append(value)
            if lower == "a":
                end = (values[5], values[6])
            else:
                end = (values[-2], values[-1])
            target = (current[0] + end[0], current[1] + end[1]) if relative else end
            push(target, from_curve=True)
        elif lower == "z":
            push(start, from_curve=False)
        else:
            break

        if index < len(tokens) and re.match(r"[A-Za-z]", tokens[index]):
            continue

    return points, curve_flags


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated SVG diagram.")
    parser.add_argument("svg_file", type=Path, help="SVG file to validate")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="one-line OK/FAIL summary; still print failures and warnings",
    )
    args = parser.parse_args()

    return Validator(args.svg_file, no_color=args.no_color, quiet=args.quiet).run()


if __name__ == "__main__":
    sys.exit(main())
