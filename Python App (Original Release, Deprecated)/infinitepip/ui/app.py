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

        # UI references used for responsive/conditional rendering
        self._close_all_button = None
        self._regions_cards_container = None
        self._regions_input_card = None
        self._regions_preview_card = None
        self._regions_layout_after_id = None
        self._regions_columns_current = None

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
            # Match TSX Tailwind palette closely
            "bg_primary": "#030712",  # gray-950
            "bg_secondary": "#111827",  # gray-900
            "bg_card": "#111827",  # gray-900
            "bg_card_hover": "#1f2937",  # gray-800
            "bg_input": "#1f2937",  # gray-800
            "accent_primary": "#f97316",  # orange-500
            "accent_primary_hover": "#ea580c",  # orange-600
            "accent_secondary": "#22c55e",  # green-500
            "accent_danger": "#dc2626",  # red-600
            "accent_danger_hover": "#b91c1c",  # red-700
            "text_primary": "#f9fafb",  # near-white
            "text_secondary": "#9ca3af",  # gray-400
            "text_muted": "#6b7280",  # gray-500
            "border": "#1f2937",  # gray-800
            "border_strong": "#374151",  # gray-700
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
        self.style.configure(
            "ModernCardHover.TFrame",
            background=self.colors["bg_card_hover"],
            relief="flat",
            borderwidth=1,
        )

        # Typography styles
        self.style.configure(
            "ModernTitle.TLabel",
            font=("Segoe UI", 32, "bold"),
            background=self.colors["bg_primary"],
            foreground=self.colors["accent_primary"],  # TSX title is orange
        )

        self.style.configure(
            "ModernSubtitle.TLabel",
            font=("Segoe UI", 16),
            background=self.colors["bg_primary"],
            foreground=self.colors["text_secondary"],
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
            background=[
                ("active", self.colors["accent_primary_hover"]),
                ("pressed", "#c2410c"),  # orange-700-ish
            ],
        )

        self.style.configure(
            "ModernSecondary.TButton",
            background=self.colors["bg_card_hover"],  # TSX secondary buttons are gray-800
            foreground=self.colors["text_primary"],
            font=("Segoe UI", 10),
            borderwidth=1,
            relief="flat",
            padding=(16, 8),
        )

        self.style.map(
            "ModernSecondary.TButton",
            background=[("active", "#374151")],  # gray-700 hover
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
        self.style.map(
            "ModernDanger.TButton",
            background=[("active", self.colors["accent_danger_hover"])],
        )

        # Notebook styles kept for any ttk internals (we use a custom tab bar)
        self.style.configure("Modern.TNotebook", background=self.colors["bg_primary"], borderwidth=0)
        self.style.configure("Modern.TNotebook.Tab", padding=[0, 0])

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

            # Use ASCII-only output for maximum Windows console compatibility.
            print("[InfinitePIP] Remote control server started on port 38474")

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
        # Root grid: header fixed, content grows, footer fixed
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        main_container = ttk.Frame(self.root, style="Modern.TFrame", padding=(0, 0))
        main_container.grid(row=0, column=0, sticky="nsew")
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(0, weight=1)

        # Header section
        self.create_header(main_container)

        # Content area (expands)
        content_frame = tk.Frame(main_container, bg=self.colors["bg_primary"])
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        self.create_modern_tabs(content_frame)

        # Footer with actions
        self.create_footer(main_container)

        # Keep text responsive on resize (wrap long labels)
        self.root.bind("<Configure>", self._on_root_resize, add="+")

    def create_header(self, parent):
        """Create modern header with title and status"""
        header_outer = tk.Frame(parent, bg=self.colors["bg_secondary"])
        header_outer.grid(row=0, column=0, sticky="ew")
        header_outer.grid_columnconfigure(0, weight=1)

        # Header content
        header_frame = tk.Frame(header_outer, bg=self.colors["bg_secondary"])
        header_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=16)
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)

        # Bottom border line (TSX: border-b border-gray-800)
        tk.Frame(header_outer, bg=self.colors["border"], height=1).grid(
            row=1, column=0, sticky="ew"
        )

        # Left side - Title and subtitle
        title_section = tk.Frame(header_frame, bg=self.colors["bg_secondary"])
        title_section.grid(row=0, column=0, sticky="w")

        # Icon + title (match TSX "🔥 InfinitePIP")
        title_row = tk.Frame(title_section, bg=self.colors["bg_secondary"])
        title_row.grid(row=0, column=0, sticky="w")

        icon_label = ttk.Label(
            title_row,
            text="🔥",
            font=("Segoe UI", 34),
            background=self.colors["bg_secondary"],
            foreground=self.colors["accent_primary"],
        )
        icon_label.grid(row=0, column=0, sticky="w", padx=(0, 12))

        title_label = ttk.Label(
            title_row, text="InfinitePIP", style="ModernTitle.TLabel"
        )
        title_label.grid(row=0, column=1, sticky="w")

        self._header_subtitle_label = ttk.Label(
            title_section,
            text="Advanced Picture-in-Picture for Desktop",
            style="ModernSubtitle.TLabel",
        )
        self._header_subtitle_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        # Right side - Status and info
        status_section = tk.Frame(header_frame, bg=self.colors["bg_secondary"])
        status_section.grid(row=0, column=1, sticky="e")

        # Status row: dot + label (TSX: small colored dot + text)
        status_row = tk.Frame(status_section, bg=self.colors["bg_secondary"])
        status_row.grid(row=0, column=0, sticky="e")

        self._status_dot = tk.Canvas(
            status_row,
            width=10,
            height=10,
            bg=self.colors["bg_secondary"],
            highlightthickness=0,
        )
        self._status_dot.grid(row=0, column=0, sticky="e", padx=(0, 8))
        self._status_dot_id = self._status_dot.create_oval(
            1, 1, 9, 9, fill=self.colors["accent_secondary"], outline=""
        )

        self.status_label = tk.Label(
            status_row,
            text="Ready",
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 10, "bold"),
        )
        self.status_label.grid(row=0, column=1, sticky="e")

        # Counter row: orange number + gray text (TSX: number orange-500)
        counter_row = tk.Frame(status_section, bg=self.colors["bg_secondary"])
        counter_row.grid(row=1, column=0, sticky="e", pady=(6, 0))

        self._pips_counter_number = tk.Label(
            counter_row,
            text="0",
            bg=self.colors["bg_secondary"],
            fg=self.colors["accent_primary"],
            font=("Segoe UI", 10, "bold"),
        )
        self._pips_counter_number.grid(row=0, column=0, sticky="e")

        self.pips_counter = tk.Label(
            counter_row,
            text=" Active PIPs",
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 10),
        )
        self.pips_counter.grid(row=0, column=1, sticky="e")

    def create_modern_tabs(self, parent):
        """Create TSX-style tab bar + content stack (custom, not ttk.Notebook)."""
        container = tk.Frame(parent, bg=self.colors["bg_primary"])
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Tab bar (TSX: bg-gray-900 with bottom border)
        tabbar_outer = tk.Frame(container, bg=self.colors["bg_secondary"])
        tabbar_outer.grid(row=0, column=0, sticky="ew")
        tabbar_outer.grid_columnconfigure(0, weight=1)

        tabbar = tk.Frame(tabbar_outer, bg=self.colors["bg_secondary"])
        tabbar.grid(row=0, column=0, sticky="ew", padx=24)

        tk.Frame(tabbar_outer, bg=self.colors["border"], height=1).grid(
            row=1, column=0, sticky="ew"
        )

        # Content stack
        self._tab_stack = tk.Frame(container, bg=self.colors["bg_primary"])
        self._tab_stack.grid(row=1, column=0, sticky="nsew")
        self._tab_stack.grid_rowconfigure(0, weight=1)
        self._tab_stack.grid_columnconfigure(0, weight=1)

        # Build tab pages
        self._tabs = {}
        self._tab_buttons = {}
        self._tab_underlines = {}

        self._tabs["monitors"] = self.create_monitors_tab(self._tab_stack)
        self._tabs["windows"] = self.create_windows_tab(self._tab_stack)
        self._tabs["regions"] = self.create_regions_tab(self._tab_stack)
        self._tabs["active"] = self.create_active_pips_tab(self._tab_stack)

        # Create tab buttons
        tab_defs = [
            ("monitors", "Monitors"),
            ("windows", "Windows"),
            ("regions", "Regions"),
            ("active", "Active PIPs"),
        ]

        for i, (tab_id, label) in enumerate(tab_defs):
            btn = tk.Label(
                tabbar,
                text=label,
                bg=self.colors["bg_secondary"],
                fg=self.colors["text_secondary"],
                font=("Segoe UI", 10),
                padx=18,
                pady=10,
                cursor="hand2",
            )
            btn.grid(row=0, column=i, sticky="w")
            btn.bind("<Button-1>", lambda _e, t=tab_id: self.show_tab(t), add="+")

            underline = tk.Frame(tabbar, bg=self.colors["bg_secondary"], height=2, width=1)
            underline.grid(row=1, column=i, sticky="ew")

            self._tab_buttons[tab_id] = btn
            self._tab_underlines[tab_id] = underline

        # Default tab
        self._active_tab = "monitors"
        self.show_tab(self._active_tab)

    def show_tab(self, tab_id: str) -> None:
        """Show a tab page and update the TSX-like tab styling."""
        if not hasattr(self, "_tabs") or tab_id not in self._tabs:
            return

        self._active_tab = tab_id

        # Raise content
        frame = self._tabs[tab_id]
        try:
            frame.tkraise()
        except Exception:
            pass

        # Update tab visuals
        for tid, btn in getattr(self, "_tab_buttons", {}).items():
            is_active = tid == tab_id
            try:
                btn.configure(
                    fg=self.colors["accent_primary"] if is_active else self.colors["text_secondary"],
                    font=("Segoe UI", 10, "bold") if is_active else ("Segoe UI", 10),
                )
            except Exception:
                pass
            ul = self._tab_underlines.get(tid)
            if ul is not None:
                try:
                    ul.configure(bg=self.colors["accent_primary"] if is_active else self.colors["bg_secondary"])
                except Exception:
                    pass

    def create_monitors_tab(self, parent):
        """Create monitors tab with scrollable content"""
        # Main frame for monitors
        monitors_frame = tk.Frame(parent, bg=self.colors["bg_primary"])
        monitors_frame.grid(row=0, column=0, sticky="nsew")
        monitors_frame.grid_rowconfigure(0, weight=1)
        monitors_frame.grid_columnconfigure(0, weight=1)

        # Add padding frame
        padded_frame = tk.Frame(monitors_frame, bg=self.colors["bg_primary"])
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        # Section title
        title_label = tk.Label(
            padded_frame,
            text="Available Monitors",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 18, "bold"),
        )
        title_label.pack(anchor=tk.W, pady=(0, 6))

        subtitle_label = tk.Label(
            padded_frame,
            text="Create picture-in-picture windows from any connected monitor",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 10),
        )
        subtitle_label.pack(anchor=tk.W, pady=(0, 18))

        # Create scrollable area
        scrollable_area = ModernScrollableFrame(padded_frame)
        scrollable_area.pack(fill=tk.BOTH, expand=True)
        scrollable_area.configure_canvas(background=self.colors["bg_primary"])
        try:
            scrollable_area.scrollable_frame.configure(style="Modern.TFrame")
        except Exception:
            pass

        # Create grid container
        grid_container = tk.Frame(scrollable_area.scrollable_frame, bg=self.colors["bg_primary"])
        grid_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Build cards once; grid them responsively based on available width.
        self._monitors_grid_container = grid_container
        self._monitor_cards = []
        self._monitor_columns_current = None
        self._monitor_layout_after_id = None

        for i, monitor in enumerate(self.monitors):
            card = self._create_monitor_card_widget(grid_container, monitor, i)
            self._monitor_cards.append(card)

        # Initial layout + responsive relayout on resize.
        self._layout_monitor_cards()
        scrollable_area.canvas.bind("<Configure>", self._schedule_layout_monitor_cards, add="+")
        grid_container.bind("<Configure>", self._schedule_layout_monitor_cards, add="+")

        return monitors_frame

    def _create_monitor_card_widget(self, parent, monitor, index):
        """Create a modern monitor card widget (positioned later by responsive grid)."""
        # Use ModernCard for exact Tailwind-like border behavior.
        card_container = ModernCard(
            parent,
            padding=16,
            bg=self.colors["bg_card"],
            border=self.colors["border"],
            border_hover=self.colors["accent_primary"],
        )

        # Monitor icon and number (large)
        icon_frame = tk.Frame(card_container.content_frame, bg=self.colors["bg_card"])
        icon_frame.pack(pady=(0, 10), fill=tk.X)

        # Large monitor icon
        icon_label = tk.Label(
            icon_frame,
            text="🖥️",
            font=("Segoe UI", 28),
            bg=self.colors["bg_card"],
            fg=self.colors["accent_primary"],
        )
        icon_label.pack()

        # Preview image
        preview_frame = tk.Frame(icon_frame, bg=self.colors["bg_card"])
        preview_frame.pack(pady=(5, 0))

        try:
            # Capture preview screenshot
            preview_image = self.capture_monitor_preview(index)
            if preview_image:
                # Resize to thumbnail
                preview_image = preview_image.resize((120, 68), Image.Resampling.LANCZOS)
                preview_photo = ImageTk.PhotoImage(preview_image)

                preview_label = tk.Label(preview_frame, image=preview_photo, bg=self.colors["bg_card"])
                preview_label.image = preview_photo  # Keep a reference
                preview_label.pack()
            else:
                tk.Label(
                    preview_frame,
                    text="Preview unavailable",
                    font=("Segoe UI", 8),
                    bg=self.colors["bg_card"],
                    fg=self.colors["text_muted"],
                ).pack()
        except Exception:
            tk.Label(
                preview_frame,
                text="Preview unavailable",
                font=("Segoe UI", 8),
                bg=self.colors["bg_card"],
                fg=self.colors["text_muted"],
            ).pack()

        # Monitor number
        monitor_num = index + 1
        num_text = f"Monitor {monitor_num}"
        if monitor.is_primary:
            num_text += " (Primary)"

        num_label = tk.Label(
            icon_frame,
            text=num_text,
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
        )
        num_label.pack(pady=(5, 0))

        # Monitor specs (compact)
        specs_frame = tk.Frame(card_container.content_frame, bg=self.colors["bg_card"])
        specs_frame.pack(pady=(0, 10), fill=tk.X)

        # Resolution (main info)
        resolution_label = tk.Label(
            specs_frame,
            text=f"Resolution: {monitor.width}×{monitor.height}",
            font=("Segoe UI", 10),
            bg=self.colors["bg_card"],
            fg=self.colors["text_secondary"],
        )
        resolution_label.pack()

        # Aspect ratio
        aspect_ratio = round(monitor.width / monitor.height, 2)
        aspect_label = tk.Label(
            specs_frame,
            text=f"Aspect Ratio: {aspect_ratio}:1",
            font=("Segoe UI", 10),
            bg=self.colors["bg_card"],
            fg=self.colors["text_secondary"],
        )
        aspect_label.pack()

        # Position (smaller)
        position_label = tk.Label(
            specs_frame,
            text=f"Position: ({monitor.x}, {monitor.y})",
            font=("Segoe UI", 10),
            bg=self.colors["bg_card"],
            fg=self.colors["text_secondary"],
        )
        position_label.pack(pady=(2, 0))

        # Action button (full width)
        button_frame = tk.Frame(card_container.content_frame, bg=self.colors["bg_card"])
        button_frame.pack(fill=tk.X)

        create_button = ModernButton(
            button_frame,
            text="Create PIP",
            command=lambda idx=index: self.create_monitor_pip(idx),
            style_type="primary",
        )
        create_button.pack(fill=tk.X)

        return card_container

    def _schedule_layout_monitor_cards(self, _event=None):
        """Debounce monitor card relayout (called on resize/configure events)."""
        try:
            if self._monitor_layout_after_id:
                self.root.after_cancel(self._monitor_layout_after_id)
        except Exception:
            pass
        self._monitor_layout_after_id = self.root.after(50, self._layout_monitor_cards)

    def _layout_monitor_cards(self):
        """Responsive grid: choose column count based on available width."""
        if not hasattr(self, "_monitors_grid_container"):
            return
        parent = self._monitors_grid_container
        width = parent.winfo_width()
        if width <= 1:
            return

        min_card_width = 300
        gap = 16
        columns = max(1, min(4, (width + gap) // (min_card_width + gap)))

        if columns != self._monitor_columns_current:
            # Reset column weights
            for c in range(0, 8):
                parent.grid_columnconfigure(c, weight=0)
            for c in range(columns):
                parent.grid_columnconfigure(c, weight=1, uniform="monitor")
            self._monitor_columns_current = columns

        # Grid cards
        for i, card in enumerate(getattr(self, "_monitor_cards", [])):
            row = i // columns
            col = i % columns
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)

    def create_windows_tab(self, parent):
        """Create windows tab with scrollable content"""
        windows_frame = tk.Frame(parent, bg=self.colors["bg_primary"])
        windows_frame.grid(row=0, column=0, sticky="nsew")
        windows_frame.grid_rowconfigure(0, weight=1)
        windows_frame.grid_columnconfigure(0, weight=1)

        # Add padding frame
        padded_frame = tk.Frame(windows_frame, bg=self.colors["bg_primary"])
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        # Section header
        header_frame = tk.Frame(padded_frame, bg=self.colors["bg_primary"])
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = tk.Label(
            header_frame,
            text="Application Windows",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 18, "bold"),
        )
        title_label.pack(side=tk.LEFT, anchor=tk.W)

        refresh_button = ModernButton(
            header_frame, text="Refresh", command=self.refresh_windows, style_type="secondary"
        )
        refresh_button.pack(side=tk.RIGHT)

        subtitle_label = tk.Label(
            padded_frame,
            text="Capture and display content from any application window",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 10),
        )
        subtitle_label.pack(anchor=tk.W, pady=(0, 20))

        # Create scrollable area
        scrollable_area = ModernScrollableFrame(padded_frame)
        scrollable_area.pack(fill=tk.BOTH, expand=True)
        scrollable_area.configure_canvas(background=self.colors["bg_primary"])

        # Window list container
        self.windows_container = scrollable_area.scrollable_frame
        self.update_windows_list()
        return windows_frame

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
        card = ModernCard(
            parent,
            padding=16,
            bg=self.colors["bg_card"],
            border=self.colors["border"],
            border_hover=self.colors["accent_primary"],
        )
        card.pack(fill=tk.X, pady=8, padx=5)

        # Window title and details
        title_frame = tk.Frame(card.content_frame, bg=self.colors["bg_card"])
        title_frame.pack(fill=tk.X, pady=(0, 15))

        # Window icon and title
        window_title = window.get("title", "Unknown Window")
        if len(window_title) > 60:
            window_title = window_title[:60] + "..."

        title_label = tk.Label(
            title_frame,
            text=f"{window_title}",
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 12, "bold"),
        )
        title_label.pack(anchor=tk.W)

        # Preview image
        preview_frame = tk.Frame(title_frame, bg=self.colors["bg_card"])
        preview_frame.pack(anchor=tk.W, pady=(8, 0))

        try:
            # Capture preview screenshot
            preview_image = self.capture_window_preview(window)
            if preview_image:
                # Resize to thumbnail
                preview_image = preview_image.resize((120, 68), Image.Resampling.LANCZOS)
                preview_photo = ImageTk.PhotoImage(preview_image)

                preview_label = tk.Label(preview_frame, image=preview_photo, bg=self.colors["bg_card"])
                preview_label.image = preview_photo  # Keep a reference
                preview_label.pack()
            else:
                tk.Label(
                    preview_frame,
                    text="Preview unavailable",
                    font=("Segoe UI", 8),
                    bg=self.colors["bg_card"],
                    fg=self.colors["text_muted"],
                ).pack()
        except Exception:
            tk.Label(
                preview_frame,
                text="Preview unavailable",
                font=("Segoe UI", 8),
                bg=self.colors["bg_card"],
                fg=self.colors["text_muted"],
            ).pack()

        # Window specs
        specs_frame = tk.Frame(card.content_frame, bg=self.colors["bg_card"])
        specs_frame.pack(fill=tk.X, pady=(0, 15))

        if "bbox" in window:
            bbox = window["bbox"]
            size_label = tk.Label(
                specs_frame,
                text=f"Size: {bbox[2]}×{bbox[3]} • Position: ({bbox[0]}, {bbox[1]})",
                bg=self.colors["bg_card"],
                fg=self.colors["text_secondary"],
                font=("Segoe UI", 10),
            )
            size_label.pack(anchor=tk.W)

        # Action button
        button_frame = tk.Frame(card.content_frame, bg=self.colors["bg_card"])
        button_frame.pack(anchor=tk.W)

        create_button = ModernButton(
            button_frame,
            text="Create PIP",
            command=lambda idx=index: self.create_window_pip(idx),
            style_type="primary",
        )
        create_button.pack(side=tk.LEFT)

    def create_regions_tab(self, parent):
        """Create regions tab with custom region definition"""
        regions_frame = tk.Frame(parent, bg=self.colors["bg_primary"])
        regions_frame.grid(row=0, column=0, sticky="nsew")
        regions_frame.grid_rowconfigure(0, weight=1)
        regions_frame.grid_columnconfigure(0, weight=1)

        # Add padding frame
        padded_frame = tk.Frame(regions_frame, bg=self.colors["bg_primary"])
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        # Section title
        title_label = tk.Label(
            padded_frame,
            text="Custom Screen Regions",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 18, "bold"),
        )
        title_label.pack(anchor=tk.W, pady=(0, 6))

        subtitle_label = tk.Label(
            padded_frame,
            text="Define custom screen areas to capture",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 10),
        )
        subtitle_label.pack(anchor=tk.W, pady=(0, 18))

        # Two-column layout (TSX: config + preview side-by-side on large screens)
        cards_container = tk.Frame(padded_frame, bg=self.colors["bg_primary"])
        cards_container.pack(fill=tk.BOTH, expand=True)
        cards_container.grid_columnconfigure(0, weight=1, uniform="regions")
        cards_container.grid_columnconfigure(1, weight=1, uniform="regions")

        self._regions_cards_container = cards_container

        # Create input card
        input_card = ModernCard(
            cards_container,
            padding=16,
            bg=self.colors["bg_card"],
            border=self.colors["border"],
            border_hover=self.colors["accent_primary"],
        )
        self._regions_input_card = input_card

        # Responsive input grid (reflows on narrow widths)
        self._region_fields_container = tk.Frame(input_card.content_frame, bg=self.colors["bg_card"])
        self._region_fields_container.pack(fill=tk.X)
        self._region_field_frames = []

        def _make_field(label: str, default: str):
            frame = tk.Frame(self._region_fields_container, bg=self.colors["bg_card"])
            tk.Label(
                frame,
                text=label,
                bg=self.colors["bg_card"],
                fg=self.colors["text_secondary"],
                font=("Segoe UI", 10),
            ).pack(anchor=tk.W)
            entry = ttk.Entry(frame, width=1, style="Modern.TEntry")
            entry.pack(fill=tk.X, expand=True, pady=(5, 0))
            entry.insert(0, default)
            return frame, entry

        x_frame, self.region_x_entry = _make_field("X Position", "0")
        y_frame, self.region_y_entry = _make_field("Y Position", "0")
        w_frame, self.region_width_entry = _make_field("Width", "800")
        h_frame, self.region_height_entry = _make_field("Height", "600")
        self._region_field_frames = [x_frame, y_frame, w_frame, h_frame]

        self._region_fields_columns_current = None
        self._layout_region_fields()
        self._region_fields_container.bind("<Configure>", self._schedule_layout_region_fields, add="+")

        # Preview section
        preview_card = ModernCard(
            cards_container,
            padding=16,
            bg=self.colors["bg_card"],
            border=self.colors["border"],
            border_hover=self.colors["accent_primary"],
        )
        self._regions_preview_card = preview_card

        tk.Label(
            preview_card.content_frame,
            text="📷 Region Preview",
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=tk.W)

        # Preview image container
        self.region_preview_container = tk.Frame(preview_card.content_frame, bg=self.colors["bg_card"])
        self.region_preview_container.pack(anchor=tk.W, pady=(15, 0))

        # Preview button
        preview_button_frame = tk.Frame(preview_card.content_frame, bg=self.colors["bg_card"])
        preview_button_frame.pack(anchor=tk.W, pady=(15, 0))

        preview_button = ModernButton(
            preview_button_frame,
            text="Update Preview",
            command=self.update_region_preview,
            style_type="secondary",
        )
        preview_button.pack(side=tk.LEFT)

        # Create button
        button_frame = tk.Frame(input_card.content_frame, bg=self.colors["bg_card"])
        button_frame.pack(anchor=tk.W, pady=(20, 0))

        create_button = ModernButton(
            button_frame, text="Create Region PIP", command=self.create_region_pip, style_type="primary"
        )
        create_button.pack(side=tk.LEFT)

        # Initial responsive placement + relayout on resize
        self._layout_regions_cards()
        cards_container.bind("<Configure>", self._schedule_layout_regions_cards, add="+")
        return regions_frame

    def create_active_pips_tab(self, parent):
        """Create active PIPs management tab"""
        active_frame = tk.Frame(parent, bg=self.colors["bg_primary"])
        active_frame.grid(row=0, column=0, sticky="nsew")
        active_frame.grid_rowconfigure(0, weight=1)
        active_frame.grid_columnconfigure(0, weight=1)

        # Add padding frame
        padded_frame = tk.Frame(active_frame, bg=self.colors["bg_primary"])
        padded_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        # Section header
        header_frame = tk.Frame(padded_frame, bg=self.colors["bg_primary"])
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = tk.Label(
            header_frame,
            text="Active PIP Windows",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 18, "bold"),
        )
        title_label.pack(side=tk.LEFT, anchor=tk.W)

        close_all_button = ModernButton(
            header_frame, text="Close All", command=self.close_all_pips, style_type="danger"
        )
        close_all_button.pack(side=tk.RIGHT)
        self._close_all_button = close_all_button

        subtitle_label = tk.Label(
            padded_frame,
            text="Manage all active picture-in-picture windows",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 10),
        )
        subtitle_label.pack(anchor=tk.W, pady=(0, 20))

        # Create scrollable area
        scrollable_area = ModernScrollableFrame(padded_frame)
        scrollable_area.pack(fill=tk.BOTH, expand=True)
        scrollable_area.configure_canvas(background=self.colors["bg_primary"])

        # Active PIPs container
        self.active_pips_container = scrollable_area.scrollable_frame
        self.update_active_pips_list()
        return active_frame

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
            self._update_close_all_visibility()
            return

        # Create PIP cards
        for i, pip in enumerate(self.active_pips):
            self.create_pip_card(self.active_pips_container, pip, i)

        self._update_close_all_visibility()

    def create_pip_card(self, parent, pip, index):
        """Create a card for an active PIP"""
        card = ModernCard(
            parent,
            padding=16,
            bg=self.colors["bg_card"],
            border=self.colors["border"],
            border_hover=self.colors["accent_primary"],
        )
        card.pack(fill=tk.X, pady=8, padx=5)

        # PIP title and details
        title_frame = tk.Frame(card.content_frame, bg=self.colors["bg_card"])
        title_frame.pack(fill=tk.X, pady=(0, 15))

        pip_title = pip.get_source_name()
        title_label = tk.Label(
            title_frame,
            text=pip_title,
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 12, "bold"),
        )
        title_label.pack(anchor=tk.W)

        # PIP specs
        specs_frame = tk.Frame(card.content_frame, bg=self.colors["bg_card"])
        specs_frame.pack(fill=tk.X, pady=(0, 15))

        source_type_label = tk.Label(
            specs_frame,
            text=f"Source Type: {pip.source_type}",
            bg=self.colors["bg_card"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 10),
        )
        source_type_label.pack(anchor=tk.W)

        if pip.window and pip.window.winfo_exists():
            size_text = f"Size: {pip.window.winfo_width()}×{pip.window.winfo_height()}"
            size_label = tk.Label(
                specs_frame,
                text=size_text,
                bg=self.colors["bg_card"],
                fg=self.colors["text_secondary"],
                font=("Segoe UI", 10),
            )
            size_label.pack(anchor=tk.W, pady=(2, 0))

        # Action button
        button_frame = tk.Frame(card.content_frame, bg=self.colors["bg_card"])
        button_frame.pack(anchor=tk.W)

        close_button = ModernButton(
            button_frame, text="Close PIP", command=lambda p=pip: self.close_pip(p), style_type="danger"
        )
        close_button.pack(side=tk.LEFT)

    def create_footer(self, parent):
        """Create footer with actions and info"""
        footer_outer = tk.Frame(parent, bg=self.colors["bg_secondary"])
        footer_outer.grid(row=2, column=0, sticky="ew")
        footer_outer.grid_columnconfigure(0, weight=1)

        # Top border line (TSX: border-t border-gray-800)
        tk.Frame(footer_outer, bg=self.colors["border"], height=1).grid(
            row=0, column=0, sticky="ew"
        )

        footer_content = tk.Frame(footer_outer, bg=self.colors["bg_secondary"])
        footer_content.grid(row=1, column=0, sticky="ew", padx=24, pady=14)
        footer_content.grid_columnconfigure(0, weight=1)
        footer_content.grid_columnconfigure(1, weight=0)

        # Left side - Info
        info_frame = tk.Frame(footer_content, bg=self.colors["bg_secondary"])
        info_frame.grid(row=0, column=0, sticky="w")

        info_text = "💡 PIPs stay on top, can be moved by dragging, and resized by dragging edges/corners"
        self._footer_info_label = tk.Label(
            info_frame,
            text=info_text,
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 9),
            justify="left",
            wraplength=1,
        )
        self._footer_info_label.grid(row=0, column=0, sticky="w")

        # Right side - Actions
        actions_frame = tk.Frame(footer_content, bg=self.colors["bg_secondary"])
        actions_frame.grid(row=0, column=1, sticky="e")

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

    def _on_root_resize(self, _event=None):
        """Keep long labels readable on resize (prevents clipping/overlap)."""
        try:
            w = max(1, self.root.winfo_width())
        except Exception:
            return

        # Header subtitle wraps sooner to avoid running into the status column.
        if hasattr(self, "_header_subtitle_label"):
            try:
                self._header_subtitle_label.configure(wraplength=max(300, int(w * 0.55)))
            except Exception:
                pass

        # Footer tip wraps based on available width.
        if hasattr(self, "_footer_info_label"):
            try:
                self._footer_info_label.configure(wraplength=max(380, int(w * 0.60)))
            except Exception:
                pass

    def _schedule_layout_region_fields(self, _event=None):
        try:
            if hasattr(self, "_region_fields_after_id") and self._region_fields_after_id:
                self.root.after_cancel(self._region_fields_after_id)
        except Exception:
            pass
        self._region_fields_after_id = self.root.after(50, self._layout_region_fields)

    def _layout_region_fields(self):
        """Responsive region input layout: 4 columns wide, 2 columns medium, 1 column narrow."""
        if not hasattr(self, "_region_fields_container"):
            return
        container = self._region_fields_container
        width = container.winfo_width()
        if width <= 1:
            # Not yet laid out; try later
            try:
                self.root.after(50, self._layout_region_fields)
            except Exception:
                pass
            return

        if width >= 760:
            cols = 4
        elif width >= 420:
            cols = 2
        else:
            cols = 1

        if cols != self._region_fields_columns_current:
            # Clear existing grid placements
            for f in self._region_field_frames:
                f.grid_forget()
            for c in range(0, 6):
                container.grid_columnconfigure(c, weight=0)
            for c in range(cols):
                container.grid_columnconfigure(c, weight=1, uniform="region_fields")

            for i, f in enumerate(self._region_field_frames):
                r = i // cols
                c = i % cols
                f.grid(row=r, column=c, sticky="ew", padx=(0 if c == 0 else 14, 0), pady=(0, 12))

            self._region_fields_columns_current = cols

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
            try:
                self._status_dot.itemconfig(self._status_dot_id, fill=self.colors["accent_secondary"])
            except Exception:
                pass
            try:
                self.status_label.configure(text="Ready")
            except Exception:
                pass
            try:
                self._pips_counter_number.configure(text="0")
                self.pips_counter.configure(text=" Active PIPs")
            except Exception:
                pass
        else:
            try:
                self._status_dot.itemconfig(self._status_dot_id, fill=self.colors["accent_primary"])
            except Exception:
                pass
            try:
                self.status_label.configure(text="Active")
            except Exception:
                pass
            try:
                self._pips_counter_number.configure(text=str(pip_count))
                self.pips_counter.configure(text=" Active PIPs")
            except Exception:
                pass
        self._update_close_all_visibility()

    def _update_close_all_visibility(self):
        """Show 'Close All' only when there are active PIPs (matches TSX behavior)."""
        try:
            if self._close_all_button is None:
                return
            if len(self.active_pips) > 0:
                if not self._close_all_button.winfo_ismapped():
                    self._close_all_button.pack(side=tk.RIGHT)
            else:
                if self._close_all_button.winfo_ismapped():
                    self._close_all_button.pack_forget()
        except Exception:
            # Never allow UI updates to crash the app
            pass

    def _schedule_layout_regions_cards(self, _event=None):
        """Debounce regions relayout (called on resize)."""
        try:
            if self._regions_layout_after_id:
                self.root.after_cancel(self._regions_layout_after_id)
        except Exception:
            pass
        self._regions_layout_after_id = self.root.after(50, self._layout_regions_cards)

    def _layout_regions_cards(self):
        """Responsive Regions layout: 2 columns when wide, 1 column when narrow."""
        if (
            self._regions_cards_container is None
            or self._regions_input_card is None
            or self._regions_preview_card is None
        ):
            return

        container = self._regions_cards_container
        width = container.winfo_width()
        if width <= 1:
            # Not yet laid out; try again shortly.
            try:
                self._schedule_layout_regions_cards()
            except Exception:
                pass
            return

        cols = 2 if width >= 900 else 1
        if cols == self._regions_columns_current:
            return

        # Clear existing grid placements
        self._regions_input_card.grid_forget()
        self._regions_preview_card.grid_forget()

        if cols == 2:
            container.grid_columnconfigure(0, weight=1, uniform="regions")
            container.grid_columnconfigure(1, weight=1, uniform="regions")
            self._regions_input_card.grid(
                row=0, column=0, sticky="nsew", padx=(0, 12), pady=10
            )
            self._regions_preview_card.grid(
                row=0, column=1, sticky="nsew", padx=(12, 0), pady=10
            )
        else:
            container.grid_columnconfigure(0, weight=1)
            container.grid_columnconfigure(1, weight=0)
            self._regions_input_card.grid(row=0, column=0, sticky="ew", pady=(0, 18))
            self._regions_preview_card.grid(row=1, column=0, sticky="ew")

        self._regions_columns_current = cols

    def remove_pip(self, pip_window):
        """Remove a PIP from the active list (called by PIP window on close)"""
        if pip_window in self.active_pips:
            self.active_pips.remove(pip_window)
            self.update_status()
            self.update_active_pips_list()

    def run(self):
        """Start the application"""
        self.root.mainloop()


