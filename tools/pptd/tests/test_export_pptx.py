#!/usr/bin/env python3

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SKILL_ROOT = Path(__file__).resolve().parents[3] / "pptd"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import export_pptx as EXPORT  # noqa: E402
import pptd_deck  # noqa: E402
import pptd_pptx  # noqa: E402
import validate_pptd as VALIDATE  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MINIMAL = FIXTURES / "minimal"
QA_DECK = FIXTURES / "qa-deck"
ADVANCED_CHARTS = FIXTURES / "advanced-charts"
WASM_HASH = "589b362a444824c948f21ae99cdc32958c83b28e47a296d4f5905c76b04e0e6e"


def make_deck(root: Path, manifest: str | None = None, page: str | None = None) -> Path:
    (root / "pages").mkdir(parents=True)
    manifest_path = root / "deck.pptd"
    manifest_path.write_text(
        manifest
        or """version: v2
title: Validation fixture
size: [960, 540]
pages:
  - pages/01.page
""",
        encoding="utf-8",
    )
    (root / "pages" / "01.page").write_text(
        page
        or """elements:
  - elementId: title
    elementType: text
    bounds: [100, 100, 400, 80]
    content:
      text: Hello
""",
        encoding="utf-8",
    )
    return manifest_path


class DeckValidationTests(unittest.TestCase):
    def test_valid_project_summary(self):
        with tempfile.TemporaryDirectory() as name:
            project = pptd_deck.build_local_project(make_deck(Path(name)))
            summary = pptd_deck.validation_summary(project)
            self.assertTrue(summary["valid"])
            self.assertEqual(summary["slides"], 1)
            self.assertEqual(summary["elements"], 1)
            self.assertEqual(summary["warnings"], [])

    def test_rejects_non_string_page_entries(self):
        manifest = """version: v2
size: [960, 540]
pages:
  - {}
"""
        with tempfile.TemporaryDirectory() as name:
            path = make_deck(Path(name), manifest=manifest)
            with self.assertRaisesRegex(EXPORT.ExportError, "non-empty string"):
                pptd_deck.build_local_project(path)

    def test_rejects_duplicate_element_ids(self):
        page = """elements:
  - {elementId: same, elementType: text, bounds: [0, 0, 100, 50], content: {text: One}}
  - {elementId: same, elementType: text, bounds: [0, 60, 100, 50], content: {text: Two}}
"""
        with tempfile.TemporaryDirectory() as name:
            path = make_deck(Path(name), page=page)
            with self.assertRaisesRegex(EXPORT.ExportError, "duplicate elementId"):
                pptd_deck.build_local_project(path)

    def test_rejects_missing_local_media(self):
        page = """elements:
  - elementId: photo
    elementType: image
    bounds: [0, 0, 100, 100]
    src: media/missing.png
"""
        with tempfile.TemporaryDirectory() as name:
            path = make_deck(Path(name), page=page)
            with self.assertRaisesRegex(EXPORT.ExportError, "missing local image"):
                pptd_deck.build_local_project(path)

    def test_rejects_paths_outside_the_project(self):
        manifest = """version: v2
size: [960, 540]
pages:
  - ../outside.page
"""
        with tempfile.TemporaryDirectory() as name:
            path = make_deck(Path(name), manifest=manifest)
            with self.assertRaisesRegex(EXPORT.ExportError, "escapes"):
                pptd_deck.build_local_project(path)

    def test_warns_instead_of_rejecting_intentional_bleed(self):
        page = """elements:
  - elementId: bleed
    elementType: text
    bounds: [-20, 100, 400, 80]
    content: {text: Bleed}
"""
        with tempfile.TemporaryDirectory() as name:
            project = pptd_deck.build_local_project(make_deck(Path(name), page=page))
            self.assertEqual(len(project["warnings"]), 1)
            self.assertIn("beyond the slide canvas", project["warnings"][0])

    def test_rejects_non_positive_element_size(self):
        page = """elements:
  - elementId: bad
    elementType: text
    bounds: [0, 0, 0, 80]
    content: {text: Bad}
"""
        with tempfile.TemporaryDirectory() as name:
            path = make_deck(Path(name), page=page)
            with self.assertRaisesRegex(EXPORT.ExportError, "must be positive"):
                pptd_deck.build_local_project(path)

    def test_validation_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as name:
            output = io.StringIO()
            with redirect_stdout(output):
                result = VALIDATE.main([str(make_deck(Path(name)))])
            self.assertEqual(result, 0)
            summary = json.loads(output.getvalue())
            self.assertTrue(summary["valid"])
            self.assertEqual(summary["slides"], 1)


