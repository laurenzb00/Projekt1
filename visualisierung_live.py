import os
import shutil
from tkinter import StringVar
import tkinter as tk
from tkinter import ttk

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.style.use("dark_background")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from PIL import Image

# psutil ist optional – falls nicht installiert, zeigen wir es im Systemstatus-Tab an
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")

UPDATE_INTERVAL = 60 * 1000  # 1 Minute

# CSV-Limits für RAM-schonendes Einlesen
MAX_FRONIUS_ROWS = 700_000  # ca. 7 Tage bei 1s Takt
MAX_BMK_ROWS = 20_000  # viele Tage bei 60s Takt

FRONIUS_DISPLAY_HOURS = 48
PV_ERTRAG_DAYS = 7  # PV-Ertrag für letzte X Tage


def read_csv_tail(path: str, max_rows: int, **kwargs) -> pd.DataFrame:
    """
    Liest nur die letzten max_rows Datenzeilen einer CSV (Header bleibt erhalten),
    ohne alles in den RAM zu laden.
    """
    try:
        total_lines = 0
        with open(path, "r", encoding="utf-8") as f:
            for total_lines, _ in enumerate(f, start=1):
                pass
    except FileNotFoundError:
        raise
    except Exception as e:
        raise RuntimeError(f"Fehler beim Lesen von {path}: {e}")

    if total_lines == 0:
        return pd.DataFrame()

    # Kleine Datei -> komplett lesen
    if total_lines <= max_rows + 1:
        return pd.read_csv(path, **kwargs)

    first_data_line = 1  # Header = Zeile 0
    cut_from = max(first_data_line + 1, total_lines - max_rows)

    def _skiprows(i: int) -> bool:
        if i == 0:  # Header behalten
            return False
        return i < cut_from

    return pd.read_csv(path, skiprows=_skiprows, **kwargs)


def get_cpu_temperature() -> float | None:
    """
    Versucht, die CPU-/SoC-Temperatur des Systems (z. B. Raspberry Pi) auszulesen.
    Liefert °C oder None.
    """
    candidates = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/hwmon/hwmon0/temp1_input",
    ]
    for p in candidates:
        try:
            if os.path.exists(p):
                with open(p, "r") as f:
                    v = f.read().strip()
                    temp_c = int(v) / 1000.0
                    return temp_c
        except Exception:
            continue
    return None


