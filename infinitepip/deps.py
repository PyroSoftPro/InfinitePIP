"""
Centralized imports / dependency availability flags.

The original project was single-file and performed dependency checks at import time.
We keep the same behavior here so `python infinitepip_modern.py` fails fast with the
same messages when required dependencies are missing.
"""

from __future__ import annotations

import platform
import sys
from typing import Any

TRAY_AVAILABLE: bool
WINDOWS_CAPTURE_AVAILABLE: bool

# --- Optional tray support (pystray) ---
try:
    import pystray  # type: ignore[import-not-found]
    from PIL import Image, ImageDraw  # type: ignore[import-not-found]

    TRAY_AVAILABLE = True
except ImportError:
    print("Warning: pystray not available. Tray functionality will be limited.")
    pystray = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    TRAY_AVAILABLE = False

# --- Required imaging (Pillow) ---
try:
    from PIL import Image, ImageTk  # type: ignore[import-not-found]
except ImportError:
    print("Error: Pillow not available. Please install it with: pip install pillow")
    sys.exit(1)

# --- Required capture libs ---
try:
    import mss  # type: ignore[import-not-found]
except ImportError:
    print("Error: mss not available. Please install it with: pip install mss")
    sys.exit(1)

try:
    import screeninfo  # type: ignore[import-not-found]
except ImportError:
    print("Error: screeninfo not available. Please install it with: pip install screeninfo")
    sys.exit(1)

try:
    import pyautogui  # type: ignore[import-not-found]
except ImportError:
    print("Error: pyautogui not available. Please install it with: pip install pyautogui")
    sys.exit(1)

# --- Platform-specific imports for window capture ---
win32gui: Any = None
win32ui: Any = None
win32con: Any = None
win32api: Any = None
windll: Any = None

if platform.system() == "Windows":
    try:
        import win32gui as _win32gui  # type: ignore[import-not-found]
        import win32ui as _win32ui  # type: ignore[import-not-found]
        import win32con as _win32con  # type: ignore[import-not-found]
        import win32api as _win32api  # type: ignore[import-not-found]
        from ctypes import windll as _windll

        win32gui = _win32gui
        win32ui = _win32ui
        win32con = _win32con
        win32api = _win32api
        windll = _windll
        WINDOWS_CAPTURE_AVAILABLE = True
    except ImportError:
        print("Warning: pywin32 not available. Windows-specific capture will be limited.")
        WINDOWS_CAPTURE_AVAILABLE = False
else:
    WINDOWS_CAPTURE_AVAILABLE = False


