from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass
class SupError(Exception):
    message: str
    line: int | None = None
    column: int | None = None
    suggestion: str | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial formatting
        location = f" on line {self.line}" if self.line is not None else ""
        details = f"Error{location}: {self.message}"
        if self.suggestion:
            details += f"\nSuggestion: {self.suggestion}"
        return details


class SupSyntaxError(SupError):
    pass


class SupRuntimeError(SupError):
    pass


def nearest_phrase(bad: str, candidates: list[str]) -> str | None:
    if not bad or not candidates:
        return None
    match = difflib.get_close_matches(bad, candidates, n=1)
    return match[0] if match else None