class LivePlotApp:
    def __init__(self, root, fullscreen: bool = True) -> None:
        self.root = root
        self.root.title("Live-Daten Visualisierung")
        self.root.geometry("1024x600")
        self.root.resizable(False, False)

        # App-Startzeit für Uptime
        self.app_start_time = pd.Timestamp.now()

        # Theme-Status
        self.dark_mode = True
        self.bg_color = "#222222"
        self.fg_color = "#ffffff"
        self.grid_color = "#444444"

        # ---------- Styles ----------
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()
        self.root.configure(bg=self.bg_color)

        # ---------- Notebook ----------
        self.notebook = ttk.Notebook(root, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Dashboard Tab (Startseite)
        self.dashboard_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.dashboard_frame, text="Dashboard")

        # Fronius Tab
        self.fronius_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.fronius_frame, text="Fronius")
        self.fronius_fig, self.fronius_ax = plt.subplots(figsize=(8, 3))
        self.fronius_ax2 = self.fronius_ax.twinx()
        self.fronius_canvas = FigureCanvasTkAgg(
            self.fronius_fig, master=self.fronius_frame
        )
        self.fronius_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # BMK Tab (Temperaturen 2 Tage)
        self.bmk_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.bmk_frame, text="Temperaturen 2 Tage")
        self.bmk_fig, self.bmk_ax = plt.subplots(figsize=(8, 3))
        self.bmk_canvas = FigureCanvasTkAgg(self.bmk_fig, master=self.bmk_frame)
        self.bmk_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # PV-Ertrag Tab
        self.pv_ertrag_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.pv_ertrag_frame, text=f"PV-Ertrag ({PV_ERTRAG_DAYS} Tage)")
        self.pv_ertrag_fig, self.pv_ertrag_ax = plt.subplots(figsize=(8, 3))
        self.pv_ertrag_canvas = FigureCanvasTkAgg(
            self.pv_ertrag_fig, master=self.pv_ertrag_frame
        )
        self.pv_ertrag_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Batterie Verlauf
        self.batt_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.batt_frame, text="Batterie Verlauf")
        self.batt_fig, self.batt_ax = plt.subplots(figsize=(8, 3))
        self.batt_canvas = FigureCanvasTkAgg(self.batt_fig, master=self.batt_frame)
        self.batt_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Zusammenfassung
        self.summary_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.summary_frame, text="Zusammenfassung")
        self.summary_fig, self.summary_ax = plt.subplots(figsize=(8, 3))
        self.summary_canvas = FigureCanvasTkAgg(
            self.summary_fig, master=self.summary_frame
        )
        self.summary_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Heizungs-Info Tab
        self.info_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.info_frame, text="Heizungs-Info")
        self.info_fig, self.info_ax = plt.subplots(figsize=(8, 3))
        self.info_canvas = FigureCanvasTkAgg(self.info_fig, master=self.info_frame)
        self.info_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Systemstatus Tab
        self.sys_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.sys_frame, text="Systemstatus")

        # Statuszeile (eigener Balken, immer sichtbar)
        self.status_var = StringVar(value="Letztes Update: -")
        self.status_label = ttk.Label(
            self.root, textvariable=self.status_var, style="Status.TLabel", anchor="w"
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Button-Leiste unten (touchfreundlich)
        self.button_frame = ttk.Frame(root, style="Dark.TFrame")
        self.button_frame.pack(side=tk.BOTTOM, pady=6)

        self.close_button = ttk.Button(
            self.button_frame,
            text="Schließen",
            command=self.root.destroy,
            style="Dark.TButton",
        )
        self.close_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=6)

        self.minimize_button = ttk.Button(
            self.button_frame,
            text="Minimieren",
            command=self.minimize_window,
            style="Dark.TButton",
        )
        self.minimize_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=6)

        self.theme_button = ttk.Button(
            self.button_frame,
            text="Light Mode",
            command=self.toggle_theme,
            style="Dark.TButton",
        )
        self.theme_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=6)

        # Icons (ohne Hintergrundbild)
        self.icons: dict[str, Image.Image] = {}
        self.offset_images_cache: dict[str, np.ndarray] = {}
        for icon in [
            "temperature.png",
            "outdoor.png",
            "battery.png",
            "house.png",
            "power.png",
        ]:
            path = os.path.join(WORKING_DIRECTORY, "icons", icon)
            if os.path.exists(path):
                self.icons[icon] = Image.open(path)

        # Dashboard-Variablen
        self.dashboard_pv_today_var = StringVar(value="-")
        self.dashboard_pv_now_var = StringVar(value="-")
        self.dashboard_haus_now_var = StringVar(value="-")
        self.dashboard_batt_var = StringVar(value="-")
        self.dashboard_puffer_oben_var = StringVar(value="-")
        self.dashboard_puffer_mitte_var = StringVar(value="-")
        self.dashboard_puffer_unten_var = StringVar(value="-")
        self.dashboard_aussen_var = StringVar(value="-")
        self.dashboard_heizstatus_var = StringVar(value="-")
        self.daily_summary_var = StringVar(
            value="Noch keine Auswertung verfügbar."
        )

        # Systemstatus-Variablen
        self.sys_cpu_var = StringVar(value="-")
        self.sys_ram_var = StringVar(value="-")
        self.sys_swap_var = StringVar(value="-")
        self.sys_disk_var = StringVar(value="-")
        self.sys_temp_var = StringVar(value="-")
        self.sys_note_var = StringVar(
            value="psutil nicht installiert – Systeminfos eingeschränkt."
            if not HAS_PSUTIL
            else ""
        )

        self._build_dashboard_ui()
        self._build_systemstatus_ui()

        self.update_plots()

    # ---------- Theme / Styles ----------
    def _configure_styles(self) -> None:
        bg = self.bg_color
        fg = self.fg_color
        tab_bg = "#333333" if self.dark_mode else "#dddddd"
        tab_sel = "#777777" if self.dark_mode else "#ffffff"
        status_bg = "#444444" if self.dark_mode else "#cccccc"

        # Notebook / Tabs
        self.style.configure("TNotebook", background=bg, borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=tab_bg,
            foreground=fg,
            padding=[16, 8],  # größere Tabs
            font=("Arial", 11, "bold"),  # gut lesbar auf Touch
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", tab_sel)],
            foreground=[("selected", fg)],
        )

        # Frames / Labels / Buttons
        self.style.configure("Dark.TFrame", background=bg)
        self.style.configure(
            "Dark.TLabel",
            background=bg,
            foreground=fg,
            font=("Arial", 11),
        )
        self.style.configure(
            "Dark.TButton",
            background=tab_bg,
            foreground=fg,
            padding=8,  # mehr Padding -> größere Fläche
            relief="flat",
            font=("Arial", 11, "bold"),
        )
        self.style.map(
            "Dark.TButton",
            background=[("active", tab_sel)],
            foreground=[("active", fg)],
        )

        # Status-Balken
        self.style.configure(
            "Status.TLabel",
            background=status_bg,
            foreground=fg,
            font=("Arial", 9),
        )

    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.bg_color = "#222222"
            self.fg_color = "#ffffff"
            self.grid_color = "#444444"
            self.theme_button.config(text="Light Mode")
        else:
            self.bg_color = "#f0f0f0"
            self.fg_color = "#000000"
            self.grid_color = "#aaaaaa"
            self.theme_button.config(text="Dark Mode")

        self._configure_styles()
        self.root.configure(bg=self.bg_color)
        # Dashboard & Systemstatus neu aufbauen, damit Farben aktualisiert werden
        self._build_dashboard_ui(rebuild=True)
        self._build_systemstatus_ui(rebuild=True)
        # Plots neu zeichnen mit neuen Farben
        self.update_plots()

    # ---------- Dashboard UI ----------
    def _build_dashboard_ui(self, rebuild: bool = False) -> None:
        if rebuild:
            for w in self.dashboard_frame.winfo_children():
                w.destroy()

        container = tk.Frame(self.dashboard_frame, bg=self.bg_color)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Obere Zeile: PV & Batterie / Haus
        top_frame = tk.Frame(container, bg=self.bg_color)
        top_frame.pack(fill="x", pady=(0, 20))

        # PV-Ertrag heute
        pv_frame = tk.Frame(top_frame, bg=self.bg_color)
        pv_frame.pack(side="left", expand=True, fill="x")
        tk.Label(
            pv_frame,
            text="PV-Ertrag (Referenztag)",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            pv_frame,
            textvariable=self.dashboard_pv_today_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 28, "bold"),
        ).pack(anchor="w", pady=(5, 0))

        # Aktuelle Leistungen
        power_frame = tk.Frame(top_frame, bg=self.bg_color)
        power_frame.pack(side="left", expand=True, fill="x")
        tk.Label(
            power_frame,
            text="Aktuelle Leistung",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            power_frame,
            textvariable=self.dashboard_pv_now_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 18),
        ).pack(anchor="w")
        tk.Label(
            power_frame,
            textvariable=self.dashboard_haus_now_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 18),
        ).pack(anchor="w")

        # Batterie
        batt_frame = tk.Frame(top_frame, bg=self.bg_color)
        batt_frame.pack(side="left", expand=True, fill="x")
        tk.Label(
            batt_frame,
            text="Batteriestand",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            batt_frame,
            textvariable=self.dashboard_batt_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 28, "bold"),
        ).pack(anchor="w", pady=(5, 0))

        # Mittlere Zeile: Puffer & Außentemperatur & Heizstatus
        mid_frame = tk.Frame(container, bg=self.bg_color)
        mid_frame.pack(fill="x", pady=(0, 20))

        # Puffer
        puffer_frame = tk.Frame(mid_frame, bg=self.bg_color)
        puffer_frame.pack(side="left", expand=True, fill="x")
        tk.Label(
            puffer_frame,
            text="Pufferspeicher",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            puffer_frame,
            textvariable=self.dashboard_puffer_oben_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 14),
        ).pack(anchor="w")
        tk.Label(
            puffer_frame,
            textvariable=self.dashboard_puffer_mitte_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 14),
        ).pack(anchor="w")
        tk.Label(
            puffer_frame,
            textvariable=self.dashboard_puffer_unten_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 14),
        ).pack(anchor="w")

        # Außentemperatur / Wetter
        weather_frame = tk.Frame(mid_frame, bg=self.bg_color)
        weather_frame.pack(side="left", expand=True, fill="x")
        tk.Label(
            weather_frame,
            text="Außentemperatur",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            weather_frame,
            textvariable=self.dashboard_aussen_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 28, "bold"),
        ).pack(anchor="w", pady=(5, 0))

        # Heizstatus
        heating_frame = tk.Frame(mid_frame, bg=self.bg_color)
        heating_frame.pack(side="left", expand=True, fill="x")
        tk.Label(
            heating_frame,
            text="Heizstatus",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            heating_frame,
            textvariable=self.dashboard_heizstatus_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 18),
        ).pack(anchor="w")

        # Tägliche Zusammenfassung
        summary_frame = tk.Frame(container, bg=self.bg_color)
        summary_frame.pack(fill="both", expand=True)
        tk.Label(
            summary_frame,
            text="Tägliche Auswertung",
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            summary_frame,
            textvariable=self.daily_summary_var,
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Arial", 12),
            justify="left",
        ).pack(anchor="w", fill="both", expand=True)
