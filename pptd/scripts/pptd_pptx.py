from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import NamedTuple

from pptd_common import ExportError

PPTX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
)
FADE_TRANSITION_XML = '<p:transition spd="fast" advClick="1"><p:fade/></p:transition>'
SLIDE_NAME_PATTERN = re.compile(r"ppt/slides/slide\d+\.xml")


def is_pptx(path: Path) -> bool:
    if not path.is_file() or path.name.endswith(".crdownload"):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            if "ppt/presentation.xml" not in archive.namelist():
                return False
            return PPTX_CONTENT_TYPE.encode() in archive.read("[Content_Types].xml")
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def replace_transition(slide_xml: bytes, transition: str) -> bytes:
    text = slide_xml.decode("utf-8")
    text = re.sub(
        r"<p:transition\b[^>]*(?:/>|>.*?</p:transition>)", "", text, flags=re.DOTALL
    )
    if transition == "none":
        return text.encode("utf-8")
    color_map = re.search(
        r"<p:clrMapOvr\b[^>]*(?:/>|>.*?</p:clrMapOvr>)", text, re.DOTALL
    )
    common_slide = re.search(r"<p:cSld\b[^>]*(?:/>|>.*?</p:cSld>)", text, re.DOTALL)
    anchor = color_map or common_slide
    if anchor is None:
        raise ExportError("slide XML has no cSld/clrMapOvr insertion anchor")
    position = anchor.end()
    return (text[:position] + FADE_TRANSITION_XML + text[position:]).encode("utf-8")


class TransitionFacts(NamedTuple):
    names: list[str]
    transition_indexes: list[int]
    has_direct_fade: bool


def slide_transition_facts(slide_xml: bytes) -> TransitionFacts:
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError as exc:
        raise ExportError(f"invalid slide XML: {exc}") from exc
    names = [child.tag.rsplit("}", 1)[-1] for child in root]
    indexes = [index for index, name in enumerate(names) if name == "transition"]
    has_fade = bool(indexes) and any(
        child.tag.rsplit("}", 1)[-1] == "fade" for child in root[indexes[0]]
    )
    return TransitionFacts(names, indexes, has_fade)


def validate_transition_order(facts: TransitionFacts, transition: str) -> None:
    if transition == "none":
        if facts.transition_indexes:
            raise ExportError("transition=none left a root-level transition")
        return
    if len(facts.transition_indexes) != 1 or not facts.has_direct_fade:
        raise ExportError("slide does not contain exactly one root-level fade transition")
    index = facts.transition_indexes[0]
    for before in ("cSld", "clrMapOvr"):
        if before in facts.names and facts.names.index(before) > index:
            raise ExportError(f"{before} appears after transition")
    for after in ("timing", "extLst"):
        if after in facts.names and facts.names.index(after) < index:
            raise ExportError(f"{after} appears before transition")


def patch_transitions(pptx: Path, transition: str) -> int:
    temporary = pptx.with_name(f".{pptx.name}.{uuid.uuid4().hex}.tmp")
    slide_count = 0
    try:
        with zipfile.ZipFile(pptx) as source, zipfile.ZipFile(temporary, "w") as target:
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


def verify_output(pptx: Path, transition: str) -> dict[str, object]:
    if not is_pptx(pptx):
        raise ExportError(f"output is not a valid PPTX ZIP: {pptx}")
    with zipfile.ZipFile(pptx) as archive:
        broken = archive.testzip()
        if broken:
            raise ExportError(f"PPTX CRC check failed at: {broken}")
        slide_names = [
            name for name in archive.namelist() if SLIDE_NAME_PATTERN.fullmatch(name)
        ]
        fade_count = 0
        for name in slide_names:
            facts = slide_transition_facts(archive.read(name))
            validate_transition_order(facts, transition)
            fade_count += int(facts.has_direct_fade)
        if transition == "fade" and fade_count != len(slide_names):
            raise ExportError("fade transition was not written to every slide")
        font_parts = [
            name
            for name in archive.namelist()
            if name.startswith("ppt/fonts/") and not name.endswith("/")
        ]
        return {
            "slides": len(slide_names),
            "fadeTransitions": fade_count,
            "fontParts": len(font_parts),
            "bytes": pptx.stat().st_size,
        }
