#!/usr/bin/env python3
"""
InfinitePIP - Modern UI Edition
A completely reimagined user interface for advanced picture-in-picture functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import sys
import json
import os
from pathlib import Path
import base64
import io
import socket
import socketserver
import platform

# === Embedded from `hide_console.py` (inlined for single-file distribution) ===
def hide_console():
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
            info['LSUIElement'] = True
        except Exception:
            pass
    # Linux and other platforms don't typically show console windows for GUI apps
    return False

def show_console():
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

# Hide console window
hide_console()

# Try to import system tray functionality
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    print("Warning: pystray not available. Tray functionality will be limited.")
    TRAY_AVAILABLE = False

try:
    from PIL import Image, ImageTk
except ImportError:
    print("Error: Pillow not available. Please install it with: pip install pillow")
    sys.exit(1)

try:
    import mss
except ImportError:
    print("Error: mss not available. Please install it with: pip install mss")
    sys.exit(1)

try:
    import screeninfo
except ImportError:
    print("Error: screeninfo not available. Please install it with: pip install screeninfo")
    sys.exit(1)

try:
    import pyautogui
except ImportError:
    print("Error: pyautogui not available. Please install it with: pip install pyautogui")
    sys.exit(1)

# Platform-specific imports for window capture
if platform.system() == "Windows":
    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
        from ctypes import windll
        WINDOWS_CAPTURE_AVAILABLE = True
    except ImportError:
        print("Warning: pywin32 not available. Windows-specific capture will be limited.")
        WINDOWS_CAPTURE_AVAILABLE = False
else:
    WINDOWS_CAPTURE_AVAILABLE = False

# === Embedded from `screen_selector.py` (inlined for single-file distribution) ===
class ScreenAreaSelector:
    """Visual screen area selection tool with camera-style overlay"""
    
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
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                
                # Apply dark overlay
                overlay = Image.new('RGBA', img.size, (0, 0, 0, int(255 * self.overlay_alpha)))
                img_with_overlay = Image.alpha_composite(img.convert('RGBA'), overlay)
                
                return img_with_overlay.convert('RGB')
        except Exception as e:
            print(f"Error capturing screen: {e}")
            # Create a dark placeholder
            return Image.new('RGB', (self.screen_width, self.screen_height), (40, 40, 40))
    
    def show_selector(self):
        """Show the screen area selector overlay"""
        # Create fullscreen overlay window
        self.root = tk.Toplevel()
        self.root.title("Select Screen Area")
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='black', cursor='crosshair')
        
        # Handle escape key to cancel
        self.root.bind('<Escape>', self.cancel_selection)
        self.root.bind('<Return>', self.confirm_selection)
        
        # Create canvas for drawing
        self.canvas = tk.Canvas(
            self.root,
            bg='black',
            highlightthickness=0,
            width=self.screen_width,
            height=self.screen_height
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind mouse events
        self.canvas.bind('<Button-1>', self.start_selection)
        self.canvas.bind('<B1-Motion>', self.update_selection)
        self.canvas.bind('<ButtonRelease-1>', self.end_selection)
        self.canvas.bind('<Motion>', self.update_crosshair)
        
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
                bg_img = bg_img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.background_image = ImageTk.PhotoImage(bg_img)
            
            # Display background
            self.canvas.delete("background")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.background_image, tags="background")
            
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
            "💡 Selected area will be used for PIP creation"
        ]
        
        # Create instruction panel
        panel_width = 400
        panel_height = 200
        panel_x = (self.screen_width - panel_width) // 2
        panel_y = 50
        
        # Semi-transparent background
        self.canvas.create_rectangle(
            panel_x, panel_y,
            panel_x + panel_width, panel_y + panel_height,
            fill='#000000', outline='#f97316', width=2,
            stipple='gray50', tags="instructions"
        )
        
        # Add text
        for i, line in enumerate(instructions):
            y_pos = panel_y + 20 + (i * 20)
            color = '#f97316' if line.startswith('📹') else '#ffffff'
            font_weight = 'bold' if line.startswith('📹') else 'normal'
            
            self.canvas.create_text(
                panel_x + panel_width // 2, y_pos,
                text=line, fill=color, font=('Arial', 10, font_weight),
                tags="instructions"
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
        if not self.selection_active and self.start_x == self.current_x and self.start_y == self.current_y:
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
            x1, y1, x2, y2,
            outline='#f97316', width=3,
            tags="selection"
        )
        
        # Draw corner handles
        handle_size = 8
        handles = [
            (x1, y1), (x2, y1), (x1, y2), (x2, y2),  # Corners
            (x1 + width//2, y1), (x1 + width//2, y2),  # Top/bottom center
            (x1, y1 + height//2), (x2, y1 + height//2)  # Left/right center
        ]
        
        for hx, hy in handles:
            self.canvas.create_rectangle(
                hx - handle_size//2, hy - handle_size//2,
                hx + handle_size//2, hy + handle_size//2,
                fill='#f97316', outline='#ea580c', width=1,
                tags="selection"
            )
        
        # Show size information
        self.show_size_info(x1, y1, width, height)
        
        # Create preview area (clear the selected region)
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill='', outline='',
            stipple='', tags="selection"
        )
        
        # Add semi-transparent overlay to unselected areas
        if self.background_image:
            # Create mask for unselected areas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Top area
            if y1 > 0:
                self.canvas.create_rectangle(
                    0, 0, canvas_width, y1,
                    fill='#000000', stipple='gray25', tags="selection"
                )
            
            # Bottom area
            if y2 < canvas_height:
                self.canvas.create_rectangle(
                    0, y2, canvas_width, canvas_height,
                    fill='#000000', stipple='gray25', tags="selection"
                )
            
            # Left area
            self.canvas.create_rectangle(
                0, y1, x1, y2,
                fill='#000000', stipple='gray25', tags="selection"
            )
            
            # Right area
            self.canvas.create_rectangle(
                x2, y1, canvas_width, y2,
                fill='#000000', stipple='gray25', tags="selection"
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
            info_x, info_y,
            info_x + panel_width, info_y + panel_height,
            fill='#2a2a2a', outline='#f97316', width=2,
            tags="selection"
        )
        
        # Add size information
        info_lines = [
            f"📐 Selection Area",
            f"📏 Size: {width} × {height}",
            f"📍 Position: ({x}, {y})",
            f"📊 Aspect: {width/height:.2f}:1" if height > 0 else "📊 Aspect: --"
        ]
        
        for i, line in enumerate(info_lines):
            color = '#f97316' if i == 0 else '#ffffff'
            font_weight = 'bold' if i == 0 else 'normal'
            
            self.canvas.create_text(
                info_x + 10, info_y + 15 + (i * 18),
                text=line, fill=color, font=('Arial', 9, font_weight),
                anchor=tk.W, tags="selection"
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
                event.x, 0, event.x, canvas_height,
                fill='#f97316', width=1, dash=(5, 5),
                tags="crosshair"
            )
            
            # Horizontal line
            self.canvas.create_line(
                0, event.y, canvas_width, event.y,
                fill='#f97316', width=1, dash=(5, 5),
                tags="crosshair"
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
                
                self.result = {
                    'x': screen_x,
                    'y': screen_y,
                    'width': width,
                    'height': height
                }
                
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
            error_x, error_y,
            error_x + 300, error_y + 50,
            fill='#ef4444', outline='#dc2626', width=2,
            tags="error"
        )
        
        self.canvas.create_text(
            error_x + 150, error_y + 25,
            text=message, fill='white', font=('Arial', 10, 'bold'),
            tags="error"
        )
        
        # Auto-remove error after 3 seconds
        self.root.after(3000, lambda: self.canvas.delete("error"))
    
    def select_area(self, callback=None):
        """Main method to start area selection"""
        self.callback = callback
        self.show_selector()
        
        # Return result (for synchronous usage)
        return self.result


# === Embedded from `pip_anything_desktop.py` (inlined for single-file distribution) ===
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
        self.window.attributes('-topmost', True)
        
        # Remove window decorations for borderless appearance
        self.window.overrideredirect(True)
        self.window.configure(bg='black')
        
        self.canvas = tk.Canvas(self.window, bg='black', highlightthickness=0, bd=0)
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
            if self.source_type == 'monitor':
                monitors = list(screeninfo.get_monitors())
                if self.source_data['index'] < len(monitors):
                    monitor = monitors[self.source_data['index']]
                    self.source_aspect_ratio = monitor.width / monitor.height
            elif self.source_type == 'window':
                bbox = self.source_data['bbox']
                self.source_aspect_ratio = bbox[2] / bbox[3]  # width / height
            elif self.source_type == 'region':
                self.source_aspect_ratio = self.source_data['width'] / self.source_data['height']
            
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
            'se': {'cursor': 'bottom_right_corner', 'size': 20},
            'sw': {'cursor': 'bottom_left_corner', 'size': 20},
            'ne': {'cursor': 'top_right_corner', 'size': 20},
            'nw': {'cursor': 'top_left_corner', 'size': 20},
            'n': {'cursor': 'top_side', 'size': 10},
            's': {'cursor': 'bottom_side', 'size': 10},
            'e': {'cursor': 'right_side', 'size': 10},
            'w': {'cursor': 'left_side', 'size': 10}
        }
    
    def get_source_name(self):
        if self.source_type == 'monitor':
            return f"Monitor {self.source_data['index'] + 1}"
        elif self.source_type == 'window':
            return f"Window: {self.source_data['title'][:30]}..."
        elif self.source_type == 'region':
            return f"Region ({self.source_data['x']}, {self.source_data['y']})"
        return "Unknown Source"
    
    def get_resize_corner(self, x, y):
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        
        corner_size = 20
        edge_size = 10
        
        if x >= width - corner_size and y >= height - corner_size:
            return 'se'
        elif x <= corner_size and y >= height - corner_size:
            return 'sw'
        elif x >= width - corner_size and y <= corner_size:
            return 'ne'
        elif x <= corner_size and y <= corner_size:
            return 'nw'
        elif y <= edge_size:
            return 'n'
        elif y >= height - edge_size:
            return 's'
        elif x >= width - edge_size:
            return 'e'
        elif x <= edge_size:
            return 'w'
        
        return None
    
    def on_motion(self, event):
        corner = self.get_resize_corner(event.x, event.y)
        if corner:
            self.window.config(cursor=self.resize_handles[corner]['cursor'])
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
        if 'e' in self.resize_corner:
            new_width = max(200, current_width + deltax)
        elif 'w' in self.resize_corner:
            new_width = max(200, current_width - deltax)
            new_x = current_x + deltax
        
        # Handle height changes
        if 's' in self.resize_corner:
            new_height = max(150, current_height + deltay)
        elif 'n' in self.resize_corner:
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
    
    def constrain_aspect_ratio(self, new_width, new_height, new_x, new_y, current_x, current_y):
        """Constrain resize to maintain aspect ratio"""
        target_ratio = self.source_aspect_ratio
        
        # Determine which dimension to prioritize based on resize direction
        if self.resize_corner in ['e', 'w']:
            # Horizontal resize - adjust height to match width
            new_height = int(new_width / target_ratio)
            new_height = max(150, new_height)  # Ensure minimum height
            new_width = int(new_height * target_ratio)  # Recalculate width for exact ratio
        elif self.resize_corner in ['n', 's']:
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
        if 'n' in self.resize_corner:
            # Top edge moves - adjust Y position
            height_diff = new_height - self.window.winfo_height()
            new_y = current_y - height_diff
        
        if 'w' in self.resize_corner:
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
        topmost_state = self.window.attributes('-topmost')
        topmost_label = "✓ Always on Top" if topmost_state else "Always on Top"
        context_menu.add_command(label=topmost_label, command=self.toggle_topmost)
        
        # Add aspect ratio toggle if we have aspect ratio info
        if self.source_aspect_ratio:
            aspect_label = "✓ Maintain Aspect Ratio" if self.maintain_aspect_ratio else "Maintain Aspect Ratio"
            context_menu.add_command(label=aspect_label, command=self.toggle_aspect_ratio)
        
        # Add auto-resize toggle for window sources
        if self.source_type == 'window':
            auto_resize_label = "✓ Auto-resize on Source Change" if self.auto_resize_on_source_change else "Auto-resize on Source Change"
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
            (0.1, "10%")
        ]
        
        for opacity_value, label in opacity_levels:
            # Add checkmark for current opacity
            if abs(self.opacity - opacity_value) < 0.01:  # Account for floating point precision
                display_label = f"✓ {label}"
            else:
                display_label = label
            
            opacity_menu.add_command(
                label=display_label,
                command=lambda o=opacity_value: self.set_opacity(o)
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
        current_state = self.window.attributes('-topmost')
        self.window.attributes('-topmost', not current_state)
    
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
        self.window.attributes('-alpha', self.opacity)
    
    def adjust_opacity(self, delta):
        """Adjust opacity by a delta value"""
        new_opacity = self.opacity + delta
        self.set_opacity(new_opacity)
        
        # Show a temporary opacity indicator
        self.show_opacity_indicator()
    
    def show_opacity_indicator(self):
        """Show a temporary opacity indicator"""
        if hasattr(self, 'opacity_indicator'):
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
            tags="opacity_indicator"
        )
        
        # Remove the indicator after 1 second
        self.window.after(1000, lambda: self.canvas.delete(self.opacity_indicator))
    
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
                        img_resized = self.resize_image_maintain_aspect(img, canvas_width, canvas_height)
                        
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
                if (self.source_aspect_ratio is None or
                    abs(new_aspect_ratio - self.source_aspect_ratio) > 0.01):
                    
                    print(f"Source size changed to {new_width}x{new_height}, updating aspect ratio")
                    self.source_aspect_ratio = new_aspect_ratio
                    
                    # Update PIP window size to match new aspect ratio if auto-resize is enabled
                    if self.auto_resize_on_source_change:
                        self.window.after(0, self.update_pip_window_size)
                    
        except Exception as e:
            print(f"Error handling source size change: {e}")
    
    def update_pip_window_size(self):
        """Update PIP window size to match new source aspect ratio"""
        try:
            if not self.source_aspect_ratio or not self.window or not self.window.winfo_exists():
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
            if self.source_type == 'monitor':
                return self.capture_monitor()
            elif self.source_type == 'window':
                return self.capture_window()
            elif self.source_type == 'region':
                return self.capture_region()
        except Exception as e:
            print(f"Source capture error: {e}")
            return None
    
    def capture_monitor(self):
        with mss.mss() as sct:
            monitors = sct.monitors
            monitor_index = self.source_data['index']
            if monitor_index < len(monitors) - 1:
                monitor = monitors[monitor_index + 1]
                screenshot = sct.grab(monitor)
                return Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        return None
    
    def capture_window(self):
        try:
            # Try to get window handle for true window capture
            if WINDOWS_CAPTURE_AVAILABLE and 'hwnd' in self.source_data:
                return self.capture_window_direct(self.source_data['hwnd'])
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
            if 'bbox' in self.source_data and self.source_data['bbox'] != current_bbox:
                old_bbox = self.source_data['bbox']
                self.source_data['bbox'] = current_bbox
                
                # Check if size changed (not just position)
                if old_bbox[2:] != current_bbox[2:]:
                    print(f"Direct capture detected size change from {old_bbox[2]}x{old_bbox[3]} to {width}x{height}")
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
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
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
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            if result:
                # Convert to PIL Image
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
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
            if 'title' in self.source_data:
                self.update_window_position()
            
            # Use current bbox for capture
            bbox = self.source_data['bbox']
            screenshot = pyautogui.screenshot(region=bbox)
            return screenshot
        except Exception as e:
            print(f"Dynamic region capture error: {e}")
            return None
    
    def update_window_position(self):
        """Update window position for dynamic tracking"""
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(self.source_data['title'])
            if windows:
                window = windows[0]
                # Update the bbox with current window position
                old_bbox = self.source_data['bbox']
                new_bbox = (window.left, window.top, window.width, window.height)
                
                # Only update if window has actually moved or resized
                if old_bbox != new_bbox:
                    self.source_data['bbox'] = new_bbox
                    
                    # Update aspect ratio if window size changed
                    if old_bbox[2:] != new_bbox[2:]:  # Width or height changed
                        old_aspect = old_bbox[2] / old_bbox[3] if old_bbox[3] > 0 else None
                        new_aspect = new_bbox[2] / new_bbox[3] if new_bbox[3] > 0 else None
                        
                        if old_aspect != new_aspect:
                            print(f"Window size changed from {old_bbox[2]}x{old_bbox[3]} to {new_bbox[2]}x{new_bbox[3]}")
                            self.source_aspect_ratio = new_aspect
                            
                            # Update PIP window size immediately if auto-resize is enabled
                            if (self.maintain_aspect_ratio and self.auto_resize_on_source_change and
                                self.window and self.window.winfo_exists()):
                                self.window.after(0, self.update_pip_window_size)
                        
        except Exception as e:
            print(f"Window position update error: {e}")
    
    def create_placeholder_image(self, text):
        """Create a placeholder image with text"""
        try:
            # Create a simple placeholder image
            width, height = 400, 300
            img = Image.new('RGB', (width, height), (40, 40, 40))
            
            # Add text if PIL supports it
            try:
                from PIL import ImageDraw, ImageFont
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
                self.source_data['x'],
                self.source_data['y'],
                self.source_data['width'],
                self.source_data['height']
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
            self.canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
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
            width - corner_size, height - corner_size, width, height,
            fill=indicator_color, outline=""
        )
        
        # Bottom-left corner
        self.canvas.create_rectangle(
            0, height - corner_size, corner_size, height,
            fill=indicator_color, outline=""
        )
        
        # Top-right corner
        self.canvas.create_rectangle(
            width - corner_size, 0, width, corner_size,
            fill=indicator_color, outline=""
        )
        
        # Top-left corner
        self.canvas.create_rectangle(
            0, 0, corner_size, corner_size,
            fill=indicator_color, outline=""
        )
        
    
    def close(self):
        self.running = False
        if self.window:
            self.window.destroy()
        self.manager.remove_pip(self)


class RemoteControlHandler(socketserver.BaseRequestHandler):
    """Handles remote control requests for InfinitePIP"""
    
    def handle(self):
        try:
            # Receive data
            data = self.request.recv(1024).decode('utf-8')
            command_data = json.loads(data)
            
            # Process command
            response = self.process_command(command_data)
            
            # Send response
            self.request.sendall(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            error_response = {"status": "error", "message": str(e)}
            self.request.sendall(json.dumps(error_response).encode('utf-8'))
    
    def process_command(self, command_data):
        """Process a remote control command"""
        action = command_data.get("action")
        
        if action == "create_window_pip":
            return self.create_window_pip(command_data.get("window_data"))
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def create_window_pip(self, window_data):
        """Create a window PIP from external request"""
        try:
            # Get the main app instance
            app = getattr(self.server, 'app_instance', None)
            if not app:
                return {"status": "error", "message": "App instance not available"}
            
            # Create window PIP
            app.create_window_pip_from_external(window_data)
            
            return {"status": "success", "message": "Window PIP created successfully"}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}


class RemoteControlServer(socketserver.ThreadingTCPServer):
    """TCP server for remote control functionality"""
    
    def __init__(self, host, port, app_instance):
        super().__init__((host, port), RemoteControlHandler)
        self.app_instance = app_instance
        self.daemon_threads = True


class ModernScrollableFrame(ttk.Frame):
    """A modern scrollable frame with smooth scrolling and proper sizing"""
    
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack components
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel scrolling
        self.bind_mousewheel()
        
        # Configure canvas window width
        self.canvas.bind('<Configure>', self._on_canvas_configure)
    
    def _on_canvas_configure(self, event):
        """Handle canvas resize to make scrollable frame fit width"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def bind_mousewheel(self):
        """Bind mousewheel events for smooth scrolling"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")
        
        self.canvas.bind('<Enter>', _bind_to_mousewheel)
        self.canvas.bind('<Leave>', _unbind_from_mousewheel)


class ModernCard(ttk.Frame):
    """A modern card component with hover effects and consistent styling"""
    
    def __init__(self, parent, title="", subtitle="", **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(style='ModernCard.TFrame', padding="20")
        
        # Title
        if title:
            title_label = ttk.Label(self, text=title, style='CardTitle.TLabel')
            title_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Subtitle
        if subtitle:
            subtitle_label = ttk.Label(self, text=subtitle, style='CardSubtitle.TLabel')
            subtitle_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Content frame for additional widgets
        self.content_frame = ttk.Frame(self, style='ModernCard.TFrame')
        self.content_frame.pack(fill=tk.BOTH, expand=True)


class ModernButton(ttk.Button):
    """A modern button with consistent styling"""
    
    def __init__(self, parent, text="", command=None, style_type="primary", **kwargs):
        style_map = {
            "primary": "ModernPrimary.TButton",
            "secondary": "ModernSecondary.TButton",
            "success": "ModernSuccess.TButton",
            "danger": "ModernDanger.TButton"
        }
        
        style = style_map.get(style_type, "ModernPrimary.TButton")
        super().__init__(parent, text=text, command=command, style=style, **kwargs)


class InfinitePIPModernUI:
    """Completely reimagined modern UI for InfinitePIP"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.active_pips = []
        self.monitors = list(screeninfo.get_monitors())
        self.windows = []
        self.tray_icon = None
        self.is_closing = False
        self.remote_server = None
        
        # Initialize UI
        self.setup_modern_theme()
        self.setup_window()
        self.setup_layout()
        
        # Setup tray functionality
        if TRAY_AVAILABLE:
            self.setup_tray()
        
        # Setup remote control server
        self.setup_remote_control()
        
        # Refresh sources
        self.refresh_windows()
    
    def setup_modern_theme(self):
        """Setup completely modern theme with proper colors and styles"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Modern color palette
        self.colors = {
            'bg_primary': '#0a0a0a',
            'bg_secondary': '#1a1a1a', 
            'bg_card': '#1a1a1a',
            'bg_card_hover': '#2a2a2a',
            'bg_input': '#252525',
            'accent_primary': '#f97316',
            'accent_secondary': '#10b981',
            'accent_danger': '#ef4444',
            'text_primary': '#ffffff',
            'text_secondary': '#a1a1aa',
            'text_muted': '#666666',
            'border': '#333333',
            'shadow': '#00000040'
        }
        
        # Configure root window
        self.root.configure(bg=self.colors['bg_primary'])
        
        # Main frame styles
        self.style.configure('Modern.TFrame', background=self.colors['bg_primary'])
        self.style.configure('ModernCard.TFrame', 
                           background=self.colors['bg_card'],
                           relief='flat',
                           borderwidth=1)
        
        # Typography styles
        self.style.configure('ModernTitle.TLabel',
                           font=('Segoe UI', 32, 'bold'),
                           background=self.colors['bg_primary'],
                           foreground=self.colors['text_primary'])
        
        self.style.configure('ModernSubtitle.TLabel',
                           font=('Segoe UI', 16),
                           background=self.colors['bg_primary'],
                           foreground=self.colors['accent_primary'])
        
        self.style.configure('SectionTitle.TLabel',
                           font=('Segoe UI', 18, 'bold'),
                           background=self.colors['bg_primary'],
                           foreground=self.colors['text_primary'])
        
        self.style.configure('CardTitle.TLabel',
                           font=('Segoe UI', 14, 'bold'),
                           background=self.colors['bg_card'],
                           foreground=self.colors['text_primary'])
        
        self.style.configure('CardSubtitle.TLabel',
                           font=('Segoe UI', 11),
                           background=self.colors['bg_card'],
                           foreground=self.colors['text_secondary'])
        
        self.style.configure('ModernText.TLabel',
                           font=('Segoe UI', 10),
                           background=self.colors['bg_primary'],
                           foreground=self.colors['text_primary'])
        
        # Button styles
        self.style.configure('ModernPrimary.TButton',
                           background=self.colors['accent_primary'],
                           foreground='white',
                           font=('Segoe UI', 10, 'bold'),
                           borderwidth=0,
                           relief='flat',
                           padding=(20, 10))
        
        self.style.map('ModernPrimary.TButton',
                      background=[('active', '#ea580c'), ('pressed', '#c2410c')])
        
        self.style.configure('ModernSecondary.TButton',
                           background=self.colors['bg_card'],
                           foreground=self.colors['text_primary'],
                           font=('Segoe UI', 10),
                           borderwidth=1,
                           relief='flat',
                           padding=(16, 8))
        
        self.style.map('ModernSecondary.TButton',
                      background=[('active', self.colors['bg_card_hover'])])
        
        self.style.configure('ModernSuccess.TButton',
                           background=self.colors['accent_secondary'],
                           foreground='white',
                           font=('Segoe UI', 10, 'bold'),
                           borderwidth=0,
                           relief='flat',
                           padding=(16, 8))
        
        self.style.configure('ModernDanger.TButton',
                           background=self.colors['accent_danger'],
                           foreground='white',
                           font=('Segoe UI', 10, 'bold'),
                           borderwidth=0,
                           relief='flat',
                           padding=(16, 8))
        
        # Notebook styles
        self.style.configure('Modern.TNotebook',
                           background=self.colors['bg_primary'],
                           borderwidth=0)
        
        self.style.configure('Modern.TNotebook.Tab',
                           background=self.colors['bg_card'],
                           foreground=self.colors['text_secondary'],
                           padding=[16, 10],
                           font=('Segoe UI', 10))
        
        self.style.map('Modern.TNotebook.Tab',
                      background=[('selected', self.colors['accent_primary'])],
                      foreground=[('selected', 'white')],
                      padding=[('selected', [30, 18])],
                      font=[('selected', ('Segoe UI', 12, 'bold'))])
        
        # Entry styles
        self.style.configure('Modern.TEntry',
                           fieldbackground=self.colors['bg_input'],
                           borderwidth=1,
                           relief='flat',
                           insertcolor=self.colors['text_primary'],
                           foreground=self.colors['text_primary'])
    
    def setup_window(self):
        """Setup main window with modern properties"""
        self.root.title("InfinitePIP - Advanced Picture-in-Picture")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"1200x800+{x}+{y}")
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
    
    def setup_tray(self):
        """Setup system tray functionality"""
        if not TRAY_AVAILABLE:
            return
        
        # Create tray icon
        icon_image = self.create_tray_icon()
        
        # Create tray menu
        menu = pystray.Menu(
            pystray.MenuItem("InfinitePIP", self.show_window, default=True),
            pystray.MenuItem("Show/Hide", self.toggle_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Active PIPs", self.show_active_pips_info),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Close All PIPs", self.close_all_pips),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit_application)
        )
        
        # Create tray icon
        self.tray_icon = pystray.Icon(
            "InfinitePIP",
            icon_image,
            "InfinitePIP - Advanced Picture-in-Picture",
            menu
        )
        
        # Start tray in a separate thread
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()
    
    def create_tray_icon(self):
        """Create a custom tray icon"""
        # Create a simple icon with PIL
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a modern PIP-style icon
        # Outer rectangle (main screen)
        draw.rectangle([8, 8, width-8, height-8], fill='#f97316', outline='#ea580c', width=2)
        
        # Inner rectangle (PIP window)
        pip_size = 20
        pip_x = width - pip_size - 12
        pip_y = height - pip_size - 12
        draw.rectangle([pip_x, pip_y, pip_x + pip_size, pip_y + pip_size], 
                      fill='#10b981', outline='#059669', width=2)
        
        # Add a small dot to indicate active state
        dot_size = 4
        draw.ellipse([pip_x + pip_size - dot_size - 2, pip_y + 2, 
                     pip_x + pip_size - 2, pip_y + 2 + dot_size], 
                    fill='#ffffff')
        
        return image
    
    def on_window_close(self):
        """Handle window close event - minimize to tray instead of closing"""
        if TRAY_AVAILABLE and not self.is_closing:
            self.hide_window()
        else:
            self.quit_application()
    
    def show_window(self, icon=None, item=None):
        """Show the main window"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def hide_window(self):
        """Hide the main window to tray"""
        self.root.withdraw()
        if TRAY_AVAILABLE:
            # Show notification that app is running in tray
            self.tray_icon.notify(
                "InfinitePIP minimized to tray",
                "Click the tray icon to restore the window"
            )
    
    def toggle_window(self, icon=None, item=None):
        """Toggle window visibility"""
        if self.root.state() == 'withdrawn':
            self.show_window()
        else:
            self.hide_window()
    
    def show_active_pips_info(self, icon=None, item=None):
        """Show info about active PIPs"""
        if not TRAY_AVAILABLE:
            return
        
        pip_count = len(self.active_pips)
        if pip_count == 0:
            message = "No active PIPs"
        else:
            message = f"{pip_count} active PIP{'s' if pip_count != 1 else ''}"
        
        self.tray_icon.notify("InfinitePIP Status", message)
    
    def quit_application(self, icon=None, item=None):
        """Quit the application completely"""
        self.is_closing = True
        
        # Close all PIPs
        for pip in self.active_pips[:]:
            try:
                pip.close()
            except:
                pass
        
        # Stop tray icon
        if TRAY_AVAILABLE and self.tray_icon:
            self.tray_icon.stop()
        
        # Close main window
        self.root.quit()
        self.root.destroy()
    
    def setup_remote_control(self):
        """Setup remote control server for external PIP creation"""
        try:
            # Start remote control server on a specific port
            self.remote_server = RemoteControlServer('localhost', 38474, self)
            
            # Start server in a separate thread
            self.remote_thread = threading.Thread(target=self.remote_server.serve_forever, daemon=True)
            self.remote_thread.start()
            
            print("✓ Remote control server started on port 38474")
            
        except Exception as e:
            print(f"Warning: Could not start remote control server: {e}")
            self.remote_server = None
    
    def create_window_pip_from_external(self, window_data):
        """Create a window PIP from external request (called by remote control)"""
        def create_pip():
            try:
                # Add the window to our list if it's not already there
                existing_window = None
                for window in self.windows:
                    if window.get('hwnd') == window_data.get('hwnd'):
                        existing_window = window
                        break
                
                if not existing_window:
                    self.windows.append(window_data)
                    # Update windows list UI if it exists
                    if hasattr(self, 'windows_container'):
                        self.update_windows_list()
                
                # Create the PIP
                pip_window = InfinitePIPWindow('window', window_data, self)
                self.active_pips.append(pip_window)
                self.update_status()
                self.update_active_pips_list()
                
                # Show window if it's hidden
                if self.root.state() == 'withdrawn':
                    self.show_window()
                
                # Show notification
                if TRAY_AVAILABLE and self.tray_icon:
                    self.tray_icon.notify(
                        "InfinitePIP",
                        f"Created PIP for: {window_data.get('title', 'Unknown Window')}"
                    )
                
            except Exception as e:
                print(f"Error creating external PIP: {e}")
                # Show error notification
                if TRAY_AVAILABLE and self.tray_icon:
                    self.tray_icon.notify(
                        "InfinitePIP Error",
                        f"Could not create PIP: {str(e)}"
                    )
        
        # Schedule the PIP creation on the main thread
        self.root.after(0, create_pip)
    
    def setup_layout(self):
        """Setup the main layout with modern responsive design"""
        # Main container
        main_container = ttk.Frame(self.root, style='Modern.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # Header section
        self.create_header(main_container)
        
        # Content area with proper spacing
        content_frame = ttk.Frame(main_container, style='Modern.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(30, 0))
        
        # Create tabbed interface
        self.create_modern_tabs(content_frame)
        
        # Footer with actions
        self.create_footer(main_container)
    
    def create_header(self, parent):
        """Create modern header with title and status"""
        header_frame = ttk.Frame(parent, style='Modern.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Left side - Title and subtitle
        title_section = ttk.Frame(header_frame, style='Modern.TFrame')
        title_section.pack(side=tk.LEFT, anchor=tk.W)
        
        title_label = ttk.Label(title_section, text="InfinitePIP", style='ModernTitle.TLabel')
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(title_section, text="Advanced Picture-in-Picture for Desktop", 
                                 style='ModernSubtitle.TLabel')
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Right side - Status and info
        status_section = ttk.Frame(header_frame, style='Modern.TFrame')
        status_section.pack(side=tk.RIGHT, anchor=tk.E)
        
        # Active PIPs counter
        self.status_label = ttk.Label(status_section, text="● Ready", 
                                    style='ModernText.TLabel', 
                                    foreground=self.colors['accent_secondary'])
        self.status_label.pack(anchor=tk.E)
        
        self.pips_counter = ttk.Label(status_section, text="0 Active PIPs", 
                                    style='ModernText.TLabel',
                                    foreground=self.colors['text_secondary'])
        self.pips_counter.pack(anchor=tk.E, pady=(5, 0))
    
    def create_modern_tabs(self, parent):
        """Create modern tabbed interface with proper scrolling"""
        # Create notebook
        self.notebook = ttk.Notebook(parent, style='Modern.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_monitors_tab()
        self.create_windows_tab()
        self.create_regions_tab()
        self.create_active_pips_tab()
    
    def create_monitors_tab(self):
        """Create monitors tab with scrollable content"""
        # Main frame for monitors
        monitors_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(monitors_frame, text="🖥️ Monitors")
        
        # Add padding frame
        padded_frame = ttk.Frame(monitors_frame, style='Modern.TFrame')
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Section title
        title_label = ttk.Label(padded_frame, text="Available Monitors", style='SectionTitle.TLabel')
        title_label.pack(anchor=tk.W, pady=(0, 10))
        
        subtitle_label = ttk.Label(padded_frame, text="Create picture-in-picture windows from any connected monitor",
                                 style='ModernText.TLabel', foreground=self.colors['text_secondary'])
        subtitle_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Create scrollable area
        scrollable_area = ModernScrollableFrame(padded_frame, style='Modern.TFrame')
        scrollable_area.pack(fill=tk.BOTH, expand=True)
        
        # Create grid container
        grid_container = ttk.Frame(scrollable_area.scrollable_frame, style='Modern.TFrame')
        grid_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add monitor cards in grid layout
        columns = 3  # Number of columns in grid
        for i, monitor in enumerate(self.monitors):
            row = i // columns
            col = i % columns
            self.create_monitor_grid_card(grid_container, monitor, i, row, col)
    
    def create_monitor_grid_card(self, parent, monitor, index, row, col):
        """Create a modern monitor card for grid layout"""
        # Configure grid weights for responsive layout
        parent.grid_columnconfigure(col, weight=1, uniform="monitor")
        parent.grid_rowconfigure(row, weight=0)
        
        # Create square card container
        card_container = ttk.Frame(parent, style='ModernCard.TFrame', 
                                 relief='flat', borderwidth=1, padding="15")
        card_container.grid(row=row, column=col, padx=8, pady=8, sticky="ew")
        
        # Monitor icon and number (large)
        icon_frame = ttk.Frame(card_container, style='ModernCard.TFrame')
        icon_frame.pack(pady=(0, 10))
        
        # Large monitor icon
        icon_label = ttk.Label(icon_frame, text="🖥️", 
                             font=('Segoe UI', 32), style='CardTitle.TLabel')
        icon_label.pack()
        
        # Preview image
        preview_frame = ttk.Frame(icon_frame, style='ModernCard.TFrame')
        preview_frame.pack(pady=(5, 0))
        
        try:
            # Capture preview screenshot
            preview_image = self.capture_monitor_preview(index)
            if preview_image:
                # Resize to thumbnail
                preview_image = preview_image.resize((120, 68), Image.Resampling.LANCZOS)
                preview_photo = ImageTk.PhotoImage(preview_image)
                
                preview_label = ttk.Label(preview_frame, image=preview_photo, style='CardTitle.TLabel')
                preview_label.image = preview_photo  # Keep a reference
                preview_label.pack()
            else:
                # Fallback placeholder
                ttk.Label(preview_frame, text="Preview unavailable", 
                         font=('Segoe UI', 8), style='CardSubtitle.TLabel').pack()
        except Exception as e:
            # Fallback placeholder
            ttk.Label(preview_frame, text="Preview unavailable", 
                     font=('Segoe UI', 8), style='CardSubtitle.TLabel').pack()
        
        # Monitor number
        monitor_num = index + 1
        num_text = f"Monitor {monitor_num}"
        if monitor.is_primary:
            num_text += " (Primary)"
        
        num_label = ttk.Label(icon_frame, text=num_text, 
                            font=('Segoe UI', 12, 'bold'), style='CardTitle.TLabel')
        num_label.pack(pady=(5, 0))
        
        # Monitor specs (compact)
        specs_frame = ttk.Frame(card_container, style='ModernCard.TFrame')
        specs_frame.pack(pady=(0, 10))
        
        # Resolution (main info)
        resolution_label = ttk.Label(specs_frame, text=f"{monitor.width}×{monitor.height}", 
                                    font=('Segoe UI', 11, 'bold'), style='CardSubtitle.TLabel')
        resolution_label.pack()
        
        # Aspect ratio
        aspect_ratio = round(monitor.width / monitor.height, 2)
        aspect_label = ttk.Label(specs_frame, text=f"{aspect_ratio}:1", 
                               style='CardSubtitle.TLabel')
        aspect_label.pack()
        
        # Position (smaller)
        position_label = ttk.Label(specs_frame, text=f"({monitor.x}, {monitor.y})", 
                                 font=('Segoe UI', 9), style='CardSubtitle.TLabel')
        position_label.pack(pady=(2, 0))
        
        # Action button (full width)
        button_frame = ttk.Frame(card_container, style='ModernCard.TFrame')
        button_frame.pack(fill=tk.X)
        
        create_button = ModernButton(button_frame, text="Create PIP", 
                                   command=lambda idx=index: self.create_monitor_pip(idx),
                                   style_type="primary")
        create_button.pack(fill=tk.X)
    
    def create_monitor_card(self, parent, monitor, index):
        """Create a modern monitor card (legacy method - kept for compatibility)"""
        card = ModernCard(parent, padding="25")
        card.pack(fill=tk.X, pady=10, padx=5)
        
        # Card header
        header_frame = ttk.Frame(card.content_frame, style='ModernCard.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Monitor icon and title
        title_frame = ttk.Frame(header_frame, style='ModernCard.TFrame')
        title_frame.pack(side=tk.LEFT, anchor=tk.W)
        
        title_text = f"🖥️ Monitor {index + 1}"
        if monitor.is_primary:
            title_text += " (Primary)"
        
        title_label = ttk.Label(title_frame, text=title_text, style='CardTitle.TLabel')
        title_label.pack(anchor=tk.W)
        
        # Monitor specs
        specs_frame = ttk.Frame(card.content_frame, style='ModernCard.TFrame')
        specs_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Resolution
        resolution_label = ttk.Label(specs_frame, text=f"Resolution: {monitor.width}×{monitor.height}", 
                                    style='CardSubtitle.TLabel')
        resolution_label.pack(anchor=tk.W)
        
        # Position
        position_label = ttk.Label(specs_frame, text=f"Position: ({monitor.x}, {monitor.y})", 
                                 style='CardSubtitle.TLabel')
        position_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Aspect ratio
        aspect_ratio = round(monitor.width / monitor.height, 2)
        aspect_label = ttk.Label(specs_frame, text=f"Aspect Ratio: {aspect_ratio}:1", 
                               style='CardSubtitle.TLabel')
        aspect_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Action button
        button_frame = ttk.Frame(card.content_frame, style='ModernCard.TFrame')
        button_frame.pack(anchor=tk.W)
        
        create_button = ModernButton(button_frame, text="Create PIP", 
                                   command=lambda idx=index: self.create_monitor_pip(idx),
                                   style_type="primary")
        create_button.pack(side=tk.LEFT)
    
    def create_windows_tab(self):
        """Create windows tab with scrollable content"""
        windows_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(windows_frame, text="🪟 Windows")
        
        # Add padding frame
        padded_frame = ttk.Frame(windows_frame, style='Modern.TFrame')
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Section header
        header_frame = ttk.Frame(padded_frame, style='Modern.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text="Application Windows", style='SectionTitle.TLabel')
        title_label.pack(side=tk.LEFT, anchor=tk.W)
        
        refresh_button = ModernButton(header_frame, text="Refresh", 
                                    command=self.refresh_windows,
                                    style_type="secondary")
        refresh_button.pack(side=tk.RIGHT)
        
        subtitle_label = ttk.Label(padded_frame, text="Capture and display content from any application window",
                                 style='ModernText.TLabel', foreground=self.colors['text_secondary'])
        subtitle_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Create scrollable area
        scrollable_area = ModernScrollableFrame(padded_frame, style='Modern.TFrame')
        scrollable_area.pack(fill=tk.BOTH, expand=True)
        
        # Window list container
        self.windows_container = scrollable_area.scrollable_frame
        self.update_windows_list()
    
    def update_windows_list(self):
        """Update the windows list with current windows"""
        # Clear existing widgets
        for widget in self.windows_container.winfo_children():
            widget.destroy()
        
        if not self.windows:
            no_windows_label = ttk.Label(self.windows_container, 
                                       text="No windows found. Click 'Refresh' to update the list.",
                                       style='ModernText.TLabel',
                                       foreground=self.colors['text_muted'])
            no_windows_label.pack(pady=20)
            return
        
        # Create window cards
        for i, window in enumerate(self.windows):
            self.create_window_card(self.windows_container, window, i)
    
    def create_window_card(self, parent, window, index):
        """Create a modern window card"""
        card = ModernCard(parent, padding="25")
        card.pack(fill=tk.X, pady=8, padx=5)
        
        # Window title and details
        title_frame = ttk.Frame(card.content_frame, style='ModernCard.TFrame')
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Window icon and title
        window_title = window.get('title', 'Unknown Window')
        if len(window_title) > 60:
            window_title = window_title[:60] + "..."
        
        title_label = ttk.Label(title_frame, text=f"🪟 {window_title}", style='CardTitle.TLabel')
        title_label.pack(anchor=tk.W)
        
        # Preview image
        preview_frame = ttk.Frame(title_frame, style='ModernCard.TFrame')
        preview_frame.pack(anchor=tk.W, pady=(8, 0))
        
        try:
            # Capture preview screenshot
            preview_image = self.capture_window_preview(window)
            if preview_image:
                # Resize to thumbnail
                preview_image = preview_image.resize((120, 68), Image.Resampling.LANCZOS)
                preview_photo = ImageTk.PhotoImage(preview_image)
                
                preview_label = ttk.Label(preview_frame, image=preview_photo, style='CardTitle.TLabel')
                preview_label.image = preview_photo  # Keep a reference
                preview_label.pack()
            else:
                # Fallback placeholder
                ttk.Label(preview_frame, text="Preview unavailable", 
                         font=('Segoe UI', 8), style='CardSubtitle.TLabel').pack()
        except Exception as e:
            # Fallback placeholder
            ttk.Label(preview_frame, text="Preview unavailable", 
                     font=('Segoe UI', 8), style='CardSubtitle.TLabel').pack()
        
        # Window specs
        specs_frame = ttk.Frame(card.content_frame, style='ModernCard.TFrame')
        specs_frame.pack(fill=tk.X, pady=(0, 15))
        
        if 'bbox' in window:
            bbox = window['bbox']
            size_label = ttk.Label(specs_frame, text=f"Size: {bbox[2]}×{bbox[3]}", 
                                 style='CardSubtitle.TLabel')
            size_label.pack(anchor=tk.W)
            
            position_label = ttk.Label(specs_frame, text=f"Position: ({bbox[0]}, {bbox[1]})", 
                                     style='CardSubtitle.TLabel')
            position_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Action button
        button_frame = ttk.Frame(card.content_frame, style='ModernCard.TFrame')
        button_frame.pack(anchor=tk.W)
        
        create_button = ModernButton(button_frame, text="Create PIP", 
                                   command=lambda idx=index: self.create_window_pip(idx),
                                   style_type="primary")
        create_button.pack(side=tk.LEFT)
    
    def create_regions_tab(self):
        """Create regions tab with custom region definition"""
        regions_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(regions_frame, text="📐 Regions")
        
        # Add padding frame
        padded_frame = ttk.Frame(regions_frame, style='Modern.TFrame')
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Section title
        title_label = ttk.Label(padded_frame, text="Custom Screen Regions", style='SectionTitle.TLabel')
        title_label.pack(anchor=tk.W, pady=(0, 10))
        
        subtitle_label = ttk.Label(padded_frame, text="Define custom screen areas to capture",
                                 style='ModernText.TLabel', foreground=self.colors['text_secondary'])
        subtitle_label.pack(anchor=tk.W, pady=(0, 30))
        
        # Create input card
        input_card = ModernCard(padded_frame, padding="30")
        input_card.pack(fill=tk.X, pady=10)
        
        # Input grid
        input_grid = ttk.Frame(input_card.content_frame, style='ModernCard.TFrame')
        input_grid.pack(fill=tk.X)
        
        # X coordinate
        x_frame = ttk.Frame(input_grid, style='ModernCard.TFrame')
        x_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(x_frame, text="X Position", style='CardSubtitle.TLabel').pack(anchor=tk.W)
        self.region_x_entry = ttk.Entry(x_frame, width=10, style='Modern.TEntry')
        self.region_x_entry.pack(pady=(5, 0))
        self.region_x_entry.insert(0, "0")
        
        # Y coordinate
        y_frame = ttk.Frame(input_grid, style='ModernCard.TFrame')
        y_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(y_frame, text="Y Position", style='CardSubtitle.TLabel').pack(anchor=tk.W)
        self.region_y_entry = ttk.Entry(y_frame, width=10, style='Modern.TEntry')
        self.region_y_entry.pack(pady=(5, 0))
        self.region_y_entry.insert(0, "0")
        
        # Width
        width_frame = ttk.Frame(input_grid, style='ModernCard.TFrame')
        width_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(width_frame, text="Width", style='CardSubtitle.TLabel').pack(anchor=tk.W)
        self.region_width_entry = ttk.Entry(width_frame, width=10, style='Modern.TEntry')
        self.region_width_entry.pack(pady=(5, 0))
        self.region_width_entry.insert(0, "800")
        
        # Height
        height_frame = ttk.Frame(input_grid, style='ModernCard.TFrame')
        height_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(height_frame, text="Height", style='CardSubtitle.TLabel').pack(anchor=tk.W)
        self.region_height_entry = ttk.Entry(height_frame, width=10, style='Modern.TEntry')
        self.region_height_entry.pack(pady=(5, 0))
        self.region_height_entry.insert(0, "600")
        
        # Preview section
        preview_card = ModernCard(padded_frame, padding="30")
        preview_card.pack(fill=tk.X, pady=20)
        
        ttk.Label(preview_card.content_frame, text="📷 Region Preview", style='CardTitle.TLabel').pack(anchor=tk.W)
        
        # Preview image container
        self.region_preview_container = ttk.Frame(preview_card.content_frame, style='ModernCard.TFrame')
        self.region_preview_container.pack(anchor=tk.W, pady=(15, 0))
        
        # Preview button
        preview_button_frame = ttk.Frame(preview_card.content_frame, style='ModernCard.TFrame')
        preview_button_frame.pack(anchor=tk.W, pady=(15, 0))
        
        preview_button = ModernButton(preview_button_frame, text="Update Preview", 
                                    command=self.update_region_preview,
                                    style_type="secondary")
        preview_button.pack(side=tk.LEFT)
        
        # Create button
        button_frame = ttk.Frame(input_card.content_frame, style='ModernCard.TFrame')
        button_frame.pack(anchor=tk.W, pady=(20, 0))
        
        create_button = ModernButton(button_frame, text="Create Region PIP", 
                                   command=self.create_region_pip,
                                   style_type="primary")
        create_button.pack(side=tk.LEFT)
        
        # Visual selector section (temporarily hidden)
        # visual_card = ModernCard(padded_frame, padding="30")
        # visual_card.pack(fill=tk.X, pady=(20, 10))
        # 
        # # Visual selector header
        # visual_header = ttk.Frame(visual_card.content_frame, style='ModernCard.TFrame')
        # visual_header.pack(fill=tk.X, pady=(0, 15))
        # 
        # ttk.Label(visual_header, text="📹 Visual Selection", 
        #          font=('Segoe UI', 14, 'bold'), style='CardTitle.TLabel').pack(anchor=tk.W)
        # ttk.Label(visual_header, text="Use camera-style overlay to select screen area visually",
        #          style='CardSubtitle.TLabel').pack(anchor=tk.W, pady=(5, 0))
        # 
        # # Visual selector button
        # visual_button_frame = ttk.Frame(visual_card.content_frame, style='ModernCard.TFrame')
        # visual_button_frame.pack(anchor=tk.W)
        # 
        # visual_select_button = ModernButton(visual_button_frame, text="🎯 Select Area Visually", 
        #                                   command=self.start_visual_region_selection,
        #                                   style_type="success")
        # visual_select_button.pack(side=tk.LEFT)
        # 
        # # Instructions
        # instructions_frame = ttk.Frame(visual_card.content_frame, style='ModernCard.TFrame')
        # instructions_frame.pack(fill=tk.X, pady=(15, 0))
        # 
        # instructions = [
        #     "• Click 'Select Area Visually' to start camera-style selection",
        #     "• Drag to select your desired screen area",
        #     "• Live preview shows selected region size and position",
        #     "• Press Enter to confirm or Escape to cancel"
        # ]
        # 
        # for instruction in instructions:
        #     ttk.Label(instructions_frame, text=instruction, 
        #              style='CardSubtitle.TLabel').pack(anchor=tk.W, pady=1)
    
    def create_active_pips_tab(self):
        """Create active PIPs management tab"""
        active_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(active_frame, text="🎯 Active PIPs")
        
        # Add padding frame
        padded_frame = ttk.Frame(active_frame, style='Modern.TFrame')
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Section header
        header_frame = ttk.Frame(padded_frame, style='Modern.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text="Active PIP Windows", style='SectionTitle.TLabel')
        title_label.pack(side=tk.LEFT, anchor=tk.W)
        
        close_all_button = ModernButton(header_frame, text="Close All", 
                                      command=self.close_all_pips,
                                      style_type="danger")
        close_all_button.pack(side=tk.RIGHT)
        
        subtitle_label = ttk.Label(padded_frame, text="Manage all active picture-in-picture windows",
                                 style='ModernText.TLabel', foreground=self.colors['text_secondary'])
        subtitle_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Create scrollable area
        scrollable_area = ModernScrollableFrame(padded_frame, style='Modern.TFrame')
        scrollable_area.pack(fill=tk.BOTH, expand=True)
        
        # Active PIPs container
        self.active_pips_container = scrollable_area.scrollable_frame
        self.update_active_pips_list()
    
    def update_active_pips_list(self):
        """Update the active PIPs list"""
        # Clear existing widgets
        for widget in self.active_pips_container.winfo_children():
            widget.destroy()
        
        if not self.active_pips:
            no_pips_label = ttk.Label(self.active_pips_container, 
                                    text="No active PIPs. Create one from the other tabs.",
                                    style='ModernText.TLabel',
                                    foreground=self.colors['text_muted'])
            no_pips_label.pack(pady=20)
            return
        
        # Create PIP cards
        for i, pip in enumerate(self.active_pips):
            self.create_pip_card(self.active_pips_container, pip, i)
    
    def create_pip_card(self, parent, pip, index):
        """Create a card for an active PIP"""
        card = ModernCard(parent, padding="25")
        card.pack(fill=tk.X, pady=8, padx=5)
        
        # PIP title and details
        title_frame = ttk.Frame(card.content_frame, style='ModernCard.TFrame')
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        pip_title = pip.get_source_name()
        title_label = ttk.Label(title_frame, text=f"🎯 {pip_title}", style='CardTitle.TLabel')
        title_label.pack(anchor=tk.W)
        
        # PIP specs
        specs_frame = ttk.Frame(card.content_frame, style='ModernCard.TFrame')
        specs_frame.pack(fill=tk.X, pady=(0, 15))
        
        source_type_label = ttk.Label(specs_frame, text=f"Source: {pip.source_type.title()}", 
                                    style='CardSubtitle.TLabel')
        source_type_label.pack(anchor=tk.W)
        
        if pip.window and pip.window.winfo_exists():
            size_text = f"Size: {pip.window.winfo_width()}×{pip.window.winfo_height()}"
            size_label = ttk.Label(specs_frame, text=size_text, style='CardSubtitle.TLabel')
            size_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Action button
        button_frame = ttk.Frame(card.content_frame, style='ModernCard.TFrame')
        button_frame.pack(anchor=tk.W)
        
        close_button = ModernButton(button_frame, text="Close PIP", 
                                  command=lambda p=pip: self.close_pip(p),
                                  style_type="danger")
        close_button.pack(side=tk.LEFT)
    
    def create_footer(self, parent):
        """Create footer with actions and info"""
        footer_frame = ttk.Frame(parent, style='Modern.TFrame')
        footer_frame.pack(fill=tk.X, pady=(30, 0))
        
        # Separator line
        separator = ttk.Frame(footer_frame, style='Modern.TFrame', height=1)
        separator.pack(fill=tk.X, pady=(0, 20))
        separator.configure(style='Modern.TFrame')
        
        # Footer content
        footer_content = ttk.Frame(footer_frame, style='Modern.TFrame')
        footer_content.pack(fill=tk.X)
        
        # Left side - Info
        info_frame = ttk.Frame(footer_content, style='Modern.TFrame')
        info_frame.pack(side=tk.LEFT, anchor=tk.W)
        
        info_text = "💡 Tip: PIPs stay on top, can be moved by dragging, and resized by dragging edges/corners"
        info_label = ttk.Label(info_frame, text=info_text, style='ModernText.TLabel',
                             foreground=self.colors['text_secondary'])
        info_label.pack(anchor=tk.W)
        
        # Right side - Actions
        actions_frame = ttk.Frame(footer_content, style='Modern.TFrame')
        actions_frame.pack(side=tk.RIGHT, anchor=tk.E)
        
        refresh_button = ModernButton(actions_frame, text="Refresh All", 
                                    command=self.refresh_all_sources,
                                    style_type="secondary")
        refresh_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Add minimize to tray button if tray is available
        if TRAY_AVAILABLE:
            minimize_button = ModernButton(actions_frame, text="Minimize to Tray", 
                                         command=self.hide_window,
                                         style_type="secondary")
            minimize_button.pack(side=tk.RIGHT, padx=(10, 0))
    
    def capture_monitor_preview(self, monitor_index):
        """Capture a preview screenshot of a monitor"""
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                if monitor_index < len(monitors) - 1:
                    monitor = monitors[monitor_index + 1]
                    screenshot = sct.grab(monitor)
                    return Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        except Exception as e:
            print(f"Error capturing monitor preview: {e}")
        return None
    
    def capture_window_preview(self, window):
        """Capture a preview screenshot of a window using the same method as PIPs"""
        try:
            # Try direct window capture first (Windows only)
            if WINDOWS_CAPTURE_AVAILABLE and 'hwnd' in window:
                hwnd = window['hwnd']
                if hwnd and win32gui.IsWindow(hwnd):
                    # Get window dimensions
                    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                    width = right - left
                    height = bottom - top
                    
                    # Try to get client area for better capture
                    try:
                        client_rect = win32gui.GetClientRect(hwnd)
                        client_width = client_rect[2]
                        client_height = client_rect[3]
                        
                        if client_width > 100 and client_height > 100:
                            width = client_width
                            height = client_height
                    except:
                        pass
                    
                    # Skip if window is minimized or has no size
                    if width <= 0 or height <= 0:
                        return None
                    
                    # Try PrintWindow first
                    img = self.capture_with_print_window(hwnd, width, height)
                    if img:
                        return img
                    
                    # Fallback to BitBlt
                    img = self.capture_with_bitblt(hwnd, width, height)
                    if img:
                        return img
            
            # Fallback to region capture
            if 'bbox' in window:
                bbox = window['bbox']
                with mss.mss() as sct:
                    capture_bbox = {
                        'left': bbox[0],
                        'top': bbox[1],
                        'width': bbox[2],
                        'height': bbox[3]
                    }
                    screenshot = sct.grab(capture_bbox)
                    return Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                    
        except Exception as e:
            print(f"Error capturing window preview: {e}")
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
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
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
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            if result:
                # Convert to PIL Image
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
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
    
    def update_region_preview(self):
        """Update the region preview image"""
        try:
            # Clear previous preview
            for widget in self.region_preview_container.winfo_children():
                widget.destroy()
            
            # Get current region values
            x = int(self.region_x_entry.get())
            y = int(self.region_y_entry.get())
            width = int(self.region_width_entry.get())
            height = int(self.region_height_entry.get())
            
            # Capture region preview
            with mss.mss() as sct:
                bbox = {
                    'left': x,
                    'top': y,
                    'width': width,
                    'height': height
                }
                screenshot = sct.grab(bbox)
                preview_image = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                
                # Resize to thumbnail
                preview_image = preview_image.resize((200, 113), Image.Resampling.LANCZOS)
                preview_photo = ImageTk.PhotoImage(preview_image)
                
                preview_label = ttk.Label(self.region_preview_container, image=preview_photo, style='CardTitle.TLabel')
                preview_label.image = preview_photo  # Keep a reference
                preview_label.pack()
                
                # Add region info
                info_label = ttk.Label(self.region_preview_container, 
                                     text=f"Region: {width}×{height} at ({x}, {y})",
                                     font=('Segoe UI', 8), style='CardSubtitle.TLabel')
                info_label.pack(pady=(5, 0))
                
        except Exception as e:
            # Show error message
            error_label = ttk.Label(self.region_preview_container, 
                                  text=f"Preview error: {str(e)[:50]}...",
                                  font=('Segoe UI', 8), style='CardSubtitle.TLabel')
            error_label.pack()
    
    def create_monitor_pip(self, monitor_index):
        """Create a monitor PIP"""
        try:
            if monitor_index >= len(self.monitors):
                messagebox.showerror("Error", "Invalid monitor index")
                return
            
            source_data = {
                'index': monitor_index,
                'monitor': self.monitors[monitor_index]
            }
            
            pip_window = InfinitePIPWindow('monitor', source_data, self)
            self.active_pips.append(pip_window)
            self.update_status()
            self.update_active_pips_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create monitor PIP: {str(e)}")
    
    def create_window_pip(self, window_index):
        """Create a window PIP"""
        try:
            if window_index >= len(self.windows):
                messagebox.showerror("Error", "Invalid window index")
                return
            
            window_data = self.windows[window_index]
            pip_window = InfinitePIPWindow('window', window_data, self)
            self.active_pips.append(pip_window)
            self.update_status()
            self.update_active_pips_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create window PIP: {str(e)}")
    
    def create_region_pip(self):
        """Create a region PIP"""
        try:
            x = int(self.region_x_entry.get())
            y = int(self.region_y_entry.get())
            width = int(self.region_width_entry.get())
            height = int(self.region_height_entry.get())
            
            if width <= 0 or height <= 0:
                messagebox.showerror("Error", "Width and height must be positive")
                return
            
            source_data = {
                'x': x,
                'y': y,
                'width': width,
                'height': height
            }
            
            pip_window = InfinitePIPWindow('region', source_data, self)
            self.active_pips.append(pip_window)
            self.update_status()
            self.update_active_pips_list()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for all fields")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create region PIP: {str(e)}")
    
    def start_visual_region_selection(self):
        """Start visual region selection using camera-style overlay"""
        def on_selection_complete(result):
            if result:
                # Update the manual input fields with selected values
                self.region_x_entry.delete(0, tk.END)
                self.region_x_entry.insert(0, str(result['x']))
                
                self.region_y_entry.delete(0, tk.END)
                self.region_y_entry.insert(0, str(result['y']))
                
                self.region_width_entry.delete(0, tk.END)
                self.region_width_entry.insert(0, str(result['width']))
                
                self.region_height_entry.delete(0, tk.END)
                self.region_height_entry.insert(0, str(result['height']))
                
                # Show confirmation message
                messagebox.showinfo("Area Selected", 
                                  f"Selected area: {result['width']}×{result['height']} "
                                  f"at position ({result['x']}, {result['y']})\n\n"
                                  "Values have been filled in the form above. "
                                  "Click 'Create Region PIP' to create the PIP.")
                
                # Optionally auto-create the PIP
                auto_create = messagebox.askyesno("Auto Create", 
                                                "Would you like to create the PIP automatically?")
                if auto_create:
                    self.create_region_pip()
            else:
                messagebox.showinfo("Selection Cancelled", "Visual region selection was cancelled.")
        
        try:
            # Create and show the visual selector
            selector = ScreenAreaSelector(on_selection_complete)
            selector.select_area()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start visual selection: {str(e)}")
    
    def close_pip(self, pip):
        """Close a specific PIP"""
        try:
            pip.close()
            if pip in self.active_pips:
                self.active_pips.remove(pip)
            self.update_status()
            self.update_active_pips_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to close PIP: {str(e)}")
    
    def close_all_pips(self):
        """Close all active PIPs"""
        if not self.active_pips:
            messagebox.showinfo("No PIPs", "No active PIPs to close.")
            return
        
        for pip in self.active_pips[:]:
            try:
                pip.close()
            except:
                pass
        
        self.active_pips.clear()
        self.update_status()
        self.update_active_pips_list()
        messagebox.showinfo("PIPs Closed", "All PIPs have been closed.")
    
    def refresh_windows(self):
        """Refresh the windows list"""
        try:
            import pygetwindow as gw
            
            self.windows = []
            for window in gw.getAllWindows():
                if window.title and window.title.strip() and window.visible:
                    try:
                        bbox = (window.left, window.top, window.width, window.height)
                        window_data = {
                            'title': window.title,
                            'bbox': bbox
                        }
                        
                        # Add Windows-specific data if available
                        if WINDOWS_CAPTURE_AVAILABLE:
                            try:
                                hwnd = window._hWnd
                                if win32gui.IsWindow(hwnd):
                                    window_data['hwnd'] = hwnd
                            except:
                                pass
                        
                        self.windows.append(window_data)
                    except:
                        continue
            
            # Sort by title
            self.windows.sort(key=lambda x: x['title'].lower())
            
            # Update UI if windows tab is active
            if hasattr(self, 'windows_container'):
                self.update_windows_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh windows: {str(e)}")
    
    def refresh_all_sources(self):
        """Refresh all source lists"""
        try:
            # Refresh monitors
            self.monitors = list(screeninfo.get_monitors())
            
            # Refresh windows
            self.refresh_windows()
            
            messagebox.showinfo("Sources Refreshed", "All sources have been refreshed successfully.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh sources: {str(e)}")
    
    def update_status(self):
        """Update the status display"""
        pip_count = len(self.active_pips)
        if pip_count == 0:
            self.status_label.configure(text="● Ready", foreground=self.colors['accent_secondary'])
            self.pips_counter.configure(text="0 Active PIPs")
        else:
            self.status_label.configure(text="● Active", foreground=self.colors['accent_primary'])
            self.pips_counter.configure(text=f"{pip_count} Active PIP{'s' if pip_count != 1 else ''}")
    
    def remove_pip(self, pip_window):
        """Remove a PIP from the active list (called by PIP window on close)"""
        if pip_window in self.active_pips:
            self.active_pips.remove(pip_window)
            self.update_status()
            self.update_active_pips_list()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = InfinitePIPModernUI()
    app.run()


if __name__ == "__main__":
    main()