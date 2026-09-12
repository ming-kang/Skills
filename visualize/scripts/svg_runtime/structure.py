"""SVG structure, references, and the house-style contract."""

import re
import xml.etree.ElementTree as ET

from .document import local_name, number_list
from .geometry import parse_path
from .result import CheckResult
from .style import normalize_hex, is_cold_color, COLOR_KEYWORDS_OK


class StructureChecks:
    def __init__(self, document):
        self.document = document
        self.root, self.text, self.viewbox = document.root, document.text, document.viewbox
        self._background = None

    def check_svg_root(self) -> CheckResult:
        assert self.root is not None
        if self.root.tag != "{http://www.w3.org/2000/svg}svg":
            return CheckResult(
                "Checking SVG root", "fail", f"root tag is <{local_name(self.root.tag)}>",
                fix="Use <svg xmlns='http://www.w3.org/2000/svg'> as the root element.",
            )
        return CheckResult("Checking SVG root", "pass")

    def check_viewbox(self):
        assert self.root is not None
        raw = self.root.get("viewBox", "")
        try:
            values = number_list(raw)
            if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
                raise ValueError("viewBox needs positive width and height")
        except ValueError as exc:
            return CheckResult("Checking viewBox", "fail", f"invalid viewBox={raw!r}: {exc}",
                               fix="Use four finite SVG numbers: min-x min-y width height.")
        self.viewbox = tuple(values)
        self.document.viewbox = self.viewbox
        return CheckResult("Checking viewBox", "pass", f"{values[2]:g}x{values[3]:g}")

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
        mixed_marker_properties: list[str] = []
        marker_names = ("marker", "marker-start", "marker-mid", "marker-end")
        for element in self.root.iter():
            tag = local_name(element.tag)
            element_id = element.get("id")
            if element_id:
                id_counts[element_id] = id_counts.get(element_id, 0) + 1
            if tag == "marker":
                markers.append(element)
            values = {attr: self.document.value(element, attr) for attr in marker_names}
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
        details = [f"duplicate id={value!r} appears {count} times"
                   for value, count in sorted(id_counts.items()) if count > 1]
        if len(markers) != 1 or markers[0].get("id") != "arrow":
            ids = [marker.get("id") for marker in markers]
            details.append(f"expected exactly one <marker id='arrow'>; found marker ids {ids}")
        if len(markers) == 1 and markers[0].get("id") == "arrow":
            marker = markers[0]
            paths = [child for child in marker if local_name(child.tag) == "path"]
            canonical = False
            if len(paths) == 1:
                path = paths[0]
                try:
                    segments = parse_path(path.get("d")).segments
                    canonical = (len(segments) == 2 and all(part.kind == "L" for part in segments)
                                 and segments[0].start == (2, 1) and segments[0].end == (8, 5)
                                 and segments[1].end == (2, 9)
                                 and self.document.value(path, "fill", "black") == "none"
                                 and self.document.value(path, "stroke") == "context-stroke")
                except (ValueError, OverflowError):
                    pass
            if not canonical:
                details.append("marker#arrow must contain the open chevron M2 1 L8 5 L2 9 with fill=none and stroke=context-stroke")
        for tag, attr, value in marker_refs:
            if not re.fullmatch(r"url\(\s*(['\"]?)#arrow\1\s*\)", value.strip(), re.I):
                details.append(f"<{tag}> {attr} must be url(#arrow), got {value!r}")
        details.extend(mixed_marker_properties)
        if details:
            return CheckResult(
                "Checking marker contract", "fail", details=details[:12],
                fix="Keep one marker#arrow; use element/inline marker properties targeting url(#arrow), including inherited or resolved CSS declarations.",
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

    def check_white_background(self) -> CheckResult:
        assert self.root is not None
        if self.document.unresolved_css:
            return CheckResult("Checking white background", "warn",
                               "unresolved CSS may affect the background; inspect it in a browser")
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
        if self.document.has_transform(element):
            return CheckResult(
                "Checking white background", "fail", "the canvas background rect is transformed",
                fix="Use an untransformed full-canvas white rect as the first painted root child.",
            )
        if self.document.is_hidden(element):
            return CheckResult(
                "Checking white background", "fail", "the canvas background rect is hidden or transparent",
                fix="Use a visible opaque full-canvas white rect as the first painted root child.",
            )
        vb_x, vb_y, vb_w, vb_h = self.viewbox
        vb_right, vb_bottom = vb_x + vb_w, vb_y + vb_h
        raw_fill = self.document.value(element, "fill", "black") or ""
        fill = normalize_hex(raw_fill)
        dimensions = self.document.lengths(element, "x", "y", "width", "height")
        if dimensions is None:
            return CheckResult("Checking white background", "fail", "unusable background dimensions")
        x, y, width, height = dimensions
        opacity = self.document.effective_opacity(element)
        fill_opacity = self.document.alpha(self.document.value(element, "fill-opacity", "1"))
        covers = (
            x <= vb_x + 0.5 and y <= vb_y + 0.5
            and x + width >= vb_right - 0.5 and y + height >= vb_bottom - 0.5
        )
        if (fill == "#ffffff" and covers and opacity >= 0.999 and fill_opacity >= 0.999
                and self.document.color_alpha(raw_fill) >= 0.999):
            self._background = element
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

    def check_palette(self) -> CheckResult:
        assert self.root is not None
        cold: dict[str, int] = {}
        for element in self.root.iter():
            for attr in ("fill", "stroke"):
                value = self.document.value(element, attr)
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

    def check_values(self):
        for element in self.root.iter():
            for paint in ("fill", "stroke", "color"):
                value = self.document.value(element, paint)
                if value:
                    self.document.color_alpha(value)
        invalid = sorted(self.document.invalid)
        return CheckResult("Checking SVG values", "fail" if invalid else "pass",
                           details=invalid[:12] or None,
                           fix="Use finite coordinates, valid CSS colors, and non-negative shape sizes.")
