from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

SKILL_DIR = Path(__file__).resolve().parent.parent


class ExportError(RuntimeError):
    pass


def log(message: str) -> None:
    print(f"[pptd] {message}", file=sys.stderr, flush=True)


def run_command(command: Sequence[str], timeout: int = 300) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [str(part) for part in command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ExportError(f"executable not found: {command[0]}") from exc
