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


class ModernCard(tk.Frame):
    """A modern card component with border + hover border, closer to Tailwind styling.

    NOTE: We intentionally use `tk.Frame` instead of `ttk.Frame` here because Tk supports
    `highlightbackground` which lets us control border color precisely (ttk does not).
    """

    def __init__(
        self,
        parent,
        title: str = "",
        subtitle: str = "",
        *,
        padding: int | str = 20,
        bg: str = "#111827",  # Tailwind gray-900
        border: str = "#1f2937",  # Tailwind gray-800
        border_hover: str = "#f97316",  # Tailwind orange-500
        title_fg: str = "#ffffff",
        subtitle_fg: str = "#9ca3af",  # Tailwind gray-400
        **kwargs,
    ):
        super().__init__(parent, bg=bg, **kwargs)

        self._bg = bg
        self._border = border
        self._border_hover = border_hover

        # Border (use highlight* for precise color)
        self.configure(highlightthickness=1, highlightbackground=self._border, highlightcolor=self._border)

        pad = int(padding) if isinstance(padding, str) else padding

        # Title
        if title:
            title_label = tk.Label(
                self,
                text=title,
                bg=self._bg,
                fg=title_fg,
                font=("Segoe UI", 14, "bold"),
            )
            title_label.pack(anchor=tk.W, padx=pad, pady=(pad, 6))

        # Subtitle
        if subtitle:
            subtitle_label = tk.Label(
                self,
                text=subtitle,
                bg=self._bg,
                fg=subtitle_fg,
                font=("Segoe UI", 10),
                justify="left",
                wraplength=1,  # will be updated on resize
            )
            subtitle_label.pack(anchor=tk.W, padx=pad, pady=(0, 10))
            self._subtitle_label = subtitle_label
        else:
            self._subtitle_label = None

        # Content frame for additional widgets
        self.content_frame = tk.Frame(self, bg=self._bg)
        # If we rendered a title/subtitle, we already applied top padding.
        # Otherwise, apply padding around the content frame.
        if title or subtitle:
            self.content_frame.pack(fill=tk.BOTH, expand=True, padx=pad, pady=(0, pad))
        else:
            self.content_frame.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)

        # Hover styling: apply to the whole card (and keep it active when hovering children).
        self._bind_hover_recursive(self)

        # Keep subtitle wrap responsive
        self.bind("<Configure>", self._on_configure, add="+")

    def _bind_hover_recursive(self, widget: tk.Misc) -> None:
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        for child in widget.winfo_children():
            self._bind_hover_recursive(child)

    def _on_enter(self, _event=None) -> None:
        try:
            # TSX hover is orange border at 50% opacity; Tk doesn't do alpha on borders,
            # so we use solid orange which reads the closest.
            self.configure(highlightbackground=self._border_hover, highlightcolor=self._border_hover)
        except Exception:
            pass

    def _on_leave(self, _event=None) -> None:
        # Only un-hover if the pointer is outside the card bounds.
        try:
            x, y = self.winfo_pointerxy()
            if not (self.winfo_rootx() <= x <= self.winfo_rootx() + self.winfo_width() and
                    self.winfo_rooty() <= y <= self.winfo_rooty() + self.winfo_height()):
                self.configure(highlightbackground=self._border, highlightcolor=self._border)
        except Exception:
            try:
                self.configure(highlightbackground=self._border, highlightcolor=self._border)
            except Exception:
                pass

    def _on_configure(self, _event=None) -> None:
        """Update wrap length to match available width."""
        if not self._subtitle_label:
            return
        try:
            # Leave some room for padding; keep it readable at small sizes.
            w = max(200, self.winfo_width() - 60)
            self._subtitle_label.configure(wraplength=w)
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


