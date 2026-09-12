#!/usr/bin/env python3
"""Validate SVG files. The implementation belongs to this skill's private runtime."""

import hashlib
import importlib.util
import sys
from pathlib import Path

def _runtime_module(name: str):
    """Load this copy of the runtime without trusting caller-specific sys.path."""
    directory = Path(__file__).resolve().parent / "svg_runtime"
    digest = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()[:16]
    package_name = f"_visualize_runtime_{digest}"
    if package_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            package_name, directory / "__init__.py",
            submodule_search_locations=[str(directory)],
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load SVG runtime from {directory}")
        package = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = package
        try:
            spec.loader.exec_module(package)
        except Exception:
            sys.modules.pop(package_name, None)
            raise
    return importlib.import_module(f"{package_name}.{name}")

_runtime = _runtime_module("validator")
_geometry = _runtime_module("geometry")
Validator = _runtime.Validator
CheckResult = _runtime.CheckResult
WARM_PALETTE = _runtime.WARM_PALETTE
normalize_hex = _runtime.normalize_hex
# Retain the geometry functions exposed by previous versions of this module.
for _name in _geometry.__all__:
    globals()[_name] = getattr(_geometry, _name)

if __name__ == "__main__":
    raise SystemExit(_runtime_module("cli").main())
