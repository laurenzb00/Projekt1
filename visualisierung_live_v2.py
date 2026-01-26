"""
MODERNES ENERGIE-DASHBOARD v2
=====================================
Vollständig redesigntes Dashboard mit:
- Zusammengefasstem PV-Hauptfeld
- Modernem Glasmorphism Design
- Besseren Visualisierungen
- PIL für bessere Grafiken
- Touch-optimiert für 1024x600
"""

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
import datetime
from PIL import Image, ImageDraw, ImageTk
from boiler_widget import ModernBoilerWidget  # <--- MODERNES BOILER WIDGET
from modern_widgets import BatteryGaugeWidget  # <--- BATTERIE GAUGE
from energy_flow_widget_v2 import EnergyFlowWidgetV2  # <--- NEUE SCHÖNE ENERGIEFLUSS

# Matplotlib Stil
plt.style.use("dark_background")

# --- KONFIGURATION ---
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")
ERTRAG_CSV = os.path.join(WORKING_DIRECTORY, "ErtragHistory.csv")

UPDATE_INTERVAL = 60 * 1000
MAX_PLOT_POINTS = 10000

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600

# Typografie
FONT_FAMILY = "Segoe UI"
FONT_SIZE_LARGE = 42
FONT_SIZE_MEDIUM = 16
FONT_SIZE_SMALL = 11
FONT_SIZE_TINY = 9

# Glasmorphism Design-System (dunkel & transparent)
COLOR_DARK_BG = "#0a0e1a"      # Sehr dunkler Hintergrund (fast schwarz)
COLOR_CARD_BG = "#1a1f2e"      # Transparente Cards (dunkel)
COLOR_GLASS_BG = "#1a1f2e"     # Glass Cards mit Transparency
COLOR_CARD_HOVER = "#242938"   # Hover State
COLOR_PRIMARY = "#3b82f6"      # Primary Blau (Tabs, Buttons)
COLOR_SUCCESS = "#10b981"      # Grün für positive Flows
COLOR_WARNING = "#f59e0b"      # Orange für Verbrauch
COLOR_DANGER = "#ef4444"       # Rot nur für Fehler
COLOR_TEXT = "#e2e8f0"         # Off-White für Text
COLOR_SUBTEXT = "#64748b"      # Gedimmtes Grau für Secondary
COLOR_BORDER = "#2d3548"       # Glass Border (subtiler)

# Backward Compatibility: Alte Farbnamen → Neue Farben (für Plot-Code)
COLOR_PV = COLOR_SUCCESS       # PV = Grün (Produktion)
COLOR_LOAD = COLOR_WARNING     # Load = Orange (Verbrauch)
COLOR_BATTERY = COLOR_PRIMARY  # Battery = Primary Blue
COLOR_GRID = COLOR_DANGER      # Grid = Rot (Netzbezug)
COLOR_ACCENT_LIGHT = COLOR_BORDER  # Accent = Border

# --- HILFSFUNKTIONEN ---
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
        
        if "Zeitstempel" in df.columns:
            df["Zeitstempel"] = pd.to_datetime(df["Zeitstempel"], errors='coerce')
            df = df.dropna(subset=["Zeitstempel"])
        
        return df
    except Exception as e:
        print(f"Fehler beim Lesen von {path}: {e}")
        return None

