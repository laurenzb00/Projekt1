import os
import tkinter as tk
from tkinter import StringVar

# --- DESIGN & PLOTTING ---
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
import numpy as np
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
# Wie viele Zeilen sollen maximal für die Graphen geladen werden? (Performance)
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
        
        # 2. Gesamtanzahl der Zeilen ermitteln (ohne die Datei komplett zu laden)
        with open(path, "rb") as f:
            total_lines = sum(1 for _ in f)
            
        # 3. Berechnen, ab wo wir lesen müssen
        # Wir überspringen alles bis auf die letzten 'max_rows', aber lassen Zeile 0 (Header) weg
        skip_rows = max(1, total_lines - max_rows)
        
        # 4. Daten lesen und Namen zuweisen
        df = pd.read_csv(path, sep=",", names=col_names, skiprows=skip_rows)
        
        # Leerzeichen in Spaltennamen entfernen (macht es robuster)
        df.columns = df.columns.str.strip()
        
        return df
        
    except Exception as e:
        print(f"Fehler beim Lesen von {path}: {e}")
        return None

class EnergyDashboard(ttk.Window):
    def __init__(self):
        # Fenster erstellen mit modernem Theme
        super().__init__(themename="superhero") # Alternativen: "darkly", "cyborg"
        self.title("Energy Dashboard")
        self.geometry("1024x600")
        
        # Farben aus dem Theme laden
        self.bg_color = self.style.lookup("TFrame", "background")
        self.fg_color = "white"
        self.grid_color = "#444444"

        # Variablen für UI
        self.init_variables()

        # Haupt-Container
        self.main_container = ttk.Frame(self)
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
        
        self.spotify_frame.columnconfigure(0, weight=1)
        self.spotify_frame.columnconfigure(1, weight=2)
        self.spotify_frame.rowconfigure(0, weight=1)

        # Links: Cover
        cover_frame = ttk.Frame(self.spotify_frame, bootstyle="secondary")
        cover_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        ttk.Label(cover_frame, text="🎵", font=("Arial", 80)).place(relx=0.5, rely=0.4, anchor="center")
        self.spotify_track_lbl = ttk.Label(cover_frame, text="Keine Wiedergabe", font=("Arial", 14, "bold"))
        self.spotify_track_lbl.place(relx=0.5, rely=0.7, anchor="center")

        # Rechts: Suche & Steuerung
        ctrl_frame = ttk.Frame(self.spotify_frame)
        ctrl_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # Suche
        ttk.Label(ctrl_frame, text="Musik suchen & starten", bootstyle="warning", font=("Arial", 12)).pack(anchor="w", pady=(0,5))
        search_box = ttk.Frame(ctrl_frame)
        search_box.pack(fill=X, pady=5)
        
        self.spotify_search_entry = ttk.Entry(search_box, font=("Arial", 12))
        self.spotify_search_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0,10))
        ttk.Button(search_box, text="Starten", bootstyle="warning", command=self.action_spotify_search).pack(side=RIGHT)

        ttk.Separator(ctrl_frame).pack(fill=X, pady=20)

        # Steuerung
        btn_box = ttk.Frame(ctrl_frame)
        btn_box.pack(fill=X)
        ttk.Button(btn_box, text="⏮", bootstyle="outline").pack(side=LEFT, padx=5)
        ttk.Button(btn_box, text="⏯ Play/Pause", bootstyle="success", width=15).pack(side=LEFT, padx=5)
        ttk.Button(btn_box, text="⏭", bootstyle="outline").pack(side=LEFT, padx=5)

    def setup_bottom_bar(self):
        bar = ttk.Frame(self, bootstyle="dark")
        bar.pack(side=BOTTOM, fill=X)
        ttk.Button(bar, text="Beenden", bootstyle="danger-outline", command=self.destroy).pack(side=LEFT, padx=5, pady=5)
        ttk.Label(bar, textvariable=self.status_time_var, bootstyle="inverse-dark").pack(side=RIGHT, padx=10)

    def action_spotify_search(self):
        """Dummy Funktion für Spotify Start"""
        query = self.spotify_search_entry.get()
        if query:
            self.spotify_track_lbl.config(text=f"Lade: {query}...")
            # Hier würde später der echte API Aufruf stehen
            print(f"Spotify API Aufruf: Suche nach '{query}'")

    # --- UPDATE LOGIK ---
    def update_plots(self):
        now = pd.Timestamp.now()
        
        # 1. Daten laden (mit der neuen, sicheren Funktion)
        fronius_df = read_csv_tail_fixed(FRONIUS_CSV, MAX_PLOT_POINTS)
        bmk_df = read_csv_tail_fixed(BMK_CSV, MAX_PLOT_POINTS)

        # 2. PV & Batterie Daten verarbeiten
        if fronius_df is not None and not fronius_df.empty:
            try:
                # Zeitstempel konvertieren
                fronius_df["Zeitstempel"] = pd.to_datetime(fronius_df["Zeitstempel"])
                
                # Letzten Wert für Dashboard holen
                last = fronius_df.iloc[-1]
                
                # Werte auslesen (Fehler abfangen, falls Spalte fehlt)
                pv = last.get("PV-Leistung (kW)", 0)
                haus = last.get("Hausverbrauch (kW)", 0)
                soc = last.get("Batterieladestand (%)", 0)
                
                # UI Update
                self.dash_pv_now.set(f"{pv:.2f} kW")
                self.dash_haus_now.set(f"{haus:.2f} kW")
                self.meter_batt.configure(amountused=int(soc))
                
                # Graphen Update
                self._plot_fronius(fronius_df, now)
                self._plot_battery(fronius_df, now)
                self.dash_status.set("PV Daten aktuell.")
            except Exception as e:
                print(f"Fehler bei Fronius Verarbeitung: {e}")

        # 3. Temperatur Daten verarbeiten
        if bmk_df is not None and not bmk_df.empty:
            try:
                bmk_df["Zeitstempel"] = pd.to_datetime(bmk_df["Zeitstempel"])
                last = bmk_df.iloc[-1]
                
                top = last.get("Pufferspeicher Oben", 0)
                mid = last.get("Pufferspeicher Mitte", 0)
                bot = last.get("Pufferspeicher Unten", 0)
                aussen = last.get("Außentemperatur", 0)
                
                self.gauge_puffer.configure(value=top, mask=f"Oben: {top:.1f}°C")
                self.dash_temp_mid_str.set(f"{mid:.1f} °C")
                self.dash_temp_bot_str.set(f"{bot:.1f} °C")
                self.dash_aussen.set(f"{aussen:.1f} °C")
                
                self._plot_temps(bmk_df, now)
            except Exception as e:
                print(f"Fehler bei BMK Verarbeitung: {e}")

        self.status_time_var.set(f"Letztes Update: {now.strftime('%H:%M:%S')}")
        self.after(UPDATE_INTERVAL, self.update_plots)

    # --- PLOTTING DETAILS ---
    def _style_ax(self, ax):
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

        # Nur letzte 24h
        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=24))
        df_sub = df.loc[mask]

        if not df_sub.empty:
            ax.fill_between(df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"], color="#f39c12", alpha=0.3)
            ax.plot(df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"], label="PV", color="#f39c12")
            ax.plot(df_sub["Zeitstempel"], df_sub["Hausverbrauch (kW)"], label="Haus", color="#3498db")
            
            # Batterie Linie auf zweiter Achse
            ax2.plot(df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"], color="white", linestyle=":", alpha=0.5, label="SoC")
            ax2.set_ylim(0, 100)
            
            ax.legend(loc="upper left")
            ax.set_title("PV Leistung & Verbrauch (24h)", color="white")
            
            # Formatierung X-Achse
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.fronius_fig.autofmt_xdate()
        
        self.fronius_canvas.draw()

    def _plot_battery(self, df, now):
        ax = self.batt_ax
        ax.clear()
        self._style_ax(ax)
        
        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=48))
        df_sub = df.loc[mask]
        
        if not df_sub.empty:
            ax.plot(df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"], color="#2ecc71", linewidth=2)
            ax.fill_between(df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"], color="#2ecc71", alpha=0.2)
            ax.set_ylim(0, 100)
            ax.set_title("Batterieverlauf (48h)", color="white")
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.batt_fig.autofmt_xdate()
            
        self.batt_canvas.draw()

    def _plot_temps(self, df, now):
        ax = self.bmk_ax
        ax.clear()
        self._style_ax(ax)
        
        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=24))
        df_sub = df.loc[mask]
        
        if not df_sub.empty:
            ax.plot(df_sub["Zeitstempel"], df_sub["Pufferspeicher Oben"], color="#e74c3c", label="Oben")
            ax.plot(df_sub["Zeitstempel"], df_sub["Pufferspeicher Mitte"], color="#e67e22", label="Mitte")
            ax.plot(df_sub["Zeitstempel"], df_sub["Pufferspeicher Unten"], color="#3498db", label="Unten")
            ax.legend()
            ax.set_title("Pufferspeicher Temperaturen", color="white")
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.bmk_fig.autofmt_xdate()
            
        self.bmk_canvas.draw()

if __name__ == "__main__":
    app = EnergyDashboard()
    app.mainloop()