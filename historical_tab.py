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
    emoji,
)
from ui.components.card import Card


class HistoricalTab:
    """Tab für historische Daten: Temperaturen (letzte Woche)."""

    def __init__(self, root: tk.Tk, notebook: ttk.Notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True

        self.tab_frame = tk.Frame(self.notebook, bg=COLOR_ROOT)
        self.notebook.add(self.tab_frame, text=emoji("📈 Historie", "Historie"))

        self.tab_frame.grid_columnconfigure(0, weight=1)

        # Temperaturen Card
        self.temp_card = Card(self.tab_frame)
        self.temp_card.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.temp_card.add_title("Temperaturen (letzte 7 Tage)", icon="🌡️")
        self.temp_fig, self.temp_ax = plt.subplots(figsize=(6.8, 3.6), dpi=100)
        self.temp_fig.patch.set_facecolor(COLOR_CARD)
        self.temp_ax.set_facecolor(COLOR_CARD)
        self.temp_canvas = FigureCanvasTkAgg(self.temp_fig, master=self.temp_card.content())
        self.temp_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._last_temp_key = None

        self._update_plots()

    def stop(self):
        self.alive = False

    def _load_temps(self):
        path = self._data_path("Heizungstemperaturen.csv")
        if not os.path.exists(path):
            return []
        rows = []
        all_rows = []
        cutoff = datetime.now() - timedelta(days=7)
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        ts = datetime.fromisoformat(row.get("Zeit", row.get("Zeitstempel", "")))
                        top = float(row.get("Pufferspeicher Oben", row.get("Puffer_Top", row.get("PufferTop", row.get("puffer_top", 0)))))
                        boiler = float(row.get("Kesseltemperatur", row.get("Boiler", row.get("Kessel", 0))))
                        outside = float(row.get("Außentemperatur", row.get("Aussentemperatur", row.get("Aussen", row.get("out_temp", 0)))))
                        all_rows.append((ts, top, boiler, outside))
                        if ts >= cutoff:
                            rows.append((ts, top, boiler, outside))
                    except Exception:
                        continue
        except Exception:
            return []
        rows.sort(key=lambda r: r[0])
        if rows:
            return rows
        # Fallback: wenn keine Daten im Zeitraum, zeige letzte 500 Einträge
        all_rows.sort(key=lambda r: r[0])
        return all_rows[-500:]

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
        temp_key = (len(temp_rows), temp_rows[-1]) if temp_rows else ("empty",)
        temp_changed = temp_key != self._last_temp_key
        if temp_changed:
            self._last_temp_key = temp_key
            self.temp_ax.clear()
            self._style_axes(self.temp_ax)
            if temp_rows:
                ts, top, boiler, outside = zip(*temp_rows)
                self.temp_ax.plot(ts, top, color=COLOR_PRIMARY, label="Puffer Oben", linewidth=1.6)
                self.temp_ax.plot(ts, boiler, color=COLOR_INFO, label="Boiler", linewidth=1.4)
                self.temp_ax.plot(ts, outside, color=COLOR_SUBTEXT, label="Außen", linewidth=1.4)
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

        if temp_changed:
            self.temp_fig.autofmt_xdate()
            self.temp_canvas.draw_idle()

        # Refresh alle 5 Minuten
        self.root.after(5 * 60 * 1000, self._update_plots)

    @staticmethod
    def _data_path(filename: str) -> str:
        ui_dir = os.path.dirname(os.path.abspath(__file__))
        data_root = os.path.dirname(ui_dir)
        return os.path.join(data_root, filename)
