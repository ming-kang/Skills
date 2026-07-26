#!/usr/bin/env python3
"""Regression tests for svgkit and validate_svg (stdlib only).

Run from anywhere:
    python3 visualize/scripts/test_visualize.py
"""

from __future__ import annotations

import contextlib
import io
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from svgkit import Box, Diagram, text_width
from validate_svg import Validator


ROOT = Path(__file__).resolve().parent.parent
SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


def validate(path: Path) -> tuple[int, Validator]:
    validator = Validator(path, no_color=True, quiet=True)
    with contextlib.redirect_stdout(io.StringIO()):
        code = validator.run()
    return code, validator


class SvgkitTests(unittest.TestCase):
    def test_text_width_counts_cjk_as_wide(self) -> None:
        self.assertGreater(text_width("中文"), text_width("ab"))

    def test_row_and_col_center_mixed_sizes(self) -> None:
        d = Diagram(400, 400, title="Alignment", desc="Mixed node sizes align centrally.")
        row = d.row([{"title": "Short"}, {"title": "Tall", "sub": "two lines"}])
        col = d.col([{"title": "A"}, {"title": "A much wider label"}], y=180)
        self.assertEqual(row[0].cy, row[1].cy)
        self.assertEqual(col[0].cx, col[1].cx)

    def test_pipeline_exposes_start_alignment(self) -> None:
        d = Diagram(400, 200, title="Alignment", desc="Top-aligned pipeline.")
        boxes = d.pipeline(
            [{"title": "One"}, {"title": "Two", "sub": "detail"}],
            align="start",
        )
        self.assertEqual(boxes[0].y, boxes[1].y)

    def test_self_loop_routes_outside_box(self) -> None:
        d = Diagram(240, 140, title="Loop", desc="A retry loop around one node.")
        box = d.node(40, 40, "Retry")
        d.connect(box, box, label="again")
        route = d._layers["arrows"][-1]
        self.assertIn("<path", route)
        self.assertIn(str(int(box.x + box.w + 32)), route)
        self.assertNotIn(f'x1="{int(box.x + box.w)}"', route)

    def test_connect_rejects_overlap_and_unknown_route(self) -> None:
        d = Diagram(400, 200, title="Routing", desc="Invalid routes are rejected.")
        a = d.node(40, 40, "A")
        with self.assertRaises(ValueError):
            d.connect(a, Box(60, 50, 120, 40))
        with self.assertRaises(ValueError):
            d.connect(a, Box(240, 40, 120, 40), route="banana")

    def test_ortho_bidirectional_propagates_both_markers(self) -> None:
        d = Diagram(500, 300, title="Duplex", desc="A bidirectional orthogonal route.")
        a = d.node(40, 40, "A")
        b = d.node(300, 180, "B")
        d.connect(a, b, route="ortho", bidirectional=True)
        route = d._layers["arrows"][-1]
        self.assertIn('marker-start="url(#arrow)"', route)
        self.assertIn('marker-end="url(#arrow)"', route)

    def test_fit_expands_all_sides_and_legend_has_no_double_footer(self) -> None:
        d = Diagram(200, 100, title="Fit", desc="Negative content stays visible.")
        d.node(-20, -10, "Negative")
        d.legend([("green", "primary")])
        d.fit()
        self.assertLessEqual(d._viewbox_x, -60)
        self.assertLessEqual(d._viewbox_y, -50)
        self.assertAlmostEqual(d._viewbox_y + d.height - d._content_max_y, 40)

    def test_legend_wrap_uses_effective_content_width(self) -> None:
        d = Diagram(400, 160, title="Legend", desc="Legend uses grown content width.")
        d.row([
            {"title": "A", "family": "green"},
            {"title": "B", "family": "purple"},
            {"title": "C", "family": "amber"},
            {"title": "D", "family": "terracotta"},
        ])
        d.auto_legend()
        ys = set(re.findall(r'<rect x="[^\"]+" y="([^\"]+)" width="12"', "\n".join(d._layers["legend"])))
        self.assertEqual(len(ys), 1)

    def test_opacity_fades_fill_not_stroke(self) -> None:
        d = Diagram(200, 120, title="Tint", desc="Only the fill is faded.")
        d.node(40, 40, "Stage", family="green", opacity=0.55)
        rect = d._layers["boxes"][-1]
        self.assertIn('fill-opacity="0.55"', rect)
        self.assertNotIn(' opacity=', rect)
        with self.assertRaises(ValueError):
            d.node(40, 100, "Bad", opacity=1.2)

    def test_save_creates_parent_directories_and_valid_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "diagram.svg"
            d = Diagram(200, 120, title="Save", desc="Parent directory is created.")
            d.node(40, 40, "Node")
            self.assertEqual(d.save(path), str(path))
            self.assertTrue(path.is_file())
            root = ET.parse(path).getroot()
            self.assertEqual(root.tag.rsplit("}", 1)[-1], "svg")

    def test_custom_color_is_validated(self) -> None:
        d = Diagram(200, 100, title="Color", desc="Unsafe colors are rejected.")
        with self.assertRaises(ValueError):
            d.arrow((0, 0), (10, 10), color='" onclick="alert(1)')


