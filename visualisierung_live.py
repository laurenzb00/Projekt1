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
import numpy as np
from ttkbootstrap.icons import Icon

# Matplotlib fest auf Dunkel setzen
plt.style.use("dark_background")

# --- KONFIGURATION ---
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")

# Aktualisierungsrate (ms)
UPDATE_INTERVAL = 60 * 1000 
MAX_PLOT_POINTS = 10000 

# --- HILFSFUNKTION: CSV SICHER LESEN ---
def read_csv_tail_fixed(path: str, max_rows: int) -> pd.DataFrame:
    if not os.path.exists(path):
        return None
    try:
        header_df = pd.read_csv(path, nrows=0, sep=",")
        col_names = header_df.columns.tolist()
        with open(path, "rb") as f:
            total_lines = sum(1 for _ in f)
        skip_rows = max(1, total_lines - max_rows)
        df = pd.read_csv(path, sep=",", names=col_names, skiprows=skip_rows)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print(f"Fehler beim Lesen von {path}: {e}")
        return None

# --- HAUPTKLASSE ---
class LivePlotApp:
    def __init__(self, root):
        self.root = root
        
        self.style = ttk.Style()
        self.chart_bg = self.style.lookup("TFrame", "background")
        self.chart_fg = "white"
        self.chart_grid = "#555555"
        
        self.init_variables()
        self.spotify_instance = None 

        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=BOTH, expand=YES)

        self.notebook = ttk.Notebook(self.main_container, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        # Tabs erstellen
        self.setup_dashboard_tab()
        self.setup_plot_tabs()

        self.setup_bottom_bar()
        self.update_plots()

        # Ensure the application starts in fullscreen mode
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))

    def init_variables(self):
        self.dash_pv_now = StringVar(value="-- kW")
        self.dash_haus_now = StringVar(value="-- kW")
        self.dash_ertrag_heute = StringVar(value="-- kWh") 
        self.dash_autarkie = StringVar(value="-- %")       
        
        self.dash_temp_top_str = StringVar(value="-- °C")
        self.dash_temp_mid_str = StringVar(value="-- °C")
        self.dash_temp_bot_str = StringVar(value="-- °C")
        self.dash_aussen = StringVar(value="-- °C")
        
        self.dash_status = StringVar(value="System startet...")
        self.status_time_var = StringVar(value="-")

    # --- UI SETUP ---
    def setup_dashboard_tab(self):
            # Neues Layout für das Dashboard
            self.dashboard_frame = ttk.Frame(self.root, padding=10)
            self.dashboard_frame.pack(fill=tk.BOTH, expand=True)

            # PV-Leistung und Verbrauch
            self.pv_frame = ttk.Frame(self.dashboard_frame, padding=10, bootstyle="info")
            self.pv_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            ttk.Label(self.pv_frame, text="PV Erzeugung", font=("Arial", 14)).pack()
            ttk.Label(self.pv_frame, text="1.70 kW", font=("Arial", 24)).pack()

            self.verbrauch_frame = ttk.Frame(self.dashboard_frame, padding=10, bootstyle="info")
            self.verbrauch_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            ttk.Label(self.verbrauch_frame, text="Verbrauch", font=("Arial", 14)).pack()
            ttk.Label(self.verbrauch_frame, text="6.40 kW", font=("Arial", 24)).pack()

            # Speicher
            self.speicher_frame = ttk.Frame(self.dashboard_frame, padding=10, bootstyle="success")
            self.speicher_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
            ttk.Label(self.speicher_frame, text="Speicher", font=("Arial", 14)).pack()
            ttk.Label(self.speicher_frame, text="8 % SoC", font=("Arial", 24)).pack()

            # Pufferspeicher
            self.puffer_frame = ttk.Frame(self.dashboard_frame, padding=10, bootstyle="danger")
            self.puffer_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
            ttk.Label(self.puffer_frame, text="Pufferspeicher", font=("Arial", 14)).pack()

            self.canvas_puffer = tk.Canvas(self.puffer_frame, width=200, height=180, bg="black")
            self.canvas_puffer.pack(anchor="center", pady=10)

            update_puffer_animation()

            # Dynamische Größenanpassung
            self.root.grid_rowconfigure(0, weight=1)
            self.root.grid_rowconfigure(1, weight=1)
            self.root.grid_columnconfigure(0, weight=1)
            self.root.grid_columnconfigure(1, weight=1)
            self.root.grid_columnconfigure(2, weight=1)

    def setup_plot_tabs(self):
        # Alle Tabs aktiv
        self.create_single_plot_tab("PV-Leistung", "fronius")
        self.create_single_plot_tab("Temperaturen", "bmk")
        self.create_single_plot_tab("Batterie", "batt")  # WIEDER DA
        self.create_single_plot_tab("Ertrag", "ertrag")

    def create_single_plot_tab(self, name, var_prefix):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=f" {name} ")
        
        fig, ax = plt.subplots(figsize=(8, 3), dpi=100)
        fig.patch.set_facecolor(self.chart_bg)
        ax.set_facecolor(self.chart_bg)
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        setattr(self, f"{var_prefix}_fig", fig)
        setattr(self, f"{var_prefix}_ax", ax)
        setattr(self, f"{var_prefix}_canvas", canvas)
        
        if var_prefix == "fronius":
            self.fronius_ax2 = ax.twinx()

    def setup_bottom_bar(self):
        bar = ttk.Frame(self.root, bootstyle="dark")
        bar.pack(side=BOTTOM, fill=X)
        ttk.Button(bar, text="Beenden", bootstyle="danger-outline", command=self.root.destroy).pack(side=LEFT, padx=5, pady=5)
        ttk.Label(bar, textvariable=self.status_time_var, bootstyle="inverse-dark").pack(side=RIGHT, padx=10)

    # --- UPDATE LOGIC ---
    def update_plots(self):
        now = pd.Timestamp.now()
        
        fronius_df = read_csv_tail_fixed(FRONIUS_CSV, MAX_PLOT_POINTS)
        bmk_df = read_csv_tail_fixed(BMK_CSV, MAX_PLOT_POINTS)

        # 1. PV Daten
        if fronius_df is not None and not fronius_df.empty:
            try:
                fronius_df["Zeitstempel"] = pd.to_datetime(fronius_df["Zeitstempel"])
                last = fronius_df.iloc[-1]
                
                pv = last.get("PV-Leistung (kW)", 0)
                haus = last.get("Hausverbrauch (kW)", 0)
                soc = last.get("Batterieladestand (%)", 0)
                
                self.dash_pv_now.set(f"{pv:.2f} kW")
                self.dash_haus_now.set(f"{haus:.2f} kW")
                self.meter_batt.configure(amountused=int(soc))
                
                if haus > 0:
                    autarkie = min(pv, haus) / haus * 100
                    self.dash_autarkie.set(f"{int(autarkie)} %")
                else:
                    self.dash_autarkie.set("100 %")
                
                today_mask = fronius_df["Zeitstempel"].dt.date == now.date()
                df_today = fronius_df[today_mask]
                if not df_today.empty:
                    df_today = df_today.sort_values(by="Zeitstempel")
                    df_today["TimeDiff"] = df_today["Zeitstempel"].diff().dt.total_seconds().fillna(0) / 3600
                    df_today["Energy"] = df_today["PV-Leistung (kW)"] * df_today["TimeDiff"]
                    kwh_today = df_today["Energy"].sum()
                    self.dash_ertrag_heute.set(f"{kwh_today:.1f} kWh")

                self._plot_fronius(fronius_df, now)
                self._plot_battery(fronius_df, now) # WIEDER AKTIV
                self._plot_ertrag(fronius_df, now)
                self.dash_status.set("PV Daten aktuell.")
            except Exception as e:
                print(f"Fronius Update Fehler: {e}")

        # 2. Temperatur Daten
        if bmk_df is not None and not bmk_df.empty:
            try:
                bmk_df["Zeitstempel"] = pd.to_datetime(bmk_df["Zeitstempel"])
                last = bmk_df.iloc[-1]
                
                top = last.get("Pufferspeicher Oben", 0)
                mid = last.get("Pufferspeicher Mitte", 0)
                bot = last.get("Pufferspeicher Unten", 0)
                aussen = last.get("Außentemperatur", 0)
                
                self.gauge_puffer.configure(value=top)
                self.dash_temp_top_str.set(f"{top:.1f} °C")
                self.dash_temp_mid_str.set(f"{mid:.1f} °C")
                self.dash_temp_bot_str.set(f"{bot:.1f} °C")
                self.dash_aussen.set(f"{aussen:.1f} °C")
                
                self._plot_temps(bmk_df, now)
            except Exception as e:
                print(f"BMK Update Fehler: {e}")

        self.status_time_var.set(f"Update: {now.strftime('%H:%M:%S')}")
        self.root.after(UPDATE_INTERVAL, self.update_plots)

    # --- PLOTTING ---
    def _style_ax(self, ax):
        ax.set_facecolor(self.chart_bg)
        ax.tick_params(colors=self.chart_fg, which='both')
        for spine in ax.spines.values():
            spine.set_color(self.chart_grid)
        ax.yaxis.label.set_color(self.chart_fg)
        ax.xaxis.label.set_color(self.chart_fg)
        ax.grid(True, color=self.chart_grid, linestyle='--', alpha=0.3)

    def _plot_fronius(self, df, now):
        ax = self.fronius_ax
        ax2 = self.fronius_ax2
        ax.clear()
        ax2.clear()
        self._style_ax(ax)

        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=48))
        df_sub = df.loc[mask]

        if not df_sub.empty:
            ax.fill_between(df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"], color="#f39c12", alpha=0.3)
            ax.plot(df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"], label="PV", color="#f39c12")
            ax.plot(df_sub["Zeitstempel"], df_sub["Hausverbrauch (kW)"], label="Haus", color="#3498db")
            
            ax2.plot(df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"], color="white", linestyle=":", alpha=0.5, label="SoC")
            ax2.set_ylim(0, 100)
            ax2.tick_params(colors="white")
            
            ax.legend(loc="upper left", facecolor=self.chart_bg, labelcolor="white")
            ax.set_title("PV Leistung & Verbrauch (48h)", color="white")
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

    def _plot_ertrag(self, df, now):
        ax = self.ertrag_ax
        ax.clear()
        self._style_ax(ax)

        try:
            df_calc = df.copy()
            df_calc.set_index("Zeitstempel", inplace=True)
            df_hourly = df_calc["PV-Leistung (kW)"].resample('h').mean()
            df_daily = df_hourly.resample('D').sum()

            # Adjust to show daily yields for the last 30 days
            start_date = (now - pd.Timedelta(days=30)).replace(hour=0, minute=0, second=0)
            df_daily = df_daily[df_daily.index >= start_date]

            if not df_daily.empty:
                ax.bar(df_daily.index, df_daily.values, color="#f1c40f", width=0.5)
                ax.set_title("Tagesertrag (letzte 30 Tage) in kWh", color="white")
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))
                ax.set_xlabel("Datum", color="white")
                ax.set_ylabel("Ertrag (kWh)", color="white")
            else:
                ax.text(0.5, 0.5, "Keine Daten verfügbar", color="white", ha="center")
        except Exception as e:
            print(f"Ertrag Plot Fehler: {e}")

        self.ertrag_canvas.draw()

    def _plot_temps(self, df, now):
        ax = self.bmk_ax
        ax.clear()
        self._style_ax(ax)
        
        mask = df["Zeitstempel"] >= (now - pd.Timedelta(days=7))
        df_sub = df.loc[mask]
        
        if not df_sub.empty:
            ax.plot(df_sub["Zeitstempel"], df_sub["Pufferspeicher Oben"], color="#e74c3c", label="Oben")
            ax.plot(df_sub["Zeitstempel"], df_sub["Pufferspeicher Mitte"], color="#e67e22", label="Mitte")
            ax.plot(df_sub["Zeitstempel"], df_sub["Pufferspeicher Unten"], color="#3498db", label="Unten")
            ax.plot(df_sub["Zeitstempel"], df_sub["Außentemperatur"], color="cyan", label="Außen", linestyle="--", alpha=0.7)
            
            ax.legend(facecolor=self.chart_bg, labelcolor="white")
            ax.set_title("Temperaturen (7 Tage)", color="white")
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))
            self.bmk_fig.autofmt_xdate()
        self.bmk_canvas.draw()

    # --- Neue Funktionen für Buttons ---
    def show_consumption_details(self):
        print("Verbrauchsdetails anzeigen")
        # Hier könnte ein neues Fenster oder eine Ansicht geöffnet werden

    def show_historical_data(self):
        print("Historische Daten anzeigen")
        # Hier könnte ein Diagramm oder eine Ansicht geöffnet werden

        # Sicherstellen, dass die Animation ohne Icon funktioniert
        try:
            icon_path = os.path.join(WORKING_DIRECTORY, "icons/puffer.png")
            if not os.path.exists(icon_path):
                print("Warnung: Icon icons/puffer.png konnte nicht geladen werden.")
        except Exception as e:
            print(f"Fehler beim Laden des Icons: {e}")