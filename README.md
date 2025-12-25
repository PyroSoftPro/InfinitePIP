# InfinitePIP

**InfinitePIP** is an advanced desktop **picture-in-picture (PiP)** tool by **PyroSoft Productions** with a modern interface. It lets you create always-on-top, borderless PiP windows from **monitors**, **application windows**, or a **custom screen region**.

- **Open source / free code**: This repository contains the full source code for InfinitePIP.
- **Donationware binaries**: Prebuilt binaries are published on **Itch.io** as **donationware** (free to download, with an optional donation).
- **Sponsored by**: **Playcast.io**

---

## Project status

- **Current app**: InfinitePIP for Electron (this repository root)
- **Original release (deprecated)**: `Python App (Original Release, Deprecated)/`

## What’s implemented (first slice)

- Pick a **Screen** or **Window** source (with thumbnails)
- Open a **borderless, always-on-top PiP** window streaming that source
- PiP controls: **opacity**, **zoom**, **pan (drag)**, **always-on-top toggle**

## Requirements

- Node.js (LTS recommended)

## Install

```bash
npm install
```

## Run

```bash
npm run dev
```

## Notes

- Capture uses Electron’s `desktopCapturer` + Chromium `getUserMedia` with `chromeMediaSourceId`.
- This is intentionally minimal (no bundler yet). Once the behavior is stable, we can add Vite/React, packaging, tray, remote-control, and region selection.


