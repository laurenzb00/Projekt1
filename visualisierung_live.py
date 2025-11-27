import os
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

WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")

UPDATE_INTERVAL = 60 * 1000  # 1 Minute

# CSV-Limits für RAM-schonendes Einlesen
MAX_FRONIUS_ROWS = 700_000   # ca. 7 Tage bei 1s Takt
MAX_BMK_ROWS = 20_000        # locker genug für viele Tage bei 60s Takt

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
        if i == 0:      # Header behalten
            return False
        return i < cut_from

    return pd.read_csv(path, skiprows=_skiprows, **kwargs)


class LivePlotApp:
    def __init__(self, root, fullscreen=True):
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
        self.fronius_canvas = FigureCanvasTkAgg(self.fronius_fig, master=self.fronius_frame)
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
        self.pv_ertrag_canvas = FigureCanvasTkAgg(self.pv_ertrag_fig, master=self.pv_ertrag_frame)
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
        self.summary_canvas = FigureCanvasTkAgg(self.summary_fig, master=self.summary_frame)
        self.summary_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Heizungs-Info Tab
        self.info_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.info_frame, text="Heizungs-Info")
        self.info_fig, self.info_ax = plt.subplots(figsize=(8, 3))
        self.info_canvas = FigureCanvasTkAgg(self.info_fig, master=self.info_frame)
        self.info_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Statuszeile
        self.status_var = StringVar(value="Letztes Update: -")
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, style="Dark.TLabel", anchor="w")
        self.status_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        # Button-Leiste
        self.button_frame = ttk.Frame(root, style="Dark.TFrame")
        self.button_frame.pack(side=tk.BOTTOM, pady=10)
        self.close_button = ttk.Button(self.button_frame, text="Schließen", command=self.root.destroy, style="Dark.TButton")
        self.close_button.pack(side=tk.LEFT, padx=10)
        self.minimize_button = ttk.Button(self.button_frame, text="Minimieren", command=self.minimize_window, style="Dark.TButton")
        self.minimize_button.pack(side=tk.LEFT, padx=10)
        self.theme_button = ttk.Button(self.button_frame, text="Light Mode", command=self.toggle_theme, style="Dark.TButton")
        self.theme_button.pack(side=tk.LEFT, padx=10)

        # Bilder
        self.icons = {}
        self.offset_images_cache = {}
        for icon in ["temperature.png", "outdoor.png", "battery.png", "house.png", "power.png"]:
            path = os.path.join(WORKING_DIRECTORY, "icons", icon)
            if os.path.exists(path):
                self.icons[icon] = Image.open(path)
        bg_path = os.path.join(WORKING_DIRECTORY, "icons", "background.png")
        self.bg_img = Image.open(bg_path).resize((1024, 600), Image.LANCZOS) if os.path.exists(bg_path) else None

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
        self.daily_summary_var = StringVar(value="Noch keine Auswertung verfügbar.")

        self._build_dashboard_ui()

        self.update_plots()

    # ---------- Theme / Styles ----------
    def _configure_styles(self):
        bg = self.bg_color
        fg = self.fg_color
        tab_bg = "#333333" if self.dark_mode else "#dddddd"
        tab_sel = "#555555" if self.dark_mode else "#ffffff"

        self.style.configure("TNotebook", background=bg, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=tab_bg, foreground=fg, padding=[10, 5])
        self.style.map("TNotebook.Tab",
                       background=[("selected", tab_sel)],
                       foreground=[("selected", fg)])
        self.style.configure("Dark.TFrame", background=bg)
        self.style.configure("Dark.TLabel", background=bg, foreground=fg)
        self.style.configure("Dark.TButton", background=tab_bg, foreground=fg, padding=6, relief="flat")
        self.style.map("Dark.TButton",
                       background=[("active", tab_sel)],
                       foreground=[("active", fg)])

    def toggle_theme(self):
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
        # Dashboard neu aufbauen, damit Farben aktualisiert werden
        self._build_dashboard_ui(rebuild=True)
        # Plots neu zeichnen mit neuen Farben
        self.update_plots()

    # ---------- Dashboard UI ----------
    def _build_dashboard_ui(self, rebuild=False):
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
        tk.Label(pv_frame, text="PV-Ertrag heute", bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 16, "bold")).pack(anchor="w")
        tk.Label(pv_frame, textvariable=self.dashboard_pv_today_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 28, "bold")).pack(anchor="w", pady=(5, 0))

        # Aktuelle Leistungen
        power_frame = tk.Frame(top_frame, bg=self.bg_color)
        power_frame.pack(side="left", expand=True, fill="x")
        tk.Label(power_frame, text="Aktuelle Leistung", bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 16, "bold")).pack(anchor="w")
        tk.Label(power_frame, textvariable=self.dashboard_pv_now_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 18)).pack(anchor="w")
        tk.Label(power_frame, textvariable=self.dashboard_haus_now_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 18)).pack(anchor="w")

        # Batterie
        batt_frame = tk.Frame(top_frame, bg=self.bg_color)
        batt_frame.pack(side="left", expand=True, fill="x")
        tk.Label(batt_frame, text="Batteriestand", bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 16, "bold")).pack(anchor="w")
        tk.Label(batt_frame, textvariable=self.dashboard_batt_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 28, "bold")).pack(anchor="w", pady=(5, 0))

        # Mittlere Zeile: Puffer & Außentemperatur & Heizstatus
        mid_frame = tk.Frame(container, bg=self.bg_color)
        mid_frame.pack(fill="x", pady=(0, 20))

        # Puffer
        puffer_frame = tk.Frame(mid_frame, bg=self.bg_color)
        puffer_frame.pack(side="left", expand=True, fill="x")
        tk.Label(puffer_frame, text="Pufferspeicher", bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 16, "bold")).pack(anchor="w")
        tk.Label(puffer_frame, textvariable=self.dashboard_puffer_oben_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 14)).pack(anchor="w")
        tk.Label(puffer_frame, textvariable=self.dashboard_puffer_mitte_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 14)).pack(anchor="w")
        tk.Label(puffer_frame, textvariable=self.dashboard_puffer_unten_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 14)).pack(anchor="w")

        # Außentemperatur / Wetter
        weather_frame = tk.Frame(mid_frame, bg=self.bg_color)
        weather_frame.pack(side="left", expand=True, fill="x")
        tk.Label(weather_frame, text="Außentemperatur", bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 16, "bold")).pack(anchor="w")
        tk.Label(weather_frame, textvariable=self.dashboard_aussen_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 24)).pack(anchor="w", pady=(5, 0))
        # Optional: „Wetter-Icon“: einfach Text (Sonne / Wolkig) aus Tendenz
        self.dashboard_weather_label = tk.Label(weather_frame, text="", bg=self.bg_color, fg=self.fg_color,
                                                font=("Arial", 14))
        self.dashboard_weather_label.pack(anchor="w")

        # Heizungsstatus
        heiz_frame = tk.Frame(mid_frame, bg=self.bg_color)
        heiz_frame.pack(side="left", expand=True, fill="x")
        tk.Label(heiz_frame, text="Heizung", bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 16, "bold")).pack(anchor="w")
        tk.Label(heiz_frame, textvariable=self.dashboard_heizstatus_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 14), wraplength=280, justify="left").pack(anchor="w")

        # Untere Zeile: Tageszusammenfassung
        bottom_frame = tk.Frame(container, bg=self.bg_color)
        bottom_frame.pack(fill="both", expand=True)

        tk.Label(bottom_frame, text="Tageszusammenfassung", bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 16, "bold")).pack(anchor="w")
        tk.Label(bottom_frame, textvariable=self.daily_summary_var, bg=self.bg_color, fg=self.fg_color,
                 font=("Arial", 12), wraplength=960, justify="left").pack(anchor="w", pady=(5, 0))

    # ---------- Hilfsfunktionen ----------
    def new_method(self, icon):
        if not hasattr(self, "offset_images_cache"):
            self.offset_images_cache = {}
        if icon not in self.offset_images_cache and icon in self.icons:
            self.offset_images_cache[icon] = OffsetImage(
                np.array(self.icons[icon].convert("RGBA")), zoom=0.07
            )
        return self.offset_images_cache.get(icon)

    def _downsample(self, df, time_col, max_points=2000):
        """Reduziert die Anzahl der Datenpunkte für schnelleres Plotten."""
        if df is None or df.empty:
            return df
        if len(df) <= max_points:
            return df
        step = max(len(df) // max_points, 1)
        return df.iloc[::step].reset_index(drop=True)

    def _format_duration(self, seconds: float) -> str:
        seconds = int(max(0, seconds))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        if h > 0:
            return f"{h}h {m:02d}min"
        return f"{m}min"

    # ---------- Haupt-Update ----------
    def update_plots(self):
        now = pd.Timestamp.now()

        # ---------- CSVs nur EINMAL einlesen ----------
        fronius_df = None
        bmk_df = None
        fronius_error = None
        bmk_error = None

        # Aggregationswerte
        pv_today_kwh = None
        haus_today_kwh = None
        eigenverbrauch_quote = None
        autarkie = None

        # Fronius-Daten
        if os.path.exists(FRONIUS_CSV):
            try:
                fronius_df = read_csv_tail(
                    FRONIUS_CSV,
                    MAX_FRONIUS_ROWS,
                    parse_dates=["Zeitstempel"],
                )
                fronius_df = fronius_df.sort_values("Zeitstempel")

                # Tageswerte PV / Haus / Eigenverbrauch
                if not fronius_df.empty:
                    df_today_f = fronius_df[fronius_df["Zeitstempel"].dt.date == now.date()].copy()
                    if len(df_today_f) > 1:
                        t_hours = (df_today_f["Zeitstempel"] - df_today_f["Zeitstempel"].iloc[0]).dt.total_seconds() / 3600.0
                        pv_y = df_today_f["PV-Leistung (kW)"].values
                        haus_y = df_today_f["Hausverbrauch (kW)"].values
                        pv_today_kwh = float(np.trapz(pv_y, t_hours))
                        haus_today_kwh = float(np.trapz(haus_y, t_hours))
                        grid_import = None
                        if "Netz-Leistung (kW)" in df_today_f.columns:
                            netz_y = df_today_f["Netz-Leistung (kW)"].values
                            grid_import = float(np.trapz(np.clip(netz_y, 0, None), t_hours))
                        if pv_today_kwh and grid_import is not None and pv_today_kwh > 0:
                            pv_for_load = haus_today_kwh - grid_import
                            eigenverbrauch_quote = max(0.0, min(1.0, pv_for_load / pv_today_kwh))
                        if haus_today_kwh and grid_import is not None and haus_today_kwh > 0:
                            autarkie = max(0.0, min(1.0, (haus_today_kwh - grid_import) / haus_today_kwh))

            except Exception as e:
                fronius_df = None
                fronius_error = e
        else:
            fronius_error = FileNotFoundError(f"{FRONIUS_CSV} nicht gefunden")

        # BMK-Daten
        if os.path.exists(BMK_CSV):
            try:
                bmk_df = read_csv_tail(
                    BMK_CSV,
                    MAX_BMK_ROWS,
                    parse_dates=["Zeitstempel"],
                )
                bmk_df = bmk_df.sort_values("Zeitstempel")
            except Exception as e:
                bmk_df = None
                bmk_error = e
        else:
            bmk_error = FileNotFoundError(f"{BMK_CSV} nicht gefunden")

        # ---------- Fronius-Tab (48h) ----------
        try:
            self.fronius_fig.patch.set_facecolor(self.bg_color)
            self.fronius_ax.clear()
            self.fronius_ax2.clear()
            self.fronius_ax.set_facecolor(self.bg_color)
            self.fronius_ax2.set_facecolor(self.bg_color)

            if fronius_error is not None:
                self.fronius_ax.text(0.5, 0.5, f"Fehler Fronius:\n{fronius_error}", ha="center", va="center",
                                     color=self.fg_color)
            elif fronius_df is None or fronius_df.empty:
                self.fronius_ax.text(0.5, 0.5, "Keine Fronius-Daten in den letzten 48h", ha="center", va="center",
                                     color=self.fg_color)
            else:
                df_48 = fronius_df[fronius_df["Zeitstempel"] >= now - pd.Timedelta(hours=FRONIUS_DISPLAY_HOURS)]
                if df_48.empty:
                    self.fronius_ax.text(0.5, 0.5, "Keine Fronius-Daten in den letzten 48h", ha="center", va="center",
                                         color=self.fg_color)
                else:
                    df_48 = self._downsample(df_48, "Zeitstempel", max_points=2000)

                    pv_smooth = df_48["PV-Leistung (kW)"].rolling(window=20, min_periods=1, center=True).mean()
                    haus_smooth = df_48["Hausverbrauch (kW)"].rolling(window=20, min_periods=1, center=True).mean()

                    self.fronius_ax.plot(df_48["Zeitstempel"], pv_smooth,
                                         label="PV-Leistung (kW, geglättet)", color="orange")
                    self.fronius_ax.plot(df_48["Zeitstempel"], haus_smooth,
                                         label="Hausverbrauch (kW, geglättet)", color="lightblue")
                    self.fronius_ax.set_ylabel("Leistung (kW)", color=self.fg_color)
                    self.fronius_ax.set_xlabel("Zeit", color=self.fg_color)

                    max_pv_value = pv_smooth.max()
                    if pd.isna(max_pv_value):
                        max_pv_value = 0.0
                    self.fronius_ax.set_ylim(0, max(10, float(max_pv_value) * 1.2))

                    self.fronius_ax.grid(True, which='major', linestyle='--', alpha=0.5, color=self.grid_color)
                    self.fronius_ax.legend(loc="upper left", facecolor=self.bg_color, edgecolor=self.grid_color)

                    if "Batterieladestand (%)" in df_48.columns:
                        self.fronius_ax2.plot(df_48["Zeitstempel"], df_48["Batterieladestand (%)"],
                                              label="Batterieladestand (%)", color="purple", linestyle="--")
                        self.fronius_ax2.set_ylabel("Batterieladestand (%)", color=self.fg_color)
                        self.fronius_ax2.set_ylim(0, 100)
                        self.fronius_ax2.grid(False)
                        self.fronius_ax2.legend(loc="upper right", facecolor=self.bg_color, edgecolor=self.grid_color)

                    self.fronius_fig.autofmt_xdate()
                    self.fronius_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    self.fronius_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))

                    for label in self.fronius_ax.get_xticklabels() + self.fronius_ax.get_yticklabels():
                        label.set_color(self.fg_color)
                    for label in self.fronius_ax2.get_yticklabels():
                        label.set_color(self.fg_color)

            self.fronius_canvas.draw()
        except Exception as e:
            self.fronius_ax.clear()
            self.fronius_ax.text(0.5, 0.5, f"Fehler Fronius:\n{e}", ha="center", va="center", color=self.fg_color)
            self.fronius_canvas.draw()

        # ---------- BMK-Tab (48h, inkl. Pufferspeicher Unten) ----------
        try:
            self.bmk_fig.patch.set_facecolor(self.bg_color)
            self.bmk_ax.clear()
            self.bmk_ax.set_facecolor(self.bg_color)

            if bmk_error is not None:
                self.bmk_ax.text(0.5, 0.5, f"Fehler BMK:\n{bmk_error}", ha="center", va="center", color=self.fg_color)
            elif bmk_df is None or bmk_df.empty:
                self.bmk_ax.text(0.5, 0.5, "Keine BMK-Daten in den letzten 48h", ha="center", va="center",
                                 color=self.fg_color)
            else:
                df_bmk_48 = bmk_df[bmk_df["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
                if df_bmk_48.empty:
                    self.bmk_ax.text(0.5, 0.5, "Keine BMK-Daten in den letzten 48h", ha="center", va="center",
                                     color=self.fg_color)
                else:
                    df_bmk_48 = self._downsample(df_bmk_48, "Zeitstempel", max_points=2000)

                    if "Kesseltemperatur" in df_bmk_48.columns:
                        self.bmk_ax.plot(df_bmk_48["Zeitstempel"], df_bmk_48["Kesseltemperatur"],
                                         label="Kesseltemperatur (°C)", color="red")
                    if "Außentemperatur" in df_bmk_48.columns:
                        self.bmk_ax.plot(df_bmk_48["Zeitstempel"], df_bmk_48["Außentemperatur"],
                                         label="Außentemperatur (°C)", color="cyan")
                    if "Pufferspeicher Oben" in df_bmk_48.columns:
                        self.bmk_ax.plot(df_bmk_48["Zeitstempel"], df_bmk_48["Pufferspeicher Oben"],
                                         label="Pufferspeicher Oben (°C)", color="orange")
                    if "Pufferspeicher Unten" in df_bmk_48.columns:
                        self.bmk_ax.plot(df_bmk_48["Zeitstempel"], df_bmk_48["Pufferspeicher Unten"],
                                         label="Pufferspeicher Unten (°C)", color="magenta")
                    if "Warmwasser" in df_bmk_48.columns:
                        self.bmk_ax.plot(df_bmk_48["Zeitstempel"], df_bmk_48["Warmwasser"],
                                         label="Warmwasser (°C)", color="green")

                    self.bmk_ax.set_ylabel("Temperatur (°C)", color=self.fg_color)
                    self.bmk_ax.set_xlabel("Zeit", color=self.fg_color)
                    self.bmk_ax.grid(True, which='major', linestyle='--', alpha=0.5, color=self.grid_color)
                    self.bmk_ax.legend(facecolor=self.bg_color, edgecolor=self.grid_color)
                    self.bmk_fig.autofmt_xdate()
                    self.bmk_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    self.bmk_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))

                    for label in self.bmk_ax.get_xticklabels() + self.bmk_ax.get_yticklabels():
                        label.set_color(self.fg_color)

            self.bmk_canvas.draw()
        except Exception as e:
            self.bmk_ax.clear()
            self.bmk_ax.text(0.5, 0.5, f"Fehler BMK:\n{e}", ha="center", va="center", color=self.fg_color)
            self.bmk_canvas.draw()

        # ---------- PV-Ertrag (Tage, aus Fronius) ----------
        try:
            self.pv_ertrag_fig.patch.set_facecolor(self.bg_color)
            self.pv_ertrag_ax.clear()
            self.pv_ertrag_ax.set_facecolor(self.bg_color)

            if fronius_error is not None or fronius_df is None or fronius_df.empty:
                self.pv_ertrag_ax.text(0.5, 0.5, f"Keine PV-Ertragsdaten ({PV_ERTRAG_DAYS} Tage)", ha="center",
                                       va="center", color=self.fg_color)
            else:
                df_pv = fronius_df.set_index("Zeitstempel")
                df_pv = df_pv[df_pv.index >= now - pd.Timedelta(days=PV_ERTRAG_DAYS)]

                pv_per_day = []
                if not df_pv.empty:
                    for day, group in df_pv.groupby(df_pv.index.date):
                        if len(group) > 1:
                            t = (group.index - group.index[0]).total_seconds() / 3600
                            y = group["PV-Leistung (kW)"].values
                            kwh = np.trapz(y, t)
                            pv_per_day.append((pd.Timestamp(day), kwh))

                if pv_per_day:
                    days, kwhs = zip(*pv_per_day)
                    self.pv_ertrag_ax.plot(days, kwhs, marker="o", color="orange", label="PV-Ertrag (kWh)")
                    self.pv_ertrag_ax.legend(facecolor=self.bg_color, edgecolor=self.grid_color)
                else:
                    self.pv_ertrag_ax.text(0.5, 0.5, f"Keine PV-Ertragsdaten ({PV_ERTRAG_DAYS} Tage)", ha="center",
                                           va="center", color=self.fg_color)

            self.pv_ertrag_ax.set_ylabel("PV-Ertrag (kWh)", color=self.fg_color)
            self.pv_ertrag_ax.set_title(f"PV-Ertrag pro Tag (letzte {PV_ERTRAG_DAYS} Tage)", color=self.fg_color)
            self.pv_ertrag_ax.set_xlabel("Datum", color=self.fg_color)
            self.pv_ertrag_ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            self.pv_ertrag_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.pv_ertrag_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
            self.pv_ertrag_ax.grid(True, which='major', linestyle='--', alpha=0.7, color=self.grid_color)
            self.pv_ertrag_fig.autofmt_xdate()

            for label in self.pv_ertrag_ax.get_xticklabels() + self.pv_ertrag_ax.get_yticklabels():
                label.set_color(self.fg_color)

            self.pv_ertrag_canvas.draw()
        except Exception as e:
            self.pv_ertrag_ax.clear()
            self.pv_ertrag_ax.text(0.5, 0.5, f"Fehler PV-Ertrag:\n{e}", ha="center", va="center",
                                   color=self.fg_color)
            self.pv_ertrag_canvas.draw()

        # ---------- Batterie-Verlauf ----------
        try:
            self.batt_fig.patch.set_facecolor(self.bg_color)
            self.batt_ax.clear()
            self.batt_ax.set_facecolor(self.bg_color)

            if fronius_error is not None or fronius_df is None or fronius_df.empty:
                self.batt_ax.text(0.5, 0.5, "Keine Batteriedaten vorhanden", ha="center", va="center",
                                  color=self.fg_color)
            else:
                if "Batterieladestand (%)" in fronius_df.columns:
                    df_batt = self._downsample(fronius_df, "Zeitstempel", max_points=2000)
                    self.batt_ax.plot(df_batt["Zeitstempel"], df_batt["Batterieladestand (%)"], color="purple")
                    self.batt_ax.set_ylim(0, 100)
                else:
                    self.batt_ax.text(0.5, 0.5, "Keine Batteriedaten vorhanden", ha="center", va="center",
                                      color=self.fg_color)

            self.batt_ax.set_ylabel("Batterieladestand (%)", color=self.fg_color)
            self.batt_ax.set_title("Batterieladestand Verlauf", color=self.fg_color)
            self.batt_ax.set_xlabel("Zeit", color=self.fg_color)
            self.batt_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.batt_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
            self.batt_ax.grid(True, which='major', linestyle='--', alpha=0.7, color=self.grid_color)
            self.batt_fig.autofmt_xdate()

            for label in self.batt_ax.get_xticklabels() + self.batt_ax.get_yticklabels():
                label.set_color(self.fg_color)

            self.batt_canvas.draw()
        except Exception as e:
            self.batt_ax.clear()
            self.batt_ax.text(0.5, 0.5, f"Fehler Batterie:\n{e}", ha="center", va="center", color=self.fg_color)
            self.batt_canvas.draw()

        # ---------- Zusammenfassung ----------
        try:
            self.summary_fig.patch.set_facecolor(self.bg_color)
            self.summary_ax.clear()
            self.summary_ax.axis("off")

            if self.bg_img is not None:
                self.summary_ax.imshow(self.bg_img, extent=[0, 1, -0.25, 1.05], aspect="auto", zorder=0)
            rect = Rectangle((0, -0.25), 1, 1.3, facecolor="white", alpha=0.15, zorder=1)
            self.summary_ax.add_patch(rect)

            def fmt2(val):
                try:
                    return f"{float(val):.2f}"
                except Exception:
                    return val

            soc = haus = netz = "n/a"
            puffer_oben = puffer_mitte = puffer_unten = kessel = aussen = "n/a"

            if fronius_df is not None and not fronius_df.empty:
                last_f = fronius_df.iloc[-1]
                soc = last_f.get("Batterieladestand (%)", "n/a")
                haus = fmt2(last_f.get("Hausverbrauch (kW)", "n/a"))
                netz = fmt2(last_f.get("Netz-Leistung (kW)", "n/a"))

            if bmk_df is not None and not bmk_df.empty:
                last_b = bmk_df.iloc[-1]
                puffer_oben = last_b.get("Pufferspeicher Oben", "n/a")
                puffer_mitte = last_b.get("Pufferspeicher Mitte", "n/a")
                puffer_unten = last_b.get("Pufferspeicher Unten", "n/a")
                kessel = last_b.get("Kesseltemperatur", "n/a")
                aussen = last_b.get("Außentemperatur", "n/a")

            icon_positions = [
                ("temperature.png", 0.18, 0.85, f"{puffer_oben} °C", "Puffertemperatur Oben"),
                ("temperature.png", 0.18, 0.70, f"{puffer_mitte} °C", "Puffertemperatur Mitte"),
                ("temperature.png", 0.18, 0.55, f"{puffer_unten} °C", "Puffertemperatur Unten"),
                ("temperature.png", 0.18, 0.40, f"{kessel} °C", "Kesseltemperatur"),
                ("outdoor.png",     0.18, 0.25, f"{aussen} °C", "Außentemperatur"),
                ("battery.png",     0.18, 0.10, f"{soc} %", "Batterieladestand"),
                ("house.png",       0.18, -0.05, f"{haus} kW", "Hausverbrauch"),
                ("power.png",       0.18, -0.20, f"{netz} kW", "Netz-Leistung"),
            ]

            for icon, x, y, value, label in icon_positions:
                oi = self.new_method(icon)
                if oi is not None:
                    ab = AnnotationBbox(oi, (x, y), frameon=False, box_alignment=(0.5, 0.5), zorder=2)
                    self.summary_ax.add_artist(ab)
                self.summary_ax.text(
                    x + 0.11, y, label,
                    fontsize=17, color=self.fg_color,
                    va="center", ha="left", weight="bold", zorder=3
                )
                self.summary_ax.text(
                    x + 0.65, y, value,
                    fontsize=19, color=self.fg_color,
                    va="center", ha="left", weight="bold", zorder=3
                )

            self.summary_ax.set_xlim(0, 1)
            self.summary_ax.set_ylim(-0.25, 1.05)
            self.summary_canvas.draw()
        except Exception as e:
            self.summary_ax.clear()
            self.summary_ax.text(0.5, 0.5, f"Fehler Zusammenfassung:\n{e}", ha="center", va="center",
                                 color=self.fg_color)
            self.summary_canvas.draw()

        # ---------- Heizungs-Info Tab (Warmwasser-Prognose, Heizung aktiv, Uptime + Summarytext) ----------
        try:
            self.info_fig.patch.set_facecolor(self.bg_color)
            self.info_ax.clear()
            self.info_ax.axis("off")

            if self.bg_img is not None:
                self.info_ax.imshow(self.bg_img, extent=[0, 1, -0.1, 1.1], aspect="auto", zorder=0)
            rect = Rectangle((0, -0.1), 1, 1.2, facecolor="white", alpha=0.12, zorder=1)
            self.info_ax.add_patch(rect)

            warmwasser_text = "Warmwasser: keine Daten"
            heizstatus_text = "Heizung: keine Daten"
            schichtung_text = "Schichtung: keine Daten"
            uptime_text = "Uptime: -"
            letzte_bmk_text = "Letzte Heizdaten: -"
            heating_minutes_today = None

            # Uptime
            uptime_sec = (now - self.app_start_time).total_seconds()
            uptime_text = f"Projekt-Laufzeit: {self._format_duration(uptime_sec)}"

            if bmk_df is not None and not bmk_df.empty:
                last_b = bmk_df.iloc[-1]
                last_time = last_b.get("Zeitstempel", None)
                if pd.notna(last_time):
                    delta_min = (now - last_time).total_seconds() / 60.0
                    letzte_bmk_text = f"Letzte BMK-Daten vor: {delta_min:.1f} min"

                # Schichtung
                try:
                    t_top = float(last_b.get("Pufferspeicher Oben", np.nan))
                    t_bottom = float(last_b.get("Pufferspeicher Unten", np.nan))
                    if not np.isnan(t_top) and not np.isnan(t_bottom):
                        dT = t_top - t_bottom
                        if dT >= 15:
                            schichtung_text = f"Schichtung: gut (Δ {dT:.1f} °C)"
                        elif dT >= 5:
                            schichtung_text = f"Schichtung: mittel (Δ {dT:.1f} °C)"
                        else:
                            schichtung_text = f"Schichtung: gering (Δ {dT:.1f} °C)"
                except Exception:
                    pass

                # Warmwasser-Prognose (letzte 6h)
                try:
                    t_top_now = float(last_b.get("Pufferspeicher Oben", np.nan))
                    if not np.isnan(t_top_now):
                        df_recent = bmk_df[bmk_df["Zeitstempel"] >= now - pd.Timedelta(hours=6)].copy()
                        if len(df_recent) >= 3:
                            times = (df_recent["Zeitstempel"] - df_recent["Zeitstempel"].iloc[0]).dt.total_seconds() / 3600.0
                            temps = pd.to_numeric(df_recent["Pufferspeicher Oben"], errors="coerce")
                            mask = temps.notna()
                            times = times[mask]
                            temps = temps[mask]
                            if len(times) >= 2:
                                coeffs = np.polyfit(times.values, temps.values, 1)
                                slope = coeffs[0]  # °C/h
                                target = 40.0
                                if t_top_now <= target:
                                    warmwasser_text = f"Warmwasser: bereits knapp ({t_top_now:.1f} °C oben)"
                                else:
                                    if slope >= -0.1:
                                        warmwasser_text = f"Warmwasser: ausreichend (ΔT fällt kaum, {t_top_now:.1f} °C)"
                                    else:
                                        hours_left = (t_top_now - target) / abs(slope)
                                        if hours_left < 0:
                                            warmwasser_text = f"Warmwasser: bald knapp ({t_top_now:.1f} °C)"
                                        else:
                                            warmwasser_text = (
                                                f"Warmwasser reicht etwa noch: {self._format_duration(hours_left * 3600)} "
                                                f"(oben {t_top_now:.1f} °C)"
                                            )
                            else:
                                warmwasser_text = f"Warmwasser: {t_top_now:.1f} °C oben (zu wenig Verlauf für Prognose)"
                        else:
                            warmwasser_text = f"Warmwasser: {t_top_now:.1f} °C oben (zu wenig Daten)"
                except Exception:
                    pass

                # Heizung aktiv / inaktiv (letzte 2h)
                try:
                    df_kessel = bmk_df[bmk_df["Zeitstempel"] >= now - pd.Timedelta(hours=2)].copy()
                    df_kessel = df_kessel.dropna(subset=["Kesseltemperatur"])
                    if len(df_kessel) >= 3:
                        times = (df_kessel["Zeitstempel"] - df_kessel["Zeitstempel"].iloc[0]).dt.total_seconds() / 3600.0
                        temps = pd.to_numeric(df_kessel["Kesseltemperatur"], errors="coerce")
                        mask = temps.notna()
                        times = times[mask]
                        temps = temps[mask]
                        if len(times) >= 2:
                            coeffs = np.polyfit(times.values, temps.values, 1)
                            slope_k = coeffs[0]  # °C/h
                            t_now_k = float(df_kessel["Kesseltemperatur"].iloc[-1])
                            if slope_k > 5:
                                heizstatus_text = f"Heizung: aktiv (Kessel heizt, {t_now_k:.1f} °C)"
                            elif slope_k < -5:
                                heizstatus_text = f"Heizung: kühlt ab ({t_now_k:.1f} °C)"
                            else:
                                heizstatus_text = f"Heizung: Standby ({t_now_k:.1f} °C)"
                        else:
                            heizstatus_text = "Heizung: zu wenig Verlauf für Status"
                    else:
                        heizstatus_text = "Heizung: zu wenig Daten für Status"
                except Exception:
                    pass

                # Heizlaufzeit heute (Kessel > 45°C)
                try:
                    df_today_bmk = bmk_df[bmk_df["Zeitstempel"].dt.date == now.date()].copy()
                    if len(df_today_bmk) >= 2 and "Kesseltemperatur" in df_today_bmk.columns:
                        temps_k = pd.to_numeric(df_today_bmk["Kesseltemperatur"], errors="coerce")
                        times_k = df_today_bmk["Zeitstempel"]
                        if len(times_k) > 1:
                            diffs = np.diff(times_k.values).astype("timedelta64[s]").astype(float)
                            dt_secs = float(np.median(diffs)) if len(diffs) > 0 else 60.0
                        else:
                            dt_secs = 60.0
                        heating_on = temps_k > 45
                        heating_seconds = heating_on.sum() * dt_secs
                        heating_minutes_today = heating_seconds / 60.0
                except Exception:
                    heating_minutes_today = None

            # hübsche Anordnung mit Icons
            self.info_ax.set_xlim(0, 1)
            self.info_ax.set_ylim(-0.1, 1.1)

            rows = [
                ("temperature.png", 0.18, 0.80, "Warmwasser-Prognose", warmwasser_text),
                ("power.png",       0.18, 0.62, "Heizungsstatus",      heizstatus_text),
                ("temperature.png", 0.18, 0.44, "Puffer-Schichtung",   schichtung_text),
                ("battery.png",     0.18, 0.26, "Projekt-Laufzeit",    uptime_text),
                ("house.png",       0.18, 0.08, "Heizdaten",           letzte_bmk_text),
            ]

            for icon, x, y, label, value in rows:
                oi = self.new_method(icon)
                if oi is not None:
                    ab = AnnotationBbox(oi, (x, y), frameon=False, box_alignment=(0.5, 0.5), zorder=2)
                    self.info_ax.add_artist(ab)
                self.info_ax.text(
                    x + 0.11, y, label,
                    fontsize=16, color=self.fg_color,
                    va="center", ha="left", weight="bold", zorder=3
                )
                self.info_ax.text(
                    x + 0.60, y, value,
                    fontsize=13, color=self.fg_color,
                    va="center", ha="left", zorder=3
                )

            self.info_canvas.draw()

            # ---------- Dashboard-Werte & Tageszusammenfassung ----------

            # Letzte Fronius/BMK-Werte
            last_f = fronius_df.iloc[-1] if (fronius_df is not None and not fronius_df.empty) else None
            last_b = bmk_df.iloc[-1] if (bmk_df is not None and not bmk_df.empty) else None

            # Dashboard: heute PV-Ertrag
            if pv_today_kwh is not None:
                self.dashboard_pv_today_var.set(f"{pv_today_kwh:.1f} kWh")
            else:
                self.dashboard_pv_today_var.set("-")

            # Dashboard: momentane Leistungen
            if last_f is not None:
                try:
                    pv_now = float(last_f.get("PV-Leistung (kW)", np.nan))
                    haus_now = float(last_f.get("Hausverbrauch (kW)", np.nan))
                    soc_now = float(last_f.get("Batterieladestand (%)", np.nan))
                    self.dashboard_pv_now_var.set(f"PV: {pv_now:.2f} kW")
                    self.dashboard_haus_now_var.set(f"Haus: {haus_now:.2f} kW")
                    self.dashboard_batt_var.set(f"{soc_now:.0f} %")
                except Exception:
                    self.dashboard_pv_now_var.set("PV: -")
                    self.dashboard_haus_now_var.set("Haus: -")
                    self.dashboard_batt_var.set("-")
            else:
                self.dashboard_pv_now_var.set("PV: -")
                self.dashboard_haus_now_var.set("Haus: -")
                self.dashboard_batt_var.set("-")

            # Dashboard: Puffer / Außentemp
            if last_b is not None:
                try:
                    p_oben = last_b.get("Pufferspeicher Oben", "n/a")
                    p_mitte = last_b.get("Pufferspeicher Mitte", "n/a")
                    p_unten = last_b.get("Pufferspeicher Unten", "n/a")
                    aussen = last_b.get("Außentemperatur", "n/a")
                    self.dashboard_puffer_oben_var.set(f"Oben: {p_oben} °C")
                    self.dashboard_puffer_mitte_var.set(f"Mitte: {p_mitte} °C")
                    self.dashboard_puffer_unten_var.set(f"Unten: {p_unten} °C")
                    self.dashboard_aussen_var.set(f"{aussen} °C")
                except Exception:
                    self.dashboard_puffer_oben_var.set("Oben: -")
                    self.dashboard_puffer_mitte_var.set("Mitte: -")
                    self.dashboard_puffer_unten_var.set("Unten: -")
                    self.dashboard_aussen_var.set("-")
            else:
                self.dashboard_puffer_oben_var.set("Oben: -")
                self.dashboard_puffer_mitte_var.set("Mitte: -")
                self.dashboard_puffer_unten_var.set("Unten: -")
                self.dashboard_aussen_var.set("-")

            # Dashboard: Heizstatus
            self.dashboard_heizstatus_var.set(heizstatus_text)

            # Dashboard: "Wetter-Icon"-Text anhand Außentemp + PV
            weather_txt = ""
            try:
                if last_b is not None and last_f is not None:
                    aussen_val = float(last_b.get("Außentemperatur", np.nan))
                    pv_now = float(last_f.get("PV-Leistung (kW)", np.nan))
                    if np.isnan(aussen_val):
                        weather_txt = ""
                    else:
                        if pv_now > 0.5 and aussen_val > 10:
                            weather_txt = "Wetter: sonnig / leicht bewölkt"
                        elif aussen_val < 0:
                            weather_txt = "Wetter: kalt (evtl. frostig)"
                        else:
                            weather_txt = "Wetter: eher bedeckt"
            except Exception:
                weather_txt = ""
            self.dashboard_weather_label.config(text=weather_txt)

            # Tageszusammenfassung-Text
            summary_lines = []
            if pv_today_kwh is not None and haus_today_kwh is not None:
                if pv_today_kwh < 1:
                    quality = "ein sehr schwacher PV-Tag"
                elif pv_today_kwh < 5:
                    quality = "ein eher schwacher PV-Tag"
                elif pv_today_kwh < 10:
                    quality = "ein guter PV-Tag"
                else:
                    quality = "ein sehr guter PV-Tag"
                line1 = f"Heute war bisher {quality}. Bis jetzt wurden {pv_today_kwh:.1f} kWh PV-Energie erzeugt."
                line2 = f"Der Hausverbrauch liegt bei {haus_today_kwh:.1f} kWh."
                if eigenverbrauch_quote is not None:
                    line2 += f" Davon wurden etwa {eigenverbrauch_quote * 100:,.0f}% direkt aus PV gedeckt."
                summary_lines.append(line1)
                summary_lines.append(line2)

            if schichtung_text != "Schichtung: keine Daten":
                summary_lines.append(f"Der Pufferspeicher ist aktuell: {schichtung_text.replace('Schichtung: ', '')}.")

            if heating_minutes_today is not None:
                summary_lines.append(f"Die Heizung war heute ungefähr {heating_minutes_today:.0f} Minuten aktiv.")

            if not summary_lines:
                summary_lines.append("Noch nicht genug Daten für eine Tageszusammenfassung.")

            self.daily_summary_var.set("\n".join(summary_lines))

        except Exception as e:
            self.info_ax.clear()
            self.info_ax.text(0.5, 0.5, f"Fehler Heizungs-Info:\n{e}", ha="center", va="center", color=self.fg_color)
            self.info_canvas.draw()

        # ---------- Abschluss ----------
        self.status_var.set(f"Letztes Update: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.root.after(UPDATE_INTERVAL, self.update_plots)

    def minimize_window(self):
        self.root.iconify()


if __name__ == "__main__":
    root = tk.Tk()
    app = LivePlotApp(root)
    root.mainloop()
