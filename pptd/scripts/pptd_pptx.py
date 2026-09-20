#!/usr/bin/env python3
"""PPTX post-processing: slide transitions and output verification.

The local WASM writer produces a valid PPTX, but it does not guarantee the
schema-correct placement of slide transitions (``p:transition`` must be a
direct child of ``p:sld`` after ``cSld``/``clrMapOvr`` and before
``timing``/``extLst``). This module patches that in and then verifies the
result, so a structurally broken deck fails loudly here instead of in
PowerPoint.

Two deliberate choices:

* The *edit* is a surgical string splice, not a full ElementTree
  re-serialization: reserializing would rewrite every slide's namespace
  prefixes and attribute order, a much larger behavioral surface than the
  insertion itself.
* The *verification* parses each slide exactly once and answers every
  structural question from that one parse (child order, transition presence,
  fade presence), so validation can never disagree with itself.
"""

from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict, List, NamedTuple

from pptd_common import ExportError, log

PPTX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
)
FADE_TRANSITION_XML = (
    '<p:transition spd="fast" advClick="1"><p:fade/></p:transition>'
)
SLIDE_NAME_PATTERN = re.compile(r"ppt/slides/slide\d+\.xml")


def is_pptx(path: Path) -> bool:
    if not path.is_file() or path.name.endswith(".crdownload"):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            if "ppt/presentation.xml" not in archive.namelist():
                return False
            content_types = archive.read("[Content_Types].xml")
            return PPTX_CONTENT_TYPE.encode("utf-8") in content_types
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def replace_transition(slide_xml: bytes, transition: str) -> bytes:
    text = slide_xml.decode("utf-8")
    pattern = re.compile(
        r"<p:transition\b[^>]*(?:/>|>.*?</p:transition>)", re.DOTALL
    )
    text = pattern.sub("", text)
    if transition == "none":
        return text.encode("utf-8")

    # CT_Slide requires transition as a direct child after cSld/clrMapOvr and
    # before timing/extLst. Searching for the first p:extLst is incorrect:
    # shapes may contain their own nested extLst inside cSld, causing Office to
    # ignore a transition inserted there.
    color_map = re.search(
        r"<p:clrMapOvr\b[^>]*(?:/>|>.*?</p:clrMapOvr>)", text, re.DOTALL
    )
    common_slide = re.search(
        r"<p:cSld\b[^>]*(?:/>|>.*?</p:cSld>)", text, re.DOTALL
    )
    anchor = color_map or common_slide
    if anchor is None:
        raise ExportError("slide XML has no cSld/clrMapOvr insertion anchor")
    position = anchor.end()
    return (text[:position] + FADE_TRANSITION_XML + text[position:]).encode("utf-8")


class TransitionFacts(NamedTuple):
    """Everything verification needs to know about one slide, from one parse."""

    names: List[str]
    transition_indexes: List[int]
    has_direct_fade: bool


def slide_transition_facts(slide_xml: bytes) -> TransitionFacts:
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError as exc:
        raise ExportError(f"invalid slide XML: {exc}") from exc
    names = [child.tag.rsplit("}", 1)[-1] for child in root]
    transition_indexes = [index for index, name in enumerate(names) if name == "transition"]
    has_direct_fade = False
    if transition_indexes:
        transition = root[transition_indexes[0]]
        has_direct_fade = any(
            child.tag.rsplit("}", 1)[-1] == "fade" for child in transition
        )
    return TransitionFacts(names, transition_indexes, has_direct_fade)


def validate_transition_order(facts: TransitionFacts, transition: str) -> None:
    names = facts.names
    transition_indexes = facts.transition_indexes
    if transition == "none":
        if transition_indexes:
            raise ExportError("transition=none left a root-level transition")
        return
    if len(transition_indexes) != 1 or not facts.has_direct_fade:
        raise ExportError("slide does not contain exactly one root-level fade transition")
    transition_index = transition_indexes[0]
    for required_before in ("cSld", "clrMapOvr"):
        if required_before in names and names.index(required_before) > transition_index:
            raise ExportError(f"{required_before} appears after transition")
    for required_after in ("timing", "extLst"):
        if required_after in names and names.index(required_after) < transition_index:
            raise ExportError(f"{required_after} appears before transition")


def patch_transitions(pptx: Path, transition: str) -> int:
    temporary = pptx.with_name(f".{pptx.name}.{uuid.uuid4().hex}.tmp")
    slide_count = 0
    try:
        with zipfile.ZipFile(pptx, "r") as source, zipfile.ZipFile(temporary, "w") as target:
            target.comment = source.comment
            for info in source.infolist():
                data = source.read(info.filename)
                if SLIDE_NAME_PATTERN.fullmatch(info.filename):
                    data = replace_transition(data, transition)
                    slide_count += 1
                target.writestr(info, data, compress_type=info.compress_type)
        if slide_count == 0:
            raise ExportError("exported PPTX contains no slide XML")
        temporary.replace(pptx)
    finally:
        temporary.unlink(missing_ok=True)
    return slide_count


def verify_output(pptx: Path, transition: str, expect_fonts: bool) -> Dict[str, object]:
    if not is_pptx(pptx):
        raise ExportError(f"output is not a valid PPTX ZIP: {pptx}")
    with zipfile.ZipFile(pptx) as archive:
        broken = archive.testzip()
        if broken:
            raise ExportError(f"PPTX CRC check failed at: {broken}")
        slide_names = [
            name
            for name in archive.namelist()
            if SLIDE_NAME_PATTERN.fullmatch(name)
        ]
        transition_hits = 0
        for name in slide_names:
            facts = slide_transition_facts(archive.read(name))
            validate_transition_order(facts, transition)
            if facts.has_direct_fade:
                transition_hits += 1
        if transition == "fade" and transition_hits != len(slide_names):
            raise ExportError("fade transition was not written to every slide")
        fonts = [
            name
            for name in archive.namelist()
            if name.startswith("ppt/fonts/") and not name.endswith("/")
        ]
        if expect_fonts and not fonts:
            log(
                "warning: embed-fonts was enabled, but the official writer produced no font part"
            )
        return {
            "slides": len(slide_names),
            "fadeTransitions": transition_hits,
            "fontParts": len(fonts),
            "bytes": pptx.stat().st_size,
        }
