from __future__ import annotations

import os

from .platform.console import hide_console


def main() -> None:
    # Match original behavior: hide the console window on Windows for GUI usage.
    hide_console()

    # Importing the UI pulls in dependency checks via `infinitepip.deps`.
    from .ui.app import InfinitePIPModernUI

    app = InfinitePIPModernUI()

    # Optional smoke-test mode: start up, then exit quickly.
    # This is useful for CI/headless verification of the entrypoint wiring.
    if os.environ.get("INFINITEPIP_AUTOTEST") == "1":
        try:
            app.root.after(250, app.quit_application)
        except Exception:
            # Fallback: at least break out of mainloop if quit_application fails.
            try:
                app.root.after(250, app.root.quit)
            except Exception:
                pass
    app.run()