class TransitionTests(unittest.TestCase):
    def test_fade_is_inserted_before_timing(self):
        source = (
            b'<p:sld xmlns:p="urn:test"><p:cSld><p:spTree><p:extLst/>'
            b'</p:spTree></p:cSld><p:clrMapOvr/><p:timing/><p:extLst/></p:sld>'
        )
        result = pptd_pptx.replace_transition(source, "fade")
        text = result.decode()
        self.assertGreater(text.index("<p:transition"), text.index("<p:clrMapOvr"))
        self.assertLess(text.index("<p:transition"), text.index("<p:timing"))
        pptd_pptx.validate_transition_order(pptd_pptx.slide_transition_facts(result), "fade")

    def test_existing_transition_is_replaced_or_removed(self):
        source = (
            b'<p:sld xmlns:p="urn:test"><p:cSld/>'
            b'<p:transition><p:wipe/></p:transition><p:extLst/></p:sld>'
        )
        faded = pptd_pptx.replace_transition(source, "fade")
        self.assertNotIn(b"p:wipe", faded)
        self.assertEqual(faded.count(b"<p:transition"), 1)
        cleared = pptd_pptx.replace_transition(source, "none")
        self.assertNotIn(b"p:transition", cleared)

    def test_nested_transition_is_relocated_to_slide_root(self):
        source = (
            b'<p:sld xmlns:p="urn:test"><p:cSld><p:spTree>'
            b'<p:transition><p:fade/></p:transition><p:extLst/>'
            b'</p:spTree></p:cSld><p:clrMapOvr/><p:extLst/></p:sld>'
        )
        facts = pptd_pptx.slide_transition_facts(pptd_pptx.replace_transition(source, "fade"))
        self.assertEqual(facts.names, ["cSld", "clrMapOvr", "transition", "extLst"])

    def test_patch_transitions_preserves_zip_integrity(self):
        with tempfile.TemporaryDirectory() as name:
            deck = Path(name) / "test.pptx"
            with zipfile.ZipFile(deck, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                    '<Override PartName="/ppt/presentation.xml" '
                    f'ContentType="{pptd_pptx.PPTX_CONTENT_TYPE}"/></Types>',
                )
                archive.writestr("ppt/presentation.xml", "<p:presentation xmlns:p='urn:test'/>")
                archive.writestr(
                    "ppt/slides/slide1.xml", '<p:sld xmlns:p="urn:test"><p:cSld/></p:sld>'
                )
            self.assertEqual(pptd_pptx.patch_transitions(deck, "fade"), 1)
            summary = pptd_pptx.verify_output(deck, "fade")
            self.assertEqual(summary["slides"], 1)
            self.assertEqual(summary["fadeTransitions"], 1)


