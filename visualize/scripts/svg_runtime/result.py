"""Structured findings shared by the validator and its command-line interface."""

from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    status: str
    message: str = ""
    details: list[str] | None = None
    fix: str = ""
