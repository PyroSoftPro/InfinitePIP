"""
InfinitePIP package.

This repository originally shipped as a single-file script.
It has been refactored into a small package while keeping the same runtime behavior.
"""

from __future__ import annotations


def main() -> None:
    """Run the InfinitePIP app."""
    from .entrypoint import main as _main

    _main()


__all__ = ["main"]


