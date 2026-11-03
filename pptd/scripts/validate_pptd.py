#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from pptd_common import ExportError
from pptd_deck import build_local_project, validation_summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a PPTD v2 project without a browser")
    parser.add_argument("input", type=Path, help=".pptd manifest or project directory")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        project = build_local_project(args.input)
    except (ExportError, OSError) as exc:
        print(f"pptd validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(validation_summary(project), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
