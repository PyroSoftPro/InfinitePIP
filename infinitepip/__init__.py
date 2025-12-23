"""
InfinitePIP package.

This repository originally shipped as a single-file script (`infinitepip_modern.py`).
It has been refactored into a small package while keeping the same runtime behavior.
"""

from .entrypoint import main

__all__ = ["main"]