def create_gradient_image(width, height, color1, color2):
    """Erstellt ein Gradient-Bild (horizontal)"""
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # Hex zu RGB
    c1 = tuple(int(color1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    c2 = tuple(int(color2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    for x in range(width):
        r = int(c1[0] + (c2[0] - c1[0]) * x / width)
        g = int(c1[1] + (c2[1] - c1[1]) * x / width)
        b = int(c1[2] + (c2[2] - c1[2]) * x / width)
        draw.line([(x, 0), (x, height)], fill=(r, g, b))
    
    return img

# --- HAUPTKLASSE ---
class LivePlotApp:
    def __init__(self, root):
        self.root = root
        
        self.init_variables()
        self.spotify_instance = None

        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=BOTH, expand=YES)

        self.notebook = ttk.Notebook(self.main_container)
        
        # Custom Tab Styling (modernes flaches Design) - verwende tkinter.ttk.Style statt ttkbootstrap
        from tkinter import ttk as tkinter_ttk
        style = tkinter_ttk.Style()
        
        try:
            style.theme_use('clam')  # Modernes Theme als Basis
        except:
            pass  # Falls Theme nicht verfügbar, nutze Standard
        
        # Tab-Hintergrund (sehr dunkel für Glasmorphism)
        style.configure('TNotebook', background=COLOR_DARK_BG, borderwidth=0)
        style.configure('TNotebook.Tab', 
                       background=COLOR_GLASS_BG,
                       foreground=COLOR_SUBTEXT,
                       padding=[16, 12],
                       borderwidth=0,
                       font=('Segoe UI', 10))
        
        # Aktiver Tab (Primary Blue mit leichtem Glow)
        style.map('TNotebook.Tab',
                 background=[('selected', COLOR_PRIMARY), ('active', COLOR_GLASS_BG)],
                 foreground=[('selected', '#ffffff'), ('active', COLOR_TEXT)],
                 expand=[('selected', [1, 1, 1, 0])])
        
        self.notebook.pack(fill=BOTH, expand=YES)

        # Dashboard Tab
        self.dashboard_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.setup_dashboard_tab()
        
        # Alle anderen Tabs
        self.setup_plot_tabs()

        self.setup_bottom_bar()
        self.update_plots()
        self.schedule_ertrag_updates()

        # Vollbildmodus
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.geometry(f'{SCREEN_WIDTH}x{SCREEN_HEIGHT}+0+0')
        self.root.overrideredirect(True)
        self.root.bind('<Escape>', self.exit_fullscreen)

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
        
        self.pv_flow_value = 0
        self.load_flow_value = 0
        self.grid_flow_value = 0

    def exit_fullscreen(self, event=None):
        self.root.destroy()

    def _update_battery_color(self, soc):
        """Ändert Batterie-Farbe basierend auf Ladestand"""
        if soc < 20:
            color = "#ef4444"
        elif soc < 50:
            color = "#f59e0b"
        elif soc < 80:
            color = "#10b981"
        else:
            color = "#059669"
        
        try:
            self.battery_col.configure(bg=color)
            self.battery_value_label.configure(bg=color)
        except:
            pass

    def _highlight_card(self, card, highlight_color):
        """Hebt eine Karte hervor"""
        try:
            original_color = card.cget("bg")
            card.configure(bg=highlight_color)
            self.root.after(500, lambda: card.configure(bg=original_color))
        except:
            pass

    # --- MODERNES DASHBOARD LAYOUT ---
    def setup_dashboard_tab(self):
        self.dashboard_frame = tk.Frame(self.dashboard_tab, bg=COLOR_DARK_BG)
        self.dashboard_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== HEADER (TOP - Full Width) =====
        self._create_header_info_widget()
        
        # ===== MAIN CONTAINER (Asymmetric Layout) =====
        main_container = tk.Frame(self.dashboard_frame, bg=COLOR_DARK_BG)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        
        # LEFT: Large Energiefluss (70% width - dominant)
        left_frame = tk.Frame(main_container, bg=COLOR_DARK_BG)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        self._create_pv_main_card(parent=left_frame)
        
        # RIGHT: Vertical stack (fixed ~320px, lässt mehr Breite für Energiefluss)
        right_frame = tk.Frame(main_container, bg=COLOR_DARK_BG, width=320)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        
        # RIGHT TOP: Pufferspeicher (jetzt oben, da Light-Buttons im Header sind)
        puffer_container = self._create_glass_card(
            parent=right_frame,
            title="Pufferspeicher",
            icon="🔥"
        )
        
        # Modernes Boiler-Widget mit Heatmap
        self.boiler_widget = ModernBoilerWidget(
            puffer_container, 
            width=300, 
            height=340,
            style="heatmap"
        )
        self.boiler_widget.pack(padx=12, pady=8, fill=tk.BOTH, expand=True)
        
        # Initiale Testwerte für Pufferspeicher
        self.boiler_widget.update_temperatures(65, 58, 48, 70)

        # Start Animationen
        self.update_puffer_animation()
        self.update_flow_clock_animation()

    def _create_pv_main_card(self, parent=None):
        """Großes PV-Haupt-Feld mit Glasmorphism Energiefluss-Animation"""
        if parent is None:
            parent = self.dashboard_frame
            
        # Glass Card mit transparentem Effekt
        card = self._create_glass_card(
            parent=parent,
            title="Energiefluss",
            icon="⚡"
        )
        # Content: Großer Energiefluss
        content = tk.Frame(card, bg=COLOR_GLASS_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        
        # Großer Energiefluss mit neuen schönen Icons - maximaler Platz
        self.energy_flow_widget = EnergyFlowWidgetV2(content, width=700, height=400, style="glass")
        self.energy_flow_widget.frame.pack(fill=tk.BOTH, expand=True)
        
        # Initiale Darstellung mit Testwerten (wird später durch echte Daten ersetzt)
        self.energy_flow_widget.update_flows(2500, 1800, -500, 200, 65)
        
        self.pv_card = content  # Für spätere Highlight-Funktionen
        self.verbrauch_card = content

        return card
    
    def _create_glass_card(self, parent, title="", icon="", subtitle=""):
        """Erstellt Glasmorphism Card mit transparentem Blur-Effekt"""
        # Outer Container für Glow-Effekt (wird ins Parent gepackt)
        container = tk.Frame(parent, bg=COLOR_DARK_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        
        # Glass Card mit Border (simuliert Glasrand)
        glass_border = tk.Frame(
            container,
            bg=COLOR_BORDER,
            highlightthickness=0
        )
        glass_border.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Haupt Glass Card (transparenter Effekt durch dunkle Farbe)
        card = tk.Frame(
            glass_border,
            bg=COLOR_GLASS_BG,
            highlightthickness=0
        )
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Header mit Titel
        if title or icon:
            header = tk.Frame(card, bg=COLOR_GLASS_BG)
            header.pack(fill=tk.X, padx=16, pady=(16, 8))
            
            if icon:
                tk.Label(
                    header, 
                    text=icon, 
                    font=("Segoe UI", 16), 
                    bg=COLOR_GLASS_BG, 
                    fg=COLOR_TEXT
                ).pack(side=tk.LEFT, padx=(0, 10))
            
            title_frame = tk.Frame(header, bg=COLOR_GLASS_BG)
            title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            tk.Label(
                title_frame, 
                text=title,
                font=("Segoe UI", 13, "bold"), 
                bg=COLOR_GLASS_BG, 
                fg=COLOR_TEXT
            ).pack(anchor="w")
            
            if subtitle:
                tk.Label(
                    title_frame,
                    text=subtitle,
                    font=("Segoe UI", 9),
                    bg=COLOR_GLASS_BG,
                    fg=COLOR_SUBTEXT
                ).pack(anchor="w")
        
        return card
    
    def _create_modern_card(self, parent, title="", icon="", subtitle=""):
        """Legacy wrapper - nutzt jetzt Glass Cards"""
        return self._create_glass_card(parent, title, icon, subtitle)
    
    def _create_header_info_widget(self):
        """Erstellt Top-Zeile mit Glasmorphism Header"""
        # Glass Card für Header
        header_card = tk.Frame(self.dashboard_frame, bg=COLOR_GLASS_BG, height=80)
        header_card.pack(fill=tk.X, padx=20, pady=(16, 12))
        header_card.pack_propagate(False)
        
        # Border für Glass-Effekt
        border_frame = tk.Frame(header_card, bg=COLOR_BORDER)
        border_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        header_content = tk.Frame(border_frame, bg=COLOR_GLASS_BG)
        header_content.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        inner_content = tk.Frame(header_content, bg=COLOR_GLASS_BG)
        inner_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=12)
        
        # Linke Seite: Datum (kleiner, gedimmter)
        left_frame = tk.Frame(inner_content, bg=COLOR_GLASS_BG)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(
            left_frame, 
            text="DATUM", 
            font=("Segoe UI", 8, "bold"), 
            fg=COLOR_SUBTEXT, 
            bg=COLOR_GLASS_BG
        ).pack(anchor="w")
        self.date_header_label = tk.Label(
            left_frame, 
            text="", 
            font=("Segoe UI", 14),
            fg=COLOR_TEXT, 
            bg=COLOR_GLASS_BG
        )
        self.date_header_label.pack(anchor="w", pady=(2, 0))
        
        # Mitte: Uhrzeit (dominant, Primary Farbe)
        middle_frame = tk.Frame(inner_content, bg=COLOR_GLASS_BG)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.clock_header_label = tk.Label(
            middle_frame, 
            text="--:--", 
            font=("Segoe UI", 38, "bold"),
            fg=COLOR_PRIMARY, 
            bg=COLOR_GLASS_BG
        )
        self.clock_header_label.pack()
        
        # Rechte Seite: Außentemperatur + Light Toggle Buttons
        right_frame = tk.Frame(inner_content, bg=COLOR_GLASS_BG)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Oben: Außentemperatur
        temp_frame = tk.Frame(right_frame, bg=COLOR_GLASS_BG)
        temp_frame.pack(anchor="e", pady=(0, 8))
        
        tk.Label(
            temp_frame, 
            text="AUẞEN", 
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_SUBTEXT, 
            bg=COLOR_GLASS_BG
        ).pack(anchor="e")
        self.aussen_header_label = tk.Label(
            temp_frame, 
            text="-- °C", 
            font=("Segoe UI", 16, "bold"),
            fg=COLOR_WARNING, 
            bg=COLOR_GLASS_BG
        )
        self.aussen_header_label.pack(anchor="e")
        
        # Unten: Light Toggle Buttons (Glasmorphism Style)
        light_buttons_frame = tk.Frame(right_frame, bg=COLOR_GLASS_BG)
        light_buttons_frame.pack(anchor="e", pady=(10, 0))
        
        # Glass Button Style
        self.light_on_btn = tk.Button(
            light_buttons_frame,
            text="💡 AN",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_SUCCESS,
            fg="white",
            padx=10,
            pady=5,
            command=self.turn_lights_on,
            relief=tk.FLAT,
            cursor="hand2",
            activebackground="#0d9668",
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_BORDER
        )
        self.light_on_btn.pack(side=tk.LEFT, padx=3)
        
        self.light_off_btn = tk.Button(
            light_buttons_frame,
            text="🌙 AUS",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_BORDER,
            fg=COLOR_TEXT,
            padx=10,
            pady=5,
            command=self.turn_lights_off,
            relief=tk.FLAT,
            cursor="hand2",
            activebackground="#1f2937",
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_BORDER
        )
        self.light_off_btn.pack(side=tk.LEFT, padx=3)
        
        # Speichere Referenz für Updates (optional)
        self.light_status_label = None
    
    def _create_battery_status_widget(self):
        """Erstellt Batterie-Status Widget mit großem Symbol"""
        content = tk.Frame(self.battery_card, bg=COLOR_CARD_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Batterie-Symbol (groß)
        battery_frame = tk.Frame(content, bg=COLOR_CARD_BG)
        battery_frame.pack(expand=True)
        
        self.battery_main_widget = BatteryGaugeWidget(battery_frame, width=150, height=200, style="pil")
        self.battery_main_widget.pack()
    
    def turn_lights_on(self):
        """Schaltet alle Lichter an"""
        self.light_status_label.configure(text="✓ Licht AN", fg="#10b981")
        print("Licht AN geklickt")
        try:
            if hasattr(self, 'bridge') and self.bridge:
                for light in self.bridge.lights:
                    light.on = True
        except Exception as e:
            print(f"Fehler beim Einschalten: {e}")
    
    def turn_lights_off(self):
        """Schaltet alle Lichter aus"""
        self.light_status_label.configure(text="✗ Licht AUS", fg="#6b7280")
        print("Licht AUS geklickt")
        try:
            if hasattr(self, 'bridge') and self.bridge:
                for light in self.bridge.lights:
                    light.on = False
        except Exception as e:
            print(f"Fehler beim Ausschalten: {e}")
        """Erstellt Uhrzeit-Widget mit Batterie-Status integriert"""
        content = tk.Frame(self.clock_card, bg=COLOR_CARD_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Uhrzeit (groß)
        self.clock_label = tk.Label(
            content, 
            text="--:--",
            font=("Segoe UI", 48, "bold"),
            fg="white",
            bg=COLOR_CARD_BG
        )
        self.clock_label.pack(pady=(10, 5))
        
        # Datum
        self.date_label = tk.Label(
            content,
            text="",
            font=("Segoe UI", 12),
            fg=COLOR_SUBTEXT,
            bg=COLOR_CARD_BG
        )
        self.date_label.pack(pady=(0, 15))
        
        # Batterie-Status (klein mit Icon und %)
        battery_info = tk.Frame(content, bg=COLOR_CARD_BG)
        battery_info.pack(pady=5)
        
        tk.Label(
            battery_info,
            text="🔋",
            font=("Segoe UI", 16),
            bg=COLOR_CARD_BG
        ).pack(side=tk.LEFT, padx=5)
        
        self.battery_status_label = tk.Label(
            battery_info,
            text="---%",
            font=("Segoe UI", 14, "bold"),
            fg=COLOR_BATTERY,
            bg=COLOR_CARD_BG
        )
        self.battery_status_label.pack(side=tk.LEFT)

    def _create_chart_card(self, parent, row=None, col=None, colspan=None, title=""):
        """Erstellt eine Karte für Charts (grid oder pack-basiert)"""
        card = tk.Frame(
            parent,
            bg=COLOR_CARD_BG,
            relief=tk.FLAT,
            bd=0,
            highlightbackground=COLOR_ACCENT_LIGHT,
            highlightthickness=1
        )
        
        # Grid-basiert wenn row/col gegeben, sonst pack
        if row is not None and col is not None:
            card.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=4, pady=4)
        else:
            # Pack-basiert (wird automatisch von parent.pack() genutzt)
            pass
        
        header = tk.Frame(card, bg="#142038")
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text=title,
            font=("Segoe UI", 10, "bold"),
            bg="#142038", fg="white",
            pady=6, padx=10
        ).pack(anchor="w")
        
        return card

    def _create_mini_chart(self):
        """Erstellt minimales Chart"""
        fig, ax = plt.subplots(figsize=(5.5, 2.5), dpi=85)
        fig.patch.set_facecolor(COLOR_CARD_BG)
        ax.set_facecolor(COLOR_CARD_BG)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#243354')
        ax.spines['bottom'].set_color('#243354')
        ax.tick_params(colors='#8ba2c7', labelsize=8)
        ax.grid(True, color='#243354', linestyle='--', alpha=0.18, linewidth=0.6)
        return fig, ax

    def setup_plot_tabs(self):
        self.create_single_plot_tab("PV-Leistung", "fronius")
        self.create_single_plot_tab("Temperaturen", "bmk")
        self.create_single_plot_tab("Batterie", "batt")
        self.create_single_plot_tab("Ertrag", "ertrag")

    def create_single_plot_tab(self, name, var_prefix):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=f" {name} ")
        
        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        fig.patch.set_facecolor(COLOR_CARD_BG)
        ax.set_facecolor(COLOR_CARD_BG)
        
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
        ttk.Button(bar, text="✕ Beenden", bootstyle="danger-outline", 
                  command=self.root.destroy, width=12).pack(side=LEFT, padx=3, pady=3)
        ttk.Label(bar, textvariable=self.status_time_var, 
                 bootstyle="inverse-dark", font=("Segoe UI", 8)).pack(side=RIGHT, padx=8)

    # --- UPDATE LOGIC ---
    def update_plots(self):
        now = pd.Timestamp.now()
        
        fronius_df = read_csv_tail_fixed(FRONIUS_CSV, MAX_PLOT_POINTS)
        bmk_df = read_csv_tail_fixed(BMK_CSV, MAX_PLOT_POINTS)

        if fronius_df is not None and not fronius_df.empty:
            try:
                last = fronius_df.iloc[-1]
                
                pv = last.get("PV-Leistung (kW)", 0)
                haus = last.get("Hausverbrauch (kW)", 0)
                soc = last.get("Batterieladestand (%)", 0)
                battery_power = last.get("Batterie-Leistung (kW)", 0)  # Für Energiefluss
                
                self.dash_pv_now.set(f"{pv:.2f} kW")
                self.dash_haus_now.set(f"{haus:.2f} kW")
                
                # Speichere SOC für Energiefluss-Widget (neue Batterie-Anzeige)
                self.last_battery_soc = int(soc)
                
                # Speichere Werte für Energiefluss (später nutzbar)
                self.current_pv = pv * 1000  # in Watt
                self.current_load = haus * 1000
                self.current_battery = battery_power * 1000
                self.current_grid = last.get("Netz-Leistung (kW)", 0) * 1000
                
                # Update Energiefluss-Widget mit neuer schöner Anzeige UND Battery SOC
                self.energy_flow_widget.update_flows(
                    self.current_pv,
                    self.current_load,
                    self.current_battery,
                    self.current_grid,
                    battery_soc=float(self.last_battery_soc)
                )
                
                self._update_battery_color(soc)
                
                if pv > 0.5:
                    self._highlight_card(self.pv_card, COLOR_PV)
                
                if haus > 5.0:
                    self._highlight_card(self.verbrauch_card, "#dc2626")
                
                if haus > 0:
                    autarkie = min(pv, haus) / haus * 100
                    self.dash_autarkie.set(f"{int(autarkie)} %")
                else:
                    self.dash_autarkie.set("100 %")
                
                # Stromfluss
                self.pv_flow_value = max(0, pv)
                if "Netz-Leistung (kW)" in last.index:
                    netz = last.get("Netz-Leistung (kW)", 0)
                    self.grid_flow_value = max(0, netz)
                else:
                    self.grid_flow_value = 0
                
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
                # self._update_combined_trend(fronius_df, bmk_df, now)  # Removed - old tab visualization
                self.dash_status.set("PV Daten aktuell.")
            except Exception as e:
                import traceback
                print(f"Fronius Update Fehler: {e}")
                traceback.print_exc()

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
        if self.root.winfo_exists():
            self.root.after(UPDATE_INTERVAL, self.update_plots)

    # --- ERTRAG AGGREGATION ---
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
                mask = fronius_df["Zeitstempel"] >= (pd.Timestamp.now() - pd.Timedelta(hours=48))
                segment = fronius_df[mask]
            if segment.empty:
                return
            self._append_ertrag_segment(segment)
        except Exception as e:
            print(f"Ertrag Aggregation Fehler: {e}")

    def schedule_ertrag_updates(self):
        self._ensure_ertrag_file()
        self._update_ertrag_hourly()
        try:
            self._plot_ertrag()
        except Exception:
            pass
        if self.root.winfo_exists():
            self.root.after(60 * 60 * 1000, self.schedule_ertrag_updates)

    # --- PLOTTING ---
    def _style_ax(self, ax):
        ax.set_facecolor(COLOR_CARD_BG)
        ax.tick_params(colors=COLOR_SUBTEXT, which='both', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#243354')
            spine.set_linewidth(1.0)
        ax.yaxis.label.set_color(COLOR_SUBTEXT)
        ax.xaxis.label.set_color(COLOR_SUBTEXT)
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
            ax.fill_between(
                df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"],
                color="#22d3ee", alpha=0.35, label="PV Erzeugung"
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["PV-Leistung (kW)"],
                color=COLOR_PV, linewidth=2.0, label="_nolegend_"
            )
            
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Hausverbrauch (kW)"],
                label="Hausverbrauch", color=COLOR_LOAD, linewidth=1.6, linestyle="--"
            )
            
            if "Netz-Leistung (kW)" in df_sub.columns:
                netz = df_sub["Netz-Leistung (kW)"]
                bezug_mask = netz > 0.1
                if bezug_mask.any():
                    ax.plot(
                        df_sub.loc[bezug_mask, "Zeitstempel"], 
                        df_sub.loc[bezug_mask, "Netz-Leistung (kW)"],
                        color=COLOR_GRID, linewidth=1.3, label="Netzbezug", marker=".", markersize=2.5
                    )
            
            ax2.plot(
                df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"],
                color=COLOR_BATTERY, linestyle=":", alpha=0.7, linewidth=1.2, label="Batterie %"
            )
            ax2.set_ylim(0, 100)
            ax2.tick_params(colors=COLOR_BATTERY, labelsize=8)
            ax2.spines['right'].set_color(COLOR_BATTERY)
            ax2.yaxis.label.set_color(COLOR_BATTERY)
            ax2.set_ylabel("Batterie (%)", color=COLOR_BATTERY, fontsize=9, fontweight='bold')
            
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2,
                     loc="upper left", facecolor=COLOR_CARD_BG, edgecolor='#243354',
                     labelcolor='white', fontsize=8, framealpha=0.9)
            
            ax.set_title("Energie-Fluss (48h)", color="white", fontsize=11, fontweight='bold')
            ax.set_ylabel("Leistung (kW)", color=COLOR_SUBTEXT, fontsize=9)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.fronius_fig.patch.set_facecolor(COLOR_CARD_BG)
            self.fronius_fig.autofmt_xdate()
        self.fronius_canvas.draw()

    def _plot_battery(self, df, now):
        ax = self.batt_ax
        ax.clear()
        self._style_ax(ax)
        
        mask = df["Zeitstempel"] >= (now - pd.Timedelta(hours=48))
        df_sub = df.loc[mask]
        
        if not df_sub.empty:
            ax.fill_between(
                df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"],
                color=COLOR_BATTERY, alpha=0.28
            )
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Batterieladestand (%)"],
                color=COLOR_BATTERY, linewidth=1.6
            )
            ax.set_ylim(0, 100)
            ax.set_title("Batterieverlauf (48h)", color="white", fontsize=11, fontweight='bold')
            ax.set_ylabel("Ladestand (%)", color=COLOR_SUBTEXT, fontsize=9)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.batt_fig.patch.set_facecolor(COLOR_CARD_BG)
            self.batt_fig.autofmt_xdate()
        self.batt_canvas.draw()

    def _plot_ertrag(self):
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
                
                ax.fill_between(
                    dates, values,
                    color="#06b6d4", alpha=0.25, label="Ertrag"
                )
                ax.plot(
                    dates, values,
                    color="#06b6d4", linewidth=1.8, marker="o", markersize=2.5, label="Tagesertrag"
                )

                avg = df_daily["Ertrag_kWh"].mean()
                ax.axhline(
                    y=avg, color="#f59e0b", linestyle="--", linewidth=1.2, alpha=0.6,
                    label=f"Ø {avg:.1f} kWh"
                )

                max_day = df_daily["Ertrag_kWh"].idxmax()
                max_val = df_daily["Ertrag_kWh"].max()
                min_day = df_daily["Ertrag_kWh"].idxmin()
                min_val = df_daily["Ertrag_kWh"].min()
                
                ax.plot(max_day, max_val, "*", color="#10b981", markersize=12, label=f"Max: {max_val:.1f} kWh")
                ax.plot(min_day, min_val, "v", color="#ef4444", markersize=6, label=f"Min: {min_val:.1f} kWh")

                total = df_daily["Ertrag_kWh"].sum()
                ax.text(
                    0.98, 0.98, f"Summe: {total:.0f} kWh",
                    transform=ax.transAxes, ha="right", va="top",
                    color="white", fontsize=10, fontweight="bold",
                    bbox=dict(boxstyle="round", facecolor=COLOR_CARD_BG, alpha=0.8, edgecolor="#243354")
                )

                ax.legend(loc="upper left", facecolor=COLOR_CARD_BG, edgecolor="#243354",
                         labelcolor="white", fontsize=8, framealpha=0.9)
                ax.set_title("Tagesertrag (90+ Tage)", color="white", fontsize=11, fontweight="bold")
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m."))
                ax.set_xlabel("Datum", color=COLOR_SUBTEXT, fontsize=9)
                ax.set_ylabel("Ertrag (kWh)", color=COLOR_SUBTEXT, fontsize=9)
                self.ertrag_fig.patch.set_facecolor(COLOR_CARD_BG)
                self.ertrag_fig.autofmt_xdate()
            else:
                ax.text(0.5, 0.5, "Keine Daten verfügbar", color="white", ha="center",
                        transform=ax.transAxes, fontsize=12)
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
            
            ax.plot(
                df_sub["Zeitstempel"], df_sub["Außentemperatur"],
                color="#06b6d4", label="Außentemperatur", linestyle="--", 
                alpha=0.85, linewidth=1.3
            )
            
            if "Kesseltemperatur" in df_sub.columns:
                ax.plot(
                    df_sub["Zeitstempel"], df_sub["Kesseltemperatur"],
                    color="#a855f7", label="Kessel", linewidth=1.4, alpha=0.75
                )
            
            ax.legend(facecolor=COLOR_CARD_BG, edgecolor='#243354',
                     labelcolor='white', fontsize=8, framealpha=0.9, loc='best')
            ax.set_title("Heizungs-Temperaturen (7 Tage)", color="white", 
                        fontsize=11, fontweight='bold')
            ax.set_ylabel("Temperatur (°C)", color=COLOR_SUBTEXT, fontsize=9)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))
            self.bmk_fig.patch.set_facecolor(COLOR_CARD_BG)
            self.bmk_fig.autofmt_xdate()
        self.bmk_canvas.draw()

    def _update_combined_trend(self, df_pv, df_temp, now):
        ax = self.pv_trend_ax
        ax.clear()
        
        mask_pv = df_pv["Zeitstempel"] >= (now - pd.Timedelta(hours=24))
        df_pv_sub = df_pv.loc[mask_pv]
        
        mask_temp = df_temp["Zeitstempel"] >= (now - pd.Timedelta(hours=24))
        df_temp_sub = df_temp.loc[mask_temp]
        
        if not df_pv_sub.empty:
            ax.fill_between(
                df_pv_sub["Zeitstempel"], df_pv_sub["PV-Leistung (kW)"],
                alpha=0.32, color="#22d3ee"
            )
            ax.plot(
                df_pv_sub["Zeitstempel"], df_pv_sub["PV-Leistung (kW)"],
                color=COLOR_PV, linewidth=1.6, label="PV Leistung"
            )
            ax.set_ylabel("PV (kW)", color="#0ea5e9", fontsize=10, fontweight='bold')
            ax.tick_params(axis='y', labelcolor="#0ea5e9")
            
        if not df_temp_sub.empty:
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
            
        ax.set_facecolor(COLOR_CARD_BG)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_color('#243354')
        ax.spines['bottom'].set_color('#243354')
        ax.tick_params(colors=COLOR_SUBTEXT, labelsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid(True, color='#243354', linestyle='--', alpha=0.22, linewidth=0.6)
        
        self.pv_trend_canvas.draw()

    # --- ANIMATIONEN ---
    def update_puffer_animation(self):
        """Aktualisiert das moderne Boiler-Widget"""
        try:
            top_temp = float(self.dash_temp_top_str.get().replace(" °C", "").replace("-- ", "0"))
            mid_temp = float(self.dash_temp_mid_str.get().replace(" °C", "").replace("-- ", "0"))
            bot_temp = float(self.dash_temp_bot_str.get().replace(" °C", "").replace("-- ", "0"))
        except (ValueError, AttributeError):
            top_temp, mid_temp, bot_temp = 0, 0, 0

        # Update Boiler Widget statt Canvas
        self.boiler_widget.update_temperatures(top_temp, mid_temp, bot_temp)

        if self.root.winfo_exists():
            self.root.after(2000, self.update_puffer_animation)

    def update_flow_clock_animation(self):
        """Aktualisiert Uhrzeit, Datum und Außentemperatur im Header"""
        import datetime
        
        now = datetime.datetime.now()
        
        # Header: Uhrzeit (groß mittig)
        time_str = now.strftime("%H:%M")
        self.clock_header_label.configure(text=time_str)
        
        # Header: Datum (links)
        date_str = now.strftime("%d.%m.%Y")
        weekday = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][now.weekday()]
        self.date_header_label.configure(text=f"{weekday}\n{date_str}")
        
        # Header: Außentemperatur (rechts)
        try:
            aussen_temp = self.dash_aussen.get()
        except:
            aussen_temp = "-- °C"
        self.aussen_header_label.configure(text=aussen_temp)
        
        # Update Batterie-Widget
        try:
            if hasattr(self, 'battery_main_widget') and hasattr(self, 'last_battery_soc'):
                self.battery_main_widget.update_soc(self.last_battery_soc)
        except:
            pass
        
        if self.root.winfo_exists():
            self.root.after(1000, self.update_flow_clock_animation)


# --- MAIN ---
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry(f'{SCREEN_WIDTH}x{SCREEN_HEIGHT}')
    root.resizable(False, False)
    root.title("Modern Energy Dashboard")
    
    app = LivePlotApp(root)
    root.mainloop()
