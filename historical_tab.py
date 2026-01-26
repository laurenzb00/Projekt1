import os
import tkinter as tk
from tkinter import ttk
import csv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.styles import (
    COLOR_ROOT,
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    COLOR_PRIMARY,
    COLOR_INFO,
)
from ui.components.card import Card


class HistoricalTab:
    """Tab für historische Daten: Temperaturen (7 Tage) + PV-Ertrag (90 Tage)."""

    def __init__(self, root: tk.Tk, notebook: ttk.Notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True

        self.tab_frame = tk.Frame(self.notebook, bg=COLOR_ROOT)
        self.notebook.add(self.tab_frame, text="📈 Historie")

        self.tab_frame.grid_columnconfigure(0, weight=1)
        self.tab_frame.grid_columnconfigure(1, weight=1)

        # Temperaturen Card
        self.temp_card = Card(self.tab_frame)
        self.temp_card.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.temp_card.add_title("Temperaturen (7 Tage)", icon="🌡️")
        self.temp_fig, self.temp_ax = plt.subplots(figsize=(4.8, 3.2), dpi=100)
        self.temp_fig.patch.set_facecolor(COLOR_CARD)
        self.temp_ax.set_facecolor(COLOR_CARD)
        self.temp_canvas = FigureCanvasTkAgg(self.temp_fig, master=self.temp_card.content())
        self.temp_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # PV-Ertrag Card
        self.pv_card = Card(self.tab_frame)
        self.pv_card.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.pv_card.add_title("PV-Ertrag (90 Tage)", icon="⚡")
        self.pv_fig, self.pv_ax = plt.subplots(figsize=(4.8, 3.2), dpi=100)
        self.pv_fig.patch.set_facecolor(COLOR_CARD)
        self.pv_ax.set_facecolor(COLOR_CARD)
        self.pv_canvas = FigureCanvasTkAgg(self.pv_fig, master=self.pv_card.content())
        self.pv_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._update_plots()

    def stop(self):
        self.alive = False

    def _load_pv(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ErtragHistory.csv")
        if not os.path.exists(path):
            return []
        rows = []
        cutoff = datetime.now() - timedelta(days=90)
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        ts = datetime.fromisoformat(row.get("Zeitstempel", ""))
                        if ts < cutoff:
                            continue
                        val = float(row.get("Ertrag_kWh", 0))
                        rows.append((ts, val))
                    except Exception:
                        continue
        except Exception:
            return []
        rows.sort(key=lambda r: r[0])
        return rows

    def _load_temps(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Heizungstemperaturen.csv")
        if not os.path.exists(path):
            return []
        rows = []
        cutoff = datetime.now() - timedelta(days=30)
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        ts = datetime.fromisoformat(row.get("Zeit", row.get("Zeitstempel", "")))
                        if ts < cutoff:
                            continue
                        top = float(row.get("Puffer_Top", row.get("PufferTop", row.get("puffer_top", row.get("Pufferspeicher Oben", 0)))))
                        mid = float(row.get("Puffer_Mitte", row.get("PufferMid", row.get("puffer_mid", row.get("Pufferspeicher Mitte", 0)))))
                        bot = float(row.get("Puffer_Bottom", row.get("PufferBot", row.get("puffer_bot", row.get("Pufferspeicher Unten", 0)))))
                        rows.append((ts, top, mid, bot))
                    except Exception:
                        continue
        except Exception:
            return []
        rows.sort(key=lambda r: r[0])
        return rows

    def _style_axes(self, ax):
        ax.set_facecolor(COLOR_CARD)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color(COLOR_BORDER)
            ax.spines[spine].set_linewidth(1)

    def _update_plots(self):
        if not self.alive:
            return

        # Temps
        temp_rows = self._load_temps()
        self.temp_ax.clear()
        self._style_axes(self.temp_ax)
        if temp_rows:
            ts, top, mid, bot = zip(*temp_rows)
            self.temp_ax.plot(ts, top, color=COLOR_PRIMARY, label="Top", linewidth=1.6)
            self.temp_ax.plot(ts, mid, color=COLOR_INFO, label="Mid", linewidth=1.4)
            self.temp_ax.plot(ts, bot, color=COLOR_SUBTEXT, label="Bottom", linewidth=1.4)
            self.temp_ax.set_ylabel("°C", color=COLOR_TEXT, fontsize=10)
            self.temp_ax.tick_params(axis="y", colors=COLOR_TEXT, labelsize=9)
            self.temp_ax.tick_params(axis="x", colors=COLOR_SUBTEXT, labelsize=8)
            self.temp_ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
            self.temp_ax.grid(True, color=COLOR_BORDER, alpha=0.3, linewidth=0.8)
            self.temp_ax.legend(facecolor=COLOR_CARD, edgecolor=COLOR_BORDER, labelcolor=COLOR_TEXT, fontsize=8)
        else:
            self.temp_ax.text(0.5, 0.5, "Keine Daten", color=COLOR_SUBTEXT, ha="center", va="center", transform=self.temp_ax.transAxes)
            self.temp_ax.set_xticks([])
            self.temp_ax.set_yticks([])

        # PV
        pv_rows = self._load_pv()
        self.pv_ax.clear()
        self._style_axes(self.pv_ax)
        if pv_rows:
            ts, vals = zip(*pv_rows)
            self.pv_ax.plot(ts, vals, color=COLOR_PRIMARY, linewidth=2.0, marker="o", markersize=3)
            self.pv_ax.fill_between(ts, vals, color=COLOR_PRIMARY, alpha=0.15)
            self.pv_ax.set_ylabel("Ertrag (kWh)", color=COLOR_TEXT, fontsize=10)
            self.pv_ax.tick_params(axis="y", colors=COLOR_TEXT, labelsize=9)
            self.pv_ax.tick_params(axis="x", colors=COLOR_SUBTEXT, labelsize=8)
            self.pv_ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
            self.pv_ax.grid(True, color=COLOR_BORDER, alpha=0.3, linewidth=0.8)
        else:
            self.pv_ax.text(0.5, 0.5, "Keine Daten", color=COLOR_SUBTEXT, ha="center", va="center", transform=self.pv_ax.transAxes)
            self.pv_ax.set_xticks([])
            self.pv_ax.set_yticks([])

        self.temp_fig.autofmt_xdate()
        self.pv_fig.autofmt_xdate()
        self.temp_canvas.draw_idle()
        self.pv_canvas.draw_idle()

        # Refresh alle 5 Minuten
        self.root.after(5 * 60 * 1000, self._update_plots)
