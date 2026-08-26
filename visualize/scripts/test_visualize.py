#!/usr/bin/env python3
"""Regression tests for svgkit and validate_svg (standard library only)."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import svgkit  # noqa: E402
from validate_svg import Validator  # noqa: E402


MARKER = """  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke"
            stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>"""


def svg_document(
    body: str = "",
    *,
    width: int = 500,
    height: int = 300,
    title_desc: str | None = None,
    defs: str = MARKER,
    background: str | None = '#FFFFFF',
) -> str:
    first = title_desc
    if first is None:
        first = "  <title>Test diagram</title>\n  <desc>A validator regression fixture.</desc>"
    bg = "" if background is None else (
        f'  <rect x="0" y="0" width="{width}" height="{height}" fill="{background}"/>'
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img">',
        first,
        "  <style>text { font-family: sans-serif; }</style>",
        defs,
        bg,
        body,
        "</svg>",
        "",
    ]
    return "\n".join(part for part in parts if part != "")


def write_svg(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def result_named(results, name: str):
    for result in results:
        if result.name == name:
            return result
    raise AssertionError(f"missing validator result: {name!r}; got {[r.name for r in results]}")


class SaveContractTests(unittest.TestCase):
    def test_hard_failure_raises_after_writing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "overlap.svg"
            d = svgkit.Diagram(420, 220, title="Overlap", desc="Two nodes overlap.")
            d.node(40, 70, "Alpha", "one")
            d.node(100, 85, "Beta", "two", family="green")
            error_type = getattr(svgkit, "ValidationError", AssertionError)
            stderr = io.StringIO()
            with self.assertRaises(error_type), contextlib.redirect_stderr(stderr):
                d.save(str(out))
            self.assertTrue(out.is_file(), "invalid output must remain available for inspection")
            self.assertIn("Checking box overlap", stderr.getvalue())
            self.assertIn("Fix:", stderr.getvalue())

    def test_warning_is_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "warning.svg"
            d = svgkit.Diagram(420, 220, title="Warning", desc="A deliberately narrow node.")
            d.node(40, 70, "A title much wider than this box", w=120)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                returned = d.save(str(out))
            self.assertEqual(returned, str(out))
            self.assertTrue(out.is_file())
            self.assertIn("Checking text fit", stderr.getvalue())

    def test_validator_import_ignores_shadowing_top_level_module(self) -> None:
        fake = types.ModuleType("validate_svg")
        calls: list[str] = []

        class WrongValidator:
            def __init__(self, *args, **kwargs):
                calls.append("wrong module used")
                raise RuntimeError("shadow validator")

        fake.Validator = WrongValidator
        previous = sys.modules.get("validate_svg")
        sys.modules["validate_svg"] = fake
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "clean.svg"
                d = svgkit.Diagram(320, 180, title="Clean", desc="A clean node.")
                d.node(40, 70, "Node")
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    d.save(str(out))
                self.assertEqual(calls, [])
                self.assertIn("self-check passed", stderr.getvalue())
        finally:
            if previous is None:
                sys.modules.pop("validate_svg", None)
            else:
                sys.modules["validate_svg"] = previous

    def test_validator_load_failure_is_not_silent(self) -> None:
        self.assertTrue(hasattr(svgkit, "_load_validator_module"))
        error_type = getattr(svgkit, "ValidationError", AssertionError)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "load-error.svg"
            d = svgkit.Diagram(320, 180, title="Load error", desc="Validator cannot load.")
            with mock.patch.object(
                svgkit, "_load_validator_module", side_effect=RuntimeError("loader exploded")
            ):
                with self.assertRaises(error_type) as caught:
                    d.save(str(out))
            self.assertIn("loader exploded", str(caught.exception))
            self.assertTrue(out.is_file())


class ValidatorLifecycleTests(unittest.TestCase):
    def test_reused_validator_resets_geometry_parse_state_and_counters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = write_svg(
                directory,
                "reuse.svg",
                svg_document('<rect x="40" y="80" width="120" height="56" fill="#F5F4ED"/>'),
            )
            validator = Validator(path, no_color=True)
            first = validator.collect()
            self.assertEqual(result_named(first, "Checking box overlap").status, "pass")

            path.write_text(
                svg_document(
                    '<rect x="40" y="80" width="160" height="80" fill="#F5F4ED"/>'
                    '\n<rect x="100" y="100" width="160" height="80" fill="#E1F5EE"/>'
                ),
                encoding="utf-8",
            )
            second = validator.collect()
            self.assertEqual(result_named(second, "Checking box overlap").status, "fail")

            warning_svg = svg_document(
                '<rect x="40" y="80" width="120" height="56" fill="#F5F4ED"/>'
                '\n<text x="100" y="108" text-anchor="middle" dominant-baseline="central" '
                'font-size="14" data-role="node-text">This label is far too wide</text>'
            )
            path.write_text(warning_svg, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                validator.run(quiet=True)
            first_warning_count = validator.warnings
            with contextlib.redirect_stdout(io.StringIO()):
                validator.run(quiet=True)
            self.assertEqual(validator.warnings, first_warning_count)

            path.write_text("<svg>", encoding="utf-8")
            malformed = validator.collect()
            self.assertTrue(any(r.status == "fail" for r in malformed))
            self.assertIsNone(validator.root)
            self.assertIsNone(validator.viewbox)


class PathGeometryTests(unittest.TestCase):
    def test_implicit_and_inherited_fill_create_obstacles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            body = (
                '<path d="M 20 40 L 120 40 L 120 100 L 20 100 Z"/>'
                '\n<g fill="#E1F5EE"><path d="M 180 40 L 280 40 L 280 100 L 180 100 Z"/></g>'
            )
            path = write_svg(directory, "paint.svg", svg_document(body))
            validator = Validator(path, no_color=True)
            validator.collect()
            paths = [b for b in validator.collect_obstacles() if b.element == "path"]
            self.assertEqual(len(paths), 2)

    def test_bezier_and_arc_bounds_include_curve_extrema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            bezier = write_svg(
                directory,
                "bezier.svg",
                svg_document(
                    '<path d="M 10 100 C 10 10 90 10 90 100 L 90 130 L 10 130 Z" '
                    'fill="#F5F4ED"/>'
                ),
            )
            vb = Validator(bezier, no_color=True)
            vb.collect()
            bezier_box = next(b for b in vb.collect_obstacles() if b.element == "path")
            self.assertAlmostEqual(bezier_box.top, 32.5, places=1)

            arc = write_svg(
                directory,
                "arc.svg",
                svg_document(
                    '<path d="M 10 50 A 40 20 0 0 1 90 50 L 90 110 L 10 110 Z" '
                    'fill="#F5F4ED"/>'
                ),
            )
            va = Validator(arc, no_color=True)
            va.collect()
            arc_box = next(b for b in va.collect_obstacles() if b.element == "path")
            self.assertAlmostEqual(arc_box.top, 30.0, places=1)

    def test_cylinder_bounds_and_cap_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "cylinder.svg"
            d = svgkit.Diagram(420, 220, title="Cylinder", desc="An arrow crosses the upper cap.")
            store = d.cylinder(140, 50, "Store", family="green", w=120, h=54)
            d.arrow((40, 55), (360, 55))
            out.write_text(d.render(), encoding="utf-8")

            validator = Validator(out, no_color=True)
            results = validator.collect()
            path_box = next(b for b in validator.collect_obstacles() if b.element == "path")
            self.assertAlmostEqual(path_box.top, store.y, places=1)
            self.assertAlmostEqual(path_box.bottom, store.y + store.h, places=1)
            self.assertEqual(result_named(results, "Checking arrow collisions").status, "fail")


class TextRoleTests(unittest.TestCase):
    def test_explicit_arrow_label_inside_node_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "label-node.svg",
                svg_document(
                    '<rect x="100" y="80" width="200" height="80" data-role="node" '
                    'fill="#F5F4ED"/>'
                    '\n<text x="200" y="120" text-anchor="middle" dominant-baseline="central" '
                    'font-size="12" data-role="arrow-label">arrow label</text>'
                ),
            )
            results = Validator(path, no_color=True).collect()
            self.assertEqual(result_named(results, "Checking label vs box").status, "warn")

    def test_explicit_free_labels_inside_panel_still_collide_with_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "labels-panel.svg",
                svg_document(
                    '<rect x="60" y="50" width="300" height="180" data-role="panel" '
                    'fill="#FFFFFF" stroke="#73726C"/>'
                    '\n<text x="200" y="120" text-anchor="middle" dominant-baseline="central" '
                    'font-size="12" data-role="arrow-label">first label</text>'
                    '\n<text x="200" y="120" text-anchor="middle" dominant-baseline="central" '
                    'font-size="12" data-role="arrow-label">second label</text>'
                ),
            )
            results = Validator(path, no_color=True).collect()
            self.assertEqual(result_named(results, "Checking label vs label").status, "warn")
            self.assertEqual(result_named(results, "Checking label vs box").status, "pass")

    def test_positioned_tspan_is_skipped_with_explicit_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "tspan.svg",
                svg_document(
                    '<text x="100" y="80" font-size="12">'
                    '<tspan x="100" y="80">first</tspan>'
                    '<tspan x="100" y="110">second</tspan>'
                    '</text>'
                ),
            )
            results = Validator(path, no_color=True).collect()
            warning = result_named(results, "Checking unsupported text geometry")
            self.assertEqual(warning.status, "warn")
            self.assertTrue(any("tspan" in detail.lower() for detail in warning.details or []))


class ShapeOverlapTests(unittest.TestCase):
    def test_node_containment_fails_but_panel_containment_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            nodes = write_svg(
                directory,
                "node-containment.svg",
                svg_document(
                    '<rect x="40" y="40" width="300" height="200" data-role="node" '
                    'fill="#F5F4ED"/>'
                    '\n<rect x="100" y="100" width="120" height="56" data-role="node" '
                    'fill="#E1F5EE"/>'
                ),
            )
            node_result = result_named(Validator(nodes, no_color=True).collect(), "Checking box overlap")
            self.assertEqual(node_result.status, "fail")

            panel = write_svg(
                directory,
                "panel-containment.svg",
                svg_document(
                    '<rect x="40" y="40" width="300" height="200" data-role="panel" '
                    'fill="#FFFFFF" stroke="#73726C"/>'
                    '\n<rect x="100" y="100" width="120" height="56" data-role="node" '
                    'fill="#E1F5EE"/>'
                ),
            )
            panel_result = result_named(Validator(panel, no_color=True).collect(), "Checking box overlap")
            self.assertEqual(panel_result.status, "pass")

    def test_disjoint_diamonds_with_overlapping_aabbs_do_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "diamonds.svg",
                svg_document(
                    '<polygon points="50,0 100,50 50,100 0,50" data-role="node" '
                    'fill="#FAEEDA"/>'
                    '\n<polygon points="140,90 190,140 140,190 90,140" data-role="node" '
                    'fill="#E1F5EE"/>'
                ),
            )
            result = result_named(Validator(path, no_color=True).collect(), "Checking box overlap")
            self.assertEqual(result.status, "pass")


class ContractCheckTests(unittest.TestCase):
    def assert_check_fails(self, text: str, check_name: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(Path(tmp), "contract.svg", text)
            result = result_named(Validator(path, no_color=True).collect(), check_name)
            self.assertEqual(result.status, "fail", result)

    def test_accessibility_requires_nonempty_title_desc_as_first_children(self) -> None:
        self.assert_check_fails(
            svg_document(title_desc="  <style>text { font-family: sans-serif; }</style>"),
            "Checking accessibility",
        )
        self.assert_check_fails(
            svg_document(title_desc="  <desc>out of order</desc>\n  <title>Title</title>"),
            "Checking accessibility",
        )

    def test_marker_contract_rejects_duplicates_and_wrong_marker_refs(self) -> None:
        duplicate_defs = MARKER.replace("  </defs>", "") + (
            '\n    <marker id="arrow"><path d="M0 0L1 1"/></marker>\n  </defs>'
        )
        self.assert_check_fails(
            svg_document(defs=duplicate_defs),
            "Checking marker contract",
        )
        wrong = MARKER.replace('id="arrow"', 'id="other"')
        self.assert_check_fails(
            svg_document(
                '<line x1="20" y1="20" x2="100" y2="20" marker-end="url(#other)"/>',
                defs=wrong,
            ),
            "Checking marker contract",
        )

    def test_white_background_is_required(self) -> None:
        self.assert_check_fails(svg_document(background="#000000"), "Checking white background")
        self.assert_check_fails(svg_document(background=None), "Checking white background")

    def test_gradients_and_filters_are_forbidden(self) -> None:
        gradient_defs = MARKER.replace(
            "  </defs>",
            '    <linearGradient id="g"><stop offset="0" stop-color="#fff"/></linearGradient>\n  </defs>',
        )
        self.assert_check_fails(svg_document(defs=gradient_defs), "Checking flat style")
        filter_defs = MARKER.replace(
            "  </defs>",
            '    <filter id="f"><feGaussianBlur stdDeviation="2"/></filter>\n  </defs>',
        )
        self.assert_check_fails(svg_document(defs=filter_defs), "Checking flat style")


class CliAndDocumentationTests(unittest.TestCase):
    def test_quiet_cli_is_silent_for_clean_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(Path(tmp), "clean.svg", svg_document())
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "validate_svg.py"), "--no-color", "-q", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(proc.stdout, "")
            self.assertEqual(proc.stderr, "")

    def test_state_machine_retains_transition_action_and_validates(self) -> None:
        path = SKILL_DIR / "assets" / "gallery" / "state-machine.svg"
        text = path.read_text(encoding="utf-8")
        self.assertIn("pay / confirm", text)
        results = Validator(path, no_color=True).collect()
        self.assertFalse([r for r in results if r.status == "fail"])

    def test_curve_label_offset_is_documented(self) -> None:
        cookbook = (SKILL_DIR / "references" / "svg-cookbook.md").read_text(encoding="utf-8")
        self.assertIn("marker=True, dashed=False, label_offset=8", cookbook)


class FinalReviewRegressionTests(unittest.TestCase):
    def test_aligned_rectangles_with_positive_overlap_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "aligned-overlap.svg",
                svg_document(
                    '<rect x="40" y="80" width="120" height="56" fill="#F5F4ED"/>'
                    '\n<rect x="150" y="80" width="120" height="56" fill="#E1F5EE"/>'
                ),
            )
            result = result_named(Validator(path, no_color=True).collect(), "Checking box overlap")
            self.assertEqual(result.status, "fail")

    def test_generated_actor_label_without_host_remains_collision_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actor-label.svg"
            d = svgkit.Diagram(440, 260, title="Actor label", desc="Actor text reaches a use case.")
            d.actor(100, 70, "A very long external administrator")
            d.usecase(120, 112, "Manage accounts", w=180)
            path.write_text(d.render(), encoding="utf-8")
            result = result_named(Validator(path, no_color=True).collect(), "Checking label vs box")
            self.assertEqual(result.status, "warn")

    def test_transformed_arrow_is_skipped_instead_of_checked_at_raw_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "transformed-arrow.svg",
                svg_document(
                    '<rect x="100" y="80" width="120" height="56" fill="#F5F4ED"/>'
                    '\n<line x1="20" y1="100" x2="300" y2="100" '
                    'transform="translate(0 150)" marker-end="url(#arrow)"/>'
                ),
            )
            results = Validator(path, no_color=True).collect()
            self.assertEqual(result_named(results, "Checking arrow collisions").status, "pass")
            self.assertEqual(result_named(results, "Checking unsupported transforms").status, "warn")

    def test_foreground_white_rect_does_not_satisfy_background_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "foreground-background.svg",
                svg_document(
                    '<rect x="80" y="80" width="120" height="56" fill="#F5F4ED"/>'
                    '\n<rect width="500" height="300" fill="#FFFFFF"/>',
                    background=None,
                ),
            )
            result = result_named(Validator(path, no_color=True).collect(), "Checking white background")
            self.assertEqual(result.status, "fail")

    def test_inline_style_and_inherited_marker_targets_must_use_arrow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "style-marker.svg",
                svg_document(
                    '<g id="other"/>'
                    '\n<g style="marker-end: url(#other)">'
                    '<line x1="20" y1="40" x2="100" y2="40"/></g>'
                ),
            )
            result = result_named(Validator(path, no_color=True).collect(), "Checking marker contract")
            self.assertEqual(result.status, "fail")

    def test_missing_local_href_fragment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "missing-fragment.svg",
                svg_document('<use href="#missing" x="20" y="20"/>'),
            )
            result = result_named(
                Validator(path, no_color=True).collect(), "Checking URL/marker references"
            )
            self.assertEqual(result.status, "fail")

    def test_external_paint_urls_and_relative_assets_are_rejected(self) -> None:
        fixtures = (
            '<rect x="20" y="20" width="100" height="60" '
            'fill="url(https://example.test/paint.svg#fill)"/>',
            '<image href="assets/picture.png" x="20" y="20" width="100" height="60"/>',
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for index, body in enumerate(fixtures):
                path = write_svg(directory, f"external-{index}.svg", svg_document(body))
                result = result_named(
                    Validator(path, no_color=True).collect(), "Checking renderer-safe assets"
                )
                self.assertEqual(result.status, "fail", body)


class SecondReviewRegressionTests(unittest.TestCase):
    def test_marker_shorthand_is_enforced_and_classifies_arrows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            wrong = write_svg(
                directory,
                "marker-shorthand-wrong.svg",
                svg_document(
                    '<g id="other"/>'
                    '\n<line x1="20" y1="40" x2="100" y2="40" '
                    'style="marker: url(#other); stroke: #73726C"/>'
                ),
            )
            wrong_result = result_named(
                Validator(wrong, no_color=True).collect(), "Checking marker contract"
            )
            self.assertEqual(wrong_result.status, "fail")

            crossing = write_svg(
                directory,
                "marker-shorthand-arrow.svg",
                svg_document(
                    '<rect x="100" y="80" width="120" height="56" fill="#F5F4ED"/>'
                    '\n<line x1="20" y1="100" x2="300" y2="100" '
                    'style="marker: url(#arrow); stroke: #73726C"/>'
                ),
            )
            crossing_result = result_named(
                Validator(crossing, no_color=True).collect(), "Checking arrow collisions"
            )
            self.assertEqual(crossing_result.status, "fail")

    def test_css_transforms_skip_raw_geometry_with_warning(self) -> None:
        fixtures = (
            '<rect x="100" y="80" width="120" height="56" fill="#F5F4ED"/>'
            '\n<line x1="20" y1="100" x2="300" y2="100" stroke="#73726C" '
            'style="transform: translate(0, 150px)" marker-end="url(#arrow)"/>',
            '<style>.moved { transform: translate(0, 150px); }</style>'
            '\n<rect x="100" y="80" width="120" height="56" fill="#F5F4ED"/>'
            '\n<line class="moved" x1="20" y1="100" x2="300" y2="100" '
            'stroke="#73726C" marker-end="url(#arrow)"/>',
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for index, body in enumerate(fixtures):
                path = write_svg(directory, f"css-transform-{index}.svg", svg_document(body))
                results = Validator(path, no_color=True).collect()
                self.assertEqual(
                    result_named(results, "Checking arrow collisions").status, "pass", body
                )
                self.assertEqual(
                    result_named(results, "Checking unsupported transforms").status, "warn", body
                )

    def test_curved_arrow_uses_curve_geometry_not_endpoint_chord(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "curved-arrow.svg",
                svg_document(
                    '<rect x="120" y="100" width="80" height="40" fill="#F5F4ED"/>'
                    '\n<path d="M20 180 C20 20 300 20 300 60" fill="none" '
                    'stroke="#73726C" marker-end="url(#arrow)"/>'
                ),
            )
            result = result_named(Validator(path, no_color=True).collect(), "Checking arrow collisions")
            self.assertEqual(result.status, "pass")

    def test_background_and_obstacles_honor_effective_visibility_and_alpha(self) -> None:
        hidden_backgrounds = (
            '<rect width="500" height="300" fill="#FFFFFF" display="none"/>',
            '<rect width="500" height="300" fill="#FFFFFF" fill-opacity="50%"/>',
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for index, background in enumerate(hidden_backgrounds):
                path = write_svg(
                    directory,
                    f"hidden-background-{index}.svg",
                    svg_document(background, background=None),
                )
                result = result_named(
                    Validator(path, no_color=True).collect(), "Checking white background"
                )
                self.assertEqual(result.status, "fail", background)

            invisible_node = write_svg(
                directory,
                "invisible-node.svg",
                svg_document(
                    '<rect x="40" y="80" width="160" height="80" fill="#F5F4ED"/>'
                    '\n<rect x="100" y="100" width="160" height="80" '
                    'fill="#E1F5EE" opacity="0"/>'
                ),
            )
            overlap = result_named(
                Validator(invisible_node, no_color=True).collect(), "Checking box overlap"
            )
            self.assertEqual(overlap.status, "pass")

    def test_inline_text_shadow_fails_flat_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "text-shadow.svg",
                svg_document(
                    '<text x="40" y="80" style="text-shadow: 2px 2px #000" '
                    'font-size="12">shadowed</text>'
                ),
            )
            result = result_named(Validator(path, no_color=True).collect(), "Checking flat style")
            self.assertEqual(result.status, "fail")


class AdvancedGeometryAndStyleTests(unittest.TestCase):
    def test_concave_polygons_distinguish_overlap_from_empty_cavity(self) -> None:
        u_points = "40,40 240,40 240,240 180,240 180,100 100,100 100,240 40,240"
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            identical = write_svg(
                directory,
                "concave-identical.svg",
                svg_document(
                    f'<polygon points="{u_points}" fill="#F5F4ED"/>'
                    f'\n<polygon points="{u_points}" fill="#E1F5EE"/>'
                ),
            )
            identical_result = result_named(
                Validator(identical, no_color=True).collect(), "Checking box overlap"
            )
            self.assertEqual(identical_result.status, "fail")

            cavity = write_svg(
                directory,
                "concave-cavity.svg",
                svg_document(
                    f'<polygon points="{u_points}" fill="#F5F4ED"/>'
                    '\n<rect x="105" y="120" width="70" height="60" fill="#E1F5EE"/>'
                ),
            )
            cavity_result = result_named(
                Validator(cavity, no_color=True).collect(), "Checking box overlap"
            )
            self.assertEqual(cavity_result.status, "pass")

    def test_individual_css_transforms_follow_skip_policy(self) -> None:
        fixtures = (
            '<rect x="100" y="80" width="120" height="56" fill="#F5F4ED"/>'
            '\n<line x1="20" y1="100" x2="300" y2="100" stroke="#73726C" '
            'style="translate: 0 150px" marker-end="url(#arrow)"/>',
            '<style>.moved { translate: 0 150px; }</style>'
            '\n<rect x="100" y="80" width="120" height="56" fill="#F5F4ED"/>'
            '\n<line class="moved" x1="20" y1="100" x2="300" y2="100" '
            'stroke="#73726C" marker-end="url(#arrow)"/>',
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for index, body in enumerate(fixtures):
                path = write_svg(directory, f"individual-transform-{index}.svg", svg_document(body))
                results = Validator(path, no_color=True).collect()
                self.assertEqual(result_named(results, "Checking arrow collisions").status, "pass")
                self.assertEqual(result_named(results, "Checking unsupported transforms").status, "warn")

            moved_background = write_svg(
                directory,
                "moved-background.svg",
                svg_document(
                    '<rect width="500" height="300" fill="#FFFFFF" '
                    'style="translate: 100px 0"/>',
                    background=None,
                ),
            )
            background_result = result_named(
                Validator(moved_background, no_color=True).collect(), "Checking white background"
            )
            self.assertEqual(background_result.status, "fail")

    def test_zero_alpha_rgba_fill_and_stroke_are_not_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            transparent_box = write_svg(
                directory,
                "transparent-box.svg",
                svg_document(
                    '<rect x="100" y="80" width="120" height="56" '
                    'fill="rgba(0,0,0,0)"/>'
                    '\n<line x1="20" y1="100" x2="300" y2="100" '
                    'stroke="#73726C" marker-end="url(#arrow)"/>'
                ),
            )
            box_result = result_named(
                Validator(transparent_box, no_color=True).collect(), "Checking arrow collisions"
            )
            self.assertEqual(box_result.status, "pass")

            transparent_arrow = write_svg(
                directory,
                "transparent-arrow.svg",
                svg_document(
                    '<rect x="100" y="80" width="120" height="56" fill="#F5F4ED"/>'
                    '\n<line x1="20" y1="100" x2="300" y2="100" '
                    'stroke="rgba(0,0,0,0)" marker-end="url(#arrow)"/>'
                ),
            )
            arrow_result = result_named(
                Validator(transparent_arrow, no_color=True).collect(), "Checking arrow collisions"
            )
            self.assertEqual(arrow_result.status, "pass")

    def test_external_xml_stylesheet_processing_instruction_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = (
                '<?xml-stylesheet type="text/css" href="https://example.test/theme.css"?>\n'
                + svg_document()
            )
            path = write_svg(Path(tmp), "xml-stylesheet.svg", text)
            result = result_named(
                Validator(path, no_color=True).collect(), "Checking renderer-safe assets"
            )
            self.assertEqual(result.status, "fail")

    def test_stylesheet_marker_none_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "stylesheet-marker-none.svg",
                svg_document(
                    '<style>line { marker: none; marker-end: none; }</style>'
                    '\n<line x1="20" y1="40" x2="100" y2="40" stroke="#73726C" '
                    'marker-end="url(#arrow)"/>'
                ),
            )
            result = result_named(Validator(path, no_color=True).collect(), "Checking marker contract")
            self.assertEqual(result.status, "fail")

    def test_nested_tspan_is_skipped_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                Path(tmp),
                "nested-tspan.svg",
                svg_document(
                    '<rect x="80" y="70" width="180" height="80" fill="#F5F4ED"/>'
                    '\n<text data-role="arrow-label"><a href="#arrow">'
                    '<tspan x="120" y="100">linked label</tspan></a></text>'
                ),
            )
            result = result_named(
                Validator(path, no_color=True).collect(), "Checking unsupported text geometry"
            )
            self.assertEqual(result.status, "warn")
            self.assertTrue(any("tspan" in detail.lower() for detail in result.details or []))

    def test_cookbook_panel_template_has_semantic_roles(self) -> None:
        cookbook = (SKILL_DIR / "references" / "svg-cookbook.md").read_text(encoding="utf-8")
        self.assertIn('<rect data-role="panel" x="120" y="40"', cookbook)
        self.assertIn('<text data-role="container-label" x="140" y="66"', cookbook)
        self.assertNotIn("Full containment is fine", cookbook)


class CSSCascadeTests(unittest.TestCase):
    def test_inline_important_visibility_and_alpha_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            hidden_background = write_svg(
                directory,
                "important-background.svg",
                svg_document(
                    '<rect width="500" height="300" fill="#FFFFFF" '
                    'style="display: none !important; display: block"/>',
                    background=None,
                ),
            )
            background_result = result_named(
                Validator(hidden_background, no_color=True).collect(), "Checking white background"
            )
            self.assertEqual(background_result.status, "fail")

            invisible_node = write_svg(
                directory,
                "important-opacity.svg",
                svg_document(
                    '<rect x="40" y="80" width="160" height="80" fill="#F5F4ED"/>'
                    '\n<rect x="100" y="100" width="160" height="80" '
                    'fill="#E1F5EE" style="opacity: 0 !important; opacity: 1"/>'
                ),
            )
            overlap_result = result_named(
                Validator(invisible_node, no_color=True).collect(), "Checking box overlap"
            )
            self.assertEqual(overlap_result.status, "pass")


class ParserAndCompatibilityTests(unittest.TestCase):
    def test_path_parser_supports_relative_repeated_hv_sqt_arc_and_close(self) -> None:
        from validate_svg import parse_path, parse_path_points, path_bounds

        path = (
            "m 10 10 20 0 0 10 "
            "h 10 5 v 10 -5 "
            "c 5 0 5 10 10 10 5 0 5 -10 10 -10 "
            "s 5 10 10 0 5 -10 10 0 "
            "q 5 10 10 0 5 -10 10 0 "
            "t 10 0 10 10 "
            "a 10 5 0 0 1 20 0 10 5 0 0 1 20 0 z"
        )
        parsed = parse_path(path)
        self.assertEqual([segment.kind for segment in parsed.segments].count("L"), 7)
        self.assertEqual([segment.kind for segment in parsed.segments].count("C"), 4)
        self.assertEqual([segment.kind for segment in parsed.segments].count("Q"), 4)
        self.assertEqual([segment.kind for segment in parsed.segments].count("A"), 2)
        self.assertEqual(parsed.closed, {0})
        self.assertEqual(parsed.segments[-1].end, (10.0, 10.0))
        self.assertTrue(parsed.segments[-1].closes)

        bounds = path_bounds(parsed)
        self.assertIsNotNone(bounds)
        assert bounds is not None
        self.assertLessEqual(bounds[0], 10.0)
        self.assertGreaterEqual(bounds[2], 165.0)
        points = parse_path_points(path)
        self.assertEqual(points[0], (10.0, 10.0))
        self.assertIn((165.0, 35.0), points)
        self.assertEqual(points[-1], (10.0, 10.0))

    def test_generated_roles_and_connector_options_remain_compatible(self) -> None:
        self.assertEqual(svgkit.text_width("数据库", 14), 45.0)
        self.assertGreater(svgkit.text_width("数据库", 14), svgkit.text_width("abc", 14))

        d = svgkit.Diagram(760, 420, title="Compatibility", desc="Connector and role output.")
        left = d.node(40, 80, "Left")
        right = d.node(320, 80, "Right", family="green")
        d.arrow(
            left.right, right.left, label="sync", plate=True,
            dashed=True, both=True, label_offset=-8,
        )
        d.lpath(
            [(40, 200), (200, 200), (200, 260)], label="route", plate=True,
            dashed=True, both=True, label_offset=-10,
        )
        d.curve(
            (320, 200), (520, 260), label="curve",
            dashed=True, label_offset=-12,
        )
        d.container(20, 30, 700, 340, label="Scope")
        d.container(520, 80, 160, 120, label="Panel", solid=True)
        d.legend([("green", "primary")])

        rendered = d.render()
        for role in (
            "container", "panel", "node-text", "arrow-label",
            "legend-label", "container-label",
        ):
            self.assertIn(f'data-role="{role}"', rendered)
        self.assertEqual(rendered.count('marker-start="url(#arrow)"'), 2)
        self.assertGreaterEqual(rendered.count('stroke-dasharray="4 3"'), 3)
        self.assertIn('x="420" y="242"', rendered)
        self.assertIn(">curve</text>", rendered)


class GeometryModuleTests(unittest.TestCase):
    """Verify the extracted geometry.py works as a standalone module."""

    def test_geometry_import_standalone(self) -> None:
        from geometry import (
            parse_path, path_bounds, Bounds, Point, polygons_intersect,
            segment_crosses_polygon, rect_outline, ellipse_outline,
        )
        # Basic path parsing
        data = parse_path("M10,10 L100,10 L100,100 Z")
        self.assertEqual(len(data.segments), 3)
        # Bounds computation
        bounds = path_bounds(data)
        self.assertIsNotNone(bounds)
        self.assertAlmostEqual(bounds[0], 10.0)
        self.assertAlmostEqual(bounds[1], 10.0)
        # Rect outline
        outline = rect_outline(0, 0, 100, 100)
        self.assertEqual(len(outline), 4)
        # Ellipse outline
        ell = ellipse_outline(50, 50, 30, 20)
        self.assertEqual(len(ell), 64)

    def test_branch_produces_valid_curve(self) -> None:
        from svgkit import Diagram
        d = Diagram(600, 400, title="Branch test", desc="Testing branch method")
        center = d.node(200, 170, "Center", "hub", family="purple")
        leaf_right = d.node(400, 60, "Right", family="green")
        leaf_left = d.node(40, 280, "Left", family="amber")
        leaf_below = d.node(200, 320, "Below", family="terracotta")
        # All three branches should work without error
        d.branch(center, leaf_right, family="green")
        d.branch(center, leaf_left, family="amber")
        d.branch(center, leaf_below, family="terracotta")
        rendered = d.render()
        # Should have 3 bezier paths (the branches)
        self.assertEqual(rendered.count("<path d=\"M "), 3)
        # No markers on branches by default
        self.assertNotIn('marker-end=', rendered.split("<path")[1])

    def test_branch_with_marker(self) -> None:
        from svgkit import Diagram
        d = Diagram(500, 300, title="Marker branch", desc="Branch with arrow")
        center = d.node(150, 130, "A")
        target = d.node(350, 130, "B", family="green")
        d.branch(center, target, family="green", marker=True)
        rendered = d.render()
        self.assertIn('marker-end="url(#arrow)"', rendered)


if __name__ == "__main__":
    unittest.main()
