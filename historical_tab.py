import os
import tkinter as tk
from tkinter import ttk
import csv
from datetime import datetime, timedelta
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
    COLOR_INFO,
    COLOR_WARNING,
    COLOR_DANGER,
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
        self.notebook.add(self.tab_frame, text=emoji("📈 Heizung-Historie", "Heizung-Historie"))

        self.tab_frame.grid_columnconfigure(0, weight=1)
        self.tab_frame.grid_rowconfigure(0, weight=0)
        self.tab_frame.grid_rowconfigure(1, weight=1)

        # Main Card
        self.card = Card(self.tab_frame)
        self.card.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=12, pady=12)
        self.card.add_title("Heizungsdaten (letzte 7 Tage)", icon="🌡️")

        # Stats Grid: 5 stat cards in one frame
        stats_frame = tk.Frame(self.card.content(), bg=COLOR_CARD)
        stats_frame.pack(fill=tk.X, pady=(0, 12))
        
        self.var_top = tk.StringVar(value="-- °C")
        self.var_mid = tk.StringVar(value="-- °C")
        self.var_bot = tk.StringVar(value="-- °C")
        self.var_boiler = tk.StringVar(value="-- °C")
        self.var_out = tk.StringVar(value="-- °C")
        
        stats_grid = [
            ("Puffer oben", self.var_top, COLOR_PRIMARY),
            ("Puffer mitte", self.var_mid, COLOR_INFO),
            ("Puffer unten", self.var_bot, COLOR_SUBTEXT),
            ("Boiler", self.var_boiler, COLOR_WARNING),
            ("Außen", self.var_out, COLOR_TEXT),
        ]
        
        for idx, (label, var, color) in enumerate(stats_grid):
            stat_card = tk.Frame(stats_frame, bg=COLOR_CARD)
            stat_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
            
            ttk.Label(stat_card, text=label, font=("Arial", 9), foreground=color).pack(anchor="w", padx=6, pady=(4, 2))
            ttk.Label(stat_card, textvariable=var, font=("Arial", 14, "bold")).pack(anchor="w", padx=6, pady=(0, 4))

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
        cutoff = datetime.now() - timedelta(days=4)
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
                self.ax.plot(ts, outside, color=COLOR_DANGER, label="Außen", linewidth=1.2)
                self.ax.set_ylabel("°C", color=COLOR_TEXT, fontsize=10)
                # Y-Achse kann ins Minus gehen für Außentemperatur
                self.ax.tick_params(axis="y", colors=COLOR_TEXT, labelsize=9)
                self.ax.tick_params(axis="x", colors=COLOR_SUBTEXT, labelsize=8)
                self.ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=False))
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
                self.ax.grid(True, color=COLOR_BORDER, alpha=0.3, linewidth=0.8)
                self.ax.legend(facecolor=COLOR_CARD, edgecolor=COLOR_BORDER, labelcolor=COLOR_TEXT, fontsize=8)

                # Current values
                self.var_top.set(f"{top[-1]:.1f} °C")
                self.var_mid.set(f"{mid[-1]:.1f} °C")
                self.var_bot.set(f"{bot[-1]:.1f} °C")
                self.var_boiler.set(f"{boiler[-1]:.1f} °C")
                self.var_out.set(f"{outside[-1]:.1f} °C")
            else:
                self.ax.text(0.5, 0.5, "Keine Daten", color=COLOR_SUBTEXT, ha="center", va="center", transform=self.ax.transAxes)
                self.ax.set_xticks([])
                self.ax.set_yticks([])
                self.var_top.set("-- °C")
                self.var_mid.set("-- °C")
                self.var_bot.set("-- °C")
                self.var_boiler.set("-- °C")
                self.var_out.set("-- °C")

            self.fig.autofmt_xdate()
            self.canvas.draw_idle()

        self.root.after(5 * 60 * 1000, self._update_plot)

    @staticmethod
    def _data_path(filename: str) -> str:
        # Try multiple common paths
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),  # Same dir
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename),  # Parent of ui/
            os.path.join("/home/laurenz/projekt1/Projekt1", filename),  # Raspberry Pi path
            os.path.join("/home/pi/projekt1", filename),  # Alternative Pi path
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        # Default fallback
        return candidates[1]
