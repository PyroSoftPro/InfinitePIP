from __future__ import annotations

import threading
import time
import tkinter as tk

from ..deps import (
    Image,
    ImageTk,
    WINDOWS_CAPTURE_AVAILABLE,
    mss,
    pyautogui,
    screeninfo,
    win32con,
    win32gui,
    win32ui,
    windll,
)


class InfinitePIPWindow:
    def __init__(self, source_type, source_data, manager):
        self.source_type = source_type
        self.source_data = source_data
        self.manager = manager
        self.running = True
        self.window = None
        self.canvas = None
        self.capture_thread = None
        self.is_resizing = False
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_corner = None
        self.last_x = 0
        self.last_y = 0
        self.source_aspect_ratio = None
        self.maintain_aspect_ratio = True
        self.auto_resize_on_source_change = True
        self.last_source_size = None
        self.opacity = 1.0  # Default to fully opaque

        self.setup_window()
        self.calculate_aspect_ratio()
        self.start_capture_thread()

    def setup_window(self):
        self.window = tk.Toplevel()
        self.window.title(f"InfinitePIP: {self.get_source_name()}")

        # Set initial size based on source aspect ratio
        initial_width = 400
        initial_height = 300

        self.window.geometry(f"{initial_width}x{initial_height}")
        self.window.attributes("-topmost", True)

        # Remove window decorations for borderless appearance
        self.window.overrideredirect(True)
        self.window.configure(bg="black")

        self.canvas = tk.Canvas(self.window, bg="black", highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<Motion>", self.on_motion)

        # Add keyboard shortcuts for opacity control
        self.window.bind("<KeyPress-plus>", lambda e: self.adjust_opacity(0.1))
        self.window.bind("<KeyPress-equal>", lambda e: self.adjust_opacity(0.1))  # + key without shift
        self.window.bind("<KeyPress-minus>", lambda e: self.adjust_opacity(-0.1))
        self.window.bind("<KeyPress-0>", lambda e: self.set_opacity(1.0))  # Reset to opaque

        # Make sure the window can receive focus for keyboard events
        self.window.focus_set()

        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.create_resize_handles()

    def calculate_aspect_ratio(self):
        """Calculate and store the aspect ratio of the source"""
        try:
            if self.source_type == "monitor":
                monitors = list(screeninfo.get_monitors())
                if self.source_data["index"] < len(monitors):
                    monitor = monitors[self.source_data["index"]]
                    self.source_aspect_ratio = monitor.width / monitor.height
            elif self.source_type == "window":
                bbox = self.source_data["bbox"]
                self.source_aspect_ratio = bbox[2] / bbox[3]  # width / height
            elif self.source_type == "region":
                self.source_aspect_ratio = (
                    self.source_data["width"] / self.source_data["height"]
                )

            # Update initial window size to match aspect ratio
            if self.source_aspect_ratio:
                initial_width = 400
                initial_height = int(initial_width / self.source_aspect_ratio)
                # Ensure minimum size
                if initial_height < 150:
                    initial_height = 150
                    initial_width = int(initial_height * self.source_aspect_ratio)
                self.window.geometry(f"{initial_width}x{initial_height}")

        except Exception as e:
            print(f"Error calculating aspect ratio: {e}")
            self.source_aspect_ratio = None

    def create_resize_handles(self):
        self.resize_handles = {
            "se": {"cursor": "bottom_right_corner", "size": 20},
            "sw": {"cursor": "bottom_left_corner", "size": 20},
            "ne": {"cursor": "top_right_corner", "size": 20},
            "nw": {"cursor": "top_left_corner", "size": 20},
            "n": {"cursor": "top_side", "size": 10},
            "s": {"cursor": "bottom_side", "size": 10},
            "e": {"cursor": "right_side", "size": 10},
            "w": {"cursor": "left_side", "size": 10},
        }

    def get_source_name(self):
        if self.source_type == "monitor":
            return f"Monitor {self.source_data['index'] + 1}"
        elif self.source_type == "window":
            return f"Window: {self.source_data['title'][:30]}..."
        elif self.source_type == "region":
            return f"Region ({self.source_data['x']}, {self.source_data['y']})"
        return "Unknown Source"

    def get_resize_corner(self, x, y):
        width = self.window.winfo_width()
        height = self.window.winfo_height()

        corner_size = 20
        edge_size = 10

        if x >= width - corner_size and y >= height - corner_size:
            return "se"
        elif x <= corner_size and y >= height - corner_size:
            return "sw"
        elif x >= width - corner_size and y <= corner_size:
            return "ne"
        elif x <= corner_size and y <= corner_size:
            return "nw"
        elif y <= edge_size:
            return "n"
        elif y >= height - edge_size:
            return "s"
        elif x >= width - edge_size:
            return "e"
        elif x <= edge_size:
            return "w"

        return None

    def on_motion(self, event):
        corner = self.get_resize_corner(event.x, event.y)
        if corner:
            self.window.config(cursor=self.resize_handles[corner]["cursor"])
        else:
            self.window.config(cursor="")

    def on_click(self, event):
        self.resize_corner = self.get_resize_corner(event.x, event.y)
        if self.resize_corner:
            self.is_resizing = True
            self.resize_start_x = event.x_root
            self.resize_start_y = event.y_root
        else:
            self.last_x = event.x_root
            self.last_y = event.y_root

    def on_drag(self, event):
        if self.is_resizing and self.resize_corner:
            self.handle_resize(event)
        else:
            self.handle_move(event)

    def handle_move(self, event):
        deltax = event.x_root - self.last_x
        deltay = event.y_root - self.last_y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f"+{x}+{y}")
        self.last_x = event.x_root
        self.last_y = event.y_root

    def handle_resize(self, event):
        current_width = self.window.winfo_width()
        current_height = self.window.winfo_height()
        current_x = self.window.winfo_x()
        current_y = self.window.winfo_y()

        deltax = event.x_root - self.resize_start_x
        deltay = event.y_root - self.resize_start_y

        new_width = current_width
        new_height = current_height
        new_x = current_x
        new_y = current_y

        # Handle width changes
        if "e" in self.resize_corner:
            new_width = max(200, current_width + deltax)
        elif "w" in self.resize_corner:
            new_width = max(200, current_width - deltax)
            new_x = current_x + deltax

        # Handle height changes
        if "s" in self.resize_corner:
            new_height = max(150, current_height + deltay)
        elif "n" in self.resize_corner:
            new_height = max(150, current_height - deltay)
            new_y = current_y + deltay

        # Apply aspect ratio constraint if available and enabled
        if self.source_aspect_ratio and self.maintain_aspect_ratio:
            new_width, new_height, new_x, new_y = self.constrain_aspect_ratio(
                new_width, new_height, new_x, new_y, current_x, current_y
            )

        self.window.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root

    def constrain_aspect_ratio(
        self, new_width, new_height, new_x, new_y, current_x, current_y
    ):
        """Constrain resize to maintain aspect ratio"""
        target_ratio = self.source_aspect_ratio

        # Determine which dimension to prioritize based on resize direction
        if self.resize_corner in ["e", "w"]:
            # Horizontal resize - adjust height to match width
            new_height = int(new_width / target_ratio)
            new_height = max(150, new_height)  # Ensure minimum height
            new_width = int(new_height * target_ratio)  # Recalculate width for exact ratio
        elif self.resize_corner in ["n", "s"]:
            # Vertical resize - adjust width to match height
            new_width = int(new_height * target_ratio)
            new_width = max(200, new_width)  # Ensure minimum width
            new_height = int(new_width / target_ratio)  # Recalculate height for exact ratio
        else:
            # Corner resize - maintain aspect ratio by choosing the dimension that changed most
            width_change = abs(new_width - self.window.winfo_width())
            height_change = abs(new_height - self.window.winfo_height())

            if width_change > height_change:
                # Width changed more - adjust height
                new_height = int(new_width / target_ratio)
                new_height = max(150, new_height)
                new_width = int(new_height * target_ratio)
            else:
                # Height changed more - adjust width
                new_width = int(new_height * target_ratio)
                new_width = max(200, new_width)
                new_height = int(new_width / target_ratio)

        # Adjust position for corners that should stay fixed
        if "n" in self.resize_corner:
            # Top edge moves - adjust Y position
            height_diff = new_height - self.window.winfo_height()
            new_y = current_y - height_diff

        if "w" in self.resize_corner:
            # Left edge moves - adjust X position
            width_diff = new_width - self.window.winfo_width()
            new_x = current_x - width_diff

        return new_width, new_height, new_x, new_y

    def on_release(self, event):
        self.is_resizing = False
        self.resize_corner = None

    def show_context_menu(self, event):
        context_menu = tk.Menu(self.window, tearoff=0)

        # Always on Top with checkmark
        topmost_state = self.window.attributes("-topmost")
        topmost_label = "✓ Always on Top" if topmost_state else "Always on Top"
        context_menu.add_command(label=topmost_label, command=self.toggle_topmost)

        # Add aspect ratio toggle if we have aspect ratio info
        if self.source_aspect_ratio:
            aspect_label = (
                "✓ Maintain Aspect Ratio"
                if self.maintain_aspect_ratio
                else "Maintain Aspect Ratio"
            )
            context_menu.add_command(label=aspect_label, command=self.toggle_aspect_ratio)

        # Add auto-resize toggle for window sources
        if self.source_type == "window":
            auto_resize_label = (
                "✓ Auto-resize on Source Change"
                if self.auto_resize_on_source_change
                else "Auto-resize on Source Change"
            )
            context_menu.add_command(label=auto_resize_label, command=self.toggle_auto_resize)

        # Add opacity submenu
        context_menu.add_separator()
        opacity_menu = tk.Menu(context_menu, tearoff=0)
        context_menu.add_cascade(label="Opacity", menu=opacity_menu)

        # Add opacity options
        opacity_levels = [
            (1.0, "100% (Opaque)"),
            (0.9, "90%"),
            (0.8, "80%"),
            (0.7, "70%"),
            (0.6, "60%"),
            (0.5, "50%"),
            (0.4, "40%"),
            (0.3, "30%"),
            (0.2, "20%"),
            (0.1, "10%"),
        ]

        for opacity_value, label in opacity_levels:
            # Add checkmark for current opacity
            if abs(self.opacity - opacity_value) < 0.01:  # Account for floating point precision
                display_label = f"✓ {label}"
            else:
                display_label = label

            opacity_menu.add_command(
                label=display_label, command=lambda o=opacity_value: self.set_opacity(o)
            )

        context_menu.add_separator()

        # Add help submenu with keyboard shortcuts
        help_menu = tk.Menu(context_menu, tearoff=0)
        context_menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts:", state="disabled")
        help_menu.add_command(label="  + / = : Increase opacity", state="disabled")
        help_menu.add_command(label="  - : Decrease opacity", state="disabled")
        help_menu.add_command(label="  0 : Reset to 100% opacity", state="disabled")

        context_menu.add_separator()
        context_menu.add_command(label="Close PIP", command=self.close)
        context_menu.tk_popup(event.x_root, event.y_root)

    def toggle_topmost(self):
        current_state = self.window.attributes("-topmost")
        self.window.attributes("-topmost", not current_state)

    def toggle_aspect_ratio(self):
        self.maintain_aspect_ratio = not self.maintain_aspect_ratio

    def toggle_auto_resize(self):
        self.auto_resize_on_source_change = not self.auto_resize_on_source_change

    def set_opacity(self, opacity_value):
        """Set the opacity/transparency of the PIP window"""
        # Clamp opacity between 0.1 and 1.0 (don't allow completely transparent)
        self.opacity = max(0.1, min(1.0, opacity_value))

        # Set the window opacity using the -alpha attribute
        # Note: -alpha ranges from 0.0 (transparent) to 1.0 (opaque)
        self.window.attributes("-alpha", self.opacity)

    def adjust_opacity(self, delta):
        """Adjust opacity by a delta value"""
        new_opacity = self.opacity + delta
        self.set_opacity(new_opacity)

        # Show a temporary opacity indicator
        self.show_opacity_indicator()

    def show_opacity_indicator(self):
        """Show a temporary opacity indicator"""
        if hasattr(self, "opacity_indicator"):
            self.canvas.delete(self.opacity_indicator)

        # Create a temporary text indicator
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        opacity_text = f"Opacity: {int(self.opacity * 100)}%"
        self.opacity_indicator = self.canvas.create_text(
            canvas_width // 2,
            canvas_height // 2,
            text=opacity_text,
            fill="white",
            font=("Arial", 12, "bold"),
            tags="opacity_indicator",
        )

        # Remove the indicator after 1 second
        self.window.after(
            1000, lambda: self.canvas.delete(self.opacity_indicator)
        )

    def start_capture_thread(self):
        self.capture_thread = threading.Thread(target=self.capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()

    def capture_loop(self):
        while self.running:
            try:
                img = self.capture_source()
                if img and self.window and self.window.winfo_exists():
                    # Check if source size has changed
                    current_source_size = (img.width, img.height)
                    if self.last_source_size != current_source_size:
                        self.handle_source_size_change(current_source_size)
                        self.last_source_size = current_source_size

                    canvas_width = self.canvas.winfo_width()
                    canvas_height = self.canvas.winfo_height()

                    if canvas_width > 1 and canvas_height > 1:
                        # Always use crop logic to fill the entire window without black bars
                        img_resized = self.resize_image_maintain_aspect(
                            img, canvas_width, canvas_height
                        )

                        photo = ImageTk.PhotoImage(img_resized)
                        self.window.after(0, self.update_canvas, photo)

                time.sleep(0.033)
            except Exception as e:
                print(f"Capture error: {e}")
                time.sleep(0.1)

    def handle_source_size_change(self, new_size):
        """Handle changes in source size by updating aspect ratio and PIP window"""
        try:
            if not self.maintain_aspect_ratio:
                return

            # Calculate new aspect ratio
            new_width, new_height = new_size
            if new_height > 0:
                new_aspect_ratio = new_width / new_height

                # Only update if aspect ratio has changed significantly
                if (self.source_aspect_ratio is None) or (
                    abs(new_aspect_ratio - self.source_aspect_ratio) > 0.01
                ):
                    print(
                        f"Source size changed to {new_width}x{new_height}, updating aspect ratio"
                    )
                    self.source_aspect_ratio = new_aspect_ratio

                    # Update PIP window size to match new aspect ratio if auto-resize is enabled
                    if self.auto_resize_on_source_change:
                        self.window.after(0, self.update_pip_window_size)

        except Exception as e:
            print(f"Error handling source size change: {e}")

    def update_pip_window_size(self):
        """Update PIP window size to match new source aspect ratio"""
        try:
            if (not self.source_aspect_ratio) or (not self.window) or (
                not self.window.winfo_exists()
            ):
                return

            # Get current window size
            current_width = self.window.winfo_width()
            current_height = self.window.winfo_height()

            # Calculate new size maintaining the current width but adjusting height
            new_height = int(current_width / self.source_aspect_ratio)
            new_height = max(150, new_height)  # Ensure minimum height

            # If the calculated height is too different, adjust width instead
            if abs(new_height - current_height) > current_height * 0.5:
                new_width = int(current_height * self.source_aspect_ratio)
                new_width = max(200, new_width)  # Ensure minimum width
                new_height = int(new_width / self.source_aspect_ratio)
            else:
                new_width = current_width

            # Get current position
            current_x = self.window.winfo_x()
            current_y = self.window.winfo_y()

            # Update window geometry
            self.window.geometry(f"{new_width}x{new_height}+{current_x}+{current_y}")

            print(f"Updated PIP window size to {new_width}x{new_height}")

        except Exception as e:
            print(f"Error updating PIP window size: {e}")

    def capture_source(self):
        try:
            if self.source_type == "monitor":
                return self.capture_monitor()
            elif self.source_type == "window":
                return self.capture_window()
            elif self.source_type == "region":
                return self.capture_region()
        except Exception as e:
            print(f"Source capture error: {e}")
            return None

    def capture_monitor(self):
        with mss.mss() as sct:
            monitors = sct.monitors
            monitor_index = self.source_data["index"]
            if monitor_index < len(monitors) - 1:
                monitor = monitors[monitor_index + 1]
                screenshot = sct.grab(monitor)
                return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return None

    def capture_window(self):
        try:
            # Try to get window handle for true window capture
            if WINDOWS_CAPTURE_AVAILABLE and ("hwnd" in self.source_data):
                return self.capture_window_direct(self.source_data["hwnd"])
            else:
                # Fallback to region capture with dynamic window tracking
                return self.capture_window_region_dynamic()
        except Exception as e:
            print(f"Window capture error: {e}")
            return None

    def capture_window_direct(self, hwnd):
        """Direct window capture on Windows using Win32 API"""
        try:
            # Check if window still exists and is visible
            if not win32gui.IsWindow(hwnd):
                return None

            # Get window rect (full window including borders)
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            # Try to get client area (content area without borders) for better capture
            try:
                client_rect = win32gui.GetClientRect(hwnd)
                client_width = client_rect[2]
                client_height = client_rect[3]

                # Use client area if it's reasonable (not too small)
                if client_width > 100 and client_height > 100:
                    width = client_width
                    height = client_height
            except Exception:
                pass  # Use window rect if client rect fails

            # Check if window size has changed and update tracking
            current_bbox = (left, top, width, height)
            if ("bbox" in self.source_data) and (self.source_data["bbox"] != current_bbox):
                old_bbox = self.source_data["bbox"]
                self.source_data["bbox"] = current_bbox

                # Check if size changed (not just position)
                if old_bbox[2:] != current_bbox[2:]:
                    print(
                        f"Direct capture detected size change from {old_bbox[2]}x{old_bbox[3]} to {width}x{height}"
                    )
                    # Size change will be handled by the main capture loop

            # Skip if window is minimized or has no size
            if width <= 0 or height <= 0:
                return self.create_placeholder_image("Window Minimized")

            # Check if window is minimized
            if win32gui.IsIconic(hwnd):
                return self.create_placeholder_image("Window Minimized")

            # Try PrintWindow first (works better for some applications)
            img = self.capture_with_print_window(hwnd, width, height)
            if img:
                return img

            # Fallback to BitBlt (more reliable for others)
            return self.capture_with_bitblt(hwnd, width, height)

        except Exception as e:
            print(f"Direct window capture error: {e}")
            return None

    def capture_with_print_window(self, hwnd, width, height):
        """Capture using PrintWindow API"""
        try:
            # Get window device context
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # Copy window content to bitmap using ctypes
            result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)  # PW_RENDERFULLCONTENT

            if result:
                # Convert to PIL Image
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)

                img = Image.frombuffer(
                    "RGB",
                    (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                    bmpstr,
                    "raw",
                    "BGRX",
                    0,
                    1,
                )

                # Clean up
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(hwnd, hwndDC)

                return img
            else:
                # Clean up on failure
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(hwnd, hwndDC)
                return None

        except Exception as e:
            print(f"PrintWindow capture error: {e}")
            return None

    def capture_with_bitblt(self, hwnd, width, height):
        """Capture using BitBlt API (fallback method)"""
        try:
            # Get window device context
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # Copy window content using BitBlt
            result = saveDC.BitBlt(
                (0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY
            )

            if result:
                # Convert to PIL Image
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)

                img = Image.frombuffer(
                    "RGB",
                    (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                    bmpstr,
                    "raw",
                    "BGRX",
                    0,
                    1,
                )

                # Clean up
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(hwnd, hwndDC)

                return img
            else:
                # Clean up on failure
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(hwnd, hwndDC)
                return None

        except Exception as e:
            print(f"BitBlt capture error: {e}")
            return None

    def capture_window_region_dynamic(self):
        """Dynamic region capture that tracks window position"""
        try:
            # Update window position if we have a window title
            if "title" in self.source_data:
                self.update_window_position()

            # Use current bbox for capture
            bbox = self.source_data["bbox"]
            screenshot = pyautogui.screenshot(region=bbox)
            return screenshot
        except Exception as e:
            print(f"Dynamic region capture error: {e}")
            return None

    def update_window_position(self):
        """Update window position for dynamic tracking"""
        try:
            import pygetwindow as gw

            windows = gw.getWindowsWithTitle(self.source_data["title"])
            if windows:
                window = windows[0]
                # Update the bbox with current window position
                old_bbox = self.source_data["bbox"]
                new_bbox = (window.left, window.top, window.width, window.height)

                # Only update if window has actually moved or resized
                if old_bbox != new_bbox:
                    self.source_data["bbox"] = new_bbox

                    # Update aspect ratio if window size changed
                    if old_bbox[2:] != new_bbox[2:]:  # Width or height changed
                        old_aspect = old_bbox[2] / old_bbox[3] if old_bbox[3] > 0 else None
                        new_aspect = new_bbox[2] / new_bbox[3] if new_bbox[3] > 0 else None

                        if old_aspect != new_aspect:
                            print(
                                f"Window size changed from {old_bbox[2]}x{old_bbox[3]} to {new_bbox[2]}x{new_bbox[3]}"
                            )
                            self.source_aspect_ratio = new_aspect

                            # Update PIP window size immediately if auto-resize is enabled
                            if (
                                self.maintain_aspect_ratio
                                and self.auto_resize_on_source_change
                                and self.window
                                and self.window.winfo_exists()
                            ):
                                self.window.after(0, self.update_pip_window_size)

        except Exception as e:
            print(f"Window position update error: {e}")

    def create_placeholder_image(self, text):
        """Create a placeholder image with text"""
        try:
            # Create a simple placeholder image
            width, height = 400, 300
            img = Image.new("RGB", (width, height), (40, 40, 40))

            # Add text if PIL supports it
            try:
                from PIL import ImageDraw, ImageFont  # type: ignore[import-not-found]

                draw = ImageDraw.Draw(img)

                # Try to use a system font
                try:
                    font = ImageFont.truetype("arial.ttf", 16)
                except Exception:
                    font = ImageFont.load_default()

                # Calculate text position
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                x = (width - text_width) // 2
                y = (height - text_height) // 2

                # Draw text
                draw.text((x, y), text, fill=(255, 255, 255), font=font)

            except ImportError:
                pass  # Skip text if ImageDraw not available

            return img
        except Exception as e:
            print(f"Placeholder image creation error: {e}")
            return None

    def capture_region(self):
        try:
            x, y, width, height = (
                self.source_data["x"],
                self.source_data["y"],
                self.source_data["width"],
                self.source_data["height"],
            )
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            return screenshot
        except Exception as e:
            print(f"Region capture error: {e}")
            return None

    def resize_image_maintain_aspect(self, img, target_width, target_height):
        """Resize image to fill target dimensions while maintaining aspect ratio (crop if needed)"""
        original_width, original_height = img.size
        original_aspect = original_width / original_height
        target_aspect = target_width / target_height

        if original_aspect > target_aspect:
            # Image is wider than target - fit to height and crop width
            new_height = target_height
            new_width = int(target_height * original_aspect)

            # Resize image
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Crop to fit target width (center crop)
            crop_x = (new_width - target_width) // 2
            result_img = resized_img.crop((crop_x, 0, crop_x + target_width, target_height))
        else:
            # Image is taller than target - fit to width and crop height
            new_width = target_width
            new_height = int(target_width / original_aspect)

            # Resize image
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Crop to fit target height (center crop)
            crop_y = (new_height - target_height) // 2
            result_img = resized_img.crop((0, crop_y, target_width, crop_y + target_height))

        return result_img

    def update_canvas(self, photo):
        if self.canvas and self.canvas.winfo_exists():
            self.canvas.delete("all")
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo)
            self.canvas.image = photo

            # Add subtle resize indicators on borderless window
            self.draw_resize_indicators(canvas_width, canvas_height)

    def draw_resize_indicators(self, width, height):
        """Draw subtle resize indicators on borderless window"""
        # Draw corner indicators (small squares)
        corner_size = 8
        indicator_color = "#333333"

        # Bottom-right corner
        self.canvas.create_rectangle(
            width - corner_size, height - corner_size, width, height, fill=indicator_color, outline=""
        )

        # Bottom-left corner
        self.canvas.create_rectangle(
            0, height - corner_size, corner_size, height, fill=indicator_color, outline=""
        )

        # Top-right corner
        self.canvas.create_rectangle(
            width - corner_size, 0, width, corner_size, fill=indicator_color, outline=""
        )

        # Top-left corner
        self.canvas.create_rectangle(
            0, 0, corner_size, corner_size, fill=indicator_color, outline=""
        )

    def close(self):
        self.running = False
        if self.window:
            self.window.destroy()
        self.manager.remove_pip(self)


