# InfinitePIP — Features, Functionality, and UI Reference

This document is a **complete feature + UI element reference** for InfinitePIP as implemented in this repository (Tkinter-based “modern UI” + borderless PiP windows).

## Table of contents

- [What InfinitePIP is](#what-infinitepip-is)
- [Core concepts](#core-concepts)
- [Features (high-level)](#features-high-level)
- [Main application window (InfinitePIPModernUI)](#main-application-window-infinitepipmodernui)
  - [Header](#header)
  - [Tabs](#tabs)
    - [Monitors tab](#monitors-tab)
    - [Windows tab](#windows-tab)
    - [Regions tab](#regions-tab)
    - [Active PIPs tab](#active-pips-tab)
  - [Footer](#footer)
- [PiP window (InfinitePIPWindow)](#pip-window-infinitepipwindow)
  - [Window behavior](#window-behavior)
  - [Mouse controls](#mouse-controls)
  - [Resize affordances](#resize-affordances)
  - [Context menu (right-click)](#context-menu-right-click)
  - [Keyboard shortcuts (focused PiP)](#keyboard-shortcuts-focused-pip)
- [System tray integration (optional)](#system-tray-integration-optional)
- [Remote control API (local TCP, optional integration)](#remote-control-api-local-tcp-optional-integration)
- [Capture backends & platform notes](#capture-backends--platform-notes)
- [Dependencies & “availability flags”](#dependencies--availability-flags)
- [Entry points / how the app starts](#entry-points--how-the-app-starts)

## What InfinitePIP is

InfinitePIP is a desktop **picture-in-picture (PiP)** tool that creates **always-on-top**, **borderless** windows that show live content captured from:

- **A monitor**
- **An application window**
- **A fixed screen region** (x/y/width/height)

## Core concepts

- **Main window**: a multi-tab UI for selecting a capture source and managing PiP windows.
- **PiP window**: a borderless `Toplevel` that continuously captures its source and renders it into a canvas.
- **Capture loop**: a background thread per PiP window that captures ~30 FPS and schedules UI updates on Tk’s main thread.
- **Source types**:
  - **monitor**: picks a monitor index and captures via `mss`
  - **window**: captures via Win32 APIs when available, otherwise uses region capture and tracks the window position
  - **region**: captures a fixed rectangle

## Features (high-level)

- **Create multiple PiPs at once** (each PiP has its own capture thread)
- **Always-on-top PiP windows** (default on; toggleable per PiP)
- **Borderless, draggable PiP windows**
- **Resizable PiP windows** (edges/corners)
- **Aspect ratio support**
  - Source aspect ratio is detected and used for the initial PiP size
  - Optional “Maintain Aspect Ratio” toggle (when a source aspect ratio is known)
  - Optional auto-resize when a *window source* changes size
- **Opacity control**
  - Context menu presets (10%–100%)
  - Keyboard shortcuts for quick adjustments
- **Monitor previews** in the Monitors tab (thumbnail screenshots)
- **Window previews** in the Windows tab (thumbnail screenshots; uses the same capture strategies as PiPs)
- **Region preview** in the Regions tab (thumbnail screenshot of the specified rectangle)
- **System tray** support (when `pystray` is installed)
- **Remote control server** on `localhost:38474` for external automation (local-only; no authentication)

## Main application window (InfinitePIPModernUI)

The main UI is implemented by `InfinitePIPModernUI` in `infinitepip/ui/app.py`. It is a single top-level `Tk()` window containing:

- A **header** (app title + status)
- A **tabbed content area** (Monitors / Windows / Regions / Active PIPs)
- A **footer** (tip text + actions)

### Header

The header contains:

- **App title**: “InfinitePIP”
- **Subtitle**: “Advanced Picture-in-Picture for Desktop”
- **Status indicator**:
  - **“● Ready”** (green) when there are no active PiPs
  - **“● Active”** (orange) when one or more PiPs exist
- **Active PiP counter**: `N Active PIPs`

### Tabs

The main content is a `ttk.Notebook` with four tabs.

#### Monitors tab

Purpose: create a PiP window from a connected monitor.

UI elements:

- **Section title**: “Available Monitors”
- **Help text**: “Create picture-in-picture windows from any connected monitor”
- **Scrollable grid** of monitor “cards” (responsive column count)

Each monitor card includes:

- **Monitor icon**
- **Preview thumbnail** (captured via `mss`, if possible)
- **Monitor label**: “Monitor N” and “(Primary)” where applicable
- **Resolution** (e.g., `1920×1080`)
- **Aspect ratio** (rounded, displayed like `1.78:1`)
- **Position** `(x, y)` in the virtual desktop coordinate space
- **Create PIP** button

Behavior:

- Clicking **Create PIP** creates a new `InfinitePIPWindow` with source type `monitor` and adds it to the active list.

#### Windows tab

Purpose: create a PiP window from an application window.

UI elements:

- **Section title**: “Application Windows”
- **Refresh** button (top-right)
- **Help text**: “Capture and display content from any application window”
- **Scrollable list** of window cards

Each window card includes:

- **Window title** (truncated if long)
- **Preview thumbnail** (tries direct window capture on Windows; otherwise falls back to region capture)
- **Size** (from bounding box) and **Position** (from bounding box)
- **Create PIP** button

Behavior:

- Clicking **Refresh** re-enumerates visible windows (via `pygetwindow`) and repopulates the list.
- Clicking **Create PIP** creates a new `InfinitePIPWindow` with source type `window`.

Notes:

- On Windows, when `pywin32` is installed, window entries may include an `hwnd` handle, enabling direct Win32 capture.

#### Regions tab

Purpose: create a PiP window from a custom rectangle.

UI elements:

- **Section title**: “Custom Screen Regions”
- **Help text**: “Define custom screen areas to capture”
- **Input card** with numeric entries:
  - **X Position**
  - **Y Position**
  - **Width**
  - **Height**
- **Create Region PIP** button
- **Preview card** titled “📷 Region Preview”
  - **Update Preview** button
  - A **thumbnail preview** of the region (when successful)
  - An informational label like `Region: WxH at (x, y)`

Behavior:

- Clicking **Update Preview** captures the specified rectangle using `mss` and displays a thumbnail.
- Clicking **Create Region PIP** creates a new `InfinitePIPWindow` with source type `region`.

Important note about “visual selection”:

- The codebase includes a full-screen **visual region selector overlay** (`ScreenAreaSelector` in `infinitepip/ui/screen_selector.py`) and an app method `start_visual_region_selection()`.
- **In the current UI layout, there is no button wired to launch it.** (So it exists as functionality in code, but it is not exposed as a clickable UI element in the Regions tab.)

#### Active PIPs tab

Purpose: manage (and close) currently running PiP windows.

UI elements:

- **Section title**: “Active PIP Windows”
- **Close All** button
- **Help text**: “Manage all active picture-in-picture windows”
- **Scrollable list** of PiP cards

Each active PiP card includes:

- **PiP name** (derived from the source)
- **Source type**: Monitor / Window / Region
- **Current PiP size** (reads `winfo_width()` × `winfo_height()` if the window exists)
- **Close PIP** button

Behavior:

- Clicking **Close PIP** closes that PiP window and removes it from the active list.
- Clicking **Close All** closes all PiPs and clears the active list.

### Footer

The footer contains:

- **Tip text**: “PIPs stay on top, can be moved by dragging, and resized by dragging edges/corners”
- **Refresh All** button
- **Minimize to Tray** button (only when system tray support is available)

Behavior:

- **Refresh All** reloads monitor information and refreshes the windows list.
- **Minimize to Tray** hides the main window (withdraws it) instead of exiting.

## PiP window (InfinitePIPWindow)

PiP windows are implemented by `InfinitePIPWindow` in `infinitepip/ui/pip_window.py`.

### Window behavior

- **Borderless**: window decorations are removed (`overrideredirect(True)`).
- **Always-on-top**: enabled by default.
- **Live capture**: a thread captures frames in a loop and updates the canvas about every ~33ms (roughly 30 FPS).
- **Aspect-aware initial size**: tries to size the initial window based on the source aspect ratio.
- **Auto-detect source size changes**:
  - When the capture frame size changes, the PiP can update its stored aspect ratio.
  - For window sources, the PiP may auto-resize itself to match the new aspect ratio (toggleable).

### Mouse controls

- **Move**: click and drag anywhere that is *not* a resize edge/corner.
- **Resize**: click and drag edges/corners (hit-testing is based on cursor position).
- **Context menu**: right-click opens the PiP menu.

### Resize affordances

The PiP window is borderless but provides subtle cues:

- **Cursor changes** near edges/corners (e.g. `bottom_right_corner`, `left_side`, etc.)
- **Corner indicators**: small dark squares drawn into the canvas on each frame (top-left, top-right, bottom-left, bottom-right)

### Context menu (right-click)

Right-clicking a PiP opens a menu with:

- **Always on Top** (toggle)
  - Display shows a checkmark (`✓`) when enabled.
- **Maintain Aspect Ratio** (toggle; only shown when aspect ratio is known)
  - Keeps resizing constrained to the source aspect ratio.
- **Auto-resize on Source Change** (toggle; only shown for *window* sources)
  - If enabled and the captured window changes size, the PiP can resize itself to match.
- **Opacity** submenu
  - Presets: **100%**, 90%, 80%, … down to **10%**
  - The current opacity has a checkmark.
- **Help** submenu (read-only labels)
  - Lists the opacity keyboard shortcuts
- **Close PIP**

### Keyboard shortcuts (focused PiP)

When a PiP window has focus:

- **`+`** or **`=`**: increase opacity by 10%
- **`-`**: decrease opacity by 10%
- **`0`**: reset opacity to 100%

When opacity is adjusted via keyboard, the PiP briefly overlays a text indicator like **“Opacity: 80%”**.

## System tray integration (optional)

Tray support is enabled when `pystray` (and PIL’s `ImageDraw`) are installed.

Behavior:

- Closing the main window (the X button) **minimizes to tray** instead of quitting, as long as tray is available.
- The tray icon menu includes:
  - **InfinitePIP** (default action: show the window)
  - **Show/Hide**
  - **Active PIPs** (shows a notification with the count)
  - **Close All PIPs**
  - **Quit** (fully exits the app)

Notifications:

- When minimizing to tray, a notification is shown.
- When an external remote-control request creates a PiP, a notification may be shown.

## Remote control API (local TCP, optional integration)

InfinitePIP starts a TCP server on **`localhost:38474`** (best-effort; failure is non-fatal).

Protocol:

- One JSON request per connection (simple “JSON over TCP”)
- Response is JSON
- **Local-only** binding (`localhost`) with **no authentication**

Supported actions:

- **`create_window_pip`**: create a window PiP based on a `window_data` object.

Example request:

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

Example success response:

```json
{ "status": "success", "message": "Window PIP created successfully" }
```

Notes / limitations:

- The server reads up to **1024 bytes** in one `recv()` call; very large payloads may not be handled correctly.
- Because it is local-only but unauthenticated, **any local process** can connect—treat it as an integration hook, not a security boundary.

## Capture backends & platform notes

InfinitePIP uses different capture strategies depending on the source and platform:

- **Monitor capture**:
  - Uses `mss` to capture a full monitor.
- **Region capture**:
  - PiP capture uses `pyautogui.screenshot(region=...)`.
  - Region *preview* in the Regions tab uses `mss` (faster and consistent with monitor capture).
- **Window capture**:
  - On **Windows with `pywin32` installed**: attempts “true window capture” using Win32 APIs:
    - `PrintWindow` (preferred)
    - fallback to `BitBlt`
  - Otherwise: falls back to capturing the window’s bounding box as a screen region and **dynamically updates** the bbox by re-locating the window by title.

Practical implications:

- **Windows is the most capable platform** for window capture because of `hwnd` + Win32 APIs.
- On other platforms (or without `pywin32`), “window capture” behaves more like “track a region where that window is”.
- If a window is minimized, Win32 capture returns a placeholder frame (“Window Minimized”) rather than crashing.

## Dependencies & “availability flags”

Dependency import/availability is centralized in `infinitepip/deps.py`:

- **Required** (app exits if missing):
  - `Pillow` (`PIL.Image`, `PIL.ImageTk`)
  - `mss`
  - `screeninfo`
  - `pyautogui`
- **Optional**:
  - `pystray` (tray integration)
  - `pywin32` (Windows-only enhanced window capture: `win32gui`, `win32ui`, etc.)

Flags used by the app:

- **`TRAY_AVAILABLE`**: True when tray support is installed.
- **`WINDOWS_CAPTURE_AVAILABLE`**: True on Windows when `pywin32` is installed.

## Entry points / how the app starts

You can run InfinitePIP with:

- `python infinitepip.py` (root script), or
- `python -m infinitepip` (module entrypoint)

Startup flow:

- `entrypoint.main()` hides the console window on Windows (best effort).
- The UI class `InfinitePIPModernUI` is created and `mainloop()` is started.
- The remote control server is started in a background thread (best effort).


