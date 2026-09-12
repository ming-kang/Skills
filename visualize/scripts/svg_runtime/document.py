"""SVG numbers, presentation attributes, and a cached CSS cascade.

Resolve type/class/id selectors and descendant/child combinators. Unsupported
selectors are reported, rather than silently validating fictitious geometry.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"
_NUMBER = re.compile(NUMBER + r"\Z")
_LENGTH = re.compile(rf"({NUMBER})([a-z%]*)\Z", re.I)
_COMPOUND = re.compile(r"(?P<tag>\*|[\w-]+)?(?P<qualifiers>(?:[.#][\w-]+)*)\Z")
INHERITED = {
    "color", "fill", "fill-opacity", "fill-rule", "stroke", "stroke-width",
    "stroke-opacity", "stroke-dasharray", "stroke-linecap", "stroke-linejoin",
    "font-family", "font-size", "font-weight", "font-style", "text-anchor",
    "dominant-baseline", "visibility", "marker-start", "marker-mid", "marker-end",
}
GEOMETRY_STYLE = INHERITED | {
    "display", "opacity", "marker", "transform", "translate", "rotate", "scale",
    "x", "y", "width", "height", "cx", "cy", "r", "rx", "ry", "d",
    "clip-path", "mask", "font", "letter-spacing", "word-spacing",
}
LENGTH_ATTRIBUTES = {
    "x", "y", "width", "height", "cx", "cy", "r", "rx", "ry",
    "x1", "x2", "y1", "y2", "dx", "dy", "font-size", "stroke-width",
}
_VERTICAL = {"y", "cy", "ry", "height", "y1", "y2", "dy"}
_UNITS = {"": 1, "px": 1, "pt": 96 / 72, "pc": 16, "in": 96,
          "cm": 96 / 2.54, "mm": 96 / 25.4, "q": 96 / 101.6}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def iter_with_ancestors(root: ET.Element):
    stack: list[tuple[ET.Element, list[str]]] = [(root, [])]
    while stack:
        element, ancestors = stack.pop()
        yield element, ancestors
        next_ancestors = ancestors + [local_name(element.tag)]
        for child in reversed(list(element)):
            stack.append((child, next_ancestors))


def number_list(raw: str) -> list[float]:
    values = re.split(r"[\s,]+", raw.strip())
    if not raw.strip() or any(not _NUMBER.fullmatch(value) for value in values):
        raise ValueError("expected a list of SVG numbers")
    numbers = [float(value) for value in values]
    if not all(math.isfinite(value) for value in numbers):
        raise ValueError("coordinates must be finite")
    return numbers


def declarations(raw: str) -> dict[str, tuple[str, bool]]:
    """Split declarations outside quoted strings and function arguments."""
    pieces, start, depth, quote, escaped = [], 0, 0, None, False
    for index, char in enumerate(raw + ";"):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == ";" and depth == 0:
            pieces.append(raw[start:index])
            start = index + 1
    result = {}
    for piece in pieces:
        if ":" not in piece:
            continue
        key, value = piece.split(":", 1)
        key, value = key.strip().lower(), value.strip()
        important = bool(re.search(r"!important\s*$", value, re.I))
        value = re.sub(r"\s*!important\s*$", "", value, flags=re.I).strip()
        names = ("marker-start", "marker-mid", "marker-end") if key == "marker" else (key,)
        for name in names:
            if value and (name not in result or important >= result[name][1]):
                result[name] = (value, important)
    return result


@dataclass(frozen=True)
class Selector:
    compounds: tuple[str, ...]
    child: tuple[bool, ...]
    specificity: tuple[int, int, int]

    @classmethod
    def parse(cls, text: str) -> Selector | None:
        tokens = re.sub(r"\s*>\s*", " > ", text.strip()).split()
        compounds, child = [], []
        direct = False
        for token in tokens:
            if token == ">":
                if not compounds or direct:
                    return None
                direct = True
                continue
            if token != ":root" and not _COMPOUND.fullmatch(token):
                return None
            compounds.append(token)
            child.append(direct)
            direct = False
        if not compounds or direct:
            return None
        ids = sum(part.count("#") for part in compounds)
        classes = sum(part.count(".") + (part == ":root") for part in compounds)
        tags = sum(bool(re.match(r"^[\w-]", part)) for part in compounds)
        return cls(tuple(compounds), tuple(child), (ids, classes, tags))

    def matches(self, element: ET.Element, parents: dict[ET.Element, ET.Element]) -> bool:
        def compound_matches(candidate, compound):
            if compound == ":root":
                return candidate not in parents
            match = _COMPOUND.fullmatch(compound)
            tag = match.group("tag")
            if tag and tag != "*" and local_name(candidate.tag) != tag:
                return False
            classes = candidate.get("class", "").split()
            return all(candidate.get("id") == name if prefix == "#" else name in classes
                       for prefix, name in re.findall(r"([.#])([\w-]+)", match.group("qualifiers")))

        pending = [(element, len(self.compounds) - 1)]
        visited = set()
        while pending:
            candidate, index = pending.pop()
            if (candidate, index) in visited:
                continue
            visited.add((candidate, index))
            if not compound_matches(candidate, self.compounds[index]):
                continue
            if index == 0:
                return True
            parent = parents.get(candidate)
            while parent is not None:
                pending.append((parent, index - 1))
                if self.child[index]:
                    break
                parent = parents.get(parent)
        return False


class Document:
    def __init__(self, root: ET.Element, text: str):
        self.root, self.text = root, text
        self.parents = {child: parent for parent in root.iter() for child in parent}
        self.viewbox = None
        self.invalid: set[str] = set()
        self.unsupported: set[str] = set()
        self.unresolved_css: set[str] = set()
        self._specified = {}
        self._values = {}
        self._opacity = {}
        self._display_hidden = {}
        self._transformed = {}
        self._lengths = {}
        self._cascade()

    def _cascade(self):
        rules = []
        for element in self.root.iter():
            if local_name(element.tag) != "style" or not element.text:
                continue
            css = re.sub(r"/\*.*?\*/", "", element.text, flags=re.S)
            if "@" in css:
                self.unresolved_css.add("CSS at-rules need browser evaluation")
            for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
                values = declarations(block.group(2))
                for raw_selector in block.group(1).split(","):
                    selector = Selector.parse(raw_selector)
                    if selector is None:
                        if GEOMETRY_STYLE.intersection(values):
                            self.unresolved_css.add(f"unsupported CSS selector {raw_selector.strip()!r}")
                        continue
                    rules.append((selector, values))
        for element in self.root.iter():
            chosen = {key: (value, (False, 0, 0, 0, 0, -1))
                      for key, value in element.attrib.items() if key != "style"}
            # Marker presentation shorthand has the same effect as its three longhands.
            if "marker" in chosen:
                for key in ("marker-start", "marker-mid", "marker-end"):
                    chosen.setdefault(key, chosen["marker"])
                del chosen["marker"]
            for order, (selector, values) in enumerate(rules):
                if selector.matches(element, self.parents):
                    for key, (value, important) in values.items():
                        rank = (important, 0, *selector.specificity, order)
                        if key not in chosen or rank >= chosen[key][1]:
                            chosen[key] = (value, rank)
            for key, (value, important) in declarations(element.get("style", "")).items():
                rank = (important, 1, 0, 0, 0, 0)
                if key not in chosen or rank >= chosen[key][1]:
                    chosen[key] = (value, rank)
            self._specified[element] = {key: value for key, (value, _) in chosen.items()}
            for key, value in self._specified[element].items():
                if key in GEOMETRY_STYLE and (re.search(r"\b(?:var|calc)\(", value) or key == "font"):
                    self.unresolved_css.add(f"CSS {key}={value!r} needs browser evaluation")

    def value(self, element, name, default=None):
        key = (element, name)
        if key not in self._values:
            value = self._specified[element].get(name)
            value = value.strip() if value is not None else None
            keyword = value.lower() if value is not None else None
            inherit = keyword == "inherit" or (keyword in (None, "unset") and name in INHERITED)
            if inherit:
                parent = self.parents.get(element)
                value = self.value(parent, name) if parent is not None else None
            elif keyword in ("initial", "unset"):
                value = None
            self._values[key] = value
        value = self._values[key]
        return value.strip() if value is not None else default

    def alpha(self, raw, default=1.0):
        if raw is None:
            return default
        raw = raw.strip()
        try:
            value = float(raw[:-1]) / 100 if raw.endswith("%") else float(raw)
            if not math.isfinite(value):
                raise ValueError
            return max(0, min(1, value))
        except ValueError:
            self.invalid.add(f"invalid opacity {raw!r}")
            return default

    def effective_opacity(self, element):
        if element not in self._opacity:
            parent = self.parents.get(element)
            ancestor = self.effective_opacity(parent) if parent is not None else 1
            self._opacity[element] = ancestor * self.alpha(self.value(element, "opacity"))
        return self._opacity[element]

    def is_hidden(self, element):
        def display_hidden(current):
            if current not in self._display_hidden:
                parent = self.parents.get(current)
                self._display_hidden[current] = (
                    self.value(current, "display", "inline").lower() == "none"
                    or (parent is not None and display_hidden(parent))
                )
            return self._display_hidden[current]
        return (display_hidden(element) or self.effective_opacity(element) <= 0
                or self.value(element, "visibility", "visible").lower() in {"hidden", "collapse"})

    def color_alpha(self, raw):
        value = raw.strip().lower()
        if value.startswith("#"):
            if not re.fullmatch(r"#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})", value):
                self.invalid.add(f"invalid hex color {raw!r}")
                return 1
            if len(value) == 5:
                return int(value[-1] * 2, 16) / 255
            if len(value) == 9:
                return int(value[-2:], 16) / 255
        match = re.fullmatch(r"(?:rgba?|hsla?)\((.*)\)", value)
        if match:
            contents = match.group(1)
            if "/" in contents:
                return self.alpha(contents.rsplit("/", 1)[1])
            parts = contents.split(",")
            if len(parts) == 4:
                return self.alpha(parts[-1])
        return 1

    def paint_is_visible(self, element, paint):
        if self.is_hidden(element):
            return False
        value = self.value(element, paint, "black" if paint == "fill" else "none").lower()
        if value == "currentcolor":
            value = self.value(element, "color", "black")
        return (value not in {"none", "transparent"}
                and self.alpha(self.value(element, f"{paint}-opacity")) * self.color_alpha(value) > 0)

    def has_transform(self, element):
        if element not in self._transformed:
            parent = self.parents.get(element)
            self._transformed[element] = any(
                self.value(element, name, "none").lower() not in {"", "none"}
                for name in ("transform", "translate", "rotate", "scale", "clip-path", "mask")
            ) or (parent is not None and self.has_transform(parent))
        return self._transformed[element]

    def length(self, element, name, default=0.0):
        key = (element, name, default)
        if key not in self._lengths:
            raw = self.value(element, name)
            result = default
            if raw is not None:
                match = _LENGTH.fullmatch(raw.strip())
                if not match:
                    # SVG text can have per-character position lists, beyond this estimator.
                    if local_name(element.tag) == "text" and name in {"x", "y", "dx", "dy"}:
                        self.unsupported.add(f"text position list {name}={raw!r} needs browser measurement")
                    else:
                        self.invalid.add(f"<{local_name(element.tag)}> invalid {name}={raw!r}")
                    result = None
                else:
                    number, unit = float(match.group(1)), match.group(2).lower()
                    if not math.isfinite(number):
                        self.invalid.add(f"<{local_name(element.tag)}> non-finite {name}")
                        result = None
                    elif unit == "%" and self.viewbox and name != "font-size":
                        width, height = self.viewbox[2:]
                        base = (height if name in _VERTICAL else width)
                        if name in {"r", "stroke-width"}:
                            base = math.hypot(width, height) / math.sqrt(2)
                        result = number * base / 100
                    elif unit in _UNITS:
                        result = number * _UNITS[unit]
                    else:
                        self.unsupported.add(f"<{local_name(element.tag)}> {name}={raw!r} needs browser measurement")
                        result = None
            self._lengths[key] = result
        return self._lengths[key]

    def lengths(self, element, *names):
        values = tuple(self.length(element, name) for name in names)
        return values if all(value is not None for value in values) else None
