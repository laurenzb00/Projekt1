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
        self.dashboard_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
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
        # Hauptcontainer mit dunklem Hintergrund
        self.dashboard_frame = tk.Frame(self.dashboard_tab, bg="#1a1d2e")
        self.dashboard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Grid-Konfiguration für gleichmäßige Verteilung
        for i in range(4):
            self.dashboard_frame.grid_columnconfigure(i, weight=1)
        for i in range(3):
            self.dashboard_frame.grid_rowconfigure(i, weight=1)

        # ===== OBERE REIHE: Metrikkarten =====
        # PV Erzeugung - Gradient Cyan-Blue
        self.pv_card = self._create_metric_card(
            parent=self.dashboard_frame,
            row=0, col=0,
            title="PV Erzeugung",
            bg_start="#22d3ee", bg_end="#0ea5e9",
            icon="☀"
        )
        self.pv_value_label = tk.Label(
            self.pv_card, textvariable=self.dash_pv_now,
            font=("Segoe UI", 36, "bold"), fg="white", bg="#0ea5e9"
        )
        self.pv_value_label.pack(pady=(10, 5))

        # Verbrauch - Gradient Purple-Pink
        self.verbrauch_card = self._create_metric_card(
            parent=self.dashboard_frame,
            row=0, col=1,
            title="Verbrauch",
            bg_start="#a855f7", bg_end="#ec4899",
            icon="⚡"
        )
        self.verbrauch_value_label = tk.Label(
            self.verbrauch_card, textvariable=self.dash_haus_now,
            font=("Segoe UI", 36, "bold"), fg="white", bg="#ec4899"
        )
        self.verbrauch_value_label.pack(pady=(10, 5))

        # Batterie SoC - Gradient Green-Emerald
        self.battery_card = self._create_metric_card(
            parent=self.dashboard_frame,
            row=0, col=2,
            title="Batterie",
            bg_start="#10b981", bg_end="#059669",
            icon="🔋"
        )
        self.battery_soc_var = tk.StringVar(value="0 %")
        self.battery_value_label = tk.Label(
            self.battery_card, textvariable=self.battery_soc_var,
            font=("Segoe UI", 36, "bold"), fg="white", bg="#059669"
        )
        self.battery_value_label.pack(pady=(10, 5))

        # Tagesertrag - Gradient Orange-Amber
        self.ertrag_card = self._create_metric_card(
            parent=self.dashboard_frame,
            row=0, col=3,
            title="Tagesertrag",
            bg_start="#f59e0b", bg_end="#d97706",
            icon="📊"
        )
        self.ertrag_value_label = tk.Label(
            self.ertrag_card, textvariable=self.dash_ertrag_heute,
            font=("Segoe UI", 36, "bold"), fg="white", bg="#d97706"
        )
        self.ertrag_value_label.pack(pady=(10, 5))

        # ===== MITTLERE REIHE: Autarkie & Live-Charts =====
        # Autarkie Gauge
        self.autarkie_card = self._create_chart_card(
            parent=self.dashboard_frame,
            row=1, col=0, colspan=1,
            title="Autarkie"
        )
        self.autarkie_canvas = tk.Canvas(
            self.autarkie_card, width=200, height=200, 
            bg="#16213e", highlightthickness=0
        )
        self.autarkie_canvas.pack(pady=10)

        # Pufferspeicher Visualisierung (verbessert)
        self.puffer_card = self._create_chart_card(
            parent=self.dashboard_frame,
            row=1, col=1, colspan=2,
            title="Pufferspeicher"
        )
        self.canvas_puffer = tk.Canvas(
            self.puffer_card, width=400, height=200,
            bg="#16213e", highlightthickness=0
        )
        self.canvas_puffer.pack(pady=10)

        # Außentemperatur Display
        self.aussen_card = self._create_metric_card(
            parent=self.dashboard_frame,
            row=1, col=3,
            title="Außentemperatur",
            bg_start="#6366f1", bg_end="#4f46e5",
            icon="🌡"
        )
        self.aussen_value_label = tk.Label(
            self.aussen_card, textvariable=self.dash_aussen,
            font=("Segoe UI", 32, "bold"), fg="white", bg="#4f46e5"
        )
        self.aussen_value_label.pack(pady=(10, 5))

        # ===== UNTERE REIHE: Mini Charts =====
        # PV Trend (letzte 24h)
        self.pv_trend_card = self._create_chart_card(
            parent=self.dashboard_frame,
            row=2, col=0, colspan=2,
            title="PV Trend (24h)"
        )
        self.pv_trend_fig, self.pv_trend_ax = self._create_mini_chart()
        self.pv_trend_canvas = FigureCanvasTkAgg(self.pv_trend_fig, master=self.pv_trend_card)
        self.pv_trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Temperatur Trend
        self.temp_trend_card = self._create_chart_card(
            parent=self.dashboard_frame,
            row=2, col=2, colspan=2,
            title="Temperatur Trend (24h)"
        )
        self.temp_trend_fig, self.temp_trend_ax = self._create_mini_chart()
        self.temp_trend_canvas = FigureCanvasTkAgg(self.temp_trend_fig, master=self.temp_trend_card)
        self.temp_trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Start Animationen
        self.update_puffer_animation()
        self.update_autarkie_gauge()

    def _create_metric_card(self, parent, row, col, title, bg_start, bg_end, icon):
        """Erstellt eine moderne Metrik-Karte mit Gradient"""
        card = tk.Frame(parent, bg=bg_end, relief=tk.FLAT, bd=0)
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        
        # Header mit Icon
        header = tk.Frame(card, bg=bg_end)
        header.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        icon_label = tk.Label(header, text=icon, font=("Segoe UI", 24), bg=bg_end, fg="white")
        icon_label.pack(side=tk.LEFT)
        
        title_label = tk.Label(
            header, text=title, 
            font=("Segoe UI", 14, "bold"), 
            bg=bg_end, fg="white"
        )
        title_label.pack(side=tk.LEFT, padx=10)
        
        return card

    def _create_chart_card(self, parent, row, col, colspan, title):
        """Erstellt eine Karte für Charts"""
        card = tk.Frame(parent, bg="#16213e", relief=tk.FLAT, bd=0)
        card.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=8, pady=8)
        
        # Header
        header = tk.Frame(card, bg="#1e2a47")
        header.pack(fill=tk.X)
        
        title_label = tk.Label(
            header, text=title,
            font=("Segoe UI", 12, "bold"),
            bg="#1e2a47", fg="white",
            pady=10, padx=15
        )
        title_label.pack(anchor="w")
        
        return card

    def _create_mini_chart(self):
        """Erstellt ein kleines Chart für Trends"""
        fig, ax = plt.subplots(figsize=(5, 2), dpi=80)
        fig.patch.set_facecolor("#16213e")
        ax.set_facecolor("#16213e")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#2d3a5f')
        ax.spines['bottom'].set_color('#2d3a5f')
        ax.tick_params(colors='#8892b0', labelsize=8)
        ax.grid(False)
        return fig, ax

    def setup_plot_tabs(self):
        # Alle Tabs aktiv
        self.create_single_plot_tab("PV-Leistung", "fronius")
        self.create_single_plot_tab("Temperaturen", "bmk")
        self.create_single_plot_tab("Batterie", "batt")  # WIEDER DA
        self.create_single_plot_tab("Ertrag", "ertrag")

    def create_single_plot_tab(self, name, var_prefix):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=f" {name} ")
        
        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        fig.patch.set_facecolor("#16213e")
        ax.set_facecolor("#16213e")
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
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
                self.battery_soc_var.set(f"{int(soc)} %")
                
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
                self._plot_battery(fronius_df, now)
                self._plot_ertrag(fronius_df, now)
                self._update_pv_trend(fronius_df, now)
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
                
                self.dash_temp_top_str.set(f"{top:.1f} °C")
                self.dash_temp_mid_str.set(f"{mid:.1f} °C")
                self.dash_temp_bot_str.set(f"{bot:.1f} °C")
                self.dash_aussen.set(f"{aussen:.1f} °C")
                
                self._plot_temps(bmk_df, now)
                self._update_temp_trend(bmk_df, now)
            except Exception as e:
                print(f"BMK Update Fehler: {e}")

        self.status_time_var.set(f"Update: {now.strftime('%H:%M:%S')}")
        # Schedule update safely
        if self.root.winfo_exists():
            self.root.after(UPDATE_INTERVAL, self.update_plots)

    # --- PLOTTING ---
    def _style_ax(self, ax):
        ax.set_facecolor("#16213e")
        ax.tick_params(colors='#8892b0', which='both', labelsize=10)
        for spine in ax.spines.values():
            spine.set_color('#2d3a5f')
            spine.set_linewidth(1.5)
        ax.yaxis.label.set_color('#8892b0')
        ax.xaxis.label.set_color('#8892b0')
        ax.title.set_color('white')
        ax.grid(True, color='#2d3a5f', linestyle='--', alpha=0.3, linewidth=0.8)

    def _plot_fronius(self, df, now):
        ax = self.fronius_ax
        ax2 = self.fronius_ax2
        ax.clear()
        ax2.clear()
        self._style_ax(ax)

        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=48))
        df_sub = df.loc[mask]

        if not df_sub.empty:
            # PV mit Gradient Fill
            ax.fill_between(
                df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"],
                color="#22d3ee", alpha=0.4, label="PV"
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"],
                color="#0ea5e9", linewidth=2.5
            )
            
            # Hausverbrauch
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Hausverbrauch (kW)"],
                label="Verbrauch", color="#ec4899", linewidth=2.5
            )
            
            # Batterieladestand auf zweiter Y-Achse
            ax2.plot(
                df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"],
                color="#10b981", linestyle=":", alpha=0.7, linewidth=2, label="SoC"
            )
            ax2.set_ylim(0, 100)
            ax2.tick_params(colors="#8892b0")
            ax2.spines['right'].set_color('#2d3a5f')
            ax2.yaxis.label.set_color('#10b981')
            ax2.set_ylabel("Batterie (%)", color="#10b981", fontsize=10)
            
            ax.legend(loc="upper left", facecolor='#16213e', edgecolor='#2d3a5f',
                     labelcolor='white', fontsize=10, framealpha=0.9)
            ax.set_title("PV Leistung & Verbrauch (48h)", color="white", fontsize=12, fontweight='bold')
            ax.set_ylabel("Leistung (kW)", color="#8892b0", fontsize=10)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.fronius_fig.patch.set_facecolor("#16213e")
            self.fronius_fig.autofmt_xdate()
        self.fronius_canvas.draw()

    def _plot_battery(self, df, now):
        ax = self.batt_ax
        ax.clear()
        self._style_ax(ax)
        
        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=48))
        df_sub = df.loc[mask]
        
        if not df_sub.empty:
            # Gradient Fill
            ax.fill_between(
                df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"],
                color="#10b981", alpha=0.4
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"],
                color="#10b981", linewidth=2.5
            )
            ax.set_ylim(0, 100)
            ax.set_title("Batterieverlauf (48h)", color="white", fontsize=12, fontweight='bold')
            ax.set_ylabel("Ladestand (%)", color="#8892b0", fontsize=10)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.batt_fig.patch.set_facecolor("#16213e")
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

            start_date = (now - pd.Timedelta(days=30)).replace(hour=0, minute=0, second=0)
            df_daily = df_daily[df_daily.index >= start_date]

            if not df_daily.empty:
                bars = ax.bar(
                    df_daily.index, df_daily.values,
                    color="#f59e0b", width=0.7, edgecolor="#d97706", linewidth=1.5
                )
                
                # Gradient-Effekt auf Bars
                for bar in bars:
                    bar.set_alpha(0.8)
                
                ax.set_title("Tagesertrag (letzte 30 Tage)", color="white", 
                           fontsize=12, fontweight='bold')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))
                ax.set_xlabel("Datum", color="#8892b0", fontsize=10)
                ax.set_ylabel("Ertrag (kWh)", color="#8892b0", fontsize=10)
                self.ertrag_fig.patch.set_facecolor("#16213e")
            else:
                ax.text(0.5, 0.5, "Keine Daten verfügbar", 
                       color="white", ha="center", transform=ax.transAxes)
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
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Oben"],
                color="#ef4444", label="Oben", linewidth=2.5
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Mitte"],
                color="#f59e0b", label="Mitte", linewidth=2.5
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Unten"],
                color="#3b82f6", label="Unten", linewidth=2.5
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Außentemperatur"],
                color="#06b6d4", label="Außen", linestyle="--", 
                alpha=0.7, linewidth=2
            )
            
            ax.legend(facecolor='#16213e', edgecolor='#2d3a5f',
                     labelcolor='white', fontsize=10, framealpha=0.9)
            ax.set_title("Temperaturen (7 Tage)", color="white", 
                        fontsize=12, fontweight='bold')
            ax.set_ylabel("Temperatur (°C)", color="#8892b0", fontsize=10)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))
            self.bmk_fig.patch.set_facecolor("#16213e")
            self.bmk_fig.autofmt_xdate()
        self.bmk_canvas.draw()

    # --- Neue Funktionen für Buttons ---
    def show_consumption_details(self):
        print("Verbrauchsdetails anzeigen")
        # Hier könnte ein neues Fenster oder eine Ansicht geöffnet werden

    def show_historical_data(self):
        print("Historische Daten anzeigen")
        # Hier könnte ein Diagramm oder eine Ansicht geöffnet werden

    def update_puffer_animation(self):
        try:
            top_temp = float(self.dash_temp_top_str.get().replace(" °C", "").replace("-- ", "0"))
            mid_temp = float(self.dash_temp_mid_str.get().replace(" °C", "").replace("-- ", "0"))
            bot_temp = float(self.dash_temp_bot_str.get().replace(" °C", "").replace("-- ", "0"))
        except (ValueError, AttributeError):
            top_temp, mid_temp, bot_temp = 0, 0, 0

        self.canvas_puffer.delete("all")

        # Moderner Pufferspeicher mit 3D-Effekt
        x_start, y_start = 100, 30
        width, height_per_section = 100, 50

        # Schatten
        self.canvas_puffer.create_rectangle(
            x_start + 5, y_start + 5, x_start + width + 5, y_start + height_per_section * 3 + 5,
            fill="#000000", outline="", stipple="gray50"
        )

        # Hauptbehälter
        sections = [
            (top_temp, "Oben", y_start),
            (mid_temp, "Mitte", y_start + height_per_section),
            (bot_temp, "Unten", y_start + height_per_section * 2)
        ]

        for temp, label, y_pos in sections:
            color = self._get_temp_gradient_color(temp)
            
            # Sektion mit Gradient-Effekt
            self.canvas_puffer.create_rectangle(
                x_start, y_pos, x_start + width, y_pos + height_per_section,
                fill=color, outline="#2d3a5f", width=2
            )
            
            # Temperaturanzeige mit modernem Stil
            self.canvas_puffer.create_text(
                x_start + width + 30, y_pos + height_per_section // 2,
                text=f"{temp:.1f}°C",
                fill="white", font=("Segoe UI", 14, "bold"), anchor="w"
            )
            
            # Label
            self.canvas_puffer.create_text(
                x_start + width // 2, y_pos + height_per_section // 2,
                text=label,
                fill="white", font=("Segoe UI", 10, "bold")
            )

        # Überschrift
        self.canvas_puffer.create_text(
            200, 10,
            text="Pufferspeicher Status",
            fill="#8892b0", font=("Segoe UI", 12, "bold")
        )

        if self.root.winfo_exists():
            self.root.after(2000, self.update_puffer_animation)

    def _get_temp_gradient_color(self, temp):
        """Gibt Farbe basierend auf Temperatur zurück (Gradient)"""
        if temp < 20:
            return "#3b82f6"  # Blau
        elif temp < 35:
            return "#10b981"  # Grün
        elif temp < 50:
            return "#f59e0b"  # Orange
        elif temp < 65:
            return "#ef4444"  # Rot
        else:
            return "#dc2626"  # Dunkelrot

    def update_autarkie_gauge(self):
        """Erstellt eine moderne Autarkie-Anzeige"""
        try:
            autarkie_str = self.dash_autarkie.get().replace(" %", "").replace("-- ", "0")
            autarkie = float(autarkie_str)
        except (ValueError, AttributeError):
            autarkie = 0

        self.autarkie_canvas.delete("all")

        # Kreisförmige Gauge
        center_x, center_y = 100, 100
        radius = 70

        # Hintergrund-Kreis
        self.autarkie_canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            fill="#1e2a47", outline="#2d3a5f", width=3
        )

        # Fortschritts-Bogen
        extent = -360 * (autarkie / 100)
        color = "#10b981" if autarkie >= 70 else "#f59e0b" if autarkie >= 40 else "#ef4444"
        
        self.autarkie_canvas.create_arc(
            center_x - radius + 10, center_y - radius + 10,
            center_x + radius - 10, center_y + radius - 10,
            start=90, extent=extent, fill=color, outline="", width=0
        )

        # Innerer Kreis
        inner_radius = 50
        self.autarkie_canvas.create_oval(
            center_x - inner_radius, center_y - inner_radius,
            center_x + inner_radius, center_y + inner_radius,
            fill="#16213e", outline=""
        )

        # Prozentzahl
        self.autarkie_canvas.create_text(
            center_x, center_y,
            text=f"{int(autarkie)}%",
            fill="white", font=("Segoe UI", 24, "bold")
        )

        # Label
        self.autarkie_canvas.create_text(
            center_x, center_y + 30,
            text="Autarkie",
            fill="#8892b0", font=("Segoe UI", 10)
        )

        if self.root.winfo_exists():
            self.root.after(2000, self.update_autarkie_gauge)

    def _update_pv_trend(self, df, now):
        """Aktualisiert den PV-Trend Mini-Chart"""
        ax = self.pv_trend_ax
        ax.clear()
        
        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=24))
        df_sub = df.loc[mask]
        
        if not df_sub.empty:
            # Gradient Fill
            ax.fill_between(
                df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"],
                alpha=0.6, color="#22d3ee"
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"],
                color="#0ea5e9", linewidth=2
            )
            
            ax.set_facecolor("#16213e")
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#2d3a5f')
            ax.spines['bottom'].set_color('#2d3a5f')
            ax.tick_params(colors='#8892b0', labelsize=8)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.set_ylabel("kW", color="#8892b0", fontsize=9)
            
        self.pv_trend_canvas.draw()

    def _update_temp_trend(self, df, now):
        """Aktualisiert den Temperatur-Trend Mini-Chart"""
        ax = self.temp_trend_ax
        ax.clear()
        
        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=24))
        df_sub = df.loc[mask]
        
        if not df_sub.empty:
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Oben"],
                color="#ef4444", linewidth=2, label="Oben"
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Außentemperatur"],
                color="#3b82f6", linewidth=2, linestyle="--", label="Außen"
            )
            
            ax.set_facecolor("#16213e")
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#2d3a5f')
            ax.spines['bottom'].set_color('#2d3a5f')
            ax.tick_params(colors='#8892b0', labelsize=8)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.set_ylabel("°C", color="#8892b0", fontsize=9)
            ax.legend(loc='upper left', fontsize=8, facecolor='#16213e', 
                     edgecolor='#2d3a5f', labelcolor='#8892b0')
            
        self.temp_trend_canvas.draw()

    def get_color(self, temp):
        if temp < 20:
            return "blue"
        elif temp < 40:
            return "green"
        elif temp < 60:
            return "yellow"
        else:
            return "red"