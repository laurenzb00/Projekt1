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
from ui.components.rounded import RoundedFrame


class HeaderBar(tk.Frame):
    """Schlanker Header mit Datum, Uhrzeit, Toggles und Exit."""

    def __init__(self, parent: tk.Widget, on_toggle_a=None, on_toggle_b=None, on_exit=None):
        super().__init__(parent, height=60, bg=COLOR_HEADER)
        self.pack_propagate(False)

        # Rounded container
        rounded = RoundedFrame(self, bg=COLOR_CARD, border=None, radius=18, padding=0)
        rounded.pack(fill=tk.BOTH, expand=True, padx=6, pady=3)
        inner = rounded.content()

        inner.grid_columnconfigure(0, weight=1, minsize=140, uniform="hdr")
        inner.grid_columnconfigure(1, weight=2, uniform="hdr")
        inner.grid_columnconfigure(2, weight=1, minsize=140, uniform="hdr")

        # Links: Datum
        left = tk.Frame(inner, bg=COLOR_CARD)
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=6)
        self.date_label = tk.Label(left, text="--", font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT, bg=COLOR_CARD)
        self.date_label.pack(anchor="w")
        self.weekday_label = tk.Label(left, text="", font=("Segoe UI", 9), fg=COLOR_SUBTEXT, bg=COLOR_CARD)
        self.weekday_label.pack(anchor="w", pady=(2, 0))

        # Mitte: Uhrzeit + Buttons (zwischen Uhrzeit und Außentemp)
        center = tk.Frame(inner, bg=COLOR_CARD)
        center.grid(row=0, column=1, sticky="nsew")
        center.grid_columnconfigure(0, weight=1)
        center.grid_columnconfigure(1, weight=0)

        self.clock_label = tk.Label(center, text="--:--", font=("Segoe UI", 28, "bold"), fg=COLOR_PRIMARY, bg=COLOR_CARD)
        self.clock_label.grid(row=0, column=0, sticky="nsew")

        # Rechts: Außentemp
        right = tk.Frame(inner, bg=COLOR_CARD)
        right.grid(row=0, column=2, sticky="ne", padx=4, pady=2)

        self.out_temp_label = tk.Label(right, text="-- °C", font=("Segoe UI", 14, "bold"), fg=COLOR_WARNING, bg=COLOR_CARD)
        self.out_temp_label.pack(anchor="ne")
        tk.Label(right, text="Außen", font=("Segoe UI", 9), fg=COLOR_SUBTEXT, bg=COLOR_CARD).pack(anchor="ne", pady=(0, 4))

        btn_row = tk.Frame(center, bg=COLOR_CARD)
        btn_row.grid(row=0, column=1, sticky="e", padx=(6, 0))
        self.btn_a = ttk.Button(btn_row, text="An", style="Card.TButton", width=7, command=on_toggle_a)
        self.btn_a.pack(side=tk.LEFT, padx=2)
        self.btn_b = ttk.Button(btn_row, text="Aus", style="Card.TButton", width=7, command=on_toggle_b)
        self.btn_b.pack(side=tk.LEFT, padx=2)
        self.exit_btn = ttk.Button(btn_row, text="Exit", style="Card.TButton", width=7, command=on_exit)
        self.exit_btn.pack(side=tk.LEFT, padx=2)

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