class ExportTests(unittest.TestCase):
    @patch.object(EXPORT.shutil, "which", return_value=None)
    def test_missing_node_is_a_clear_error(self, _which):
        with self.assertRaisesRegex(EXPORT.ExportError, "Node.js 18"):
            EXPORT.ensure_node()

    @patch.object(EXPORT.shutil, "which", return_value="/bin/node")
    def test_old_node_is_rejected(self, _which):
        completed = subprocess.CompletedProcess([], 0, stdout="v16.20.2\n")
        with patch.object(EXPORT, "run_command", return_value=completed):
            with self.assertRaisesRegex(EXPORT.ExportError, "Node.js 18"):
                EXPORT.ensure_node()

    def test_existing_output_is_not_overwritten_without_force(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "deck.pptx"
            output.write_bytes(b"keep")
            with patch.object(EXPORT, "ensure_node", return_value="node"):
                with self.assertRaisesRegex(EXPORT.ExportError, "already exists"):
                    EXPORT.export_pptx(MINIMAL, output)
            self.assertEqual(output.read_bytes(), b"keep")

    def test_wasm_binary_is_unique_and_byte_stable(self):
        wasm_files = list(SKILL_ROOT.rglob("*.wasm"))
        self.assertEqual(wasm_files, [SKILL_ROOT / "assets" / "wasm" / "pptd_wasm_bg.wasm"])
        self.assertEqual(hashlib.sha256(wasm_files[0].read_bytes()).hexdigest(), WASM_HASH)

    @unittest.skipUnless(shutil.which("node"), "node is required")
    def test_public_cli_exports_real_wasm_pptx(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "deck.pptx"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = EXPORT.main([str(MINIMAL), "--output", str(output)])
            self.assertEqual(result, 0)
            summary = json.loads(stdout.getvalue())
            self.assertEqual(summary["exporter"], "wasm")
            self.assertEqual(summary["slides"], summary["fadeTransitions"])
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                app = archive.read("docProps/app.xml").decode()
                provenance = archive.read("customXml/provenance.xml").decode()
                slide = archive.read("ppt/slides/slide1.xml").decode()
                self.assertIn("<Application>PPT Design</Application>", app)
                self.assertIn("urn:pptd:prov:provenance", provenance)
                self.assertIn("<producer>PPT Design (local)</producer>", provenance)
                self.assertIn('xmlns:pptd="https://pptd.local/ns/2026/pptd/schema"', slide)

    @unittest.skipUnless(shutil.which("node"), "node is required")
    def test_exports_local_media_and_transition_none(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "qa.pptx"
            summary = EXPORT.export_pptx(QA_DECK, output, transition="none")
            self.assertEqual(summary["slides"], 3)
            self.assertEqual(summary["fadeTransitions"], 0)
            self.assertEqual(summary["fontParts"], 0)
            with zipfile.ZipFile(output) as archive:
                self.assertTrue(any(name.startswith("ppt/media/") for name in archive.namelist()))

    @unittest.skipUnless(shutil.which("node"), "node is required")
    def test_advanced_charts_export_as_framed_svg_pictures(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "charts.pptx"
            summary = EXPORT.export_pptx(ADVANCED_CHARTS, output)
            self.assertEqual(summary["slides"], 5)
            with zipfile.ZipFile(output) as archive:
                svgs = [n for n in archive.namelist() if n.startswith("ppt/media/") and n.endswith(".svg")]
                for svg in svgs:
                    # PowerPoint ignores dominant-baseline; text must carry explicit offsets.
                    self.assertNotIn("dominant-baseline", archive.read(svg).decode())
                for index in range(1, 5):
                    slide = archive.read(f"ppt/slides/slide{index}.xml").decode()
                    shapes = dict(re.findall(r'<p:cNvPr id="(\d+)" name="([^"]+)"', slide))
                    chart_id = f"chart-{index}"
                    self.assertIn(chart_id, shapes.values())
                    self.assertIn(f"{chart_id}-frame", shapes.values())
                    # The picture is bare: no alpha-traced shadow, no split border shape.
                    picture = re.search(r"<p:pic>.*?</p:pic>", slide, re.S).group(0)
                    self.assertNotIn("effectLst", picture)
                    self.assertFalse(any(value.endswith("-border") for value in shapes.values()))
                    self.assertNotIn('<a:ln w="0">', slide)
                    # Every frame layer animates together with the chart.
                    timing = slide[slide.index("<p:timing") :]
                    animated = set(re.findall(r'spTgt spid="(\d+)"', timing))
                    self.assertEqual(animated, set(shapes))


class ReferenceCoverageTests(unittest.TestCase):
    def test_all_44_presets_are_retained_and_indexed(self):
        root = SKILL_ROOT / "references" / "design_system"
        index = (root / "README.md").read_text(encoding="utf-8")
        presets = {path.stem for path in root.glob("*.md") if path.name != "README.md"}
        indexed = set(re.findall(r"`([a-z0-9-]+)`", index))
        self.assertEqual(len(presets), 44)
        self.assertEqual(indexed, presets)

    def test_all_seven_scenarios_are_retained_and_routed(self):
        root = SKILL_ROOT / "references" / "slides_categories"
        router = (SKILL_ROOT / "references" / "slides_categories.md").read_text(encoding="utf-8")
        scenarios = sorted(root.glob("*.md"))
        self.assertEqual(len(scenarios), 7)
        for path in scenarios:
            self.assertIn(f"references/slides_categories/{path.name}", router)


if __name__ == "__main__":
    unittest.main()
