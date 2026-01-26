import tkinter as tk
from ttkbootstrap import ttk
from ui.styles import COLOR_CARD, COLOR_BORDER, COLOR_BG, COLOR_TEXT


class StatusBar(tk.Frame):
    """32px Statusbar mit Zeitstempel und Exit-Button."""

    def __init__(self, parent: tk.Widget, on_exit=None):
        super().__init__(parent, height=32, bg=COLOR_BG)
        self.pack_propagate(False)

        border = tk.Frame(self, bg=COLOR_BORDER)
        border.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inner = tk.Frame(border, bg=COLOR_CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        inner.grid_columnconfigure(0, weight=1)
        inner.grid_columnconfigure(1, weight=0)

        self.status_label = tk.Label(inner, text="Updated --:--:--", fg=COLOR_TEXT, bg=COLOR_CARD, font=("Segoe UI", 10))
        self.status_label.grid(row=0, column=0, sticky="w", padx=12)

        self.exit_btn = ttk.Button(inner, text="Exit", style="Card.TButton", command=on_exit, width=8)
        self.exit_btn.grid(row=0, column=1, sticky="e", padx=12, pady=4)

    def update_status(self, text: str):
        self.status_label.config(text=text)
