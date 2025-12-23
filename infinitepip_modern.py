"""
Compatibility shim.

This project used to run from `infinitepip_modern.py`. The primary entrypoint is now
`infinitepip.py`, but we keep this file so existing shortcuts and docs keep working.
"""

from infinitepip.entrypoint import main


if __name__ == "__main__":
    main()