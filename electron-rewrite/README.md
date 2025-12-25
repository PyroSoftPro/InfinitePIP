# InfinitePIP (Electron rewrite)

This folder contains a **from-scratch Electron rewrite** of InfinitePIP.

## What’s implemented (first slice)

- Pick a **Screen** or **Window** source (with thumbnails)
- Open a **borderless, always-on-top PiP** window streaming that source
- PiP controls: **opacity**, **zoom**, **pan (drag)**, **always-on-top toggle**

## Requirements

- Node.js (LTS recommended)

## Install

```bash
cd electron-rewrite
npm install
```

## Run

```bash
npm run dev
```

## Package (optional)

Create installers/artifacts with `electron-builder`:

```bash
# unpacked directory
npm run pack

# installer/artifacts
npm run dist
```

## Notes

- Capture uses Electron’s `desktopCapturer` + Chromium `getUserMedia` with `chromeMediaSourceId`.
- This is intentionally minimal (no bundler yet). Once the behavior is stable, we can add Vite/React, packaging, tray, remote-control, and region selection.


