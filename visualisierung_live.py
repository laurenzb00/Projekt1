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

# Touchscreen Optimierung (1024x600)
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600 

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
        
        # Zeitstempel sofort konvertieren
        if "Zeitstempel" in df.columns:
            df["Zeitstempel"] = pd.to_datetime(df["Zeitstempel"], errors='coerce')
            # Entferne Zeilen mit ungültigem Zeitstempel
            df = df.dropna(subset=["Zeitstempel"])
        
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
        self.notebook.pack(fill=BOTH, expand=YES)

        # Tabs erstellen
        self.dashboard_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.setup_dashboard_tab()
        self.setup_plot_tabs()

        self.setup_bottom_bar()
        self.update_plots()

        # Echter Vollbildmodus für Touchscreen (überdeckt Taskleiste)
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)  # Immer im Vordergrund
        self.root.geometry(f'{SCREEN_WIDTH}x{SCREEN_HEIGHT}+0+0')
        self.root.overrideredirect(True)  # Entfernt Fensterrahmen komplett
        self.root.bind('<Escape>', self.exit_fullscreen)
        # Touch-Geste: 5 Sekunden auf Header tippen zum Beenden
        self.click_count = 0
        self.last_click_time = 0

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

    def exit_fullscreen(self, event=None):
        """Beendet Vollbildmodus und schließt Programm"""
        self.root.destroy()

    def _update_battery_color(self, soc):
        """Ändert Batterie-Farbe basierend auf Ladestand"""
        if soc < 20:
            color = "#ef4444"  # Rot
        elif soc < 50:
            color = "#f59e0b"  # Orange
        elif soc < 80:
            color = "#10b981"  # Grün
        else:
            color = "#059669"  # Dunkelgrün
        
        try:
            self.battery_card.configure(bg=color)
            self.battery_value_label.configure(bg=color)
            # Finde Header-Frame und aktualisiere
            for widget in self.battery_card.winfo_children():
                if isinstance(widget, tk.Frame):
                    widget.configure(bg=color)
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            child.configure(bg=color)
        except:
            pass

    def _highlight_card(self, card, highlight_color):
        """Hebt eine Karte kurz hervor (visuelles Feedback)"""
        try:
            original_color = card.cget("bg")
            # Kurzer Farbwechsel für Aufmerksamkeit
            card.configure(bg=highlight_color)
            # Nach 500ms zurück zur Originalfarbe
            self.root.after(500, lambda: card.configure(bg=original_color))
        except:
            pass

    # --- UI SETUP ---
    def setup_dashboard_tab(self):
        # Hauptcontainer (optimiert für 1024x600 Touchscreen)
        self.dashboard_frame = tk.Frame(self.dashboard_tab, bg="#0f1419")
        self.dashboard_frame.pack(fill=tk.BOTH, expand=True)
        
        # Grid-Konfiguration für gleichmäßige Verteilung (jetzt 2 Zeilen statt 3)
        for i in range(4):
            self.dashboard_frame.grid_columnconfigure(i, weight=1)
        for i in range(2):
            self.dashboard_frame.grid_rowconfigure(i, weight=1)

        # ===== OBERE REIHE: 4 Metrikkarten =====
        # PV Erzeugung
        self.pv_card = self._create_modern_card(
            parent=self.dashboard_frame,
            row=0, col=0,
            title="PV Erzeugung",
            bg_color="#0ea5e9",
            icon="●"  # Sonne-Symbol als Kreis
        )
        self.pv_value_label = tk.Label(
            self.pv_card, textvariable=self.dash_pv_now,
            font=("Segoe UI", 28, "bold"), fg="white", bg="#0ea5e9"
        )
        self.pv_value_label.pack(pady=4)

        # Verbrauch
        self.verbrauch_card = self._create_modern_card(
            parent=self.dashboard_frame,
            row=0, col=1,
            title="Verbrauch",
            bg_color="#ec4899",
            icon="⚡"  # Blitz funktioniert
        )
        self.verbrauch_value_label = tk.Label(
            self.verbrauch_card, textvariable=self.dash_haus_now,
            font=("Segoe UI", 28, "bold"), fg="white", bg="#ec4899"
        )
        self.verbrauch_value_label.pack(pady=4)

        # Batterie SoC - mit Animation
        self.battery_card = self._create_modern_card(
            parent=self.dashboard_frame,
            row=0, col=2,
            title="Batterie",
            bg_color="#10b981",
            icon="▮"  # Batterie als Balken
        )
        self.battery_soc_var = tk.StringVar(value="0 %")
        self.battery_value_label = tk.Label(
            self.battery_card, textvariable=self.battery_soc_var,
            font=("Segoe UI", 28, "bold"), fg="white", bg="#10b981"
        )
        self.battery_value_label.pack(pady=4)

        # Tagesertrag
        self.ertrag_card = self._create_modern_card(
            parent=self.dashboard_frame,
            row=0, col=3,
            title="Tagesertrag",
            bg_color="#f59e0b",
            icon="▲"  # Trend-Pfeil
        )
        self.ertrag_value_label = tk.Label(
            self.ertrag_card, textvariable=self.dash_ertrag_heute,
            font=("Segoe UI", 28, "bold"), fg="white", bg="#f59e0b"
        )
        self.ertrag_value_label.pack(pady=4)

        # ===== UNTERE REIHE: Kompakt für 1024x600 =====
        # Pufferspeicher (schmaler)
        self.puffer_card = self._create_chart_card(
            parent=self.dashboard_frame,
            row=1, col=0, colspan=1,
            title="Puffer"
        )
        self.canvas_puffer = tk.Canvas(
            self.puffer_card, width=200, height=210,
            bg="#16213e", highlightthickness=0
        )
        self.canvas_puffer.pack(pady=2, expand=True)

        # Außentemperatur (schmaler)
        self.aussen_card = self._create_chart_card(
            parent=self.dashboard_frame,
            row=1, col=1, colspan=1,
            title="Außen"
        )
        aussen_inner = tk.Frame(self.aussen_card, bg="#16213e")
        aussen_inner.pack(expand=True, fill=tk.BOTH)
        
        tk.Label(
            aussen_inner, text="◐",  # Besseres Thermometer-Symbol
            font=("Segoe UI", 32), fg="#6366f1", bg="#16213e"
        ).pack(pady=(8, 2))
        
        self.aussen_value_label = tk.Label(
            aussen_inner, textvariable=self.dash_aussen,
            font=("Segoe UI", 24, "bold"), fg="white", bg="#16213e"
        )
        self.aussen_value_label.pack(pady=2)

        # Trend Chart (größer, 2 Spalten breit)
        self.pv_trend_card = self._create_chart_card(
            parent=self.dashboard_frame,
            row=1, col=2, colspan=2,
            title="24h Trend"
        )
        self.pv_trend_fig, self.pv_trend_ax = self._create_mini_chart()
        self.pv_trend_canvas = FigureCanvasTkAgg(self.pv_trend_fig, master=self.pv_trend_card)
        self.pv_trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Start Animation
        self.update_puffer_animation()

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

    def _create_modern_card(self, parent, row, col, title, bg_color, icon):
        """Erstellt moderne Touch-optimierte Karte für 1024x600"""
        # Außen-Frame mit Schatten-Effekt (simuliert)
        outer_frame = tk.Frame(parent, bg="#000000")
        outer_frame.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        
        # Haupt-Karte
        card = tk.Frame(outer_frame, bg=bg_color, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Header (kompakt für Touchscreen)
        header = tk.Frame(card, bg=bg_color)
        header.pack(fill=tk.X, padx=8, pady=(8, 2))
        
        icon_label = tk.Label(header, text=icon, font=("Segoe UI", 18), bg=bg_color, fg="white")
        icon_label.pack(side=tk.LEFT)
        
        title_label = tk.Label(
            header, text=title, 
            font=("Segoe UI", 11, "bold"), 
            bg=bg_color, fg="white"
        )
        title_label.pack(side=tk.LEFT, padx=6)
        
        return card

    def _create_chart_card(self, parent, row, col, colspan, title):
        """Erstellt eine Karte für Charts (Touchscreen-optimiert)"""
        card = tk.Frame(parent, bg="#16213e", relief=tk.FLAT, bd=0)
        card.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=4, pady=4)
        
        # Header (kompakter)
        header = tk.Frame(card, bg="#1e2a47")
        header.pack(fill=tk.X)
        
        title_label = tk.Label(
            header, text=title,
            font=("Segoe UI", 10, "bold"),
            bg="#1e2a47", fg="white",
            pady=6, padx=10
        )
        title_label.pack(anchor="w")
        
        return card

    def _create_mini_chart(self):
        """Erstellt Chart für 1024x600 Auflösung"""
        fig, ax = plt.subplots(figsize=(5.5, 2.5), dpi=85)
        fig.patch.set_facecolor("#16213e")
        ax.set_facecolor("#16213e")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#2d3a5f')
        ax.spines['bottom'].set_color('#2d3a5f')
        ax.tick_params(colors='#8892b0', labelsize=8)
        ax.grid(True, color='#2d3a5f', linestyle='--', alpha=0.2)
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
        # Kompaktere Bottom-Bar für Touchscreen
        ttk.Button(bar, text="✕ Beenden", bootstyle="danger-outline", 
                  command=self.root.destroy, width=12).pack(side=LEFT, padx=3, pady=3)
        ttk.Label(bar, textvariable=self.status_time_var, 
                 bootstyle="inverse-dark", font=("Segoe UI", 8)).pack(side=RIGHT, padx=8)

    # --- UPDATE LOGIC ---
    def update_plots(self):
        now = pd.Timestamp.now()
        
        fronius_df = read_csv_tail_fixed(FRONIUS_CSV, MAX_PLOT_POINTS)
        bmk_df = read_csv_tail_fixed(BMK_CSV, MAX_PLOT_POINTS)

        # 1. PV Daten
        if fronius_df is not None and not fronius_df.empty:
            try:
                last = fronius_df.iloc[-1]
                
                pv = last.get("PV-Leistung (kW)", 0)
                haus = last.get("Hausverbrauch (kW)", 0)
                soc = last.get("Batterieladestand (%)", 0)
                
                self.dash_pv_now.set(f"{pv:.2f} kW")
                self.dash_haus_now.set(f"{haus:.2f} kW")
                self.battery_soc_var.set(f"{int(soc)} %")
                
                # Dynamische Farbanpassung für Batterie
                self._update_battery_color(soc)
                
                # PV-Karten Hervorhebung wenn Produktion
                if pv > 0.5:
                    self._highlight_card(self.pv_card, "#0ea5e9")
                
                # Verbrauchs-Warnung bei hoher Last
                if haus > 5.0:
                    self._highlight_card(self.verbrauch_card, "#dc2626")
                
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
                self._update_combined_trend(fronius_df, bmk_df, now)
                self.dash_status.set("PV Daten aktuell.")
            except Exception as e:
                print(f"Fronius Update Fehler: {e}")

        # 2. Temperatur Daten
        if bmk_df is not None and not bmk_df.empty:
            try:
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
            # PV mit schönem Gradient Fill
            ax.fill_between(
                df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"],
                color="#22d3ee", alpha=0.5, label="PV Erzeugung"
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"],
                color="#0ea5e9", linewidth=3, label="_nolegend_"
            )
            
            # Hausverbrauch in Pink
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Hausverbrauch (kW)"],
                label="Hausverbrauch", color="#ec4899", linewidth=2.5, linestyle="--"
            )
            
            # Netz-Leistung wenn vorhanden
            if "Netz-Leistung (kW)" in df_sub.columns:
                netz = df_sub["Netz-Leistung (kW)"]
                # Positive Werte = Bezug, negative = Einspeisung
                bezug_mask = netz > 0.1
                if bezug_mask.any():
                    ax.plot(
                        df_sub.loc[bezug_mask, "Zeitstempel"], 
                        df_sub.loc[bezug_mask, "Netz-Leistung (kW)"],
                        color="#ef4444", linewidth=2, label="Netzbezug", marker=".", markersize=3
                    )
            
            # Batterieladestand auf zweiter Y-Achse (transparenter)
            ax2.plot(
                df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"],
                color="#10b981", linestyle=":", alpha=0.6, linewidth=2, label="Batterie %"
            )
            ax2.set_ylim(0, 100)
            ax2.tick_params(colors="#10b981", labelsize=9)
            ax2.spines['right'].set_color('#10b981')
            ax2.yaxis.label.set_color('#10b981')
            ax2.set_ylabel("Batterie (%)", color="#10b981", fontsize=10, fontweight='bold')
            
            # Legende mit allen Infos
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2,
                     loc="upper left", facecolor='#16213e', edgecolor='#2d3a5f',
                     labelcolor='white', fontsize=9, framealpha=0.95)
            
            ax.set_title("Energie-Fluss (48h)", color="white", fontsize=12, fontweight='bold')
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
                # Bars mit Farbverlauf basierend auf Ertrag
                colors = []
                for val in df_daily.values:
                    if val < 5:
                        colors.append("#ef4444")  # Rot für wenig
                    elif val < 15:
                        colors.append("#f59e0b")  # Orange für mittel
                    elif val < 25:
                        colors.append("#10b981")  # Grün für gut
                    else:
                        colors.append("#059669")  # Dunkelgrün für sehr gut
                
                bars = ax.bar(
                    df_daily.index, df_daily.values,
                    color=colors, width=0.8, edgecolor="#2d3a5f", linewidth=1
                )
                
                # Durchschnittslinie
                avg = df_daily.mean()
                ax.axhline(y=avg, color='#06b6d4', linestyle='--', 
                          linewidth=2, alpha=0.7, label=f'Ø {avg:.1f} kWh')
                
                # Beste und schlechteste Tage markieren
                max_day = df_daily.idxmax()
                max_val = df_daily.max()
                ax.plot(max_day, max_val, 'g*', markersize=15, 
                       label=f'Max: {max_val:.1f} kWh')
                
                ax.legend(loc='upper left', facecolor='#16213e', edgecolor='#2d3a5f',
                         labelcolor='white', fontsize=9, framealpha=0.95)
                ax.set_title("Tagesertrag (30 Tage)", color="white", 
                           fontsize=12, fontweight='bold')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))
                ax.set_xlabel("Datum", color="#8892b0", fontsize=10)
                ax.set_ylabel("Ertrag (kWh)", color="#8892b0", fontsize=10)
                self.ertrag_fig.patch.set_facecolor("#16213e")
            else:
                ax.text(0.5, 0.5, "Keine Daten verfügbar", 
                       color="white", ha="center", transform=ax.transAxes, fontsize=12)
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
            # Temperaturen mit schönen Gradienten
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Oben"],
                color="#ef4444", label="Puffer Oben", linewidth=2.5, marker='o', markersize=2
            )
            ax.fill_between(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Oben"],
                alpha=0.2, color="#ef4444"
            )
            
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Mitte"],
                color="#f59e0b", label="Puffer Mitte", linewidth=2.5
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Unten"],
                color="#3b82f6", label="Puffer Unten", linewidth=2.5
            )
            
            # Außentemperatur gestrichelt
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Außentemperatur"],
                color="#06b6d4", label="Außentemperatur", linestyle="--", 
                alpha=0.8, linewidth=2
            )
            
            # Kesseltemperatur wenn vorhanden
            if "Kesseltemperatur" in df_sub.columns:
                ax.plot(
                    df_sub["Zeitstempel"], df_sub["Kesseltemperatur"],
                    color="#a855f7", label="Kessel", linewidth=2, alpha=0.7
                )
            
            ax.legend(facecolor='#16213e', edgecolor='#2d3a5f',
                     labelcolor='white', fontsize=9, framealpha=0.95, loc='best')
            ax.set_title("Heizungs-Temperaturen (7 Tage)", color="white", 
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

        # Kompakter Pufferspeicher für 1024x600
        x_start, y_start = 60, 15
        width, height_per_section = 80, 60

        # Schatten
        self.canvas_puffer.create_rectangle(
            x_start + 3, y_start + 3, x_start + width + 3, y_start + height_per_section * 3 + 3,
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
            
            # Sektion
            self.canvas_puffer.create_rectangle(
                x_start, y_pos, x_start + width, y_pos + height_per_section,
                fill=color, outline="#2d3a5f", width=2
            )
            
            # Temperaturanzeige (kompakt)
            self.canvas_puffer.create_text(
                x_start + width // 2, y_pos + height_per_section // 2 - 5,
                text=f"{temp:.1f}°C",
                fill="white", font=("Segoe UI", 14, "bold")
            )
            
            # Label
            self.canvas_puffer.create_text(
                x_start + width // 2, y_pos + height_per_section // 2 + 15,
                text=label,
                fill="#8892b0", font=("Segoe UI", 8)
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

    def _update_combined_trend(self, df_pv, df_temp, now):
        """Kombinierter Chart für PV und Temperatur"""
        ax = self.pv_trend_ax
        ax.clear()
        
        mask_pv = df_pv["Zeitstempel"] >= (now - pd.Timedelta(hours=24))
        df_pv_sub = df_pv.loc[mask_pv]
        
        mask_temp = df_temp["Zeitstempel"] >= (now - pd.Timedelta(hours=24))
        df_temp_sub = df_temp.loc[mask_temp]
        
        if not df_pv_sub.empty:
            # PV auf linker Achse
            color_pv = "#22d3ee"
            ax.fill_between(
                df_pv_sub["Zeitstempel"], df_pv_sub["PV-Leistung (kW)"],
                alpha=0.4, color=color_pv
            )
            ax.plot(
                df_pv_sub["Zeitstempel"], df_pv_sub["PV-Leistung (kW)"],
                color="#0ea5e9", linewidth=2.5, label="PV Leistung"
            )
            ax.set_ylabel("PV (kW)", color="#0ea5e9", fontsize=10, fontweight='bold')
            ax.tick_params(axis='y', labelcolor="#0ea5e9")
            
        if not df_temp_sub.empty:
            # Temperatur auf rechter Achse
            ax2 = ax.twinx()
            ax2.plot(
                df_temp_sub["Zeitstempel"], df_temp_sub["Pufferspeicher Oben"],
                color="#ef4444", linewidth=2.5, label="Puffer Oben", marker='o', markersize=3, alpha=0.8
            )
            ax2.set_ylabel("Temp (°C)", color="#ef4444", fontsize=10, fontweight='bold')
            ax2.tick_params(axis='y', labelcolor="#ef4444")
            ax2.spines['right'].set_color('#2d3a5f')
            ax2.spines['left'].set_color('#2d3a5f')
            ax2.spines['top'].set_visible(False)
            ax2.spines['bottom'].set_color('#2d3a5f')
            
        ax.set_facecolor("#16213e")
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_color('#2d3a5f')
        ax.spines['bottom'].set_color('#2d3a5f')
        ax.tick_params(colors='#8892b0', labelsize=9)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid(True, color='#2d3a5f', linestyle='--', alpha=0.3, linewidth=0.8)
        
        # Legende kombiniert
        lines1, labels1 = ax.get_legend_handles_labels()
        if not df_temp_sub.empty:
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, 
                     loc='upper left', fontsize=8, facecolor='#16213e', 
                     edgecolor='#2d3a5f', labelcolor='#8892b0', framealpha=0.9)
        else:
            ax.legend(loc='upper left', fontsize=8, facecolor='#16213e', 
                     edgecolor='#2d3a5f', labelcolor='#8892b0', framealpha=0.9)
            
        self.pv_trend_canvas.draw()

    def get_color(self, temp):
        if temp < 20:
            return "blue"
        elif temp < 40:
            return "green"
        elif temp < 60:
            return "yellow"
        else:
            return "red"