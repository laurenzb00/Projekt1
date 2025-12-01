import os
import tkinter as tk
from tkinter import StringVar

# --- DESIGN & PLOTTING ---
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

# Matplotlib Dark-Mode aktivieren
plt.style.use("dark_background")

# --- KONFIGURATION ---
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")

# Aktualisierungsrate (ms)
UPDATE_INTERVAL = 60 * 1000  # 1 Minute
MAX_PLOT_POINTS = 2000 

# --- HILFSFUNKTION: CSV SICHER LESEN ---
def read_csv_tail_fixed(path: str, max_rows: int) -> pd.DataFrame:
    """
    Liest nur die letzten Zeilen einer CSV, behält aber die korrekten
    Spaltennamen aus der ersten Zeile bei.
    """
    if not os.path.exists(path):
        return None
        
    try:
        # 1. Nur die Kopfzeile lesen (Zeile 0)
        header_df = pd.read_csv(path, nrows=0, sep=",")
        col_names = header_df.columns.tolist()
        
        # 2. Gesamtanzahl der Zeilen ermitteln
        with open(path, "rb") as f:
            total_lines = sum(1 for _ in f)
            
        # 3. Berechnen, ab wo wir lesen müssen
        skip_rows = max(1, total_lines - max_rows)
        
        # 4. Daten lesen und Namen zuweisen
        # sep="," ist Standard, aber wir setzen es explizit
        df = pd.read_csv(path, sep=",", names=col_names, skiprows=skip_rows)
        
        # Leerzeichen in Spaltennamen entfernen
        df.columns = df.columns.str.strip()
        
        return df
        
    except Exception as e:
        print(f"Fehler beim Lesen von {path}: {e}")
        return None

# --- HAUPTKLASSE (Wieder umbenannt zu LivePlotApp für Kompatibilität) ---
class LivePlotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Energy Dashboard")
        # Wir versuchen, das Theme auf das übergebene Root-Fenster anzuwenden
        self.style = ttk.Style("superhero")
        
        self.root.geometry("1024x600")
        
        # Farben aus dem Theme laden
        self.bg_color = self.style.lookup("TFrame", "background")
        self.fg_color = "white"
        self.grid_color = "#444444"

        # Variablen für UI
        self.init_variables()

        # Haupt-Container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=BOTH, expand=YES)

        # Tabs erstellen
        self.notebook = ttk.Notebook(self.main_container, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        # --- TABS DEFINIEREN ---
        self.setup_dashboard_tab()
        self.setup_plot_tabs()
        self.setup_spotify_tab()

        # Fußzeile
        self.setup_bottom_bar()

        # Starten der Update-Schleife
        self.update_plots()

    def init_variables(self):
        self.dash_pv_now = StringVar(value="-- kW")
        self.dash_haus_now = StringVar(value="-- kW")
        self.dash_temp_mid_str = StringVar(value="-- °C")
        self.dash_temp_bot_str = StringVar(value="-- °C")
        self.dash_aussen = StringVar(value="-- °C")
        self.dash_status = StringVar(value="System startet...")
        self.status_time_var = StringVar(value="-")

    # --- UI SETUP ---
    def setup_dashboard_tab(self):
        self.dash_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dash_frame, text=" Dashboard ")
        
        # Grid: 3 Spalten
        self.dash_frame.columnconfigure((0,1,2), weight=1)
        self.dash_frame.rowconfigure(0, weight=1)

        # 1. Leistung (PV & Haus)
        f1 = ttk.Labelframe(self.dash_frame, text="Leistung", padding=15, bootstyle="warning")
        f1.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ttk.Label(f1, text="PV Aktuell:", font=("Arial", 12)).pack(anchor="w")
        ttk.Label(f1, textvariable=self.dash_pv_now, font=("Arial", 26, "bold"), bootstyle="warning").pack(anchor="w", pady=5)
        ttk.Separator(f1).pack(fill=X, pady=10)
        ttk.Label(f1, text="Verbrauch:", font=("Arial", 12)).pack(anchor="w")
        ttk.Label(f1, textvariable=self.dash_haus_now, font=("Arial", 26, "bold"), bootstyle="info").pack(anchor="w", pady=5)

        # 2. Speicher (Rundinstrument)
        f2 = ttk.Labelframe(self.dash_frame, text="Speicher", padding=15, bootstyle="success")
        f2.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.meter_batt = ttk.Meter(
            f2, metersize=180, amountused=0, metertype="semi", 
            subtext="SoC %", bootstyle="success", interactive=False, textright="%"
        )
        self.meter_batt.pack(expand=YES)

        # 3. Temperaturen (Balken)
        f3 = ttk.Labelframe(self.dash_frame, text="Wärme", padding=15, bootstyle="danger")
        f3.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        
        # Grafischer Balken
        self.gauge_puffer = ttk.Floodgauge(
            f3, bootstyle="danger", font=("Arial", 12, "bold"), 
            mask="Oben: {}°C", orient=VERTICAL
        )
        self.gauge_puffer.pack(side=LEFT, fill=Y, padx=10)
        
        # Textwerte daneben
        txt_f = ttk.Frame(f3)
        txt_f.pack(side=LEFT, fill=BOTH, expand=YES)
        ttk.Label(txt_f, text="Mitte:", font=("Arial", 10)).pack(anchor="w", pady=(20,0))
        ttk.Label(txt_f, textvariable=self.dash_temp_mid_str, font=("Arial", 16, "bold")).pack(anchor="w")
        ttk.Label(txt_f, text="Unten:", font=("Arial", 10)).pack(anchor="w", pady=(10,0))
        ttk.Label(txt_f, textvariable=self.dash_temp_bot_str, font=("Arial", 16, "bold")).pack(anchor="w")
        
        # Unten: Umgebung & Status
        f_bot = ttk.Frame(self.dash_frame)
        f_bot.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
        
        ttk.Label(f_bot, text="Außen:", font=("Arial", 12)).pack(side=LEFT)
        ttk.Label(f_bot, textvariable=self.dash_aussen, font=("Arial", 20, "bold"), bootstyle="info").pack(side=LEFT, padx=10)
        ttk.Label(f_bot, textvariable=self.dash_status, font=("Arial", 12), bootstyle="secondary").pack(side=RIGHT)

    def setup_plot_tabs(self):
        # Helferfunktion um Tabs zu erstellen
        def create_tab(name, var_prefix):
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=f" {name} ")
            
            fig, ax = plt.subplots(figsize=(8, 3), dpi=100)
            fig.patch.set_facecolor(self.bg_color)
            ax.set_facecolor(self.bg_color)
            
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill=BOTH, expand=YES, padx=5, pady=5)
            
            # Referenzen speichern
            setattr(self, f"{var_prefix}_fig", fig)
            setattr(self, f"{var_prefix}_ax", ax)
            setattr(self, f"{var_prefix}_canvas", canvas)
            
            if var_prefix == "fronius":
                self.fronius_ax2 = ax.twinx()

        create_tab("PV-Leistung", "fronius")
        create_tab("Temperaturen", "bmk")
        create_tab("Batterie", "batt")
        create_tab("Ertrag", "ertrag")

    def setup_spotify_tab(self):
        self.spotify_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.spotify_frame, text=" 🎵 Spotify ")
        
        self.spotify_frame.columnconfigure(0, weight