from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from ..deps import (
    Image,
    ImageDraw,
    ImageTk,
    TRAY_AVAILABLE,
    WINDOWS_CAPTURE_AVAILABLE,
    mss,
    pystray,
    screeninfo,
    win32con,
    win32gui,
    win32ui,
    windll,
)
from ..remote_control import RemoteControlServer
from .pip_window import InfinitePIPWindow
from .screen_selector import ScreenAreaSelector
from .widgets import ModernButton, ModernCard, ModernScrollableFrame


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
        self.style.theme_use("clam")

        # Modern color palette
        self.colors = {
            "bg_primary": "#0a0a0a",
            "bg_secondary": "#1a1a1a",
            "bg_card": "#1a1a1a",
            "bg_card_hover": "#2a2a2a",
            "bg_input": "#252525",
            "accent_primary": "#f97316",
            "accent_secondary": "#10b981",
            "accent_danger": "#ef4444",
            "text_primary": "#ffffff",
            "text_secondary": "#a1a1aa",
            "text_muted": "#666666",
            "border": "#333333",
            "shadow": "#00000040",
        }

        # Configure root window
        self.root.configure(bg=self.colors["bg_primary"])

        # Main frame styles
        self.style.configure("Modern.TFrame", background=self.colors["bg_primary"])
        self.style.configure(
            "ModernCard.TFrame",
            background=self.colors["bg_card"],
            relief="flat",
            borderwidth=1,
        )

        # Typography styles
        self.style.configure(
            "ModernTitle.TLabel",
            font=("Segoe UI", 32, "bold"),
            background=self.colors["bg_primary"],
            foreground=self.colors["text_primary"],
        )

        self.style.configure(
            "ModernSubtitle.TLabel",
            font=("Segoe UI", 16),
            background=self.colors["bg_primary"],
            foreground=self.colors["accent_primary"],
        )

        self.style.configure(
            "SectionTitle.TLabel",
            font=("Segoe UI", 18, "bold"),
            background=self.colors["bg_primary"],
            foreground=self.colors["text_primary"],
        )

        self.style.configure(
            "CardTitle.TLabel",
            font=("Segoe UI", 14, "bold"),
            background=self.colors["bg_card"],
            foreground=self.colors["text_primary"],
        )

        self.style.configure(
            "CardSubtitle.TLabel",
            font=("Segoe UI", 11),
            background=self.colors["bg_card"],
            foreground=self.colors["text_secondary"],
        )

        self.style.configure(
            "ModernText.TLabel",
            font=("Segoe UI", 10),
            background=self.colors["bg_primary"],
            foreground=self.colors["text_primary"],
        )

        # Button styles
        self.style.configure(
            "ModernPrimary.TButton",
            background=self.colors["accent_primary"],
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            relief="flat",
            padding=(20, 10),
        )

        self.style.map(
            "ModernPrimary.TButton",
            background=[("active", "#ea580c"), ("pressed", "#c2410c")],
        )

        self.style.configure(
            "ModernSecondary.TButton",
            background=self.colors["bg_card"],
            foreground=self.colors["text_primary"],
            font=("Segoe UI", 10),
            borderwidth=1,
            relief="flat",
            padding=(16, 8),
        )

        self.style.map(
            "ModernSecondary.TButton",
            background=[("active", self.colors["bg_card_hover"])],
        )

        self.style.configure(
            "ModernSuccess.TButton",
            background=self.colors["accent_secondary"],
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            relief="flat",
            padding=(16, 8),
        )

        self.style.configure(
            "ModernDanger.TButton",
            background=self.colors["accent_danger"],
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            relief="flat",
            padding=(16, 8),
        )

        # Notebook styles
        self.style.configure(
            "Modern.TNotebook", background=self.colors["bg_primary"], borderwidth=0
        )

        self.style.configure(
            "Modern.TNotebook.Tab",
            background=self.colors["bg_card"],
            foreground=self.colors["text_secondary"],
            padding=[16, 10],
            font=("Segoe UI", 10),
        )

        self.style.map(
            "Modern.TNotebook.Tab",
            background=[("selected", self.colors["accent_primary"])],
            foreground=[("selected", "white")],
            padding=[("selected", [30, 18])],
            font=[("selected", ("Segoe UI", 12, "bold"))],
        )

        # Entry styles
        self.style.configure(
            "Modern.TEntry",
            fieldbackground=self.colors["bg_input"],
            borderwidth=1,
            relief="flat",
            insertcolor=self.colors["text_primary"],
            foreground=self.colors["text_primary"],
        )

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
            pystray.MenuItem("Quit", self.quit_application),
        )

        # Create tray icon
        self.tray_icon = pystray.Icon(
            "InfinitePIP",
            icon_image,
            "InfinitePIP - Advanced Picture-in-Picture",
            menu,
        )

        # Start tray in a separate thread
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def create_tray_icon(self):
        """Create a custom tray icon"""
        # Create a simple icon with PIL
        width = 64
        height = 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Draw a modern PIP-style icon
        # Outer rectangle (main screen)
        draw.rectangle(
            [8, 8, width - 8, height - 8],
            fill="#f97316",
            outline="#ea580c",
            width=2,
        )

        # Inner rectangle (PIP window)
        pip_size = 20
        pip_x = width - pip_size - 12
        pip_y = height - pip_size - 12
        draw.rectangle(
            [pip_x, pip_y, pip_x + pip_size, pip_y + pip_size],
            fill="#10b981",
            outline="#059669",
            width=2,
        )

        # Add a small dot to indicate active state
        dot_size = 4
        draw.ellipse(
            [
                pip_x + pip_size - dot_size - 2,
                pip_y + 2,
                pip_x + pip_size - 2,
                pip_y + 2 + dot_size,
            ],
            fill="#ffffff",
        )

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
                "Click the tray icon to restore the window",
            )

    def toggle_window(self, icon=None, item=None):
        """Toggle window visibility"""
        if self.root.state() == "withdrawn":
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
            except Exception:
                pass

        # Stop tray icon
        if TRAY_AVAILABLE and self.tray_icon:
            self.tray_icon.stop()

        # Stop remote server
        if self.remote_server:
            try:
                self.remote_server.shutdown()
                self.remote_server.server_close()
            except Exception:
                pass

        # Close main window
        self.root.quit()
        self.root.destroy()

    def setup_remote_control(self):
        """Setup remote control server for external PIP creation"""
        try:
            # Start remote control server on a specific port
            self.remote_server = RemoteControlServer("localhost", 38474, self)

            # Start server in a separate thread
            self.remote_thread = threading.Thread(
                target=self.remote_server.serve_forever, daemon=True
            )
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
                    if window.get("hwnd") == window_data.get("hwnd"):
                        existing_window = window
                        break

                if not existing_window:
                    self.windows.append(window_data)
                    # Update windows list UI if it exists
                    if hasattr(self, "windows_container"):
                        self.update_windows_list()

                # Create the PIP
                pip_window = InfinitePIPWindow("window", window_data, self)
                self.active_pips.append(pip_window)
                self.update_status()
                self.update_active_pips_list()

                # Show window if it's hidden
                if self.root.state() == "withdrawn":
                    self.show_window()

                # Show notification
                if TRAY_AVAILABLE and self.tray_icon:
                    self.tray_icon.notify(
                        "InfinitePIP",
                        f"Created PIP for: {window_data.get('title', 'Unknown Window')}",
                    )

            except Exception as e:
                print(f"Error creating external PIP: {e}")
                # Show error notification
                if TRAY_AVAILABLE and self.tray_icon:
                    self.tray_icon.notify(
                        "InfinitePIP Error",
                        f"Could not create PIP: {str(e)}",
                    )

        # Schedule the PIP creation on the main thread
        self.root.after(0, create_pip)

    def setup_layout(self):
        """Setup the main layout with modern responsive design"""
        # Main container
        main_container = ttk.Frame(self.root, style="Modern.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

        # Header section
        self.create_header(main_container)

        # Content area with proper spacing
        content_frame = ttk.Frame(main_container, style="Modern.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(30, 0))

        # Create tabbed interface
        self.create_modern_tabs(content_frame)

        # Footer with actions
        self.create_footer(main_container)

    def create_header(self, parent):
        """Create modern header with title and status"""
        header_frame = ttk.Frame(parent, style="Modern.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 20))

        # Left side - Title and subtitle
        title_section = ttk.Frame(header_frame, style="Modern.TFrame")
        title_section.pack(side=tk.LEFT, anchor=tk.W)

        title_label = ttk.Label(
            title_section, text="InfinitePIP", style="ModernTitle.TLabel"
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(
            title_section,
            text="Advanced Picture-in-Picture for Desktop",
            style="ModernSubtitle.TLabel",
        )
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))

        # Right side - Status and info
        status_section = ttk.Frame(header_frame, style="Modern.TFrame")
        status_section.pack(side=tk.RIGHT, anchor=tk.E)

        # Active PIPs counter
        self.status_label = ttk.Label(
            status_section,
            text="● Ready",
            style="ModernText.TLabel",
            foreground=self.colors["accent_secondary"],
        )
        self.status_label.pack(anchor=tk.E)

        self.pips_counter = ttk.Label(
            status_section,
            text="0 Active PIPs",
            style="ModernText.TLabel",
            foreground=self.colors["text_secondary"],
        )
        self.pips_counter.pack(anchor=tk.E, pady=(5, 0))

    def create_modern_tabs(self, parent):
        """Create modern tabbed interface with proper scrolling"""
        # Create notebook
        self.notebook = ttk.Notebook(parent, style="Modern.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.create_monitors_tab()
        self.create_windows_tab()
        self.create_regions_tab()
        self.create_active_pips_tab()

    def create_monitors_tab(self):
        """Create monitors tab with scrollable content"""
        # Main frame for monitors
        monitors_frame = ttk.Frame(self.notebook, style="Modern.TFrame")
        self.notebook.add(monitors_frame, text="🖥️ Monitors")

        # Add padding frame
        padded_frame = ttk.Frame(monitors_frame, style="Modern.TFrame")
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Section title
        title_label = ttk.Label(
            padded_frame, text="Available Monitors", style="SectionTitle.TLabel"
        )
        title_label.pack(anchor=tk.W, pady=(0, 10))

        subtitle_label = ttk.Label(
            padded_frame,
            text="Create picture-in-picture windows from any connected monitor",
            style="ModernText.TLabel",
            foreground=self.colors["text_secondary"],
        )
        subtitle_label.pack(anchor=tk.W, pady=(0, 20))

        # Create scrollable area
        scrollable_area = ModernScrollableFrame(padded_frame, style="Modern.TFrame")
        scrollable_area.pack(fill=tk.BOTH, expand=True)

        # Create grid container
        grid_container = ttk.Frame(scrollable_area.scrollable_frame, style="Modern.TFrame")
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
        card_container = ttk.Frame(
            parent,
            style="ModernCard.TFrame",
            relief="flat",
            borderwidth=1,
            padding="15",
        )
        card_container.grid(row=row, column=col, padx=8, pady=8, sticky="ew")

        # Monitor icon and number (large)
        icon_frame = ttk.Frame(card_container, style="ModernCard.TFrame")
        icon_frame.pack(pady=(0, 10))

        # Large monitor icon
        icon_label = ttk.Label(
            icon_frame, text="🖥️", font=("Segoe UI", 32), style="CardTitle.TLabel"
        )
        icon_label.pack()

        # Preview image
        preview_frame = ttk.Frame(icon_frame, style="ModernCard.TFrame")
        preview_frame.pack(pady=(5, 0))

        try:
            # Capture preview screenshot
            preview_image = self.capture_monitor_preview(index)
            if preview_image:
                # Resize to thumbnail
                preview_image = preview_image.resize((120, 68), Image.Resampling.LANCZOS)
                preview_photo = ImageTk.PhotoImage(preview_image)

                preview_label = ttk.Label(
                    preview_frame, image=preview_photo, style="CardTitle.TLabel"
                )
                preview_label.image = preview_photo  # Keep a reference
                preview_label.pack()
            else:
                ttk.Label(
                    preview_frame,
                    text="Preview unavailable",
                    font=("Segoe UI", 8),
                    style="CardSubtitle.TLabel",
                ).pack()
        except Exception:
            ttk.Label(
                preview_frame,
                text="Preview unavailable",
                font=("Segoe UI", 8),
                style="CardSubtitle.TLabel",
            ).pack()

        # Monitor number
        monitor_num = index + 1
        num_text = f"Monitor {monitor_num}"
        if monitor.is_primary:
            num_text += " (Primary)"

        num_label = ttk.Label(
            icon_frame,
            text=num_text,
            font=("Segoe UI", 12, "bold"),
            style="CardTitle.TLabel",
        )
        num_label.pack(pady=(5, 0))

        # Monitor specs (compact)
        specs_frame = ttk.Frame(card_container, style="ModernCard.TFrame")
        specs_frame.pack(pady=(0, 10))

        # Resolution (main info)
        resolution_label = ttk.Label(
            specs_frame,
            text=f"{monitor.width}×{monitor.height}",
            font=("Segoe UI", 11, "bold"),
            style="CardSubtitle.TLabel",
        )
        resolution_label.pack()

        # Aspect ratio
        aspect_ratio = round(monitor.width / monitor.height, 2)
        aspect_label = ttk.Label(
            specs_frame, text=f"{aspect_ratio}:1", style="CardSubtitle.TLabel"
        )
        aspect_label.pack()

        # Position (smaller)
        position_label = ttk.Label(
            specs_frame,
            text=f"({monitor.x}, {monitor.y})",
            font=("Segoe UI", 9),
            style="CardSubtitle.TLabel",
        )
        position_label.pack(pady=(2, 0))

        # Action button (full width)
        button_frame = ttk.Frame(card_container, style="ModernCard.TFrame")
        button_frame.pack(fill=tk.X)

        create_button = ModernButton(
            button_frame,
            text="Create PIP",
            command=lambda idx=index: self.create_monitor_pip(idx),
            style_type="primary",
        )
        create_button.pack(fill=tk.X)

    def create_windows_tab(self):
        """Create windows tab with scrollable content"""
        windows_frame = ttk.Frame(self.notebook, style="Modern.TFrame")
        self.notebook.add(windows_frame, text="🪟 Windows")

        # Add padding frame
        padded_frame = ttk.Frame(windows_frame, style="Modern.TFrame")
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Section header
        header_frame = ttk.Frame(padded_frame, style="Modern.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = ttk.Label(
            header_frame, text="Application Windows", style="SectionTitle.TLabel"
        )
        title_label.pack(side=tk.LEFT, anchor=tk.W)

        refresh_button = ModernButton(
            header_frame, text="Refresh", command=self.refresh_windows, style_type="secondary"
        )
        refresh_button.pack(side=tk.RIGHT)

        subtitle_label = ttk.Label(
            padded_frame,
            text="Capture and display content from any application window",
            style="ModernText.TLabel",
            foreground=self.colors["text_secondary"],
        )
        subtitle_label.pack(anchor=tk.W, pady=(0, 20))

        # Create scrollable area
        scrollable_area = ModernScrollableFrame(padded_frame, style="Modern.TFrame")
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
            no_windows_label = ttk.Label(
                self.windows_container,
                text="No windows found. Click 'Refresh' to update the list.",
                style="ModernText.TLabel",
                foreground=self.colors["text_muted"],
            )
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
        title_frame = ttk.Frame(card.content_frame, style="ModernCard.TFrame")
        title_frame.pack(fill=tk.X, pady=(0, 15))

        # Window icon and title
        window_title = window.get("title", "Unknown Window")
        if len(window_title) > 60:
            window_title = window_title[:60] + "..."

        title_label = ttk.Label(
            title_frame, text=f"🪟 {window_title}", style="CardTitle.TLabel"
        )
        title_label.pack(anchor=tk.W)

        # Preview image
        preview_frame = ttk.Frame(title_frame, style="ModernCard.TFrame")
        preview_frame.pack(anchor=tk.W, pady=(8, 0))

        try:
            # Capture preview screenshot
            preview_image = self.capture_window_preview(window)
            if preview_image:
                # Resize to thumbnail
                preview_image = preview_image.resize((120, 68), Image.Resampling.LANCZOS)
                preview_photo = ImageTk.PhotoImage(preview_image)

                preview_label = ttk.Label(
                    preview_frame, image=preview_photo, style="CardTitle.TLabel"
                )
                preview_label.image = preview_photo  # Keep a reference
                preview_label.pack()
            else:
                ttk.Label(
                    preview_frame,
                    text="Preview unavailable",
                    font=("Segoe UI", 8),
                    style="CardSubtitle.TLabel",
                ).pack()
        except Exception:
            ttk.Label(
                preview_frame,
                text="Preview unavailable",
                font=("Segoe UI", 8),
                style="CardSubtitle.TLabel",
            ).pack()

        # Window specs
        specs_frame = ttk.Frame(card.content_frame, style="ModernCard.TFrame")
        specs_frame.pack(fill=tk.X, pady=(0, 15))

        if "bbox" in window:
            bbox = window["bbox"]
            size_label = ttk.Label(
                specs_frame, text=f"Size: {bbox[2]}×{bbox[3]}", style="CardSubtitle.TLabel"
            )
            size_label.pack(anchor=tk.W)

            position_label = ttk.Label(
                specs_frame,
                text=f"Position: ({bbox[0]}, {bbox[1]})",
                style="CardSubtitle.TLabel",
            )
            position_label.pack(anchor=tk.W, pady=(2, 0))

        # Action button
        button_frame = ttk.Frame(card.content_frame, style="ModernCard.TFrame")
        button_frame.pack(anchor=tk.W)

        create_button = ModernButton(
            button_frame,
            text="Create PIP",
            command=lambda idx=index: self.create_window_pip(idx),
            style_type="primary",
        )
        create_button.pack(side=tk.LEFT)

    def create_regions_tab(self):
        """Create regions tab with custom region definition"""
        regions_frame = ttk.Frame(self.notebook, style="Modern.TFrame")
        self.notebook.add(regions_frame, text="📐 Regions")

        # Add padding frame
        padded_frame = ttk.Frame(regions_frame, style="Modern.TFrame")
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Section title
        title_label = ttk.Label(
            padded_frame, text="Custom Screen Regions", style="SectionTitle.TLabel"
        )
        title_label.pack(anchor=tk.W, pady=(0, 10))

        subtitle_label = ttk.Label(
            padded_frame,
            text="Define custom screen areas to capture",
            style="ModernText.TLabel",
            foreground=self.colors["text_secondary"],
        )
        subtitle_label.pack(anchor=tk.W, pady=(0, 30))

        # Create input card
        input_card = ModernCard(padded_frame, padding="30")
        input_card.pack(fill=tk.X, pady=10)

        # Input grid
        input_grid = ttk.Frame(input_card.content_frame, style="ModernCard.TFrame")
        input_grid.pack(fill=tk.X)

        # X coordinate
        x_frame = ttk.Frame(input_grid, style="ModernCard.TFrame")
        x_frame.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(x_frame, text="X Position", style="CardSubtitle.TLabel").pack(anchor=tk.W)
        self.region_x_entry = ttk.Entry(x_frame, width=10, style="Modern.TEntry")
        self.region_x_entry.pack(pady=(5, 0))
        self.region_x_entry.insert(0, "0")

        # Y coordinate
        y_frame = ttk.Frame(input_grid, style="ModernCard.TFrame")
        y_frame.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(y_frame, text="Y Position", style="CardSubtitle.TLabel").pack(anchor=tk.W)
        self.region_y_entry = ttk.Entry(y_frame, width=10, style="Modern.TEntry")
        self.region_y_entry.pack(pady=(5, 0))
        self.region_y_entry.insert(0, "0")

        # Width
        width_frame = ttk.Frame(input_grid, style="ModernCard.TFrame")
        width_frame.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(width_frame, text="Width", style="CardSubtitle.TLabel").pack(anchor=tk.W)
        self.region_width_entry = ttk.Entry(width_frame, width=10, style="Modern.TEntry")
        self.region_width_entry.pack(pady=(5, 0))
        self.region_width_entry.insert(0, "800")

        # Height
        height_frame = ttk.Frame(input_grid, style="ModernCard.TFrame")
        height_frame.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(height_frame, text="Height", style="CardSubtitle.TLabel").pack(anchor=tk.W)
        self.region_height_entry = ttk.Entry(height_frame, width=10, style="Modern.TEntry")
        self.region_height_entry.pack(pady=(5, 0))
        self.region_height_entry.insert(0, "600")

        # Preview section
        preview_card = ModernCard(padded_frame, padding="30")
        preview_card.pack(fill=tk.X, pady=20)

        ttk.Label(
            preview_card.content_frame, text="📷 Region Preview", style="CardTitle.TLabel"
        ).pack(anchor=tk.W)

        # Preview image container
        self.region_preview_container = ttk.Frame(
            preview_card.content_frame, style="ModernCard.TFrame"
        )
        self.region_preview_container.pack(anchor=tk.W, pady=(15, 0))

        # Preview button
        preview_button_frame = ttk.Frame(preview_card.content_frame, style="ModernCard.TFrame")
        preview_button_frame.pack(anchor=tk.W, pady=(15, 0))

        preview_button = ModernButton(
            preview_button_frame,
            text="Update Preview",
            command=self.update_region_preview,
            style_type="secondary",
        )
        preview_button.pack(side=tk.LEFT)

        # Create button
        button_frame = ttk.Frame(input_card.content_frame, style="ModernCard.TFrame")
        button_frame.pack(anchor=tk.W, pady=(20, 0))

        create_button = ModernButton(
            button_frame, text="Create Region PIP", command=self.create_region_pip, style_type="primary"
        )
        create_button.pack(side=tk.LEFT)

    def create_active_pips_tab(self):
        """Create active PIPs management tab"""
        active_frame = ttk.Frame(self.notebook, style="Modern.TFrame")
        self.notebook.add(active_frame, text="🎯 Active PIPs")

        # Add padding frame
        padded_frame = ttk.Frame(active_frame, style="Modern.TFrame")
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Section header
        header_frame = ttk.Frame(padded_frame, style="Modern.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = ttk.Label(
            header_frame, text="Active PIP Windows", style="SectionTitle.TLabel"
        )
        title_label.pack(side=tk.LEFT, anchor=tk.W)

        close_all_button = ModernButton(
            header_frame, text="Close All", command=self.close_all_pips, style_type="danger"
        )
        close_all_button.pack(side=tk.RIGHT)

        subtitle_label = ttk.Label(
            padded_frame,
            text="Manage all active picture-in-picture windows",
            style="ModernText.TLabel",
            foreground=self.colors["text_secondary"],
        )
        subtitle_label.pack(anchor=tk.W, pady=(0, 20))

        # Create scrollable area
        scrollable_area = ModernScrollableFrame(padded_frame, style="Modern.TFrame")
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
            no_pips_label = ttk.Label(
                self.active_pips_container,
                text="No active PIPs. Create one from the other tabs.",
                style="ModernText.TLabel",
                foreground=self.colors["text_muted"],
            )
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
        title_frame = ttk.Frame(card.content_frame, style="ModernCard.TFrame")
        title_frame.pack(fill=tk.X, pady=(0, 15))

        pip_title = pip.get_source_name()
        title_label = ttk.Label(title_frame, text=f"🎯 {pip_title}", style="CardTitle.TLabel")
        title_label.pack(anchor=tk.W)

        # PIP specs
        specs_frame = ttk.Frame(card.content_frame, style="ModernCard.TFrame")
        specs_frame.pack(fill=tk.X, pady=(0, 15))

        source_type_label = ttk.Label(
            specs_frame, text=f"Source: {pip.source_type.title()}", style="CardSubtitle.TLabel"
        )
        source_type_label.pack(anchor=tk.W)

        if pip.window and pip.window.winfo_exists():
            size_text = f"Size: {pip.window.winfo_width()}×{pip.window.winfo_height()}"
            size_label = ttk.Label(specs_frame, text=size_text, style="CardSubtitle.TLabel")
            size_label.pack(anchor=tk.W, pady=(2, 0))

        # Action button
        button_frame = ttk.Frame(card.content_frame, style="ModernCard.TFrame")
        button_frame.pack(anchor=tk.W)

        close_button = ModernButton(
            button_frame, text="Close PIP", command=lambda p=pip: self.close_pip(p), style_type="danger"
        )
        close_button.pack(side=tk.LEFT)

    def create_footer(self, parent):
        """Create footer with actions and info"""
        footer_frame = ttk.Frame(parent, style="Modern.TFrame")
        footer_frame.pack(fill=tk.X, pady=(30, 0))

        # Separator line
        separator = ttk.Frame(footer_frame, style="Modern.TFrame", height=1)
        separator.pack(fill=tk.X, pady=(0, 20))
        separator.configure(style="Modern.TFrame")

        # Footer content
        footer_content = ttk.Frame(footer_frame, style="Modern.TFrame")
        footer_content.pack(fill=tk.X)

        # Left side - Info
        info_frame = ttk.Frame(footer_content, style="Modern.TFrame")
        info_frame.pack(side=tk.LEFT, anchor=tk.W)

        info_text = "💡 Tip: PIPs stay on top, can be moved by dragging, and resized by dragging edges/corners"
        info_label = ttk.Label(
            info_frame,
            text=info_text,
            style="ModernText.TLabel",
            foreground=self.colors["text_secondary"],
        )
        info_label.pack(anchor=tk.W)

        # Right side - Actions
        actions_frame = ttk.Frame(footer_content, style="Modern.TFrame")
        actions_frame.pack(side=tk.RIGHT, anchor=tk.E)

        refresh_button = ModernButton(
            actions_frame, text="Refresh All", command=self.refresh_all_sources, style_type="secondary"
        )
        refresh_button.pack(side=tk.RIGHT, padx=(10, 0))

        # Add minimize to tray button if tray is available
        if TRAY_AVAILABLE:
            minimize_button = ModernButton(
                actions_frame,
                text="Minimize to Tray",
                command=self.hide_window,
                style_type="secondary",
            )
            minimize_button.pack(side=tk.RIGHT, padx=(10, 0))

    def capture_monitor_preview(self, monitor_index):
        """Capture a preview screenshot of a monitor"""
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                if monitor_index < len(monitors) - 1:
                    monitor = monitors[monitor_index + 1]
                    screenshot = sct.grab(monitor)
                    return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        except Exception as e:
            print(f"Error capturing monitor preview: {e}")
        return None

    def capture_window_preview(self, window):
        """Capture a preview screenshot of a window using the same method as PIPs"""
        try:
            # Try direct window capture first (Windows only)
            if WINDOWS_CAPTURE_AVAILABLE and "hwnd" in window:
                hwnd = window["hwnd"]
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
                    except Exception:
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
            if "bbox" in window:
                bbox = window["bbox"]
                with mss.mss() as sct:
                    capture_bbox = {
                        "left": bbox[0],
                        "top": bbox[1],
                        "width": bbox[2],
                        "height": bbox[3],
                    }
                    screenshot = sct.grab(capture_bbox)
                    return Image.frombytes("RGB", screenshot.size, screenshot.rgb)

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
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

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
                bbox = {"left": x, "top": y, "width": width, "height": height}
                screenshot = sct.grab(bbox)
                preview_image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

                # Resize to thumbnail
                preview_image = preview_image.resize((200, 113), Image.Resampling.LANCZOS)
                preview_photo = ImageTk.PhotoImage(preview_image)

                preview_label = ttk.Label(
                    self.region_preview_container, image=preview_photo, style="CardTitle.TLabel"
                )
                preview_label.image = preview_photo  # Keep a reference
                preview_label.pack()

                # Add region info
                info_label = ttk.Label(
                    self.region_preview_container,
                    text=f"Region: {width}×{height} at ({x}, {y})",
                    font=("Segoe UI", 8),
                    style="CardSubtitle.TLabel",
                )
                info_label.pack(pady=(5, 0))

        except Exception as e:
            error_label = ttk.Label(
                self.region_preview_container,
                text=f"Preview error: {str(e)[:50]}...",
                font=("Segoe UI", 8),
                style="CardSubtitle.TLabel",
            )
            error_label.pack()

    def create_monitor_pip(self, monitor_index):
        """Create a monitor PIP"""
        try:
            if monitor_index >= len(self.monitors):
                messagebox.showerror("Error", "Invalid monitor index")
                return

            source_data = {"index": monitor_index, "monitor": self.monitors[monitor_index]}

            pip_window = InfinitePIPWindow("monitor", source_data, self)
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
            pip_window = InfinitePIPWindow("window", window_data, self)
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

            source_data = {"x": x, "y": y, "width": width, "height": height}

            pip_window = InfinitePIPWindow("region", source_data, self)
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
                self.region_x_entry.insert(0, str(result["x"]))

                self.region_y_entry.delete(0, tk.END)
                self.region_y_entry.insert(0, str(result["y"]))

                self.region_width_entry.delete(0, tk.END)
                self.region_width_entry.insert(0, str(result["width"]))

                self.region_height_entry.delete(0, tk.END)
                self.region_height_entry.insert(0, str(result["height"]))

                messagebox.showinfo(
                    "Area Selected",
                    f"Selected area: {result['width']}×{result['height']} "
                    f"at position ({result['x']}, {result['y']})\n\n"
                    "Values have been filled in the form above. "
                    "Click 'Create Region PIP' to create the PIP.",
                )

                auto_create = messagebox.askyesno(
                    "Auto Create", "Would you like to create the PIP automatically?"
                )
                if auto_create:
                    self.create_region_pip()
            else:
                messagebox.showinfo(
                    "Selection Cancelled", "Visual region selection was cancelled."
                )

        try:
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
            except Exception:
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
                        window_data = {"title": window.title, "bbox": bbox}

                        # Add Windows-specific data if available
                        if WINDOWS_CAPTURE_AVAILABLE:
                            try:
                                hwnd = window._hWnd
                                if win32gui.IsWindow(hwnd):
                                    window_data["hwnd"] = hwnd
                            except Exception:
                                pass

                        self.windows.append(window_data)
                    except Exception:
                        continue

            # Sort by title
            self.windows.sort(key=lambda x: x["title"].lower())

            # Update UI if windows tab is active
            if hasattr(self, "windows_container"):
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

            messagebox.showinfo(
                "Sources Refreshed", "All sources have been refreshed successfully."
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh sources: {str(e)}")

    def update_status(self):
        """Update the status display"""
        pip_count = len(self.active_pips)
        if pip_count == 0:
            self.status_label.configure(
                text="● Ready", foreground=self.colors["accent_secondary"]
            )
            self.pips_counter.configure(text="0 Active PIPs")
        else:
            self.status_label.configure(
                text="● Active", foreground=self.colors["accent_primary"]
            )
            self.pips_counter.configure(
                text=f"{pip_count} Active PIP{'s' if pip_count != 1 else ''}"
            )

    def remove_pip(self, pip_window):
        """Remove a PIP from the active list (called by PIP window on close)"""
        if pip_window in self.active_pips:
            self.active_pips.remove(pip_window)
            self.update_status()
            self.update_active_pips_list()

    def run(self):
        """Start the application"""
        self.root.mainloop()


