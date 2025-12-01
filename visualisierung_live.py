import os
import shutil
import tkinter as tk
from tkinter import StringVar

# --- NEU: ttkbootstrap für modernes Design ---
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Matplotlib Style passend zum Theme setzen
plt.style.use("dark_background")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from PIL import Image

# --- PSUTIL CHECK ---
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

# --- KONFIGURATION ---
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")
UPDATE_INTERVAL = 60 * 1000  # 1 Minute

MAX_FRONIUS_ROWS = 700_000
MAX_BMK_ROWS = 20_000
FRONIUS_DISPLAY_HOURS = 48
PV_ERTRAG_DAYS = 7


# --- HILFSFUNKTIONEN (unverändert) ---
def read_csv_tail(path: str, max_rows: int, **kwargs) -> pd.DataFrame:
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

    if total_lines <= max_rows + 1:
        return pd.read_csv(path, **kwargs)

    first_data_line = 1
    cut_from = max(first_data_line + 1, total_lines - max_rows)

    def _skiprows(i: int) -> bool:
        if i == 0: return False
        return i < cut_from

    return pd.read_csv(path, skiprows=_skiprows, **kwargs)

def get_cpu_temperature() -> float | None:
    candidates = ["/sys/class/thermal/thermal_zone0/temp", "/sys/class/hwmon/hwmon0/temp1_input"]
    for p in candidates:
        try:
            if os.path.exists(p):
                with open(p, "r") as f:
                    return int(f.read().strip()) / 1000.0
        except Exception:
            continue
    return None


class LivePlotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Energy Dashboard")
        self.root.geometry("1024x600")
        
        # --- THEME SETUP (ttkbootstrap) ---
        # Gute Themes für Touch/Dark: "superhero", "darkly", "cyborg"
        self.style = ttk.Style(theme="superhero") 
        
        # Farben aus dem Style extrahieren für Matplotlib
        self.bg_color = self.style.lookup("TFrame", "background")
        self.fg_color = self.style.lookup("TLabel", "foreground")
        self.grid_color = "#444444" # Manuell etwas heller als Schwarz

        self.app_start_time = pd.Timestamp.now()

        # ---------- GUI AUFBAU ----------
        
        # Hauptcontainer
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=BOTH, expand=YES)

        # Tabs (Notebook)
        self.notebook = ttk.Notebook(self.main_container, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        # -- TAB DEFINITIONEN --
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text=" Dashboard ")

        self.fronius_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.fronius_frame, text=" PV-Leistung ")
        self._setup_plot_tab(self.fronius_frame, "fronius")

        self.bmk_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.bmk_frame, text=" Temperaturen ")
        self._setup_plot_tab(self.bmk_frame, "bmk")

        self.batt_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.batt_frame, text=" Batterie ")
        self._setup_plot_tab(self.batt_frame, "batt")

        self.pv_ertrag_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.pv_ertrag_frame, text=" Ertrag ")
        self._setup_plot_tab(self.pv_ertrag_frame, "ertrag")
        
        self.info_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.info_frame, text=" Info & Status ")
        self._setup_plot_tab(self.info_frame, "info") # Kombiniert Info + Systemstatus in Plots

        # -- VARIABLEN --
        self.init_variables()
        
        # -- DASHBOARD BAUEN --
        self._build_dashboard_grid()

        # -- BUTTON LEISTE --
        self._build_bottom_bar()

        # -- BILDER CACHE --
        self.icons = {}
        self.offset_images_cache = {}
        self._load_icons()

        # -- START --
        self.update_plots()

    def init_variables(self):
        # Dashboard Strings
        self.dash_pv_now = StringVar(value="0 W")
        self.dash_haus_now = StringVar(value="0 W")
        self.dash_netz_now = StringVar(value="0 W")
        self.dash_soc = tk.IntVar(value=0) # Int für Meter
        self.dash_temp_top = tk.IntVar(value=20) # Int für Gauge
        self.dash_temp_top_str = StringVar(value="-- °C")
        self.dash_temp_mid_str = StringVar(value="-- °C")
        self.dash_temp_bot_str = StringVar(value="-- °C")
        self.dash_aussen = StringVar(value="-- °C")
        self.dash_status = StringVar(value="Initialisiere...")
        self.status_time_var = StringVar(value="-")

    def _setup_plot_tab(self, parent, name):
        """Erstellt Matplotlib Canvas Standard-Setup"""
        fig, ax = plt.subplots(figsize=(8, 3))
        fig.patch.set_facecolor(self.bg_color)
        ax.set_facecolor(self.bg_color)
        
        # Canvas
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        # Attribute dynamisch setzen
        setattr(self, f"{name}_fig", fig)
        setattr(self, f"{name}_ax", ax)
        setattr(self, f"{name}_canvas", canvas)
        
        if name == "fronius":
            self.fronius_ax2 = ax.twinx()

    def _load_icons(self):
        # Hier Pfade zu deinen Icons prüfen
        for icon in ["temperature.png", "outdoor.png", "battery.png", "house.png", "power.png"]:
            path = os.path.join(WORKING_DIRECTORY, "icons", icon)
            if os.path.exists(path):
                self.icons[icon] = Image.open(path)
        
        # Background optional
        bg_path = os.path.join(WORKING_DIRECTORY, "icons", "background.png")
        if os.path.exists(bg_path):
            self.bg_img = Image.open(bg_path).resize((1024, 600), Image.LANCZOS)
        else:
            self.bg_img = None

    def new_method(self, icon):
        """Optimierter Icon Cache für Matplotlib"""
        if icon in self.icons:
            if icon not in self.offset_images_cache:
                self.offset_images_cache[icon] = np.array(self.icons[icon].convert("RGBA"))
            return OffsetImage(self.offset_images_cache[icon], zoom=0.07)
        return None

    # ---------- UI BUILDER: DASHBOARD ----------
    def _build_dashboard_grid(self):
        """Baut ein Kachel-basiertes Dashboard mit Grid"""
        # Grid Konfiguration: 2 Zeilen, 3 Spalten
        self.dashboard_frame.columnconfigure(0, weight=1)
        self.dashboard_frame.columnconfigure(1, weight=1)
        self.dashboard_frame.columnconfigure(2, weight=1)
        self.dashboard_frame.rowconfigure(0, weight=1)
        self.dashboard_frame.rowconfigure(1, weight=1)

        # --- KACHEL 1: PV & Haus (Oben Links) ---
        f_power = ttk.Labelframe(self.dashboard_frame, text="Leistung", bootstyle="info", padding=10)
        f_power.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ttk.Label(f_power, text="Aktuell PV", font=("Arial", 12)).pack(anchor="w")
        ttk.Label(f_power, textvariable=self.dash_pv_now, font=("Arial", 24, "bold"), bootstyle="warning").pack(anchor="w")
        
        ttk.Separator(f_power).pack(fill=X, pady=10)
        
        ttk.Label(f_power, text="Hausverbrauch", font=("Arial", 12)).pack(anchor="w")
        ttk.Label(f_power, textvariable=self.dash_haus_now, font=("Arial", 24, "bold"), bootstyle="inverse-info").pack(anchor="w")

        # --- KACHEL 2: Batterie (Oben Mitte) - METER WIDGET ---
        f_batt = ttk.Labelframe(self.dashboard_frame, text="Speicher", bootstyle="success", padding=10)
        f_batt.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Ein visuelles Meter (Tacho-ähnlich)
        self.meter_batt = ttk.Meter(
            master=f_batt,
            metersize=180,
            amountused=0,
            amounttotal=100,
            metertype="semi", 
            subtext="SoC %",
            bootstyle="success",
            interactive=False,
            textright="%"
        )
        self.meter_batt.pack(expand=YES)

        # --- KACHEL 3: Temperaturen / Puffer (Oben Rechts) ---
        f_temp = ttk.Labelframe(self.dashboard_frame, text="Pufferspeicher", bootstyle="danger", padding=10)
        f_temp.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)

        # Visualisierung Puffer als Balken (Floodgauge)
        self.gauge_puffer = ttk.Floodgauge(
            master=f_temp, 
            bootstyle="danger", 
            font=("Arial", 12, "bold"),
            mask="Oben: {}°C",
            orient=VERTICAL
        )
        self.gauge_puffer.pack(side=LEFT, fill=Y, padx=10)
        
        # Textwerte daneben
        f_temp_txt = ttk.Frame(f_temp)
        f_temp_txt.pack(side=LEFT, fill=BOTH, expand=YES)
        
        ttk.Label(f_temp_txt, text="Mitte:", font=("Arial", 11)).pack(anchor="w", pady=(10,0))
        ttk.Label(f_temp_txt, textvariable=self.dash_temp_mid_str, font=("Arial", 16, "bold")).pack(anchor="w")
        
        ttk.Label(f_temp_txt, text="Unten:", font=("Arial", 11)).pack(anchor="w", pady=(10,0))
        ttk.Label(f_temp_txt, textvariable=self.dash_temp_bot_str, font=("Arial", 16, "bold")).pack(anchor="w")

        # --- KACHEL 4: Wetter / Außen (Unten Links) ---
        f_weather = ttk.Labelframe(self.dashboard_frame, text="Umgebung", bootstyle="primary", padding=10)
        f_weather.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        ttk.Label(f_weather, text="Außentemperatur", font=("Arial", 12)).pack(anchor="center", pady=(10,5))
        ttk.Label(f_weather, textvariable=self.dash_aussen, font=("Arial", 32, "bold"), bootstyle="primary").pack(anchor="center")
        
        # --- KACHEL 5: Status Text (Unten Mitte/Rechts) ---
        f_status = ttk.Labelframe(self.dashboard_frame, text="System Status", bootstyle="secondary", padding=10)
        f_status.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=10, pady=10)
        
        ttk.Label(f_status, textvariable=self.dash_status, font=("Arial", 14), wraplength=500).pack(fill=BOTH, expand=YES, anchor="nw")


    def _build_bottom_bar(self):
        bar = ttk.Frame(self.root, bootstyle="dark")
        bar.pack(side=BOTTOM, fill=X)
        
        ttk.Label(bar, textvariable=self.status_time_var, bootstyle="inverse-dark", padding=5).pack(side=RIGHT)
        
        btn_close = ttk.Button(bar, text="Beenden", bootstyle="danger-outline", command=self.root.destroy)
        btn_close.pack(side=LEFT, padx=5, pady=5)
        
        btn_min = ttk.Button(bar, text="Minimieren", bootstyle="secondary-outline", command=self.root.iconify)
        btn_min.pack(side=LEFT, padx=5, pady=5)

    # ---------- LOGIC: UPDATES (Zusammenfassung) ----------
    
    def _downsample(self, df, time_col, max_points=2000):
        """Reduziert Datenpunkte für schnelleres Plotten"""
        if df is None or df.empty: return df
        if len(df) <= max_points: return df
        step = max(len(df) // max_points, 1)
        return df.iloc[::step].reset_index(drop=True)

    def update_plots(self):
        now = pd.Timestamp.now()
        
        # 1. Daten laden (Deine Logik)
        fronius_df = None
        bmk_df = None
        
        # -- Fronius --
        if os.path.exists(FRONIUS_CSV):
            try:
                fronius_df = read_csv_tail(FRONIUS_CSV, MAX_FRONIUS_ROWS, parse_dates=["Zeitstempel"])
                fronius_df = fronius_df.sort_values("Zeitstempel")
            except Exception: pass
            
        # -- BMK --
        if os.path.exists(BMK_CSV):
            try:
                bmk_df = read_csv_tail(BMK_CSV, MAX_BMK_ROWS, parse_dates=["Zeitstempel"])
                bmk_df = bmk_df.sort_values("Zeitstempel")
            except Exception: pass

        # 2. Dashboard Variablen updaten
        if fronius_df is not None and not fronius_df.empty:
            last = fronius_df.iloc[-1]
            pv = float(last.get("PV-Leistung (kW)", 0))
            haus = float(last.get("Hausverbrauch (kW)", 0))
            soc = float(last.get("Batterieladestand (%)", 0))
            
            self.dash_pv_now.set(f"{pv:.2f} kW")
            self.dash_haus_now.set(f"{haus:.2f} kW")
            
            # Meter Update
            self.meter_batt.configure(amountused=int(soc))
            
            # Farbliche Warnung bei leerer Batterie
            if soc < 10: self.meter_batt.configure(bootstyle="danger")
            elif soc < 30: self.meter_batt.configure(bootstyle="warning")
            else: self.meter_batt.configure(bootstyle="success")

        if bmk_df is not None and not bmk_df.empty:
            last = bmk_df.iloc[-1]
            try:
                top = float(last.get("Pufferspeicher Oben", 0))
                mid = float(last.get("Pufferspeicher Mitte", 0))
                bot = float(last.get("Pufferspeicher Unten", 0))
                aussen = float(last.get("Außentemperatur", 0))
                
                # Floodgauge und Text
                self.gauge_puffer.configure(value=top, mask=f"Oben: {top:.1f}°C")
                self.dash_temp_mid_str.set(f"{mid:.1f} °C")
                self.dash_temp_bot_str.set(f"{bot:.1f} °C")
                self.dash_aussen.set(f"{aussen:.1f} °C")
                
                # Status Text generieren
                status_txt = f"Daten aktuell.\nAußentemperatur: {aussen:.1f}°C"
                self.dash_status.set(status_txt)
            except: pass

        # 3. Plots zeichnen (Logik gekürzt auf das Wesentliche für die Anzeige)
        # Hier rufst du deine bestehende Plot-Logik auf. 
        # Ich zeige exemplarisch den Fronius-Plot update, um das Styling zu zeigen.
        
        self._plot_fronius(fronius_df, now)
        self._plot_bmk(bmk_df, now)
        self._plot_battery(fronius_df, now)
        # ... andere Plots hier analog ...

        self.status_time_var.set(f"Letztes Update: {now.strftime('%H:%M:%S')}")
        self.root.after(UPDATE_INTERVAL, self.update_plots)

    # --- PLOT FUNKTIONEN (Gestyled) ---
    def _style_ax(self, ax):
        """Hilfsfunktion um Plots sauber aussehen zu lassen"""
        ax.set_facecolor(self.bg_color)
        ax.tick_params(colors=self.fg_color, which='both')
        for spine in ax.spines.values():
            spine.set_color(self.grid_color)
        ax.yaxis.label.set_color(self.fg_color)
        ax.xaxis.label.set_color(self.fg_color)
        ax.grid(True, color=self.grid_color, linestyle='--', alpha=0.3)

    def _plot_fronius(self, df, now):
        ax = self.fronius_ax
        ax2 = self.fronius_ax2
        ax.clear()
        ax2.clear()
        self._style_ax(ax)
        
        if df is None or df.empty:
            ax.text(0.5, 0.5, "Keine Daten", color=self.fg_color, ha="center")
            self.fronius_canvas.draw()
            return

        # Letzte 24h filtern
        df_sub = df[df["Zeitstempel"] >= now - pd.Timedelta(hours=24)]
        if df_sub.empty: return
        
        df_sub = self._downsample(df_sub, "Zeitstempel")
        
        # Plotten mit Bootstrap-Farben (warning=orange, info=blue)
        ax.fill_between(df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"], color="#f39c12", alpha=0.3)
        ax.plot(df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"], label="PV", color="#f39c12")
        
        ax.plot(df_sub["Zeitstempel"], df_sub["Hausverbrauch (kW)"], label="Haus", color="#3498db")
        
        ax2.plot(df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"], color="#9b59b6", linestyle=":", label="SoC")
        ax2.set_ylim(0, 100)
        ax2.tick_params(colors="#9b59b6")
        
        ax.legend(facecolor=self.bg_color, edgecolor=self.grid_color, labelcolor=self.fg_color, loc="upper left")
        ax.set_title("PV Leistung & Verbrauch (24h)", color=self.fg_color)
        
        self.fronius_fig.autofmt_xdate()
        self.fronius_canvas.draw()

    def _plot_bmk(self, df, now):
        ax = self.bmk_ax
        ax.clear()
        self._style_ax(ax)
        
        if df is None or df.empty: return
        df_sub = df[df["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
        if df_sub.empty: return
        df_sub = self._downsample(df_sub, "Zeitstempel")

        ax.plot(df_sub["Zeitstempel"], df_sub["Pufferspeicher Oben"], color="#e74c3c", label="Oben")
        ax.plot(df_sub["Zeitstempel"], df_sub["Pufferspeicher Mitte"], color="#e67e22", label="Mitte")
        ax.plot(df_sub["Zeitstempel"], df_sub["Pufferspeicher Unten"], color="#3498db", label="Unten")
        
        ax.legend(facecolor=self.bg_color, edgecolor=self.grid_color, labelcolor=self.fg_color)
        ax.set_title("Temperaturverlauf (48h)", color=self.fg_color)
        self.bmk_fig.autofmt_xdate()
        self.bmk_canvas.draw()

    def _plot_battery(self, df, now):
        ax = self.batt_ax
        ax.clear()
        self._style_ax(ax)
        if df is None or df.empty: return
        df_sub = df[df["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
        df_sub = self._downsample(df_sub, "Zeitstempel")
        
        ax.plot(df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"], color="#2ecc71", linewidth=2)
        ax.fill_between(df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"], color="#2ecc71", alpha=0.1)
        ax.set_ylim(0, 100)
        ax.set_title("Batterieladestand %", color=self.fg_color)
        self.batt_fig.autofmt_xdate()
        self.batt_canvas.draw()


if __name__ == "__main__":
    # Verwende ttkbootstrap Window statt tk.Tk
    app_window = ttk.Window(themename="superhero") # oder "darkly", "cyborg"
    
    # Touchscreen Scaling
    try:
        app_window.tk.call("tk", "scaling", 1.4) 
    except: pass
    
    app = LivePlotApp(app_window)
    app_window.mainloop()