class ValidatorTests(unittest.TestCase):
    def _save(self, diagram: Diagram, name: str, directory: Path, *, fit: bool = True) -> Path:
        path = directory / name
        diagram.save(path, fit=fit)
        return path

    def test_good_diagram_passes_without_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Diagram(420, 180, title="Pipeline", desc="A short validated pipeline.")
            d.pipeline([
                {"title": "In"},
                {"title": "Out", "family": "green"},
            ])
            code, validator = validate(self._save(d, "good.svg", Path(tmp)))
            self.assertEqual(code, 0)
            self.assertEqual(validator.warnings, 0)

    def test_diagonal_arrow_collision_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Diagram(400, 240, title="Collision", desc="An arrow crosses a node.")
            d.node(140, 80, "Obstacle", w=120)
            d.arrow((40, 40), (360, 200))
            code, _ = validate(self._save(d, "collision.svg", Path(tmp), fit=False))
            self.assertEqual(code, 1)

    def test_text_overflow_is_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Diagram(300, 160, title="Overflow", desc="A label is intentionally too wide.")
            d.node(40, 40, "this label is far too long", w=80)
            code, _ = validate(self._save(d, "overflow.svg", Path(tmp), fit=False))
            self.assertEqual(code, 1)

    def test_curve_chord_is_not_a_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Diagram(500, 260, title="Curve", desc="A bezier arcs around a node.")
            hub = d.node(40, 100, "Hub", family="purple")
            leaf = d.node(340, 100, "Leaf", family="green")
            # The straight chord crosses the middle node; the drawn bezier does not.
            d.node(190, 96, "Middle", w=110)
            d.curve((hub.cx, hub.y), (leaf.cx, leaf.y), color="green")
            code, _ = validate(self._save(d, "curve.svg", Path(tmp)))
            self.assertEqual(code, 0)

    def test_gradient_is_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Diagram(300, 160, title="Gradient", desc="A forbidden gradient is present.")
            d.raw('<defs><linearGradient id="g"/></defs>', layer="containers")
            d.node(40, 40, "Node")
            code, _ = validate(self._save(d, "gradient.svg", Path(tmp), fit=False))
            self.assertEqual(code, 1)

    def test_missing_accessibility_metadata_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.svg"
            path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
                '<defs><marker id="arrow"/></defs><rect width="20" height="20" fill="#fff"/></svg>',
                encoding="utf-8",
            )
            code, _ = validate(path)
            self.assertEqual(code, 1)

    def test_all_owned_assets_pass_without_warnings(self) -> None:
        paths = sorted((ROOT / "assets" / "gallery").glob("*.svg"))
        paths += sorted((ROOT / "assets" / "samples").glob("*.svg"))
        self.assertGreaterEqual(len(paths), 20)
        failures: list[str] = []
        for path in paths:
            code, validator = validate(path)
            if code or validator.warnings:
                failures.append(f"{path.name}: code={code}, warnings={validator.warnings}")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
