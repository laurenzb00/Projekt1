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

# Matplotlib fest auf Dunkel setzen
plt.style.use("dark_background")

# --- KONFIGURATION ---
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")

# Aktualisierungsrate (ms)
UPDATE_INTERVAL = 60 * 1000 
MAX_PLOT_POINTS = 2000 

# --- HILFSFUNKTION: CSV LESEN ---
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
        print(f"Fehler CSV: {e}")
        return None

# --- HAUPTKLASSE ---
class LivePlotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Energy Dashboard")
        
        # --- FIX: DESIGN ERZWINGEN ---
        # Wir versuchen das Theme zu laden, konfigurieren aber Farben manuell als Fallback
        self.style = ttk.Style("superhero")
        
        # Hintergrund des Hauptfensters dunkel machen (falls root weiß ist)
        try:
            self.root.configure(bg="#2b3e50") 
        except: pass

        self.root.geometry("1100x650") # Etwas breiter für bessere Lesbarkeit
        
        # Konstante Farben für Matplotlib
        self.chart_bg = "#2b3e50" # Dunkelblau-Grau passend zu Superhero
        self.chart_fg = "white"
        self.chart_grid = "#555555"

        self.init_variables()

        # Haupt-Container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=BOTH, expand=YES)

        # Tabs
        self.notebook = ttk.Notebook(self.main_container, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        # Tabs erstellen
        self.setup_dashboard_tab()
        self.setup_plot_tabs()   # Erstellt PV, Temp, Batterie, Ertrag
        self.setup_spotify_tab() # Erstellt Spotify (nur einmal!)

        # Fußzeile
        self.setup_bottom_bar()

        # Start Update
        self.update_plots()

    def init_variables(self):
        self.dash_pv_now = StringVar(value="-- kW")
        self.dash_haus_now = StringVar(value="-- kW")
        self.dash_temp_top_str = StringVar(value="-- °C") # NEU
        self.dash_temp_mid_str = StringVar(value="-- °C")
        self.dash_temp_bot_str = StringVar(value="-- °C")
        self.dash_aussen = StringVar(value="-- °C")
        self.dash_status = StringVar(value="System startet...")
        self.status_time_var = StringVar(value="-")

    # --- TAB 1: DASHBOARD ---
    def setup_dashboard_tab(self):
        self.dash_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dash_frame, text=" Dashboard ")
        
        self.dash_frame.columnconfigure((0,1,2), weight=1)
        self.dash_frame.rowconfigure(0, weight=1)

        # Kachel 1: Leistung
        f1 = ttk.Labelframe(self.dash_frame, text="Leistung", padding=15, bootstyle="warning")
        f1.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ttk.Label(f1, text="PV Aktuell:", font=("Arial", 12)).pack(anchor="w")
        ttk.Label(f1, textvariable=self.dash_pv_now, font=("Arial", 26, "bold"), bootstyle="warning").pack(anchor="w", pady=5)
        ttk.Separator(f1).pack(fill=X, pady=10)
        ttk.Label(f1, text="Verbrauch:", font=("Arial", 12)).pack(anchor="w")
        ttk.Label(f1, textvariable=self.dash_haus_now, font=("Arial", 26, "bold"), bootstyle="info").pack(anchor="w", pady=5)

        # Kachel 2: Speicher
        f2 = ttk.Labelframe(self.dash_frame, text="Speicher", padding=15, bootstyle="success")
        f2.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.meter_batt = ttk.Meter(
            f2, metersize=180, amountused=0, metertype="semi", 
            subtext="SoC %", bootstyle="success", interactive=False, textright="%"
        )
        self.meter_batt.pack(expand=YES)

        # Kachel 3: Wärme (LAYOUT FIX)
        f3 = ttk.Labelframe(self.dash_frame, text="Wärme (Puffer)", padding=15, bootstyle="danger")
        f3.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        
        # Frame für Inhalt
        f3_content = ttk.Frame(f3)
        f3_content.pack(fill=BOTH, expand=YES)

        # Balken (Links) - Ohne Text im Balken, damit nichts abgeschnitten wird
        self.gauge_puffer = ttk.Floodgauge(
            f3_content, bootstyle="danger", font=("Arial", 10), 
            mask=None, orient=VERTICAL # mask=None entfernt den Text im Balken
        )
        self.gauge_puffer.pack(side=LEFT, fill=Y, padx=(0, 15))
        
        # Text (Rechts) - Alles sauber untereinander
        txt_f = ttk.Frame(f3_content)
        txt_f.pack(side=LEFT, fill=BOTH, expand=YES)
        
        # Oben
        ttk.Label(txt_f, text="Oben:", font=("Arial", 11)).pack(anchor="w", pady=(5,0))
        ttk.Label(txt_f, textvariable=self.dash_temp_top_str, font=("Arial", 16, "bold")).pack(anchor="w")
        
        # Mitte
        ttk.Label(txt_f, text="Mitte:", font=("Arial", 11)).pack(anchor="w", pady=(10,0))
        ttk.Label(txt_f, textvariable=self.dash_temp_mid_str, font=("Arial", 16, "bold")).pack(anchor="w")
        
        # Unten
        ttk.Label(txt_f, text="Unten:", font=("Arial", 11)).pack(anchor="w", pady=(10,0))
        ttk.Label(txt_f, textvariable=self.dash_temp_bot_str, font=("Arial", 16, "bold")).pack(anchor="w")
        
        # Untere Leiste: Status
        f_bot = ttk.Frame(self.dash_frame)
        f_bot.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
        ttk.Label(f_bot, text="Außen:", font=("Arial", 12)).pack(side=LEFT)
        ttk.Label(f_bot, textvariable=self.dash_aussen, font=("Arial", 20, "bold"), bootstyle="info").pack(side=LEFT, padx=10)
        ttk.Label(f_bot, textvariable=self.dash_status, font=("Arial", 12), bootstyle="secondary").pack(side=RIGHT)

    # --- TAB 2-5: DIAGRAMME ---
    def setup_plot_tabs(self):
        # Wir erstellen die Tabs explizit, um Dopplungen zu vermeiden
        self.create_single_plot_tab("PV-Leistung", "fronius")
        self.create_single_plot_tab("Temperaturen", "bmk")
        self.create_single_plot_tab("Batterie", "batt")
        self.create_single_plot_tab("Ertrag", "ertrag")

    def create_single_plot_tab(self, name, var_prefix):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=f" {name} ")
        
        # Matplotlib Figur mit festem dunklen Hintergrund
        fig, ax = plt.subplots(figsize=(8, 3), dpi=100)
        fig.patch.set_facecolor(self.chart_bg) # Rahmen dunkel
        ax.set_facecolor(self.chart_bg)        # Diagramm dunkel
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        setattr(self, f"{var_prefix}_fig", fig)
        setattr(self, f"{var_prefix}_ax", ax)
        setattr(self, f"{var_prefix}_canvas", canvas)
        
        if var_prefix == "fronius":
            self.fronius_ax2 = ax.twinx()

    # --- TAB 6: SPOTIFY (Repariert) ---
    def setup_spotify_tab(self):
        self.spotify_frame = ttk.Frame(self.notebook)
        # Unicode Note statt Emoji, um Anzeigefehler "[]" zu vermeiden
        self.notebook.add(self.spotify_frame, text=" Spotify ") 
        
        self.spotify_frame.columnconfigure(0, weight=1)
        self.spotify_frame.columnconfigure(1, weight=2)
        self.spotify_frame.rowconfigure(0, weight=1)

        # Links: Cover (Platzhalter)
        cover_frame = ttk.Frame(self.spotify_frame, bootstyle="secondary")
        cover_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        ttk.Label(cover_frame, text="♫", font=("Arial", 80)).place(relx=0.5, rely=0.4, anchor="center")
        self.spotify_track_lbl = ttk.Label(cover_frame, text="Keine Wiedergabe", font=("Arial", 14, "bold"))
        self.spotify_track_lbl.place(relx=0.5, rely=0.7, anchor="center")

        # Rechts: Suche & Steuerung
        ctrl_frame = ttk.Frame(self.spotify_frame)
        ctrl_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        lbl = ttk.Label(ctrl_frame, text="Musik starten", bootstyle="warning", font=("Arial", 12))
        lbl.pack(anchor="w", pady=(0,5))
        
        search_box = ttk.Frame(ctrl_frame)
        search_box.pack(fill=X, pady=5)
        
        self.spotify_search_entry = ttk.Entry(search_box, font=("Arial", 12))
        self.spotify_search_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0,10))
        ttk.Button(search_box, text="Play", bootstyle="warning", command=self.action_spotify_search).pack(side=RIGHT)

        ttk.Separator(ctrl_frame).pack(fill=X, pady=20)

        # Steuerung Buttons
        btn_box = ttk.Frame(ctrl_frame)
        btn_box.pack(fill=X)
        ttk.Button(btn_box, text="⏮", bootstyle="outline").pack(side=LEFT, padx=5)
        ttk.Button(btn_box, text="⏯", bootstyle="success", width=10).pack(side=LEFT, padx=5)
        ttk.Button(btn_box, text="⏭", bootstyle="outline").pack(side=LEFT, padx=5)

    def setup_bottom_bar(self):
        bar = ttk.Frame(self.root, bootstyle="dark")
        bar.pack(side=BOTTOM, fill=X)
        ttk.Button(bar, text="Beenden", bootstyle="danger-outline", command=self.root.destroy).pack(side=LEFT, padx=5, pady=5)
        ttk.Label(bar, textvariable=self.status_time_var, bootstyle="inverse-dark").pack(side=RIGHT, padx=10)

    def action_spotify_search(self):
        query = self.spotify_search_entry.get()
        if query:
            self.spotify_track_lbl.config(text=f"Spiele: {query}")

    # --- UPDATE LOGIC ---
    def update_plots(self):
        now = pd.Timestamp.now()
        
        # Daten laden
        fronius_df = read_csv_tail_fixed(FRONIUS_CSV, MAX_PLOT_POINTS)
        bmk_df = read_csv_tail_fixed(BMK_CSV, MAX_PLOT_POINTS)

        # 1. Fronius Update
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
                
                # Plots aufrufen
                self._plot_fronius(fronius_df, now)
                self._plot_battery(fronius_df, now)
                self._plot_ertrag(fronius_df, now) # NEU: Ertrag Plot
                
                self.dash_status.set("PV Daten aktuell.")
            except Exception as e:
                print(f"Fronius Error: {e}")

        # 2. Heizung Update
        if bmk_df is not None and not bmk_df.empty:
            try:
                bmk_df["Zeitstempel"] = pd.to_datetime(bmk_df["Zeitstempel"])
                last = bmk_df.iloc[-1]
                
                top = last.get("Pufferspeicher Oben", 0)
                mid = last.get("Pufferspeicher Mitte", 0)
                bot = last.get("Pufferspeicher Unten", 0)
                aussen = last.get("Außentemperatur", 0)
                
                self.gauge_puffer.configure(value=top) # Kein Mask-Text mehr hier
                self.dash_temp_top_str.set(f"{top:.1f} °C") # Dafür Text hier
                self.dash_temp_mid_str.set(f"{mid:.1f} °C")
                self.dash_temp_bot_str.set(f"{bot:.1f} °C")
                self.dash_aussen.set(f"{aussen:.1f} °C")
                
                self._plot_temps(bmk_df, now)
            except Exception as e:
                print(f"Heizung Error: {e}")

        self.status_time_var.set(f"Update: {now.strftime('%H:%M:%S')}")
        self.root.after(UPDATE_INTERVAL, self.update_plots)

    # --- PLOT FUNKTIONEN (Design Fixed) ---
    def _style_ax(self, ax):
        # Erzwingt dunkles Design, egal was das System sagt
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

        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=24))
        df_sub = df.loc[mask]

        if not df_sub.empty:
            ax.fill_between(df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"], color="#f39c12", alpha=0.3)
            ax.plot(df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"], label="PV", color="#f39c12")
            ax.plot(df_sub["Zeitstempel"], df_sub["Hausverbrauch (kW)"], label="Haus", color="#3498db")
            
            # Zweite Achse (Batterie)
            ax2.plot(df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"], color="white", linestyle=":", alpha=0.5)
            ax2.set_ylim(0, 100)
            ax2.tick_params(colors="white")
            
            ax.legend(loc="upper left", facecolor=self.chart_bg, labelcolor="white")
            ax.set_title("PV Leistung (24h)", color="white")
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
            ax.set_title("Batterie SoC", color="white")
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.batt_fig.autofmt_xdate()
        self.batt_canvas.draw()

    def _plot_ertrag(self, df, now):
        ax = self.ertrag_ax
        ax.clear()
        self._style_ax(ax)
        
        # Einfacher Balken für aktuellen Tag (Demo-Logik, da kumulierte Werte oft komplexer sind)
        # Wir nehmen hier einfach die PV-Kurve der letzten 7 Tage als Übersicht
        mask = df["Zeitstempel"] >= (now - pd.Timedelta(days=1))
        df_sub = df.loc[mask]
        
        if not df_sub.empty:
            # Wir zeigen die PV Leistung über einen längeren Zeitraum
            ax.plot(df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"], color="#f1c40f")
            ax.set_title("Ertrag Verlauf (24h Detail)", color="white")
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.ertrag_fig.autofmt_xdate()
        else:
            ax.text(0.5, 0.5, "Warte auf Daten...", color="white", ha="center")
            
        self.ertrag_canvas.draw()

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
            ax.legend(facecolor=self.chart_bg, labelcolor="white")
            ax.set_title("Temperaturen", color="white")
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.bmk_fig.autofmt_xdate()
        self.bmk_canvas.draw()