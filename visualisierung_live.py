
# Only import what is actually used in the code
import os
import tkinter as tk
from tkinter import StringVar
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import numpy as np
from ttkbootstrap.icons import Icon
plt.style.use("dark_background")

# --- KONFIGURATION ---
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")
ERTRAG_CSV = os.path.join(WORKING_DIRECTORY, "ErtragHistory.csv")

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
        expected_cols = len(col_names)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Always keep header
        data_lines = lines[1:]
        # Only keep lines with correct number of columns
        valid_lines = [lines[0]] + [l for l in data_lines if len(l.strip().split(",")) == expected_cols]
        # Write to temp file for pandas
        import tempfile
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tmp:
            tmp.writelines(valid_lines[-max_rows-1:])  # header + last max_rows
            tmp_path = tmp.name
        df = pd.read_csv(tmp_path, sep=",", header=0)
        df.columns = df.columns.str.strip()
        # Zeitstempel sofort konvertieren
        if "Zeitstempel" in df.columns:
            df["Zeitstempel"] = pd.to_datetime(df["Zeitstempel"], errors='coerce')
            df = df.dropna(subset=["Zeitstempel"])
        return df
    except Exception as e:
        pass  # Fehler beim Lesen werden ignoriert
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

        # Neuer Status-Tab
        self.status_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.status_tab, text="Status")
        self.setup_status_tab()

        # PV Status Tab
        self.pv_status_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.pv_status_tab, text="PV Status")
        self.setup_pv_status_tab()
        def setup_pv_status_tab(self):
            frame = tk.Frame(self.pv_status_tab, bg="#181e2a")
            frame.pack(fill=tk.BOTH, expand=True)

            self.pv_status_pv = StringVar(value="-- kW")
            self.pv_status_batt = StringVar(value="-- %")
            self.pv_status_grid = StringVar(value="-- kW")
            self.pv_status_recommend = StringVar(value="--")
            self.pv_status_time = StringVar(value="-")

            row = 0
            tk.Label(frame, text="PV-Leistung", font=("Segoe UI", 16), fg="#0ea5e9", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=8)
            tk.Label(frame, textvariable=self.pv_status_pv, font=("Segoe UI", 16, "bold"), fg="#0ea5e9", bg="#181e2a").grid(row=row, column=1, sticky="w")
            row += 1
            tk.Label(frame, text="Batterie", font=("Segoe UI", 14), fg="#10b981", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=4)
            tk.Label(frame, textvariable=self.pv_status_batt, font=("Segoe UI", 14), fg="#10b981", bg="#181e2a").grid(row=row, column=1, sticky="w")
            row += 1
            tk.Label(frame, text="Netzbezug", font=("Segoe UI", 14), fg="#ef4444", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=4)
            tk.Label(frame, textvariable=self.pv_status_grid, font=("Segoe UI", 14), fg="#ef4444", bg="#181e2a").grid(row=row, column=1, sticky="w")
            row += 1
            tk.Label(frame, text="Empfehlung", font=("Segoe UI", 16, "bold"), fg="#f87171", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=16)
            tk.Label(frame, textvariable=self.pv_status_recommend, font=("Segoe UI", 16, "bold"), fg="#f87171", bg="#181e2a").grid(row=row, column=1, sticky="w")
            row += 1
            tk.Label(frame, text="Letztes Update", font=("Segoe UI", 12), fg="#a3a3a3", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=8)
            tk.Label(frame, textvariable=self.pv_status_time, font=("Segoe UI", 12), fg="#a3a3a3", bg="#181e2a").grid(row=row, column=1, sticky="w")

            self.update_pv_status_tab()

        def update_pv_status_tab(self):
            df = read_csv_tail_fixed(FRONIUS_CSV, 1)
            if df is None or df.empty:
                self.pv_status_pv.set("-- kW")
                self.pv_status_batt.set("-- %")
                self.pv_status_grid.set("-- kW")
                self.pv_status_recommend.set("Keine Daten")
                self.pv_status_time.set("--")
                return
            row = df.iloc[-1]
            pv = row.get("PV-Leistung (kW)", None)
            batt = row.get("Batterieladestand (%)", None)
            grid = row.get("Netz-Leistung (kW)", None)
            self.pv_status_pv.set(f"{pv:.2f} kW" if pv is not None else "-- kW")
            self.pv_status_batt.set(f"{batt:.0f} %" if batt is not None else "-- %")
            self.pv_status_grid.set(f"{grid:.2f} kW" if grid is not None else "-- kW")
            # Empfehlung: Einfache Logik
            try:
                if pv is not None and pv < 0.2:
                    rec = "Wenig PV – Netzbezug möglich."
                elif batt is not None and batt < 20:
                    rec = "Batterie fast leer."
                elif grid is not None and grid > 0.5:
                    rec = "Hoher Netzbezug."
                else:
                    rec = "Alles ok."
            except:
                rec = "--"
            self.pv_status_recommend.set(rec)
            self.pv_status_time.set(str(row.get("Zeitstempel", "--")))
            # Automatisches Update alle 60s
            self.root.after(60000, self.update_pv_status_tab)
    def setup_status_tab(self):
        # Hauptcontainer für Status-Tab
        frame = tk.Frame(self.status_tab, bg="#181e2a")
        frame.pack(fill=tk.BOTH, expand=True)

        # Statusfelder oben
        self.status_brenner = StringVar(value="--")
        self.status_betriebsmodus = StringVar(value="--")
        self.status_puffer = StringVar(value="--")
        self.status_ww = StringVar(value="--")
        self.status_kessel = StringVar(value="--")
        self.status_empfehlung = StringVar(value="--")
        self.status_letzte_aktiv = StringVar(value="--")
        self.status_betriebsstunden = StringVar(value="--")

        # Ampel/Statusfelder
        row = 0
        tk.Label(frame, text="Brenner", font=("Segoe UI", 16), fg="white", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=8)
        tk.Label(frame, textvariable=self.status_brenner, font=("Segoe UI", 16, "bold"), fg="#f59e0b", bg="#181e2a").grid(row=row, column=1, sticky="w")
        row += 1
        tk.Label(frame, text="Betriebsmodus", font=("Segoe UI", 14), fg="white", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=4)
        tk.Label(frame, textvariable=self.status_betriebsmodus, font=("Segoe UI", 14), fg="#38bdf8", bg="#181e2a").grid(row=row, column=1, sticky="w")
        row += 1
        tk.Label(frame, text="Pufferladung", font=("Segoe UI", 14), fg="white", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=4)
        tk.Label(frame, textvariable=self.status_puffer, font=("Segoe UI", 14), fg="#10b981", bg="#181e2a").grid(row=row, column=1, sticky="w")
        row += 1
        tk.Label(frame, text="Warmwasser", font=("Segoe UI", 14), fg="white", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=4)
        tk.Label(frame, textvariable=self.status_ww, font=("Segoe UI", 14), fg="#f472b6", bg="#181e2a").grid(row=row, column=1, sticky="w")
        row += 1
        tk.Label(frame, text="Kesseltemp.", font=("Segoe UI", 14), fg="white", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=4)
        tk.Label(frame, textvariable=self.status_kessel, font=("Segoe UI", 14), fg="#fbbf24", bg="#181e2a").grid(row=row, column=1, sticky="w")

        # Handlungsempfehlung
        row += 1
        tk.Label(frame, text="Empfehlung", font=("Segoe UI", 16, "bold"), fg="#f87171", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=16)
        tk.Label(frame, textvariable=self.status_empfehlung, font=("Segoe UI", 16, "bold"), fg="#f87171", bg="#181e2a").grid(row=row, column=1, sticky="w")

        # Letzte Aktivität und Betriebsstunden
        row += 1
        tk.Label(frame, text="Letzte Aktivität", font=("Segoe UI", 12), fg="#a3a3a3", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=8)
        tk.Label(frame, textvariable=self.status_letzte_aktiv, font=("Segoe UI", 12), fg="#a3a3a3", bg="#181e2a").grid(row=row, column=1, sticky="w")
        row += 1
        tk.Label(frame, text="Betriebsstunden", font=("Segoe UI", 12), fg="#a3a3a3", bg="#181e2a").grid(row=row, column=0, sticky="w", padx=20, pady=4)
        tk.Label(frame, textvariable=self.status_betriebsstunden, font=("Segoe UI", 12), fg="#a3a3a3", bg="#181e2a").grid(row=row, column=1, sticky="w")

        # Initiales Update
        self.update_status_tab()

    def update_status_tab(self):
        # Lese aktuelle Werte aus CSV (letzte Zeile)
        df = read_csv_tail_fixed(BMK_CSV, 1)
        if df is None or df.empty:
            self.status_brenner.set("--")
            self.status_betriebsmodus.set("--")
            self.status_puffer.set("--")
            self.status_ww.set("--")
            self.status_kessel.set("--")
            self.status_empfehlung.set("Keine Daten")
            self.status_letzte_aktiv.set("--")
            self.status_betriebsstunden.set("--")
            return
        row = df.iloc[-1]
        # Dummy-Logik für Statusanzeige (später anpassen)
        # Brenner-Status: (ersetzt durch echten Wert, falls vorhanden)
        self.status_brenner.set(str(row.get("Brenner_Status", "--")))
        self.status_betriebsmodus.set(str(row.get("Betriebsmodus", "--")))
        puffer = row.get("Pufferladung", None)
        if puffer is not None:
            try:
                puffer = float(puffer)
                if puffer < 30:
                    puffer_str = f"{puffer:.0f}% (Niedrig)"
                elif puffer < 70:
                    puffer_str = f"{puffer:.0f}% (Mittel)"
                else:
                    puffer_str = f"{puffer:.0f}% (Hoch)"
            except:
                puffer_str = str(puffer)
        else:
            puffer_str = "--"
        self.status_puffer.set(puffer_str)
        self.status_ww.set(f"{row.get('Warmwassertemperatur', '--')} °C")
        self.status_kessel.set(f"{row.get('Kesseltemperatur', '--')} °C")
        # Handlungsempfehlung
        try:
            kessel = float(row.get("Kesseltemperatur", 0))
            puffer = float(row.get("Pufferladung", 0))
            brenner = str(row.get("Brenner_Status", "")).upper()
            if brenner == "AUS" and (kessel < 60 or puffer < 30):
                empfehlung = "Nachlegen!"
            elif brenner == "HEIZEN":
                empfehlung = "Kessel läuft."
            elif puffer < 30:
                empfehlung = "Puffer fast leer."
            else:
                empfehlung = "Alles ok."
        except:
            empfehlung = "--"
        self.status_empfehlung.set(empfehlung)
        # Letzte Aktivität (Dummy: Zeitstempel)
        self.status_letzte_aktiv.set(str(row.get("Zeitstempel", "--")))
        self.status_betriebsstunden.set(str(row.get("Betriebsstunden", "--")))

        # Automatisches Update alle 60s
        self.root.after(60000, self.update_status_tab)

        self.setup_bottom_bar()
        self.update_plots()
        self.schedule_ertrag_updates()

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
        self.dash_clock = StringVar(value="--:--")
        
        # Stromfluss-Animationsvariablen
        self.pv_flow_value = 0
        self.load_flow_value = 0
        self.grid_flow_value = 0

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
        # Dunkler Glas-Look Hintergrund
        self.dashboard_frame = tk.Frame(self.dashboard_tab, bg="#0b1220")
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

        # Stromfluss + Uhr
        self.flow_clock_card = self._create_chart_card(
            parent=self.dashboard_frame,
            row=1, col=2, colspan=1,
            title="Status"
        )
        self.canvas_flow = tk.Canvas(
            self.flow_clock_card, width=140, height=210,
            bg="#0f172a", highlightthickness=0
        )
        self.canvas_flow.pack(pady=2, expand=True)
        
        # Trend Chart
        self.pv_trend_card = self._create_chart_card(
            parent=self.dashboard_frame,
            row=1, col=3, colspan=1,
            title="24h Trend"
        )
        self.pv_trend_fig, self.pv_trend_ax = self._create_mini_chart()
        self.pv_trend_canvas = FigureCanvasTkAgg(self.pv_trend_fig, master=self.pv_trend_card)
        self.pv_trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Start Animation
        self.update_puffer_animation()
        self.update_flow_clock_animation()

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
        outer_frame = tk.Frame(parent, bg="#0a0f1a")
        outer_frame.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        
        # Haupt-Karte im Glas-Look
        card = tk.Frame(
            outer_frame,
            bg=bg_color,
            relief=tk.FLAT,
            bd=0,
            highlightbackground="#1f2a44",
            highlightthickness=1
        )
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
        card = tk.Frame(
            parent,
            bg="#0f172a",
            relief=tk.FLAT,
            bd=0,
            highlightbackground="#1f2a44",
            highlightthickness=1
        )
        card.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=4, pady=4)
        
        # Header (kompakter)
        header = tk.Frame(card, bg="#142038")
        header.pack(fill=tk.X)
        
        title_label = tk.Label(
            header, text=title,
            font=("Segoe UI", 10, "bold"),
            bg="#142038", fg="white",
            pady=6, padx=10
        )
        title_label.pack(anchor="w")
        
        return card

    def _create_mini_chart(self):
        """Erstellt Chart für 1024x600 Auflösung"""
        fig, ax = plt.subplots(figsize=(5.5, 2.5), dpi=85)
        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#243354')
        ax.spines['bottom'].set_color('#243354')
        ax.tick_params(colors='#8ba2c7', labelsize=8)
        ax.grid(True, color='#243354', linestyle='--', alpha=0.18, linewidth=0.6)
        return fig, ax

    def setup_plot_tabs(self):
        # Alle Tabs aktiv
        self.create_single_plot_tab("PV-Leistung", "fronius")
        self.create_single_plot_tab("Temperaturen", "bmk")
        self.create_single_plot_tab("Batterie", "batt")
        self.create_single_plot_tab("Ertrag", "ertrag")

    def create_single_plot_tab(self, name, var_prefix):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=f" {name} ")
        
        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")
        
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
                
                # Stromfluss-Werte speichern für Animation
                self.pv_flow_value = max(0, pv)
                if "Netz-Leistung (kW)" in last.index:
                    netz = last.get("Netz-Leistung (kW)", 0)
                    self.grid_flow_value = max(0, netz)  # Nur Bezug (positiv)
                else:
                    self.grid_flow_value = 0
                
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
                self._plot_ertrag()
                self._update_combined_trend(fronius_df, bmk_df, now)
                self.dash_status.set("PV Daten aktuell.")
            except Exception as e:
                pass  # Fehler beim Fronius-Update werden ignoriert

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
                pass  # Fehler beim BMK-Update werden ignoriert

        self.status_time_var.set(f"Update: {now.strftime('%H:%M:%S')}")
        # Schedule update safely
        if self.root.winfo_exists():
            self.root.after(UPDATE_INTERVAL, self.update_plots)

    # --- ERTRAG AGGREGATION (stündlich) ---
    def _ensure_ertrag_file(self):
        if not os.path.exists(ERTRAG_CSV):
            pd.DataFrame(columns=["Zeitstempel", "Ertrag_kWh"]).to_csv(ERTRAG_CSV, index=False)

    def _append_ertrag_segment(self, df_segment: pd.DataFrame):
        if df_segment.empty:
            return
        df_segment = df_segment.sort_values(by="Zeitstempel")
        df_segment["TimeDiff"] = df_segment["Zeitstempel"].diff().dt.total_seconds().fillna(0) / 3600
        df_segment["Energy"] = df_segment["PV-Leistung (kW)"] * df_segment["TimeDiff"]
        energy = df_segment["Energy"].sum()
        if energy <= 0:
            return
        end_ts = df_segment["Zeitstempel"].max()
        pd.DataFrame({"Zeitstempel": [end_ts], "Ertrag_kWh": [energy]}).to_csv(
            ERTRAG_CSV, mode="a", header=False, index=False
        )

    def _update_ertrag_hourly(self):
        fronius_df = read_csv_tail_fixed(FRONIUS_CSV, MAX_PLOT_POINTS)
        if fronius_df is None or fronius_df.empty or "Zeitstempel" not in fronius_df.columns:
            return
        try:
            ertrag_df = pd.read_csv(ERTRAG_CSV, parse_dates=["Zeitstempel"]) if os.path.exists(ERTRAG_CSV) else pd.DataFrame()
            last_ts = ertrag_df["Zeitstempel"].max() if not ertrag_df.empty else None
            if last_ts is not None:
                segment = fronius_df[fronius_df["Zeitstempel"] > last_ts]
            else:
                # Nimm maximal die letzten 48h als Start, um nicht unendlich viel zu integrieren
                mask = fronius_df["Zeitstempel"] >= (pd.Timestamp.now() - pd.Timedelta(hours=48))
                segment = fronius_df[mask]
            if segment.empty:
                return
            self._append_ertrag_segment(segment)
        except Exception as e:
            pass  # Fehler bei der Ertrag-Aggregation werden ignoriert

    def schedule_ertrag_updates(self):
        self._ensure_ertrag_file()
        self._update_ertrag_hourly()
        # Tab sofort aktualisieren
        try:
            self._plot_ertrag()
        except Exception:
            pass
        if self.root.winfo_exists():
            self.root.after(60 * 60 * 1000, self.schedule_ertrag_updates)  # 1x pro Stunde

    # --- PLOTTING ---
    def _style_ax(self, ax):
        ax.set_facecolor("#0f172a")
        ax.tick_params(colors='#8ba2c7', which='both', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#243354')
            spine.set_linewidth(1.0)
        ax.yaxis.label.set_color('#8ba2c7')
        ax.xaxis.label.set_color('#8ba2c7')
        ax.title.set_color('white')
        ax.grid(True, color='#243354', linestyle='--', alpha=0.22, linewidth=0.6)

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
                color="#22d3ee", alpha=0.35, label="PV Erzeugung"
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"],
                color="#38bdf8", linewidth=2.0, label="_nolegend_"
            )
            
            # Hausverbrauch in Pink
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Hausverbrauch (kW)"],
                label="Hausverbrauch", color="#f472b6", linewidth=1.6, linestyle="--"
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
                        color="#ef4444", linewidth=1.3, label="Netzbezug", marker=".", markersize=2.5
                    )
            
            # Batterieladestand auf zweiter Y-Achse (transparenter)
            ax2.plot(
                df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"],
                color="#34d399", linestyle=":", alpha=0.7, linewidth=1.2, label="Batterie %"
            )
            ax2.set_ylim(0, 100)
            ax2.tick_params(colors="#34d399", labelsize=8)
            ax2.spines['right'].set_color('#34d399')
            ax2.yaxis.label.set_color('#34d399')
            ax2.set_ylabel("Batterie (%)", color="#34d399", fontsize=9, fontweight='bold')
            
            # Legende mit allen Infos
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2,
                     loc="upper left", facecolor='#0f172a', edgecolor='#243354',
                     labelcolor='white', fontsize=8, framealpha=0.9)
            
            ax.set_title("Energie-Fluss (48h)", color="white", fontsize=11, fontweight='bold')
            ax.set_ylabel("Leistung (kW)", color="#8ba2c7", fontsize=9)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.fronius_fig.patch.set_facecolor("#0f172a")
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
                color="#34d399", alpha=0.28
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"],
                color="#34d399", linewidth=1.6
            )
            ax.set_ylim(0, 100)
            ax.set_title("Batterieverlauf (48h)", color="white", fontsize=11, fontweight='bold')
            ax.set_ylabel("Ladestand (%)", color="#8ba2c7", fontsize=9)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.batt_fig.patch.set_facecolor("#0f172a")
            self.batt_fig.autofmt_xdate()
        self.batt_canvas.draw()

    def _plot_ertrag(self):
        """Zeigt Tagesertrag der letzten 30 Tage aus aggregierter Datei."""
        ax = self.ertrag_ax
        ax.clear()
        self._style_ax(ax)

        if not os.path.exists(ERTRAG_CSV):
            self.ertrag_canvas.draw()
            return

        try:
            df = pd.read_csv(ERTRAG_CSV, parse_dates=["Zeitstempel"])
            if df.empty:
                self.ertrag_canvas.draw()
                return

            df = df.dropna(subset=["Zeitstempel", "Ertrag_kWh"])
            df.set_index("Zeitstempel", inplace=True)
            df_daily = df.resample('D').sum()

            start_date = (pd.Timestamp.now() - pd.Timedelta(days=90)).normalize()
            df_daily = df_daily[df_daily.index >= start_date]

            if not df_daily.empty:
                values = df_daily["Ertrag_kWh"].values
                dates = df_daily.index
                
                # Liniendiagramm statt Balken
                ax.fill_between(
                    dates, values,
                    color="#06b6d4", alpha=0.25, label="Ertrag"
                )
                ax.plot(
                    dates, values,
                    color="#06b6d4", linewidth=1.8, marker="o", markersize=2.5, label="Tagesertrag"
                )

                avg = df_daily["Ertrag_kWh"].mean()
                ax.axhline(y=avg, color='#f59e0b', linestyle='--', linewidth=1.2, alpha=0.6,
                           label=f'Ø {avg:.1f} kWh')

                max_day = df_daily["Ertrag_kWh"].idxmax()
                max_val = df_daily["Ertrag_kWh"].max()
                min_day = df_daily["Ertrag_kWh"].idxmin()
                min_val = df_daily["Ertrag_kWh"].min()
                
                ax.plot(max_day, max_val, '*', color="#10b981", markersize=12, label=f'Max: {max_val:.1f} kWh')
                ax.plot(min_day, min_val, 'v', color="#ef4444", markersize=6, label=f'Min: {min_val:.1f} kWh')

                # Gesamtertrag in Box
                total = df_daily["Ertrag_kWh"].sum()
                ax.text(
                    0.98, 0.98, f"Summe: {total:.0f} kWh",
                    transform=ax.transAxes, ha="right", va="top",
                    color="white", fontsize=10, fontweight="bold",
                    bbox=dict(boxstyle="round", facecolor="#0f172a", alpha=0.8, edgecolor="#243354")
                )

                ax.legend(loc='upper left', facecolor='#0f172a', edgecolor='#243354',
                         labelcolor='white', fontsize=8, framealpha=0.9)
                ax.set_title("Tagesertrag (90+ Tage)", color="white", fontsize=11, fontweight='bold')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))
                ax.set_xlabel("Datum", color="#8ba2c7", fontsize=9)
                ax.set_ylabel("Ertrag (kWh)", color="#8ba2c7", fontsize=9)
                self.ertrag_fig.patch.set_facecolor("#0f172a")
                self.ertrag_fig.autofmt_xdate()
            else:
                ax.text(0.5, 0.5, "Keine Daten verfügbar", color="white", ha="center",
                        transform=ax.transAxes, fontsize=12)
        except Exception as e:
            pass  # Fehler beim Ertrag-Plot werden ignoriert

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
                color="#ef4444", label="Puffer Oben", linewidth=1.6, marker='o', markersize=2.2
            )
            ax.fill_between(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Oben"],
                alpha=0.15, color="#ef4444"
            )
            
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Mitte"],
                color="#f59e0b", label="Puffer Mitte", linewidth=1.6
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Pufferspeicher Unten"],
                color="#3b82f6", label="Puffer Unten", linewidth=1.6
            )
            
            # Außentemperatur gestrichelt
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Außentemperatur"],
                color="#06b6d4", label="Außentemperatur", linestyle="--", 
                alpha=0.85, linewidth=1.3
            )
            
            # Kesseltemperatur wenn vorhanden
            if "Kesseltemperatur" in df_sub.columns:
                ax.plot(
                    df_sub["Zeitstempel"], df_sub["Kesseltemperatur"],
                    color="#a855f7", label="Kessel", linewidth=1.4, alpha=0.75
                )
            
            ax.legend(facecolor='#0f172a', edgecolor='#243354',
                     labelcolor='white', fontsize=8, framealpha=0.9, loc='best')
            ax.set_title("Heizungs-Temperaturen (7 Tage)", color="white", 
                        fontsize=11, fontweight='bold')
            ax.set_ylabel("Temperatur (°C)", color="#8ba2c7", fontsize=9)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))
            self.bmk_fig.patch.set_facecolor("#0f172a")
            self.bmk_fig.autofmt_xdate()
        self.bmk_canvas.draw()

    # --- Neue Funktionen für Buttons ---
    def show_consumption_details(self):
        pass  # Verbrauchsdetails anzeigen (Platzhalter)
        # Hier könnte ein neues Fenster oder eine Ansicht geöffnet werden

    def show_historical_data(self):
        pass  # Historische Daten anzeigen (Platzhalter)
        # Hier könnte ein Diagramm oder eine Ansicht geöffnet werden

    def update_puffer_animation(self):
        try:
            top_temp = float(self.dash_temp_top_str.get().replace(" °C", "").replace("-- ", "0"))
            mid_temp = float(self.dash_temp_mid_str.get().replace(" °C", "").replace("-- ", "0"))
            bot_temp = float(self.dash_temp_bot_str.get().replace(" °C", "").replace("-- ", "0"))
        except (ValueError, AttributeError):
            top_temp, mid_temp, bot_temp = 0, 0, 0

        self.canvas_puffer.delete("all")

        # Pufferspeicher mit Farbverlauf
        x_start, y_start = 20, 20
        width, height = 160, 170

        # Schatten
        self.canvas_puffer.create_rectangle(
            x_start + 2, y_start + 2, x_start + width + 2, y_start + height + 2,
            fill="#000000", outline="", stipple="gray50"
        )

        # Behälter-Rahmen (oben gerundet simuliert)
        self.canvas_puffer.create_rectangle(
            x_start, y_start, x_start + width, y_start + height,
            fill="#0a0f1a", outline="#243354", width=2
        )

        # Temperaturgradient-Füllung (3 Abschnitte mit Übergängen)
        section_height = height / 3
        temps = [top_temp, mid_temp, bot_temp]
        colors_gradient = []
        
        for i, temp in enumerate(temps):
            y_pos = y_start + i * section_height
            # Farbverlauf: Blau (kalt) -> Grün -> Orange -> Rot (heiß)
            if temp < 20:
                color = "#3b82f6"  # Blau
            elif temp < 35:
                color = "#10b981"  # Grün
            elif temp < 50:
                color = "#f59e0b"  # Orange
            elif temp < 65:
                color = "#ef4444"  # Rot
            else:
                color = "#dc2626"  # Dunkelrot
            
            # Abschnitt mit Gradient-Effekt (helle Linie oben, Farbe)
            self.canvas_puffer.create_rectangle(
                x_start + 2, y_pos, x_start + width - 2, y_pos + section_height,
                fill=color, outline="#1f2a44", width=1
            )
            
            # Temperaturanzeige in Abschnitt
            self.canvas_puffer.create_text(
                x_start + width // 2, y_pos + section_height // 2,
                text=f"{temp:.0f}°",
                fill="white", font=("Segoe UI", 16, "bold")
            )

        if self.root.winfo_exists():
            self.root.after(2000, self.update_puffer_animation)

    def update_flow_clock_animation(self):
        """Zeigt digitale Uhr und Stromfluss-Richtung"""
        import datetime
        
        self.canvas_flow.delete("all")
        
        # Uhr
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        
        self.canvas_flow.create_text(
            70, 30,
            text=time_str,
            fill="white", font=("Segoe UI", 32, "bold")
        )
        
        # Sekunden anzeigen
        sec_str = now.strftime("%S")
        self.canvas_flow.create_text(
            70, 50,
            text=f"Sek: {sec_str}",
            fill="#8ba2c7", font=("Segoe UI", 8)
        )
        
        # Stromfluss-Pfeile
        y_arrow = 100
        arrow_spacing = 35
        
        # PV nach Hause (wenn PV > 0)
        if self.pv_flow_value > 0:
            self.canvas_flow.create_text(10, y_arrow, text="☀", fill="#f59e0b", font=("Segoe UI", 14))
            self.canvas_flow.create_text(70, y_arrow, text="→", fill="#0ea5e9", font=("Segoe UI", 16))
            self.canvas_flow.create_text(120, y_arrow, text="🏠", fill="#ec4899", font=("Segoe UI", 14))
        
        # Netz nach Hause (wenn Bezug > 0)
        if self.grid_flow_value > 0:
            self.canvas_flow.create_text(10, y_arrow + arrow_spacing, text="⚡", fill="#ef4444", font=("Segoe UI", 14))
            self.canvas_flow.create_text(70, y_arrow + arrow_spacing, text="→", fill="#ef4444", font=("Segoe UI", 16))
            self.canvas_flow.create_text(120, y_arrow + arrow_spacing, text="🏠", fill="#ec4899", font=("Segoe UI", 14))
        
        # Status-Info
        self.canvas_flow.create_text(
            70, y_arrow + arrow_spacing * 2,
            text=f"PV: {self.pv_flow_value:.1f}kW",
            fill="#0ea5e9", font=("Segoe UI", 8)
        )
        self.canvas_flow.create_text(
            70, y_arrow + arrow_spacing * 2 + 15,
            text=f"Netz: {self.grid_flow_value:.1f}kW",
            fill="#ef4444", font=("Segoe UI", 8)
        )
        
        if self.root.winfo_exists():
            self.root.after(1000, self.update_flow_clock_animation)

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
                alpha=0.32, color=color_pv
            )
            ax.plot(
                df_pv_sub["Zeitstempel"], df_pv_sub["PV-Leistung (kW)"],
                color="#38bdf8", linewidth=1.6, label="PV Leistung"
            )
            ax.set_ylabel("PV (kW)", color="#0ea5e9", fontsize=10, fontweight='bold')
            ax.tick_params(axis='y', labelcolor="#0ea5e9")
            
        if not df_temp_sub.empty:
            # Temperatur auf rechter Achse
            ax2 = ax.twinx()
            ax2.plot(
                df_temp_sub["Zeitstempel"], df_temp_sub["Pufferspeicher Oben"],
                color="#ef4444", linewidth=1.5, label="Puffer Oben", marker='o', markersize=2.5, alpha=0.82
            )
            ax2.set_ylabel("Temp (°C)", color="#ef4444", fontsize=10, fontweight='bold')
            ax2.tick_params(axis='y', labelcolor="#ef4444")
            ax2.spines['right'].set_color('#2d3a5f')
            ax2.spines['left'].set_color('#2d3a5f')
            ax2.spines['top'].set_visible(False)
            ax2.spines['bottom'].set_color('#2d3a5f')
            
        ax.set_facecolor("#0f172a")
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_color('#243354')
        ax.spines['bottom'].set_color('#243354')
        ax.tick_params(colors='#8ba2c7', labelsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid(True, color='#243354', linestyle='--', alpha=0.22, linewidth=0.6)
        
        # Legende kombiniert
        lines1, labels1 = ax.get_legend_handles_labels()
        if not df_temp_sub.empty:
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, 
                     loc='upper left', fontsize=8, facecolor='#0f172a', 
                     edgecolor='#243354', labelcolor='#8ba2c7', framealpha=0.9)
        else:
            ax.legend(loc='upper left', fontsize=8, facecolor='#0f172a', 
                     edgecolor='#243354', labelcolor='#8ba2c7', framealpha=0.9)
            
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