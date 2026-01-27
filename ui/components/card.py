import tkinter as tk
from ui.styles import COLOR_ROOT, COLOR_BORDER, COLOR_CARD, COLOR_TEXT, emoji


class Card(tk.Frame):
    """Glasmorph-ähnlicher Card-Container mit Border und Innenbereich."""

    def __init__(self, parent: tk.Widget, padding: int = 16, *args, **kwargs):
        super().__init__(parent, bg=COLOR_ROOT, *args, **kwargs)

        border = tk.Frame(self, bg=COLOR_BORDER)
        border.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.inner = tk.Frame(border, bg=COLOR_CARD)
        self.inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.inner.pack_propagate(False)

        self._pad = padding
        self.inner.configure(padx=padding, pady=padding)

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
