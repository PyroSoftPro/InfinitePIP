# InfinitePIP

**InfinitePIP** is an advanced desktop **picture-in-picture (PiP)** tool by **PyroSoft Productions** with a modern interface. It lets you create always-on-top, borderless PiP windows from **monitors**, **application windows**, or a **custom screen region**.

- **Open source / free code**: This repository contains the full source code for InfinitePIP.
- **Donationware binaries**: Prebuilt binaries are published on **Itch.io** as **donationware** (free to download, with an optional donation).
- **Sponsored by**: **Playcast.io**

---

## Features

- **Multiple PiP sources**
  - **Monitor capture** (per monitor)
  - **Window capture** (best on Windows; includes optional handle-based capture when available)
  - **Region capture** (enter coordinates or use a visual region selector)
- **Always-on-top PiP windows** (toggleable)
- **Borderless, draggable PiP windows** with resize handles/indicators
- **Aspect-ratio controls**
  - Maintain aspect ratio (toggleable)
  - Optional auto-resize when a captured window changes size
- **Opacity controls**
  - Context menu opacity presets (10% → 100%)
  - Keyboard shortcuts for quick opacity adjustment
- **System tray support** (when `pystray` is available)
  - Minimize to tray + tray notifications
- **Remote control API (local-only)**
  - Local TCP server on `localhost:38474` for external PiP creation

---

## Requirements

- **Python**: Python 3.x
- **OS**:
  - **Windows** is the primary target (uses `pywin32` for enhanced capture paths when installed)
  - Other platforms may work, but window-capture capabilities can be limited

Python dependencies are listed in `requirements.txt`.

---

## Install (from source)

1) Create and activate a virtual environment (recommended)

2) Install dependencies:

```bash
python -m pip install -r requirements.txt
```

---

## Run

```bash
python infinitepip_modern.py
```

---

## How to use

### Create a PiP

- **Monitor PiP**: select a monitor in the UI and create a PiP window.
- **Window PiP**: refresh/select a window and create a PiP window.
- **Region PiP**:
  - Enter region coordinates (x/y/width/height), or
  - Use the visual selector to drag-select a region, then create the PiP.

### PiP window controls

- **Move**: click and drag the PiP window.
- **Resize**: drag edges/corners (subtle resize indicators are drawn on the PiP).
- **Context menu**: right-click a PiP window to access:
  - Always on Top (toggle)
  - Maintain Aspect Ratio (toggle, when aspect info is available)
  - Auto-resize on Source Change (toggle, for window sources)
  - Opacity presets
  - Close PiP

### Keyboard shortcuts (PiP window)

When a PiP window is focused:

- **`+` / `=`**: increase opacity
- **`-`**: decrease opacity
- **`0`**: reset opacity to 100%

---

## Remote control (local TCP)

InfinitePIP starts a local TCP server on **`localhost:38474`**. The protocol is JSON over TCP.

### Supported actions

- **`create_window_pip`**: Create a PiP from a window descriptor.

### Example request payload

The app expects a `window_data` object shaped like the data it uses internally (minimum: `title` + `bbox`; optional: `hwnd` on Windows).

```json
{
  "action": "create_window_pip",
  "window_data": {
    "title": "Untitled - Notepad",
    "bbox": [100, 100, 800, 600],
    "hwnd": 123456
  }
}
```

### Notes / security

- The server binds to **localhost only**, but **any local process** can connect to it. Treat this as a local integration feature, not an authenticated API.
- If the remote control server can’t start, InfinitePIP will continue running without it.

---

## Donationware binaries (Itch.io)

This repository is **free and open source**. If you prefer a packaged build, InfinitePIP binaries are available on **Itch.io** as **donationware**:

- **Free to download**
- **Optional donation** if you’d like to support continued development

---

## Sponsor

InfinitePIP is **sponsored by Playcast.io**.

---

## Contributing

Contributions are welcome!

- Bug reports and feature requests: open an issue with repro steps/logs.
- Pull requests: keep changes focused and include a short description + testing notes.

---

## License

This project is intended to be open source. See `LICENSE`.


