import tkinter as tk
from ui.styles import COLOR_ROOT, COLOR_BORDER, COLOR_CARD, COLOR_TEXT, emoji


class Card(tk.Frame):
    """Glasmorph-ähnlicher Card-Container mit Border und Innenbereich."""

    def __init__(self, parent: tk.Widget, padding: int = 16, *args, **kwargs):
        super().__init__(parent, bg=COLOR_ROOT, *args, **kwargs)

        self._pad = padding
        self._radius = 12
        self._border = COLOR_BORDER
        self._bg = COLOR_CARD

        self.canvas = tk.Canvas(self, bg=COLOR_ROOT, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.inner = tk.Frame(self.canvas, bg=COLOR_CARD)
        self.inner.pack_propagate(False)
        self.inner.configure(padx=padding, pady=padding)

        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_resize)

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _on_resize(self, event):
        w = max(1, event.width)
        h = max(1, event.height)
        r = min(self._radius, w // 2, h // 2)

        self.canvas.delete("card_bg")
        # Border
        self._round_rect(1, 1, w - 1, h - 1, r, fill=self._border, outline="", tags="card_bg")
        # Inner background
        self._round_rect(2, 2, w - 2, h - 2, max(0, r - 1), fill=self._bg, outline="", tags="card_bg")

        self.canvas.itemconfigure(self._window, width=w, height=h)

    def content(self) -> tk.Frame:
        """Gibt den inneren Container zurück."""
        return self.inner

    def add_title(self, text: str, icon: str | None = None) -> tk.Frame:
        header = tk.Frame(self.inner, bg=COLOR_CARD)
        header.pack(fill=tk.X, pady=(0, 8))

        if icon:
            icon_text = emoji(icon, "")
            if icon_text:
                tk.Label(header, text=icon_text, font=("Segoe UI", 16), bg=COLOR_CARD, fg=COLOR_TEXT).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            header,
            text=text,
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        ).pack(side=tk.LEFT)
        return header
