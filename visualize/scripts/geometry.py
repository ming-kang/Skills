#!/usr/bin/env python3
"""Computational geometry for the visualize skill's SVG validator.

Path parsing (full SVG M/L/H/V/C/S/Q/T/A/Z), axis-aligned bounding boxes,
sampled outlines, polygon intersection (SAT + ear-clip), segment collision,
and Liang-Barsky clipping.

Zero external dependencies — stdlib math only.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xml.etree.ElementTree as ET


__all__ = [
    "Point", "TAU", "EPSILON",
    "Bounds", "TextRun", "PathSegment", "PathData", "ArcGeometry",
    "parse_path", "arc_geometry", "path_bounds",
    "path_outlines", "parse_path_points",
    "point_in_polygon", "polygons_intersect", "shapes_intersect",
    "segment_crosses_polygon", "segment_hits_aabb",
    "overlap_area", "rect_outline", "ellipse_outline",
    "_sample_path_subpaths",
]

Point = tuple[float, float]
TAU = math.tau
EPSILON = 1e-9

@dataclass
class Bounds:
    left: float
    top: float
    right: float
    bottom: float
    element: str
    role: str | None = None
    outline: tuple[Point, ...] | None = None
    uncertain: bool = False
    source: ET.Element | None = field(default=None, repr=False, compare=False)

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def contains(self, other: "Bounds", tolerance: float = 1.0) -> bool:
        return (
            self.left - tolerance <= other.left
            and self.right + tolerance >= other.right
            and self.top - tolerance <= other.top
            and self.bottom + tolerance >= other.bottom
        )

    def contains_point(self, point: Point, tolerance: float = 0.0) -> bool:
        x, y = point
        return (
            self.left - tolerance <= x <= self.right + tolerance
            and self.top - tolerance <= y <= self.bottom + tolerance
        )


@dataclass
class TextRun:
    label: str
    size: float
    bounds: Bounds
    host: Bounds | None
    role: str | None
    free: bool


@dataclass(frozen=True)
class PathSegment:
    kind: str
    start: Point
    end: Point
    controls: tuple[Point, ...] = ()
    arc: tuple[float, float, float, bool, bool] | None = None
    subpath: int = 0
    closes: bool = False


@dataclass
class PathData:
    segments: list[PathSegment]
    starts: dict[int, Point]
    closed: set[int]


@dataclass(frozen=True)
class ArcGeometry:
    cx: float
    cy: float
    rx: float
    ry: float
    phi: float
    theta1: float
    delta: float


_PATH_TOKEN_RE = re.compile(
    r"[AaCcHhLlMmQqSsTtVvZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"
)
_PATH_PARAM_COUNTS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6,
                      "S": 4, "Q": 4, "T": 2, "A": 7}


def _is_command(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def _add(point: Point, delta: Point) -> Point:
    return point[0] + delta[0], point[1] + delta[1]


def _reflect(control: Point | None, around: Point) -> Point:
    if control is None:
        return around
    return 2 * around[0] - control[0], 2 * around[1] - control[1]


def parse_path(d: str | None) -> PathData:
    """Parse the SVG path commands used by the skill into normalized segments.

    Supports M/L/H/V/C/S/Q/T/A/Z, absolute and relative coordinates, repeated
    parameter groups, implicit lineto after moveto, and closepath. S and T are
    normalized to C and Q with reflected controls.
    """
    if not d:
        return PathData([], {}, set())
    tokens = _PATH_TOKEN_RE.findall(d.replace(",", " "))
    if not tokens:
        return PathData([], {}, set())

    segments: list[PathSegment] = []
    starts: dict[int, Point] = {}
    closed: set[int] = set()
    current: Point = (0.0, 0.0)
    command: str | None = None
    subpath = -1
    previous_kind = ""
    cubic_control: Point | None = None
    quadratic_control: Point | None = None
    index = 0

    def numbers(count: int) -> list[float]:
        nonlocal index
        if index + count > len(tokens) or any(_is_command(t) for t in tokens[index:index + count]):
            raise ValueError(f"path command {command!r} is missing parameters")
        values = [float(t) for t in tokens[index:index + count]]
        index += count
        return values

    while index < len(tokens):
        if _is_command(tokens[index]):
            command = tokens[index]
            index += 1
        if command is None:
            raise ValueError("path data begins without a command")

        upper = command.upper()
        relative = command.islower()
        if upper == "Z":
            if subpath < 0:
                raise ValueError("closepath appears before moveto")
            target = starts[subpath]
            segments.append(PathSegment("L", current, target, subpath=subpath, closes=True))
            current = target
            closed.add(subpath)
            previous_kind = "Z"
            cubic_control = quadratic_control = None
            command = None
            continue
        if upper not in _PATH_PARAM_COUNTS:
            raise ValueError(f"unsupported path command {command!r}")

        values = numbers(_PATH_PARAM_COUNTS[upper])
        origin = current

        def point_at(offset: int) -> Point:
            point = (values[offset], values[offset + 1])
            return _add(origin, point) if relative else point

        if upper == "M":
            current = point_at(0)
            subpath += 1
            starts[subpath] = current
            previous_kind = "M"
            cubic_control = quadratic_control = None
            command = "l" if relative else "L"
            continue
        if subpath < 0:
            raise ValueError(f"path command {command!r} appears before moveto")

        if upper == "L":
            end = point_at(0)
            segment = PathSegment("L", current, end, subpath=subpath)
            cubic_control = quadratic_control = None
        elif upper == "H":
            x = current[0] + values[0] if relative else values[0]
            end = (x, current[1])
            segment = PathSegment("L", current, end, subpath=subpath)
            cubic_control = quadratic_control = None
        elif upper == "V":
            y = current[1] + values[0] if relative else values[0]
            end = (current[0], y)
            segment = PathSegment("L", current, end, subpath=subpath)
            cubic_control = quadratic_control = None
        elif upper == "C":
            c1, c2, end = point_at(0), point_at(2), point_at(4)
            segment = PathSegment("C", current, end, (c1, c2), subpath=subpath)
            cubic_control, quadratic_control = c2, None
        elif upper == "S":
            c1 = _reflect(cubic_control if previous_kind == "C" else None, current)
            c2, end = point_at(0), point_at(2)
            segment = PathSegment("C", current, end, (c1, c2), subpath=subpath)
            cubic_control, quadratic_control = c2, None
        elif upper == "Q":
            control, end = point_at(0), point_at(2)
            segment = PathSegment("Q", current, end, (control,), subpath=subpath)
            quadratic_control, cubic_control = control, None
        elif upper == "T":
            control = _reflect(quadratic_control if previous_kind == "Q" else None, current)
            end = point_at(0)
            segment = PathSegment("Q", current, end, (control,), subpath=subpath)
            quadratic_control, cubic_control = control, None
        else:  # A
            rx, ry, rotation, large_arc, sweep, x, y = values
            end = _add(origin, (x, y)) if relative else (x, y)
            arc = (abs(rx), abs(ry), rotation, bool(round(large_arc)), bool(round(sweep)))
            segment = PathSegment("A", current, end, arc=arc, subpath=subpath)
            cubic_control = quadratic_control = None

        segments.append(segment)
        current = segment.end
        previous_kind = segment.kind

    return PathData(segments, starts, closed)


def _quadratic(a: float, b: float, c: float, t: float) -> float:
    mt = 1.0 - t
    return mt * mt * a + 2 * mt * t * b + t * t * c


def _cubic(a: float, b: float, c: float, d: float, t: float) -> float:
    mt = 1.0 - t
    return mt ** 3 * a + 3 * mt * mt * t * b + 3 * mt * t * t * c + t ** 3 * d


def _quadratic_extrema(p0: float, p1: float, p2: float) -> list[float]:
    denominator = p0 - 2 * p1 + p2
    if abs(denominator) < EPSILON:
        return []
    t = (p0 - p1) / denominator
    return [t] if EPSILON < t < 1.0 - EPSILON else []


def _cubic_extrema(p0: float, p1: float, p2: float, p3: float) -> list[float]:
    # derivative / 3 = a*t^2 + b*t + c
    a = -p0 + 3 * p1 - 3 * p2 + p3
    b = 2 * (p0 - 2 * p1 + p2)
    c = p1 - p0
    if abs(a) < EPSILON:
        if abs(b) < EPSILON:
            return []
        t = -c / b
        return [t] if EPSILON < t < 1.0 - EPSILON else []
    discriminant = b * b - 4 * a * c
    if discriminant < -EPSILON:
        return []
    root = math.sqrt(max(0.0, discriminant))
    values = [(-b + root) / (2 * a), (-b - root) / (2 * a)]
    return sorted({t for t in values if EPSILON < t < 1.0 - EPSILON})


def _vector_angle(u: Point, v: Point) -> float:
    return math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])


def arc_geometry(segment: PathSegment) -> ArcGeometry | None:
    if segment.kind != "A" or segment.arc is None:
        return None
    rx, ry, rotation, large_arc, sweep = segment.arc
    x1, y1 = segment.start
    x2, y2 = segment.end
    if rx < EPSILON or ry < EPSILON or (abs(x1 - x2) < EPSILON and abs(y1 - y2) < EPSILON):
        return None

    phi = math.radians(rotation % 360.0)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy

    scale = x1p * x1p / (rx * rx) + y1p * y1p / (ry * ry)
    if scale > 1.0:
        factor = math.sqrt(scale)
        rx *= factor
        ry *= factor

    numerator = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    denominator = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coefficient = 0.0 if denominator < EPSILON else math.sqrt(max(0.0, numerator / denominator))
    if large_arc == sweep:
        coefficient = -coefficient
    cxp = coefficient * (rx * y1p / ry)
    cyp = coefficient * (-ry * x1p / rx)

    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2.0
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2.0
    start_vector = ((x1p - cxp) / rx, (y1p - cyp) / ry)
    end_vector = ((-x1p - cxp) / rx, (-y1p - cyp) / ry)
    theta1 = _vector_angle((1.0, 0.0), start_vector)
    delta = _vector_angle(start_vector, end_vector)
    if not sweep and delta > 0:
        delta -= TAU
    elif sweep and delta < 0:
        delta += TAU
    return ArcGeometry(cx, cy, rx, ry, phi, theta1, delta)


def _arc_point(arc: ArcGeometry, theta: float) -> Point:
    cos_phi, sin_phi = math.cos(arc.phi), math.sin(arc.phi)
    cos_theta, sin_theta = math.cos(theta), math.sin(theta)
    return (
        arc.cx + arc.rx * cos_phi * cos_theta - arc.ry * sin_phi * sin_theta,
        arc.cy + arc.rx * sin_phi * cos_theta + arc.ry * cos_phi * sin_theta,
    )


def _angle_on_arc(theta: float, start: float, delta: float, tolerance: float = 1e-9) -> bool:
    if delta >= 0:
        return (theta - start) % TAU <= delta + tolerance
    return (start - theta) % TAU <= -delta + tolerance


def path_bounds(data: PathData) -> tuple[float, float, float, float] | None:
    """Exact axis-aligned bounds for parsed lines, Béziers, and elliptical arcs."""
    if not data.segments:
        return None
    points: list[Point] = []
    for segment in data.segments:
        points.extend((segment.start, segment.end))
        if segment.kind == "Q":
            control = segment.controls[0]
            for t in _quadratic_extrema(segment.start[0], control[0], segment.end[0]):
                points.append((_quadratic(segment.start[0], control[0], segment.end[0], t),
                               _quadratic(segment.start[1], control[1], segment.end[1], t)))
            for t in _quadratic_extrema(segment.start[1], control[1], segment.end[1]):
                points.append((_quadratic(segment.start[0], control[0], segment.end[0], t),
                               _quadratic(segment.start[1], control[1], segment.end[1], t)))
        elif segment.kind == "C":
            c1, c2 = segment.controls
            candidates = set(_cubic_extrema(segment.start[0], c1[0], c2[0], segment.end[0]))
            candidates.update(_cubic_extrema(segment.start[1], c1[1], c2[1], segment.end[1]))
            for t in candidates:
                points.append((_cubic(segment.start[0], c1[0], c2[0], segment.end[0], t),
                               _cubic(segment.start[1], c1[1], c2[1], segment.end[1], t)))
        elif segment.kind == "A":
            arc = arc_geometry(segment)
            if arc is not None:
                x_angle = math.atan2(-arc.ry * math.sin(arc.phi), arc.rx * math.cos(arc.phi))
                y_angle = math.atan2(arc.ry * math.cos(arc.phi), arc.rx * math.sin(arc.phi))
                for theta in (x_angle, x_angle + math.pi, y_angle, y_angle + math.pi):
                    if _angle_on_arc(theta, arc.theta1, arc.delta):
                        points.append(_arc_point(arc, theta))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _sample_segment_points(segment: PathSegment) -> list[Point]:
    """Sample one normalized segment, excluding its already-known start point."""
    if segment.kind == "L":
        return [segment.end]
    if segment.kind == "Q":
        control = segment.controls[0]
        return [
            (_quadratic(segment.start[0], control[0], segment.end[0], i / 24),
             _quadratic(segment.start[1], control[1], segment.end[1], i / 24))
            for i in range(1, 25)
        ]
    if segment.kind == "C":
        c1, c2 = segment.controls
        return [
            (_cubic(segment.start[0], c1[0], c2[0], segment.end[0], i / 32),
             _cubic(segment.start[1], c1[1], c2[1], segment.end[1], i / 32))
            for i in range(1, 33)
        ]
    arc = arc_geometry(segment)
    if arc is None:
        return [segment.end]
    count = max(8, int(math.ceil(abs(arc.delta) / (math.pi / 32))))
    return [_arc_point(arc, arc.theta1 + arc.delta * i / count)
            for i in range(1, count + 1)]


def _sample_path_subpaths(data: PathData) -> list[tuple[Point, ...]]:
    sampled: dict[int, list[Point]] = {}
    for segment in data.segments:
        points = sampled.setdefault(segment.subpath, [segment.start])
        for point in _sample_segment_points(segment):
            if math.dist(points[-1], point) > 1e-7:
                points.append(point)
    return [tuple(sampled[index]) for index in sorted(sampled) if sampled[index]]


def path_outlines(data: PathData) -> list[tuple[Point, ...]]:
    """Sample parsed segments into one outline per subpath for intersections."""
    outlines: list[tuple[Point, ...]] = []
    for sampled in _sample_path_subpaths(data):
        points = list(sampled)
        # SVG fill implicitly closes open subpaths.
        if len(points) >= 3 and math.dist(points[0], points[-1]) <= 1e-7:
            points = points[:-1]
        if len(points) >= 3:
            outlines.append(tuple(points))
    return outlines


def parse_path_points(d: str | None) -> list[Point]:
    """Sampled path points for collision routing, backed by the shared parser."""
    try:
        data = parse_path(d)
    except ValueError:
        return []
    subpaths = _sample_path_subpaths(data)
    if not subpaths:
        return []
    # Arrow paths emitted by the skill contain one subpath. Preserve the legacy
    # flat return type for callers while sampling real C/Q/A geometry.
    points: list[Point] = []
    for subpath in subpaths:
        if points and math.dist(points[-1], subpath[0]) <= 1e-7:
            points.extend(subpath[1:])
        else:
            points.extend(subpath)
    return points


def overlap_area(a: Bounds, b: Bounds) -> tuple[float, float]:
    return (
        min(a.right, b.right) - max(a.left, b.left),
        min(a.bottom, b.bottom) - max(a.top, b.top),
    )


def rect_outline(left: float, top: float, right: float, bottom: float) -> tuple[Point, ...]:
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def ellipse_outline(cx: float, cy: float, rx: float, ry: float, count: int = 64) -> tuple[Point, ...]:
    return tuple((cx + rx * math.cos(TAU * i / count), cy + ry * math.sin(TAU * i / count))
                 for i in range(count))


def _cross(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_on_segment(point: Point, a: Point, b: Point, tolerance: float = 1e-7) -> bool:
    if abs(_cross(a, b, point)) > tolerance:
        return False
    return (
        min(a[0], b[0]) - tolerance <= point[0] <= max(a[0], b[0]) + tolerance
        and min(a[1], b[1]) - tolerance <= point[1] <= max(a[1], b[1]) + tolerance
    )


def point_in_polygon(point: Point, polygon: tuple[Point, ...], strict: bool = True) -> bool:
    if len(polygon) < 3:
        return False
    inside = False
    x, y = point
    previous = polygon[-1]
    for current in polygon:
        if _point_on_segment(point, previous, current):
            return not strict
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y):
            cross_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < cross_x:
                inside = not inside
        previous = current
    return inside


def _proper_segments_intersect(a: Point, b: Point, c: Point, d: Point,
                               tolerance: float = 1e-7) -> bool:
    ab_c, ab_d = _cross(a, b, c), _cross(a, b, d)
    cd_a, cd_b = _cross(c, d, a), _cross(c, d, b)
    return (
        ((ab_c > tolerance and ab_d < -tolerance) or (ab_c < -tolerance and ab_d > tolerance))
        and ((cd_a > tolerance and cd_b < -tolerance) or (cd_a < -tolerance and cd_b > tolerance))
    )


def _is_convex_polygon(polygon: tuple[Point, ...]) -> bool:
    """Return whether a simple polygon has one consistent turn direction."""
    direction = 0
    for index, point in enumerate(polygon):
        turn = _cross(point, polygon[(index + 1) % len(polygon)],
                      polygon[(index + 2) % len(polygon)])
        if abs(turn) <= 1e-7:
            continue
        current = 1 if turn > 0 else -1
        if direction and current != direction:
            return False
        direction = current
    return direction != 0


def _convex_polygons_intersect(a: tuple[Point, ...], b: tuple[Point, ...]) -> bool:
    """SAT intersection for convex polygons; boundary-only contact is false."""
    for polygon in (a, b):
        for index, start in enumerate(polygon):
            end = polygon[(index + 1) % len(polygon)]
            axis_x, axis_y = -(end[1] - start[1]), end[0] - start[0]
            length = math.hypot(axis_x, axis_y)
            if length <= EPSILON:
                continue
            axis_x, axis_y = axis_x / length, axis_y / length
            projection_a = [point[0] * axis_x + point[1] * axis_y for point in a]
            projection_b = [point[0] * axis_x + point[1] * axis_y for point in b]
            if (max(projection_a) <= min(projection_b) + 1e-7
                    or max(projection_b) <= min(projection_a) + 1e-7):
                return False
    return True


def _polygon_signed_area(polygon: tuple[Point, ...]) -> float:
    return 0.5 * sum(
        point[0] * polygon[(index + 1) % len(polygon)][1]
        - polygon[(index + 1) % len(polygon)][0] * point[1]
        for index, point in enumerate(polygon)
    )


def _point_in_triangle(point: Point, triangle: tuple[Point, Point, Point]) -> bool:
    a, b, c = triangle
    values = (_cross(a, b, point), _cross(b, c, point), _cross(c, a, point))
    return not (any(value > 1e-7 for value in values)
                and any(value < -1e-7 for value in values))


def _triangulate_polygon(polygon: tuple[Point, ...]) -> list[tuple[Point, Point, Point]]:
    """Ear-clip a simple polygon; return [] if the outline is degenerate."""
    if len(polygon) < 3 or abs(_polygon_signed_area(polygon)) <= EPSILON:
        return []
    orientation = 1 if _polygon_signed_area(polygon) > 0 else -1
    indices = list(range(len(polygon)))
    triangles: list[tuple[Point, Point, Point]] = []
    guard = len(indices) * len(indices)
    while len(indices) > 3 and guard > 0:
        clipped = False
        for position, current in enumerate(indices):
            previous = indices[position - 1]
            following = indices[(position + 1) % len(indices)]
            triangle = (polygon[previous], polygon[current], polygon[following])
            if orientation * _cross(*triangle) <= 1e-7:
                continue
            if any(
                _point_in_triangle(polygon[index], triangle)
                for index in indices
                if index not in {previous, current, following}
            ):
                continue
            triangles.append(triangle)
            del indices[position]
            clipped = True
            break
        if not clipped:
            return []
        guard -= 1
    if len(indices) == 3:
        triangle = tuple(polygon[index] for index in indices)
        if abs(_cross(*triangle)) > 1e-7:
            triangles.append(triangle)  # type: ignore[arg-type]
    return triangles


def _polygon_interior_point(polygon: tuple[Point, ...]) -> Point | None:
    """Find a guaranteed interior point from a horizontal scanline interval."""
    levels = sorted(set(point[1] for point in polygon))
    for low, high in zip(levels, levels[1:]):
        if high - low <= 1e-7:
            continue
        y = (low + high) / 2.0
        crossings: list[float] = []
        previous = polygon[-1]
        for current in polygon:
            if (previous[1] > y) != (current[1] > y):
                crossings.append(
                    previous[0] + (current[0] - previous[0])
                    * (y - previous[1]) / (current[1] - previous[1])
                )
            previous = current
        crossings.sort()
        for left, right in zip(crossings[::2], crossings[1::2]):
            if right - left > 1e-7:
                candidate = ((left + right) / 2.0, y)
                if point_in_polygon(candidate, polygon, strict=True):
                    return candidate
    return None


def polygons_intersect(a: tuple[Point, ...], b: tuple[Point, ...]) -> bool:
    # Rectangles, diamonds, and sampled ellipses are convex. SAT handles their
    # collinear/aligned edges, where proper-edge crossing tests alone are blind.
    if _is_convex_polygon(a) and _is_convex_polygon(b):
        return _convex_polygons_intersect(a, b)

    triangles_a = _triangulate_polygon(a)
    triangles_b = _triangulate_polygon(b)
    if triangles_a and triangles_b:
        return any(
            _convex_polygons_intersect(first, second)
            for first in triangles_a
            for second in triangles_b
        )

    # Defensive fallback for malformed/non-simple outlines that cannot be
    # triangulated. Never use a vertex average: it can lie in a concavity.
    for i, a1 in enumerate(a):
        a2 = a[(i + 1) % len(a)]
        for j, b1 in enumerate(b):
            b2 = b[(j + 1) % len(b)]
            if _proper_segments_intersect(a1, a2, b1, b2):
                return True
    if any(point_in_polygon(point, b, strict=True) for point in a):
        return True
    if any(point_in_polygon(point, a, strict=True) for point in b):
        return True
    interior_a, interior_b = _polygon_interior_point(a), _polygon_interior_point(b)
    return ((interior_a is not None and point_in_polygon(interior_a, b, strict=True))
            or (interior_b is not None and point_in_polygon(interior_b, a, strict=True)))


def shapes_intersect(a: Bounds, b: Bounds, tolerance: float = 1.0) -> bool | None:
    ox, oy = overlap_area(a, b)
    if ox <= tolerance or oy <= tolerance:
        return False
    if a.outline is None or b.outline is None:
        return None
    return polygons_intersect(a.outline, b.outline)


def _segment_edge_parameter(p1: Point, p2: Point, q1: Point, q2: Point) -> float | None:
    rx, ry = p2[0] - p1[0], p2[1] - p1[1]
    sx, sy = q2[0] - q1[0], q2[1] - q1[1]
    denominator = rx * sy - ry * sx
    if abs(denominator) < EPSILON:
        return None
    qpx, qpy = q1[0] - p1[0], q1[1] - p1[1]
    t = (qpx * sy - qpy * sx) / denominator
    u = (qpx * ry - qpy * rx) / denominator
    if -1e-7 <= t <= 1.0 + 1e-7 and -1e-7 <= u <= 1.0 + 1e-7:
        return max(0.0, min(1.0, t))
    return None


def segment_crosses_polygon(p1: Point, p2: Point, polygon: tuple[Point, ...]) -> bool:
    length = math.dist(p1, p2)
    if length < EPSILON:
        return False
    parameters = [0.0, 1.0]
    for index, q1 in enumerate(polygon):
        q2 = polygon[(index + 1) % len(polygon)]
        value = _segment_edge_parameter(p1, p2, q1, q2)
        if value is not None:
            parameters.append(value)
    ordered: list[float] = []
    for value in sorted(parameters):
        if not ordered or abs(value - ordered[-1]) > 1e-7:
            ordered.append(value)
    for start, end in zip(ordered, ordered[1:]):
        if (end - start) * length <= 1.0:
            continue
        middle = (start + end) / 2.0
        point = (p1[0] + (p2[0] - p1[0]) * middle,
                 p1[1] + (p2[1] - p1[1]) * middle)
        if point_in_polygon(point, polygon, strict=True):
            return True
    return False


def segment_hits_aabb(p1: Point, p2: Point, bounds: Bounds) -> bool:
    """Liang-Barsky clipping against the open interior of an AABB."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    p = (-dx, dx, -dy, dy)
    q = (p1[0] - bounds.left, bounds.right - p1[0],
         p1[1] - bounds.top, bounds.bottom - p1[1])
    lower, upper = 0.0, 1.0
    for pi, qi in zip(p, q):
        if abs(pi) < EPSILON:
            if qi <= 0:
                return False
            continue
        ratio = qi / pi
        if pi < 0:
            lower = max(lower, ratio)
        else:
            upper = min(upper, ratio)
        if lower >= upper:
            return False
    return (upper - lower) * math.dist(p1, p2) > 1.0


