from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ModernScrollableFrame(ttk.Frame):
    """A modern scrollable frame with smooth scrolling and proper sizing"""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Create canvas and scrollbar
        # NOTE: We intentionally use a tk.Canvas here (ttk has no canvas).
        # Theme/background is configured by caller via `configure_canvas(...)`.
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        # Create window in canvas
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack components
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind mousewheel scrolling
        self.bind_mousewheel()

        # Configure canvas window width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def configure_canvas(self, *, background: str) -> None:
        """Set canvas background to match the app theme."""
        try:
            self.canvas.configure(background=background)
        except Exception:
            pass

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

        self.canvas.bind("<Enter>", _bind_to_mousewheel)
        self.canvas.bind("<Leave>", _unbind_from_mousewheel)


class ModernCard(ttk.Frame):
    """A modern card component with hover effects and consistent styling"""

    def __init__(self, parent, title: str = "", subtitle: str = "", **kwargs):
        super().__init__(parent, **kwargs)

        self._base_style = "ModernCard.TFrame"
        self._hover_style = "ModernCardHover.TFrame"
        self.configure(style=self._base_style, padding="20")

        # Title
        if title:
            title_label = ttk.Label(self, text=title, style="CardTitle.TLabel")
            title_label.pack(anchor=tk.W, pady=(0, 5))

        # Subtitle
        if subtitle:
            subtitle_label = ttk.Label(self, text=subtitle, style="CardSubtitle.TLabel")
            subtitle_label.pack(anchor=tk.W, pady=(0, 10))

        # Content frame for additional widgets
        self.content_frame = ttk.Frame(self, style="ModernCard.TFrame")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Hover styling: apply to the whole card (and keep it active when hovering children).
        self._bind_hover_recursive(self)

    def _bind_hover_recursive(self, widget: tk.Misc) -> None:
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        for child in widget.winfo_children():
            self._bind_hover_recursive(child)

    def _on_enter(self, _event=None) -> None:
        try:
            self.configure(style=self._hover_style)
        except Exception:
            pass

    def _on_leave(self, _event=None) -> None:
        # Only un-hover if the pointer is outside the card bounds.
        try:
            x, y = self.winfo_pointerxy()
            if not (self.winfo_rootx() <= x <= self.winfo_rootx() + self.winfo_width() and
                    self.winfo_rooty() <= y <= self.winfo_rooty() + self.winfo_height()):
                self.configure(style=self._base_style)
        except Exception:
            try:
                self.configure(style=self._base_style)
            except Exception:
                pass


class ModernButton(ttk.Button):
    """A modern button with consistent styling"""

    def __init__(
        self,
        parent,
        text: str = "",
        command=None,
        style_type: str = "primary",
        **kwargs,
    ):
        style_map = {
            "primary": "ModernPrimary.TButton",
            "secondary": "ModernSecondary.TButton",
            "success": "ModernSuccess.TButton",
            "danger": "ModernDanger.TButton",
        }

        style = style_map.get(style_type, "ModernPrimary.TButton")
        super().__init__(parent, text=text, command=command, style=style, **kwargs)


