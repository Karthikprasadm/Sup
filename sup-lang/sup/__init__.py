"""Sup Language package."""

__version__ = "2.8"

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only for type checkers; avoid importing at runtime to prevent runpy warning
    from .cli import main as cli_main  # noqa: F401


def __getattr__(name: str):
    if name == "cli_main":
        # Lazy import to avoid loading sup.cli during package import
        from .cli import main as cli_main  # type: ignore

        return cli_main
    raise AttributeError(f"module 'sup' has no attribute {name!r}")


__all__ = ["cli_main", "__version__"]
