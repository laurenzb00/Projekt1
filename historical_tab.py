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
    COLOR_WARNING,
    emoji,
)
from ui.components.card import Card


class HistoricalTab:
    """Historie der Heizung/Puffer/Außen + aktuelle Werte."""

    def __init__(self, root: tk.Tk, notebook: ttk.Notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True

        self.tab_frame = tk.Frame(self.notebook, bg=COLOR_ROOT)
        self.notebook.add(self.tab_frame, text=emoji("📈 Historie", "Historie"))

        self.tab_frame.grid_columnconfigure(0, weight=1)
        self.tab_frame.grid_rowconfigure(0, weight=0)
        self.tab_frame.grid_rowconfigure(1, weight=1)

        # Card
        self.card = Card(self.tab_frame)
        self.card.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=12, pady=12)
        self.card.add_title("Heizungsdaten (letzte 7 Tage)", icon="🌡️")

        # Current values row
        stats = ttk.Frame(self.card.content())
        stats.pack(fill=tk.X, pady=(0, 6))
        self.var_top = tk.StringVar(value="Puffer oben: -- °C")
        self.var_mid = tk.StringVar(value="Puffer mitte: -- °C")
        self.var_bot = tk.StringVar(value="Puffer unten: -- °C")
        self.var_boiler = tk.StringVar(value="Boiler: -- °C")
        self.var_out = tk.StringVar(value="Außen: -- °C")
        ttk.Label(stats, textvariable=self.var_top).pack(side=tk.LEFT, padx=6)
        ttk.Label(stats, textvariable=self.var_mid).pack(side=tk.LEFT, padx=6)
        ttk.Label(stats, textvariable=self.var_bot).pack(side=tk.LEFT, padx=6)
        ttk.Label(stats, textvariable=self.var_boiler).pack(side=tk.LEFT, padx=6)
        ttk.Label(stats, textvariable=self.var_out).pack(side=tk.LEFT, padx=6)

        # Plot
        self.fig, self.ax = plt.subplots(figsize=(7.2, 3.6), dpi=100)
        self.fig.patch.set_facecolor(COLOR_CARD)
        self.ax.set_facecolor(COLOR_CARD)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.card.content())
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._last_key = None
        self._update_plot()

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
                        mid = float(row.get("Pufferspeicher Mitte", row.get("Puffer_Mitte", row.get("PufferMid", row.get("puffer_mid", 0)))))
                        bot = float(row.get("Pufferspeicher Unten", row.get("Puffer_Bottom", row.get("PufferBot", row.get("puffer_bot", 0)))))
                        boiler = float(row.get("Kesseltemperatur", row.get("Boiler", row.get("Kessel", 0))))
                        outside = float(row.get("Außentemperatur", row.get("Aussentemperatur", row.get("Aussen", row.get("out_temp", 0)))))
                        all_rows.append((ts, top, mid, bot, boiler, outside))
                        if ts >= cutoff:
                            rows.append((ts, top, mid, bot, boiler, outside))
                    except Exception:
                        continue
        except Exception:
            return []
        rows.sort(key=lambda r: r[0])
        if rows:
            return rows
        all_rows.sort(key=lambda r: r[0])
        return all_rows[-500:]

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

        rows = self._load_temps()
        key = (len(rows), rows[-1]) if rows else ("empty",)
        if key != self._last_key:
            self._last_key = key
            self.ax.clear()
            self._style_axes()

            if rows:
                ts, top, mid, bot, boiler, outside = zip(*rows)
                self.ax.plot(ts, top, color=COLOR_PRIMARY, label="Puffer oben", linewidth=1.6)
                self.ax.plot(ts, mid, color=COLOR_INFO, label="Puffer mitte", linewidth=1.2)
                self.ax.plot(ts, bot, color=COLOR_SUBTEXT, label="Puffer unten", linewidth=1.2)
                self.ax.plot(ts, boiler, color=COLOR_WARNING, label="Boiler", linewidth=1.4)
                self.ax.plot(ts, outside, color=COLOR_TEXT, label="Außen", linewidth=1.2)
                self.ax.set_ylabel("°C", color=COLOR_TEXT, fontsize=10)
                self.ax.tick_params(axis="y", colors=COLOR_TEXT, labelsize=9)
                self.ax.tick_params(axis="x", colors=COLOR_SUBTEXT, labelsize=8)
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
                self.ax.grid(True, color=COLOR_BORDER, alpha=0.3, linewidth=0.8)
                self.ax.legend(facecolor=COLOR_CARD, edgecolor=COLOR_BORDER, labelcolor=COLOR_TEXT, fontsize=8)

                # Current values
                self.var_top.set(f"Puffer oben: {top[-1]:.1f} °C")
                self.var_mid.set(f"Puffer mitte: {mid[-1]:.1f} °C")
                self.var_bot.set(f"Puffer unten: {bot[-1]:.1f} °C")
                self.var_boiler.set(f"Boiler: {boiler[-1]:.1f} °C")
                self.var_out.set(f"Außen: {outside[-1]:.1f} °C")
            else:
                self.ax.text(0.5, 0.5, "Keine Daten", color=COLOR_SUBTEXT, ha="center", va="center", transform=self.ax.transAxes)
                self.ax.set_xticks([])
                self.ax.set_yticks([])
                self.var_top.set("Puffer oben: -- °C")
                self.var_mid.set("Puffer mitte: -- °C")
                self.var_bot.set("Puffer unten: -- °C")
                self.var_boiler.set("Boiler: -- °C")
                self.var_out.set("Außen: -- °C")

            self.fig.autofmt_xdate()
            self.canvas.draw_idle()

        self.root.after(5 * 60 * 1000, self._update_plot)

    @staticmethod
    def _data_path(filename: str) -> str:
        ui_dir = os.path.dirname(os.path.abspath(__file__))
        data_root = os.path.dirname(ui_dir)
        return os.path.join(data_root, filename)
