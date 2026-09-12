"""Regression cases for real SVG input and batch-validation behavior."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_visualize import SCRIPT_DIR, SKILL_DIR, Validator, result_named, svg_document, write_svg, svgkit


class _InputCase(unittest.TestCase):
    def check(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(Path(tmp), "input.svg", source)
            validator = Validator(path, no_color=True)
            results = validator.collect()
            return validator, results


class InputValidationTests(_InputCase):
    def test_percentage_background_and_position_match_the_viewbox(self):
        source = svg_document('<rect x="10%" y="25%" width="40%" height="20%" fill="#E1F5EE"/>')
        source = source.replace('width="500" height="300" fill="#FFFFFF"',
                                'width="100%" height="100%" fill="#FFFFFF"')
        validator, results = self.check(source)
        self.assertFalse([result for result in results if result.status != "pass"])
        bounds = validator.collect_obstacles()[0]
        self.assertEqual((bounds.left, bounds.top, bounds.width, bounds.height), (50, 75, 200, 60))

    def test_bad_viewbox_is_a_diagnostic_instead_of_guessed_numbers(self):
        for raw in ("0 0 500junk 300", "0 0 1e999 300", "0 0 -1 300", "0 0 500"):
            with self.subTest(raw=raw):
                _, results = self.check(svg_document().replace('viewBox="0 0 500 300"', f'viewBox="{raw}"'))
                self.assertEqual(result_named(results, "Checking viewBox").status, "fail")

    def test_standalone_svg_requires_its_namespace(self):
        for namespace in ("", "http://www.w3.org/1999/xhtml"):
            with self.subTest(namespace=namespace):
                _, results = self.check(svg_document().replace("http://www.w3.org/2000/svg", namespace))
                self.assertEqual(result_named(results, "Checking SVG root").status, "fail")

    def test_invalid_colors_and_dimensions_never_escape_as_exceptions(self):
        for fragment in (
            '<rect x="40" y="40" width="120" height="56" fill="#zzzz"/>',
            '<rect x="1e999" y="40" width="120" height="56" fill="#E1F5EE"/>',
            '<rect x="40" y="40" width="-120" height="56" fill="#E1F5EE"/>',
            '<polygon points="40 40 80" fill="#E1F5EE"/>',
        ):
            with self.subTest(fragment=fragment):
                validator, results = self.check(svg_document(fragment))
                self.assertGreater(validator.failures, 0)
                self.assertEqual(result_named(results, "Checking SVG values").status, "fail")

    def test_canvas_bounds_include_small_shapes_and_connectors(self):
        for fragment in (
            '<rect x="490" y="100" width="40" height="20" fill="#E1F5EE"/>',
            '<path d="M200 100 L520 100" fill="none" stroke="#73726C" marker-end="url(#arrow)"/>',
        ):
            with self.subTest(fragment=fragment):
                _, results = self.check(svg_document(fragment))
                self.assertEqual(result_named(results, "Checking box bounds vs viewBox").status, "fail")

    def test_free_text_outside_the_canvas_is_reported(self):
        _, results = self.check(svg_document(
            '<text x="480" y="120" font-size="12" dominant-baseline="central">Clipped text</text>'
        ))
        self.assertEqual(result_named(results, "Checking text bounds vs viewBox").status, "warn")

    def test_white_background_accepts_color_notation_but_requires_opaque_paint(self):
        for paint, expected in (
            ("white", "pass"), ("#fff", "pass"), ("#ffffffff", "pass"),
            ("rgb(100% 100% 100%)", "pass"), ("rgba(255,255,255,1)", "pass"),
            ("rgb(255 255 255 / 100%)", "pass"),
            ("#fff0", "fail"), ("#ffffff80", "fail"),
            ("rgba(255,255,255,0.5)", "fail"), ("rgb(255 255 255 / 50%)", "fail"),
        ):
            with self.subTest(paint=paint):
                _, results = self.check(svg_document().replace('fill="#FFFFFF"', f'fill="{paint}"'))
                self.assertEqual(result_named(results, "Checking white background").status, expected)

    def test_thick_stroke_extending_beyond_canvas_is_reported(self):
        _, results = self.check(svg_document(
            '<line x1="3" y1="40" x2="3" y2="200" stroke="#73726C" stroke-width="10"/>'
        ))
        self.assertEqual(result_named(results, "Checking box bounds vs viewBox").status, "fail")

    def test_filled_triangle_is_not_the_house_chevron(self):
        source = svg_document().replace('d="M2 1L8 5L2 9" fill="none"',
                                        'd="M0 0L10 5L0 10Z" fill="context-stroke"')
        _, results = self.check(source)
        self.assertEqual(result_named(results, "Checking marker contract").status, "fail")

    def test_svg_values_accept_equivalent_marker_url_quoting(self):
        _, results = self.check(svg_document(
            '<line x1="40" y1="60" x2="160" y2="60" stroke="#73726C" marker-end="url(\'#arrow\')"/>'
        ))
        self.assertEqual(result_named(results, "Checking marker contract").status, "pass")

    def test_collect_sets_counts_even_for_read_and_xml_errors(self):
        validator = Validator(Path("does-not-exist.svg"), no_color=True)
        results = validator.collect()
        self.assertEqual(validator.failures, sum(result.status == "fail" for result in results))
        self.assertGreater(validator.failures, 0)

        validator, results = self.check("<svg>")
        self.assertGreater(validator.failures, 0)

    def test_fixed_size_bar_reports_text_that_does_not_fit(self):
        d = svgkit.Diagram(400, 240, title="Timeline", desc="The label is wider than a fixed duration bar.")
        d.bar(80, 100, 40, "A long task label", family="green")
        _, results = self.check(d.render())
        self.assertEqual(result_named(results, "Checking text fit").status, "warn")

    def test_small_nodes_and_markerless_connectors_are_checked(self):
        d = svgkit.Diagram(400, 240, title="Routing", desc="A connector cuts through a narrow node.")
        d.node(100, 80, "A", w=60)
        d.raw('<line x1="40" y1="100" x2="240" y2="100" stroke="#73726C"/>', layer="arrows")
        _, results = self.check(d.render())
        self.assertEqual(result_named(results, "Checking arrow collisions").status, "fail")

    def test_broad_nodes_do_not_disappear_from_overlap_checks(self):
        d = svgkit.Diagram(500, 300, title="Overlap", desc="A large ordinary node contains another node.")
        d.node(40, 60, "Outer", w=420, h=160)
        d.node(100, 80, "Inner")
        _, results = self.check(d.render())
        self.assertEqual(result_named(results, "Checking box overlap").status, "fail")

    def test_automatic_diamond_width_leaves_room_for_long_cjk_labels(self):
        d = svgkit.Diagram(700, 240, title="Decision", desc="A long Chinese decision label.")
        d.diamond(40, 80, "所有必要的前置条件均已满足？")
        _, results = self.check(d.render())
        self.assertFalse([result for result in results if result.status != "pass"])


class PresentationTests(_InputCase):
    def test_descendant_selector_backtracks_when_a_nearer_ancestor_does_not_match(self):
        _, results = self.check(svg_document(
            '<style>#outer > .group .item { display:none }</style>'
            '<rect x="40" y="60" width="120" height="56" fill="#E1F5EE"/>'
            '<g id="outer"><g class="group"><g><g class="group">'
            '<rect class="item" x="50" y="70" width="120" height="56" fill="#E1F5EE"/>'
            '</g></g></g></g>'
        ))
        self.assertEqual(result_named(results, "Checking box overlap").status, "pass")

    def test_stylesheet_marker_accepts_important(self):
        _, results = self.check(svg_document(
            '<style>.edge { marker-end: url(#arrow) !important; }</style>'
            '<line class="edge" x1="40" y1="60" x2="160" y2="60" stroke="#73726C"/>'
        ))
        self.assertEqual(result_named(results, "Checking marker contract").status, "pass")

    def test_stylesheet_hidden_shapes_do_not_create_collisions(self):
        _, results = self.check(svg_document(
            '<style>.ghost { display: none !important; }</style>'
            '<rect x="40" y="60" width="120" height="56" fill="#E1F5EE"/>'
            '<rect class="ghost" x="50" y="70" width="120" height="56" fill="#E1F5EE" style="display:inline"/>'
        ))
        self.assertFalse([result for result in results if result.status != "pass"])

    def test_child_selector_specificity_and_inheritance(self):
        validator, results = self.check(svg_document(
            '<style>.item { fill-opacity:0 } g.group > rect.item { fill-opacity:1 }</style>'
            '<rect x="40" y="60" width="120" height="56" fill="#E1F5EE"/>'
            '<g class="group" fill="#E1F5EE"><rect class="item" x="50" y="70" width="120" height="56"/></g>'
        ))
        self.assertEqual(result_named(results, "Checking box overlap").status, "fail")
        self.assertEqual(len(validator.collect_obstacles()), 2)

    def test_visibility_can_be_overridden_but_parent_opacity_cannot(self):
        for parent, expected in (("visibility='hidden'", "fail"), ("opacity='0'", "pass")):
            with self.subTest(parent=parent):
                _, results = self.check(svg_document(
                    '<rect x="40" y="60" width="120" height="56" fill="#E1F5EE"/>'
                    f'<g {parent}><rect x="50" y="70" width="120" height="56" fill="#E1F5EE" '
                    'visibility="visible" opacity="1"/></g>'
                ))
                self.assertEqual(result_named(results, "Checking box overlap").status, expected)

    def test_unresolved_css_is_explicit_instead_of_a_clean_pass(self):
        _, results = self.check(svg_document('<style>rect:nth-child(2) { display:none }</style>'))
        self.assertTrue(any(result.status == "warn" and "CSS" in str(result.details) for result in results))


class BatchCliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run([sys.executable, "-B", str(SCRIPT_DIR / "validate_svg.py"), *map(str, arguments)],
                              check=False, capture_output=True, text=True, encoding="utf-8")

    def test_directory_json_is_recursive_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested").mkdir()
            good = write_svg(root, "good.svg", svg_document())
            write_svg(root / "nested", "bad.svg", svg_document('<rect width="120" height="56" fill="#zzzz"/>'))
            result = self.run_cli("--json", root, good)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(report["summary"]["files"], 2)
            self.assertEqual({file["status"] for file in report["files"]}, {"pass", "fail"})
            self.assertEqual(result.stderr, "")

    def test_empty_directory_and_missing_file_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            for target in (Path(tmp), Path(tmp) / "missing.svg"):
                with self.subTest(target=target):
                    result = self.run_cli("--json", target)
                    self.assertEqual(result.returncode, 1)
                    self.assertGreater(json.loads(result.stdout)["summary"]["failures"], 0)

    def test_strict_promotes_warnings_to_a_failing_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(Path(tmp), "warning.svg", svg_document(
                '<text x="490" y="100" font-size="12" dominant-baseline="central">Clipped</text>'
            ))
            self.assertEqual(self.run_cli("--json", path).returncode, 0)
            result = self.run_cli("--strict", "--json", path)
            self.assertEqual(result.returncode, 1)
            self.assertGreater(json.loads(result.stdout)["summary"]["warnings"], 0)

    def test_plain_output_has_no_ansi_when_redirected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(Path(tmp), "good.svg", svg_document())
            result = self.run_cli(path)
            self.assertEqual(result.returncode, 0)
            self.assertNotIn("\x1b[", result.stdout)


class ImportIsolationTests(unittest.TestCase):
    def test_package_import_does_not_need_scripts_on_sys_path(self):
        script = """
import sys, types
sys.path.insert(0, sys.argv[1])
sys.modules['geometry'] = types.ModuleType('geometry')
from visualize.scripts.svgkit import Diagram
d = Diagram(400, 220, title='Import', desc='Package import with a conflicting module.')
d.node(40, 60, 'Node')
d.save('out.svg')
"""
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", script, str(SKILL_DIR.parent)],
                                    cwd=tmp, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((Path(tmp) / "out.svg").is_file())
