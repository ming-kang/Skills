"""Cached layout geometry and collision checks for one SVG document."""

import math
import xml.etree.ElementTree as ET

from .document import local_name, number_list, iter_with_ancestors
from .geometry import (Bounds, TextRun, parse_path, path_bounds, path_outlines,
    shapes_intersect, point_in_polygon, segment_crosses_polygon, segment_hits_aabb, overlap_area,
    rect_outline as _rect_outline, ellipse_outline as _ellipse_outline,
    _sample_path_subpaths)
from .result import CheckResult
from .style import text_width


def format_point(point):
    return f"({point[0]:g},{point[1]:g})"


def format_bounds(bounds):
    return f"[{bounds.left:g},{bounds.top:g},{bounds.right:g},{bounds.bottom:g}]"


class LayoutChecks:
    def __init__(self, document, background):
        self.document = document
        self.root, self.viewbox = document.root, document.viewbox
        self._background = background
        self._shape_cache = {}
        self._obstacles = None
        self._labels = None
        self._text_hosts = None
        self._unsupported_text = []
        self._unsupported_transforms = []
        self._unsupported_paths = []

    def collect(self):
        for element in self.root.iter():
            tag = local_name(element.tag)
            if tag in {"use", "foreignObject"} or (tag == "svg" and element is not self.root):
                self.document.unsupported.add(f"<{tag}> geometry needs browser measurement")
        checks = [self.check_box_overlap, self.check_arrow_collisions,
                  self.check_box_viewbox_overflow, self.check_text_overflow,
                  self.check_text_viewbox, self.check_label_vs_box, self.check_label_vs_label,
                  self.check_type_scale, self.check_text_baseline,
                  self.check_unsupported_text_geometry, self.check_unsupported_transforms]
        return [check() for check in checks]

    def collect_obstacles(self) -> list[Bounds]:
        assert self.root is not None
        if self._obstacles is not None:
            return self._obstacles
        if self.document.unresolved_css:
            detail = "unresolved CSS selectors: obstacle geometry is skipped"
            if detail not in self._unsupported_transforms:
                self._unsupported_transforms.append(detail)
            self._obstacles = []
            return self._obstacles
        obstacles: list[Bounds] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(name in {"defs", "marker", "clipPath", "filter"} for name in ancestors):
                continue
            if self.document.has_transform(element):
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

    def shape_bounds(self, element):
        if element in self._shape_cache:
            return self._shape_cache[element]
        tag, role = local_name(element.tag), element.get("data-role")
        result = None
        names = {"rect": ("x", "y", "width", "height"), "circle": ("cx", "cy", "r"),
                 "ellipse": ("cx", "cy", "rx", "ry"), "image": ("x", "y", "width", "height")}
        if tag in names:
            values = self.document.lengths(element, *names[tag])
            if values is None:
                return None
            if tag in {"rect", "image"}:
                x, y, width, height = values
                outline = _rect_outline(x, y, x + width, y + height)
                result = Bounds(x, y, x + width, y + height, tag, role, outline, source=element)
            else:
                if tag == "circle":
                    cx, cy, radius = values
                    rx = ry = radius
                else:
                    cx, cy, rx, ry = values
                result = Bounds(cx-rx, cy-ry, cx+rx, cy+ry, tag, role,
                                _ellipse_outline(cx, cy, rx, ry), source=element)
        elif tag == "polygon":
            try:
                numbers = number_list(element.get("points", ""))
                if len(numbers) < 6 or len(numbers) % 2:
                    raise ValueError("polygon needs complete x,y pairs")
                points = list(zip(numbers[::2], numbers[1::2]))
                xs, ys = zip(*points)
                result = Bounds(min(xs), min(ys), max(xs), max(ys), tag, role, tuple(points), source=element)
            except ValueError as exc:
                self.document.invalid.add(f"<polygon> {exc}")
        elif tag == "path" and not self.is_arrow(element) and self.document.paint_is_visible(element, "fill"):
            try:
                data = parse_path(element.get("d"))
                raw_bounds = path_bounds(data)
                if raw_bounds is not None:
                    outlines = path_outlines(data)
                    outline = outlines[0] if len(outlines) == 1 else None
                    result = Bounds(*raw_bounds, tag, role, outline, len(outlines) != 1, element)
            except (ValueError, OverflowError) as exc:
                self._unsupported_paths.append(f"<path> geometry skipped: {exc}")
        if result is not None:
            if not all(math.isfinite(v) for v in (result.left,result.top,result.right,result.bottom)):
                self.document.invalid.add(f"<{tag}> non-finite shape bounds")
                result = None
            elif result.width < 0 or result.height < 0:
                self.document.invalid.add(f"<{tag}> negative size")
                result = None
        self._shape_cache[element] = result
        return result

    def is_non_obstacle(self, element: ET.Element, bounds: Bounds) -> bool:
        if bounds.width <= 0 or bounds.height <= 0:
            return True
        if not self.document.paint_is_visible(element, "fill") and not self.document.paint_is_visible(element, "stroke"):
            return True
        if element is self._background or bounds.role in {"decoration", "node-part", "data-mark", "background"}:
            return True
        if bounds.role == "node":
            return False
        if bounds.width < 70 or bounds.height < 30:
            return True
        return False

    def is_arrow(self, element: ET.Element) -> bool:
        if local_name(element.tag) not in {"line", "polyline", "path"}:
            return False
        if element.get("data-role") == "connector":
            return True
        shorthand = self.document.value(element, "marker")
        if shorthand is not None:
            return shorthand.strip().lower() != "none"
        for attr in ("marker-start", "marker-mid", "marker-end"):
            value = self.document.value(element, attr)
            if value and value.strip().lower() != "none":
                return True
        return False

    def arrow_segments(self, element):
        tag = local_name(element.tag)
        if tag == "line":
            values = self.document.lengths(element, "x1", "y1", "x2", "y2")
            return [((values[0], values[1]), (values[2], values[3]))] if values is not None else []
        if tag == "polyline":
            try:
                numbers = number_list(element.get("points", ""))
                if len(numbers) % 2:
                    raise ValueError("polyline needs complete x,y pairs")
                points = list(zip(numbers[::2], numbers[1::2]))
                return list(zip(points, points[1:]))
            except ValueError as exc:
                self.document.invalid.add(f"<polyline> {exc}")
                return []
        if tag == "path":
            try:
                data = parse_path(element.get("d"))
                return [segment for subpath in _sample_path_subpaths(data)
                        for segment in zip(subpath, subpath[1:])]
            except (ValueError, OverflowError) as exc:
                detail = f"<path> arrow geometry skipped: {exc}"
                if detail not in self._unsupported_paths:
                    self._unsupported_paths.append(detail)
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
            if not self.document.paint_is_visible(element, "stroke"):
                continue
            if self.document.has_transform(element):
                # collect_obstacles() records the explicit unsupported-transform
                # warning. Do not hard-check untransformed coordinates.
                continue
            for start, end in self.arrow_segments(element):
                for obstacle in obstacles:
                    if obstacle.role in {"panel", "container"}:
                        continue
                    if not segment_hits_aabb(start, end, obstacle):
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
        if self.document.unresolved_css:
            detail = "unresolved CSS selectors: text geometry is skipped"
            if detail not in self._unsupported_transforms:
                self._unsupported_transforms.append(detail)
            self._labels = []
            return self._labels
        obstacles = self.collect_text_hosts()
        runs: list[TextRun] = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(name in {"defs", "marker", "clipPath", "filter"} for name in ancestors):
                continue
            if local_name(element.tag) != "text":
                continue
            if not self.document.paint_is_visible(element, "fill") and not self.document.paint_is_visible(element, "stroke"):
                continue
            if self.document.has_transform(element):
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
            position = self.document.lengths(element, "x", "y", "dx", "dy")
            size = self.document.length(element, "font-size", 16.0)
            if position is None or size is None:
                continue
            x, y = position[0] + position[2], position[1] + position[3]
            estimated = text_width(label, int(round(size)))
            anchor = (self.document.value(element, "text-anchor", "start") or "start").lower()
            if anchor == "middle":
                left, right = x - estimated / 2, x + estimated / 2
            elif anchor == "end":
                left, right = x - estimated, x
            else:
                left, right = x, x + estimated
            half = size * 0.625
            baseline = self.document.value(element, "dominant-baseline", "auto")
            top, bottom = ((y - half, y + half) if baseline in {"central", "middle"}
                           else (y - size, y + size * 0.25))
            bounds = Bounds(left, top, right, bottom, "text",
                            element.get("data-role"), _rect_outline(left, top, right, bottom),
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
            elif role is not None:
                host, free = None, True
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
            outside_outline = (run.host.element in {"polygon", "ellipse", "circle"}
                               and run.host.outline is not None
                               and any(not point_in_polygon(point, run.host.outline, strict=False)
                                       for point in run.bounds.outline))
            if (outside_outline or run.bounds.left < run.host.left + pad - 1
                    or run.bounds.right > run.host.right - pad + 1
                    or run.bounds.top < run.host.top + 2 or run.bounds.bottom > run.host.bottom - 2):
                issues.append(
                    f'"{run.label}" (~{run.bounds.width:.0f}px @ {run.size:g}) overflows '
                    f"{run.host.element} {format_bounds(run.host)}"
                )
        if issues:
            return CheckResult(
                "Checking text fit", "warn", details=issues[:12],
                fix="Widen nodes or shorten text; place labels outside fixed-size data marks instead of changing their values.",
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
        runs = self.collect_labels()
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
        details = sorted(set(self._unsupported_transforms + self._unsupported_paths + sorted(self.document.unsupported) + sorted(self.document.unresolved_css)))
        if details:
            return CheckResult(
                "Checking unsupported transforms", "warn", details=details,
                fix="Flatten transforms/complex paths before relying on collision checks; skipped geometry is not guessed.",
            )
        return CheckResult("Checking unsupported transforms", "pass")

    def check_box_viewbox_overflow(self):
        if not self.viewbox or self.document.unresolved_css:
            return CheckResult("Checking box bounds vs viewBox", "warn", "geometry needs browser evaluation")
        x, y, width, height = self.viewbox
        canvas = Bounds(x, y, x+width, y+height, "canvas")
        issues = []
        for element, ancestors in iter_with_ancestors(self.root):
            if any(tag in {"defs", "marker", "clipPath", "filter", "pattern", "symbol", "mask"} for tag in ancestors):
                continue
            if self.document.has_transform(element) or self.document.is_hidden(element):
                continue
            if not (self.document.paint_is_visible(element,"fill") or self.document.paint_is_visible(element,"stroke")):
                continue
            tag = local_name(element.tag)
            bounds = self.shape_bounds(element)
            if tag in {"line", "polyline", "path"} and bounds is None and self.document.paint_is_visible(element,"stroke"):
                try:
                    if tag == "path":
                        raw = path_bounds(parse_path(element.get("d")))
                        bounds = Bounds(*raw, tag) if raw else None
                    else:
                        segments = self.arrow_segments(element)
                        points = [point for segment in segments for point in segment]
                        if points:
                            xs, ys = zip(*points)
                            bounds = Bounds(min(xs), min(ys), max(xs), max(ys), tag)
                except (ValueError, OverflowError) as exc:
                    self._unsupported_paths.append(f"<{tag}> bounds skipped: {exc}")
            if bounds and self.document.paint_is_visible(element, "stroke"):
                stroke = self.document.length(element, "stroke-width", 1.0)
                if stroke is not None and stroke < 0:
                    self.document.invalid.add(f"<{tag}> negative stroke-width")
                if stroke is not None and stroke > 0:
                    pad = stroke / 2
                    bounds = Bounds(bounds.left - pad, bounds.top - pad,
                                    bounds.right + pad, bounds.bottom + pad, tag)
            if bounds and not canvas.contains(bounds, tolerance=0.5):
                issues.append(f"{tag} {format_bounds(bounds)} extends beyond the viewBox")
        if issues:
            return CheckResult("Checking box bounds vs viewBox", "fail", details=issues[:12],
                               fix="Move the shape or connector inside the canvas, or expand the viewBox.")
        return CheckResult("Checking box bounds vs viewBox", "pass")

    def check_type_scale(self) -> CheckResult:
        assert self.root is not None
        sizes: set[float] = set()
        headings = 0
        for element in self.root.iter():
            if local_name(element.tag) != "text" or self.document.is_hidden(element):
                continue
            size = self.document.length(element, "font-size", 16.0)
            if size is None:
                continue
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
            if local_name(element.tag) == "text" and not self.document.is_hidden(element)
            and self.document.value(element, "dominant-baseline") is None
        )
        if missing:
            return CheckResult(
                "Checking text baseline", "warn", f"{missing} <text> without dominant-baseline",
                fix='Add dominant-baseline="central" for predictable vertical alignment.',
            )
        return CheckResult("Checking text baseline", "pass")

    def check_text_viewbox(self):
        if not self.viewbox:
            return CheckResult("Checking text bounds vs viewBox", "warn", "missing usable viewBox")
        x, y, width, height = self.viewbox
        canvas = Bounds(x, y, x+width, y+height, "canvas")
        issues = [f'"{run.label}" {format_bounds(run.bounds)} may be clipped'
                  for run in self.collect_labels() if not canvas.contains(run.bounds)]
        return CheckResult("Checking text bounds vs viewBox", "warn" if issues else "pass",
                           details=issues[:12] or None,
                           fix="Move text inside the canvas or shorten it; confirm using actual browser fonts.")


    def collect_text_hosts(self):
        if self._text_hosts is None:
            self._text_hosts = []
            for element, ancestors in iter_with_ancestors(self.root):
                if any(tag in {"defs", "marker", "clipPath", "filter", "pattern", "symbol", "mask"} for tag in ancestors):
                    continue
                if element is self._background or element.get("data-role") in {"decoration", "node-part", "background"}:
                    continue
                if self.document.has_transform(element) or self.document.is_hidden(element):
                    continue
                if not (self.document.paint_is_visible(element, "fill")
                        or self.document.paint_is_visible(element, "stroke")):
                    continue
                bounds = self.shape_bounds(element)
                if bounds and bounds.width > 0 and bounds.height > 0:
                    self._text_hosts.append(bounds)
        return self._text_hosts
