import tkinter as tk
from tkinter import ttk
from ui.styles import (
    COLOR_CARD,
    COLOR_HEADER,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    COLOR_PRIMARY,
    COLOR_BORDER,
    COLOR_WARNING,
)


class HeaderBar(tk.Frame):
    """80px Header mit Datum, Uhrzeit und Toggles."""

    def __init__(self, parent: tk.Widget, on_toggle_a=None, on_toggle_b=None):
        super().__init__(parent, height=80, bg=COLOR_HEADER)
        self.pack_propagate(False)

        # Border + inner card
        border = tk.Frame(self, bg=COLOR_BORDER)
        border.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inner = tk.Frame(border, bg=COLOR_CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        inner.grid_columnconfigure(0, weight=1, minsize=200, uniform="hdr")
        inner.grid_columnconfigure(1, weight=2, uniform="hdr")
        inner.grid_columnconfigure(2, weight=1, minsize=200, uniform="hdr")

        # Links: Datum
        left = tk.Frame(inner, bg=COLOR_CARD)
        left.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)
        self.date_label = tk.Label(left, text="--", font=("Segoe UI", 11, "bold"), fg=COLOR_TEXT, bg=COLOR_CARD)
        self.date_label.pack(anchor="w")
        self.weekday_label = tk.Label(left, text="", font=("Segoe UI", 10), fg=COLOR_SUBTEXT, bg=COLOR_CARD)
        self.weekday_label.pack(anchor="w", pady=(2, 0))

        # Mitte: Uhrzeit groß
        center = tk.Frame(inner, bg=COLOR_CARD)
        center.grid(row=0, column=1, sticky="nsew")
        self.clock_label = tk.Label(center, text="--:--", font=("Segoe UI", 36, "bold"), fg=COLOR_PRIMARY, bg=COLOR_CARD)
        self.clock_label.pack(expand=True, fill="both")

        # Rechts: Außentemp + Toggles
        right = tk.Frame(inner, bg=COLOR_CARD)
        right.grid(row=0, column=2, sticky="nsew", padx=16, pady=12)

        self.out_temp_label = tk.Label(right, text="-- °C", font=("Segoe UI", 16, "bold"), fg=COLOR_WARNING, bg=COLOR_CARD)
        self.out_temp_label.pack(anchor="e")
        tk.Label(right, text="Außen", font=("Segoe UI", 10), fg=COLOR_SUBTEXT, bg=COLOR_CARD).pack(anchor="e", pady=(2, 10))

        btn_row = tk.Frame(right, bg=COLOR_CARD)
        btn_row.pack(anchor="e")
        self.btn_a = ttk.Button(btn_row, text="An", style="Card.TButton", width=10, command=on_toggle_a)
        self.btn_a.pack(side=tk.LEFT, padx=4)
        self.btn_b = ttk.Button(btn_row, text="Aus", style="Card.TButton", width=10, command=on_toggle_b)
        self.btn_b.pack(side=tk.LEFT, padx=4)

    def update_header(self, date_text: str, weekday: str, time_text: str, out_temp: str):
        self.date_label.config(text=date_text)
        self.weekday_label.config(text=weekday)
        self.clock_label.config(text=time_text)
        self.out_temp_label.config(text=out_temp)

    def update_time(self, time_text: str):
        self.clock_label.config(text=time_text)

    def update_date(self, date_text: str, weekday: str):
        self.date_label.config(text=date_text)
        self.weekday_label.config(text=weekday)

    def update_outside_temp(self, out_temp: str):
        self.out_temp_label.config(text=out_temp)
