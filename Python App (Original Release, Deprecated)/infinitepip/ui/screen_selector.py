from __future__ import annotations

import tkinter as tk

from ..deps import Image, ImageTk, mss, screeninfo


class ScreenAreaSelector:
    """Visual screen area selection tool with camera-style overlay."""

    def __init__(self, callback=None):
        self.callback = callback
        self.root = None
        self.canvas = None
        self.selection_active = False
        self.start_x = 0
        self.start_y = 0
        self.current_x = 0
        self.current_y = 0
        self.selection_rect = None
        self.background_image = None
        self.overlay_alpha = 0.3
        self.result = None

        # Get screen dimensions
        self.screen_width = 0
        self.screen_height = 0
        self.get_screen_dimensions()

    def get_screen_dimensions(self):
        """Get the combined screen dimensions for multi-monitor setup"""
        monitors = list(screeninfo.get_monitors())
        if monitors:
            # Calculate total screen area
            min_x = min(m.x for m in monitors)
            min_y = min(m.y for m in monitors)
            max_x = max(m.x + m.width for m in monitors)
            max_y = max(m.y + m.height for m in monitors)

            self.screen_width = max_x - min_x
            self.screen_height = max_y - min_y
            self.screen_offset_x = min_x
            self.screen_offset_y = min_y
        else:
            # Fallback
            self.screen_width = 1920
            self.screen_height = 1080
            self.screen_offset_x = 0
            self.screen_offset_y = 0

    def capture_screen_background(self):
        """Capture the entire screen as background"""
        try:
            with mss.mss() as sct:
                # Capture all monitors
                monitor = sct.monitors[0]  # All monitors combined
                screenshot = sct.grab(monitor)

                # Convert to PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

                # Apply dark overlay
                overlay = Image.new(
                    "RGBA", img.size, (0, 0, 0, int(255 * self.overlay_alpha))
                )
                img_with_overlay = Image.alpha_composite(
                    img.convert("RGBA"), overlay
                )

                return img_with_overlay.convert("RGB")
        except Exception as e:
            print(f"Error capturing screen: {e}")
            # Create a dark placeholder
            return Image.new(
                "RGB", (self.screen_width, self.screen_height), (40, 40, 40)
            )

    def show_selector(self):
        """Show the screen area selector overlay"""
        # Create fullscreen overlay window
        self.root = tk.Toplevel()
        self.root.title("Select Screen Area")
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black", cursor="crosshair")

        # Handle escape key to cancel
        self.root.bind("<Escape>", self.cancel_selection)
        self.root.bind("<Return>", self.confirm_selection)

        # Create canvas for drawing
        self.canvas = tk.Canvas(
            self.root,
            bg="black",
            highlightthickness=0,
            width=self.screen_width,
            height=self.screen_height,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind mouse events
        self.canvas.bind("<Button-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.update_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)
        self.canvas.bind("<Motion>", self.update_crosshair)

        # Focus the window
        self.root.focus_set()

        # Capture and display background
        self.update_background()

        # Show instructions
        self.show_instructions()

    def update_background(self):
        """Update the background image"""
        try:
            # Capture screen
            bg_img = self.capture_screen_background()

            # Resize if needed to fit canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width > 1 and canvas_height > 1:
                bg_img = bg_img.resize(
                    (canvas_width, canvas_height), Image.Resampling.LANCZOS
                )

            # Convert to PhotoImage
            self.background_image = ImageTk.PhotoImage(bg_img)

            # Display background
            self.canvas.delete("background")
            self.canvas.create_image(
                0, 0, anchor=tk.NW, image=self.background_image, tags="background"
            )

        except Exception as e:
            print(f"Error updating background: {e}")

    def show_instructions(self):
        """Show instruction text overlay"""
        instructions = [
            "📹 Screen Area Selection",
            "",
            "🖱️ Click and drag to select area",
            "↩️ Press Enter to confirm selection",
            "⎋ Press Escape to cancel",
            "",
            "💡 Selected area will be used for PIP creation",
        ]

        # Create instruction panel
        panel_width = 400
        panel_height = 200
        panel_x = (self.screen_width - panel_width) // 2
        panel_y = 50

        # Semi-transparent background
        self.canvas.create_rectangle(
            panel_x,
            panel_y,
            panel_x + panel_width,
            panel_y + panel_height,
            fill="#000000",
            outline="#f97316",
            width=2,
            stipple="gray50",
            tags="instructions",
        )

        # Add text
        for i, line in enumerate(instructions):
            y_pos = panel_y + 20 + (i * 20)
            color = "#f97316" if line.startswith("📹") else "#ffffff"
            font_weight = "bold" if line.startswith("📹") else "normal"

            self.canvas.create_text(
                panel_x + panel_width // 2,
                y_pos,
                text=line,
                fill=color,
                font=("Arial", 10, font_weight),
                tags="instructions",
            )

    def start_selection(self, event):
        """Start the selection process"""
        self.selection_active = True
        self.start_x = event.x
        self.start_y = event.y
        self.current_x = event.x
        self.current_y = event.y

        # Clear instructions
        self.canvas.delete("instructions")

        # Start drawing selection rectangle
        self.update_selection_visual()

    def update_selection(self, event):
        """Update the selection rectangle"""
        if self.selection_active:
            self.current_x = event.x
            self.current_y = event.y
            self.update_selection_visual()

    def end_selection(self, event):
        """End the selection process"""
        if self.selection_active:
            self.current_x = event.x
            self.current_y = event.y
            self.selection_active = False
            self.update_selection_visual()

    def update_selection_visual(self):
        """Update the visual selection rectangle and info"""
        if (
            (not self.selection_active)
            and self.start_x == self.current_x
            and self.start_y == self.current_y
        ):
            return

        # Clear previous selection
        self.canvas.delete("selection")

        # Calculate selection bounds
        x1 = min(self.start_x, self.current_x)
        y1 = min(self.start_y, self.current_y)
        x2 = max(self.start_x, self.current_x)
        y2 = max(self.start_y, self.current_y)

        width = x2 - x1
        height = y2 - y1

        # Don't draw if too small
        if width < 5 or height < 5:
            return

        # Draw selection rectangle
        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline="#f97316",
            width=3,
            tags="selection",
        )

        # Draw corner handles
        handle_size = 8
        handles = [
            (x1, y1),
            (x2, y1),
            (x1, y2),
            (x2, y2),  # Corners
            (x1 + width // 2, y1),
            (x1 + width // 2, y2),  # Top/bottom center
            (x1, y1 + height // 2),
            (x2, y1 + height // 2),  # Left/right center
        ]

        for hx, hy in handles:
            self.canvas.create_rectangle(
                hx - handle_size // 2,
                hy - handle_size // 2,
                hx + handle_size // 2,
                hy + handle_size // 2,
                fill="#f97316",
                outline="#ea580c",
                width=1,
                tags="selection",
            )

        # Show size information
        self.show_size_info(x1, y1, width, height)

        # Create preview area (clear the selected region)
        self.canvas.create_rectangle(
            x1, y1, x2, y2, fill="", outline="", stipple="", tags="selection"
        )

        # Add semi-transparent overlay to unselected areas
        if self.background_image:
            # Create mask for unselected areas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # Top area
            if y1 > 0:
                self.canvas.create_rectangle(
                    0,
                    0,
                    canvas_width,
                    y1,
                    fill="#000000",
                    stipple="gray25",
                    tags="selection",
                )

            # Bottom area
            if y2 < canvas_height:
                self.canvas.create_rectangle(
                    0,
                    y2,
                    canvas_width,
                    canvas_height,
                    fill="#000000",
                    stipple="gray25",
                    tags="selection",
                )

            # Left area
            self.canvas.create_rectangle(
                0, y1, x1, y2, fill="#000000", stipple="gray25", tags="selection"
            )

            # Right area
            self.canvas.create_rectangle(
                x2,
                y1,
                canvas_width,
                y2,
                fill="#000000",
                stipple="gray25",
                tags="selection",
            )

    def show_size_info(self, x, y, width, height):
        """Show size information panel"""
        # Calculate info panel position
        info_x = x + width + 10
        info_y = y

        # Adjust if too close to screen edge
        if info_x + 200 > self.screen_width:
            info_x = x - 210
        if info_y + 100 > self.screen_height:
            info_y = y + height - 100

        # Create info panel background
        panel_width = 200
        panel_height = 100

        self.canvas.create_rectangle(
            info_x,
            info_y,
            info_x + panel_width,
            info_y + panel_height,
            fill="#2a2a2a",
            outline="#f97316",
            width=2,
            tags="selection",
        )

        # Add size information
        info_lines = [
            "📐 Selection Area",
            f"📏 Size: {width} × {height}",
            f"📍 Position: ({x}, {y})",
            f"📊 Aspect: {width/height:.2f}:1" if height > 0 else "📊 Aspect: --",
        ]

        for i, line in enumerate(info_lines):
            color = "#f97316" if i == 0 else "#ffffff"
            font_weight = "bold" if i == 0 else "normal"

            self.canvas.create_text(
                info_x + 10,
                info_y + 15 + (i * 18),
                text=line,
                fill=color,
                font=("Arial", 9, font_weight),
                anchor=tk.W,
                tags="selection",
            )

    def update_crosshair(self, event):
        """Update crosshair cursor position"""
        if not self.selection_active:
            # Clear previous crosshair
            self.canvas.delete("crosshair")

            # Draw crosshair lines
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # Vertical line
            self.canvas.create_line(
                event.x,
                0,
                event.x,
                canvas_height,
                fill="#f97316",
                width=1,
                dash=(5, 5),
                tags="crosshair",
            )

            # Horizontal line
            self.canvas.create_line(
                0,
                event.y,
                canvas_width,
                event.y,
                fill="#f97316",
                width=1,
                dash=(5, 5),
                tags="crosshair",
            )

    def confirm_selection(self, event=None):
        """Confirm the current selection"""
        if self.start_x != self.current_x or self.start_y != self.current_y:
            # Calculate final selection bounds
            x1 = min(self.start_x, self.current_x)
            y1 = min(self.start_y, self.current_y)
            x2 = max(self.start_x, self.current_x)
            y2 = max(self.start_y, self.current_y)

            width = x2 - x1
            height = y2 - y1

            # Make sure we have a valid selection
            if width > 10 and height > 10:
                # Convert canvas coordinates to screen coordinates
                screen_x = x1 + self.screen_offset_x
                screen_y = y1 + self.screen_offset_y

                self.result = {"x": screen_x, "y": screen_y, "width": width, "height": height}

                self.close_selector()
                return

        # If we get here, selection is invalid
        self.show_error("Please select a valid area (at least 10x10 pixels)")

    def cancel_selection(self, event=None):
        """Cancel the selection"""
        self.result = None
        self.close_selector()

    def close_selector(self):
        """Close the selector window"""
        if self.root:
            self.root.destroy()
            self.root = None

        # Call callback with result
        if self.callback:
            self.callback(self.result)

    def show_error(self, message):
        """Show error message"""
        # Clear previous error
        self.canvas.delete("error")

        # Show error panel
        error_x = self.screen_width // 2 - 150
        error_y = self.screen_height - 100

        self.canvas.create_rectangle(
            error_x,
            error_y,
            error_x + 300,
            error_y + 50,
            fill="#ef4444",
            outline="#dc2626",
            width=2,
            tags="error",
        )

        self.canvas.create_text(
            error_x + 150,
            error_y + 25,
            text=message,
            fill="white",
            font=("Arial", 10, "bold"),
            tags="error",
        )

        # Auto-remove error after 3 seconds
        self.root.after(3000, lambda: self.canvas.delete("error"))

    def select_area(self, callback=None):
        """Main method to start area selection"""
        self.callback = callback
        self.show_selector()

        # Return result (for synchronous usage)
        return self.result



