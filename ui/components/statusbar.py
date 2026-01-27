import tkinter as tk
from tkinter import ttk
from ui.styles import COLOR_CARD, COLOR_BORDER, COLOR_HEADER, COLOR_TEXT, COLOR_SUBTEXT
from ui.components.rounded import RoundedFrame


class StatusBar(tk.Frame):
    """32px Statusbar mit Zeitstempel, Fenster- und Exit-Button."""

    def __init__(self, parent: tk.Widget, on_exit=None, on_toggle_fullscreen=None):
        super().__init__(parent, height=32, bg=COLOR_HEADER)
        self.pack_propagate(False)

        rounded = RoundedFrame(self, bg=COLOR_CARD, border=COLOR_BORDER, radius=10, padding=0)
        rounded.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        inner = rounded.content()

        inner.grid_columnconfigure(0, weight=1)
        inner.grid_columnconfigure(1, weight=1)
        inner.grid_columnconfigure(2, weight=0)
        inner.grid_columnconfigure(3, weight=0)

        self.status_label = tk.Label(inner, text="Updated --:--:--", fg=COLOR_TEXT, bg=COLOR_CARD, font=("Segoe UI", 10))
        self.status_label.grid(row=0, column=0, sticky="w", padx=12)

        self.center_label = tk.Label(inner, text="", fg=COLOR_SUBTEXT, bg=COLOR_CARD, font=("Segoe UI", 10))
        self.center_label.grid(row=0, column=1, sticky="nsew")

        self.window_btn = ttk.Button(inner, text="Fenster", style="Card.TButton", command=on_toggle_fullscreen, width=7)
        self.window_btn.grid(row=0, column=2, sticky="e", padx=(4, 4), pady=2)

        self.exit_btn = ttk.Button(inner, text="Exit", style="Card.TButton", command=on_exit, width=7)
        self.exit_btn.grid(row=0, column=3, sticky="e", padx=(4, 8), pady=2)

    def update_status(self, text: str):
        self.status_label.config(text=text)

    def update_center(self, text: str):
        self.center_label.config(text=text)
