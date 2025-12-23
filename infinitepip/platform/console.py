import platform


def hide_console() -> bool:
    """Hide the console window on Windows, handle gracefully on other platforms."""
    if platform.system() == "Windows":
        try:
            import ctypes

            # Get console window handle
            console_window = ctypes.windll.kernel32.GetConsoleWindow()
            if console_window:
                # Hide the console window (SW_HIDE = 0)
                ctypes.windll.user32.ShowWindow(console_window, 0)
                return True
        except Exception:
            # Silently fail if ctypes or Windows API calls don't work
            pass
    elif platform.system() == "Darwin":  # macOS
        # On macOS, we can try to hide from dock if running as app
        try:
            import AppKit  # type: ignore[import-not-found]

            info = AppKit.NSBundle.mainBundle().infoDictionary()
            info["LSUIElement"] = True
        except Exception:
            pass
    # Linux and other platforms don't typically show console windows for GUI apps
    return False


def show_console() -> bool:
    """Show the console window on Windows (for debugging)."""
    if platform.system() == "Windows":
        try:
            import ctypes

            console_window = ctypes.windll.kernel32.GetConsoleWindow()
            if console_window:
                # Show the console window (SW_SHOW = 5)
                ctypes.windll.user32.ShowWindow(console_window, 5)
                return True
        except Exception:
            pass
    return False


