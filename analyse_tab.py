import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import os

# Konfiguration
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")

class AnalyseTab:
    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook
        self.style = ttk.Style()
        
        # Tab erstellen
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text=" Analyse ")
        
        # Header
        header = ttk.Frame(self.tab_frame)
        header.pack(fill=X, pady=10, padx=10)
        ttk.Label(header, text="Energie-Effizienz Analyse", font=("Arial", 18, "bold"), bootstyle="inverse-dark").pack(side=LEFT)
        ttk.Button(header, text="Aktualisieren", command=self.update_plot, bootstyle="info-outline").pack(side=RIGHT)

        # Plot Area
        self.fig, self.ax1 = plt.subplots(figsize=(8, 4), dpi=100)
        self.chart_bg = self.style.lookup("TFrame", "background")
        self.fig.patch.set_facecolor(self.chart_bg)
        self.ax1.set_facecolor(self.chart_bg)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_frame)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # Erster Aufruf
        self.update_plot()

    def read_csv_data(self, path):
        if not os.path.exists(path): return pd.DataFrame()
        try:
            # Nur letzte 5000 Zeilen für Performance
            df = pd.read_csv(path) # Hier einfach alles lesen oder optimiert wie in visualisierung_live
            # Quick fix für Header parsing wenn nötig (analog zu visualisierung_live)
            df.columns = df.columns.str.strip()
            df["Zeitstempel"] = pd.to_datetime(df["Zeitstempel"])
            return df
        except:
            return pd.DataFrame()

    def update_plot(self):
        self.ax1.clear()
        
        # Daten laden
        df_pv = self.read_csv_data(FRONIUS_CSV)
        df_temp = self.read_csv_data(BMK_CSV)
        
        if df_pv.empty or df_temp.empty:
            self.ax1.text(0.5, 0.5, "Zu wenig Daten für Analyse", color="white", ha="center")
            self.canvas.draw()
            return

        # Letzte 3 Tage filtern
        now = pd.Timestamp.now()
        start_date = now - pd.Timedelta(days=3)
        
        df_pv = df_pv[df_pv["Zeitstempel"] >= start_date]
        df_temp = df_temp[df_temp["Zeitstempel"] >= start_date]

        # Styling
        self.ax1.tick_params(colors="white", which='both')
        self.ax1.set_xlabel("Zeit", color="white")
        for spine in self.ax1.spines.values(): spine.set_color("#555555")

        # Plot 1: PV Leistung (Linke Achse)
        color1 = '#f1c40f' # Gelb
        self.ax1.set_ylabel('PV Leistung (kW)', color=color1)
        self.ax1.plot(df_pv["Zeitstempel"], df_pv["PV-Leistung (kW)"], color=color1, label="PV", linewidth=1.5)
        self.ax1.tick_params(axis='y', labelcolor=color1)
        self.ax1.fill_between(df_pv["Zeitstempel"], df_pv["PV-Leistung (kW)"], color=color1, alpha=0.1)

        # Plot 2: Puffer Oben (Rechte Achse)
        ax2 = self.ax1.twinx()
        color2 = '#e74c3c' # Rot
        ax2.set_ylabel('Puffer Oben (°C)', color=color2)
        ax2.plot(df_temp["Zeitstempel"], df_temp["Pufferspeicher Oben"], color=color2, label="Puffer", linewidth=2)
        ax2.tick_params(axis='y', labelcolor=color2)
        
        # Design für Achse 2
        for spine in ax2.spines.values(): spine.set_color("#555555")

        plt.title("Zusammenhang: Sonne vs. Wärmespeicher (3 Tage)", color="white")
        self.fig.autofmt_xdate()
        self.canvas.draw()
        
    def stop(self):
        pass # Nichts zu stoppen