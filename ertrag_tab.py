import os
import csv
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.styles import (
    COLOR_ROOT,
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    COLOR_PRIMARY,
    emoji,
)
from ui.components.card import Card


class ErtragTab:
    """PV-Ertrag pro Tag über längeren Zeitraum."""

    def __init__(self, root: tk.Tk, notebook: ttk.Notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True

        self.tab_frame = tk.Frame(self.notebook, bg=COLOR_ROOT)
        self.notebook.add(self.tab_frame, text=emoji("🔆 Ertrag", "Ertrag"))

        self.card = Card(self.tab_frame)
        self.card.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.card.add_title("PV-Ertrag (täglich)", icon="📈")

        self.fig, self.ax = plt.subplots(figsize=(7.6, 3.8), dpi=100)
        self.fig.patch.set_facecolor(COLOR_CARD)
        self.ax.set_facecolor(COLOR_CARD)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.card.content())
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        stats_frame = ttk.Frame(self.card.content())
        stats_frame.pack(fill=tk.X, pady=(8, 0))
        self.var_sum = tk.StringVar(value="Summe: -- kWh")
        self.var_avg = tk.StringVar(value="Schnitt/Tag: -- kWh")
        self.var_last = tk.StringVar(value="Letzter Tag: -- kWh")
        ttk.Label(stats_frame, textvariable=self.var_sum).pack(side=tk.LEFT, padx=6)
        ttk.Label(stats_frame, textvariable=self.var_avg).pack(side=tk.LEFT, padx=6)
        ttk.Label(stats_frame, textvariable=self.var_last).pack(side=tk.LEFT, padx=6)

        self._last_key = None
        self._update_plot()

    def stop(self):
        self.alive = False

    def _load_pv_daily(self, days: int = 365):
        path = self._data_path("ErtragHistory.csv")
        if not os.path.exists(path):
            return []
        cutoff = datetime.now() - timedelta(days=days)
        daily = {}
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        ts = datetime.fromisoformat(row.get("Zeitstempel", ""))
                        val = float(row.get("Ertrag_kWh", 0))
                        if ts < cutoff:
                            continue
                        day = ts.date()
                        daily[day] = daily.get(day, 0.0) + val
                    except Exception:
                        continue
        except Exception:
            return []

        out = [(datetime.combine(day, datetime.min.time()), total) for day, total in daily.items()]
        out.sort(key=lambda r: r[0])
        return out

    def _style_axes(self):
        self.ax.set_facecolor(COLOR_CARD)
        for spine in ["top", "right"]:
            self.ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            self.ax.spines[spine].set_color(COLOR_BORDER)
            self.ax.spines[spine].set_linewidth(1)

    def _update_plot(self):
        if not self.alive:
            return

        data = self._load_pv_daily(365)
        key = (len(data), data[-1]) if data else ("empty",)
        if key == self._last_key:
            self.root.after(5 * 60 * 1000, self._update_plot)
            return
        self._last_key = key

        self.ax.clear()
        self._style_axes()

        if data:
            ts, vals = zip(*data)
            self.ax.plot(ts, vals, color=COLOR_PRIMARY, linewidth=2.0)
            self.ax.fill_between(ts, vals, color=COLOR_PRIMARY, alpha=0.12)
            self.ax.set_ylabel("Ertrag (kWh)", color=COLOR_TEXT, fontsize=10)
            self.ax.tick_params(axis="y", colors=COLOR_TEXT, labelsize=9)
            self.ax.tick_params(axis="x", colors=COLOR_SUBTEXT, labelsize=8)
            self.ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=False))
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
            self.ax.grid(True, color=COLOR_BORDER, alpha=0.3, linewidth=0.8)

            total = sum(vals)
            avg = total / max(1, len(vals))
            self.var_sum.set(f"Summe: {total:.1f} kWh")
            self.var_avg.set(f"Schnitt/Tag: {avg:.2f} kWh")
            self.var_last.set(f"Letzter Tag: {vals[-1]:.2f} kWh")
        else:
            self.ax.text(0.5, 0.5, "Keine Daten", color=COLOR_SUBTEXT, ha="center", va="center", transform=self.ax.transAxes)
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            self.var_sum.set("Summe: -- kWh")
            self.var_avg.set("Schnitt/Tag: -- kWh")
            self.var_last.set("Letzter Tag: -- kWh")

        self.fig.autofmt_xdate()
        self.canvas.draw_idle()
        self.root.after(5 * 60 * 1000, self._update_plot)

    @staticmethod
    def _data_path(filename: str) -> str:
        ui_dir = os.path.dirname(os.path.abspath(__file__))
        data_root = os.path.dirname(ui_dir)
        return os.path.join(data_root, filename)
