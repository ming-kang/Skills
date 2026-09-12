"""Validation lifecycle and the public Validator API."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from .document import Document
from .layout import LayoutChecks
from .result import CheckResult
from .structure import StructureChecks
from .style import WARM_PALETTE, normalize_hex

ANSI = {"red": "\033[0;31m", "green": "\033[0;32m", "yellow": "\033[1;33m", "reset": "\033[0m"}


def color(text, name, enabled=True):
    return f"{ANSI[name]}{text}{ANSI['reset']}" if enabled else text


class Validator:
    def __init__(self, svg_path, no_color=False):
        self.svg_path = Path(svg_path)
        self.no_color = no_color
        self._reset()

    def _reset(self):
        self.text = ""
        self.document = None
        self.layout = None
        self.failures = self.warnings = 0

    @property
    def root(self):
        return self.document.root if self.document else None

    @property
    def viewbox(self):
        return self.document.viewbox if self.document else None

    def collect_obstacles(self):
        return self.layout.collect_obstacles() if self.layout else []

    def is_arrow(self, element):
        return self.layout.is_arrow(element) if self.layout else False

    def collect(self):
        """Read once and return findings; no output or accumulated state from prior runs."""
        self._reset()
        results = self._read()
        if self.document is not None:
            structure = StructureChecks(self.document)
            results.extend((structure.check_svg_root(), structure.check_viewbox()))
            if not any(result.status == "fail" for result in results):
                checks = [structure.check_accessibility, structure.check_renderer_compatibility,
                          structure.check_marker_contract, structure.check_references,
                          structure.check_white_background, structure.check_flat_style]
                results.extend(check() for check in checks)
                self.layout = LayoutChecks(self.document, structure._background)
                results.extend(self.layout.collect())
                results.extend((structure.check_palette(), structure.check_values()))
        self.failures = sum(result.status == "fail" for result in results)
        self.warnings = sum(result.status == "warn" for result in results)
        return results

    def _read(self):
        try:
            self.text = self.svg_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return [CheckResult("Reading SVG", "fail", str(exc), fix="Provide an existing UTF-8 SVG file.")]
        try:
            root = ET.fromstring(self.text)
        except ET.ParseError as exc:
            return [CheckResult("Checking XML syntax", "fail", str(exc),
                                fix="Repair malformed XML before checking the diagram.")]
        self.document = Document(root, self.text)
        return [CheckResult("Reading UTF-8", "pass"), CheckResult("Checking XML syntax", "pass")]

    def run(self, quiet: bool = False) -> int:
        results = self.collect()
        if quiet:
            problems = [result for result in results if result.status != "pass"]
            if not problems:
                return 0
            print(f"Validating SVG: {self.svg_path}")
            for result in problems:
                self.report(result)
            if self.failures:
                print(color(f"Validation failed ({self.failures} error(s))", "red", not self.no_color))
                return 1
            return 0

        print(f"Validating SVG: {self.svg_path}")
        print("----------------------------------------")
        for result in results:
            self.report(result)
        print("----------------------------------------")
        if self.failures == 0:
            suffix = f" ({self.warnings} warning(s))" if self.warnings else ""
            print(f"Validation complete{suffix}")
            return 0
        print(color(f"Validation failed ({self.failures} error(s))", "red", not self.no_color))
        return 1

    def report(self, result: CheckResult) -> None:
        if result.status == "pass":
            status = color("[PASS]", "green", not self.no_color and sys.stdout.isatty())
        elif result.status == "warn":
            status = color("[WARN]", "yellow", not self.no_color and sys.stdout.isatty())
        else:
            status = color("[FAIL]", "red", not self.no_color and sys.stdout.isatty())
        message = f" ({result.message})" if result.message else ""
        print(f"{result.name}... {status}{message}")
        for detail in result.details or []:
            print(f"  - {detail}")
        if result.fix and result.status != "pass":
            print(f"  Fix: {result.fix}")
