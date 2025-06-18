import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk
import tkinter as tk
import os
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
import numpy as np
import matplotlib.ticker as mticker  # Am Anfang der Datei ergänzen
from tkinter import StringVar
from datetime import datetime

WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")

UPDATE_INTERVAL = 60 * 1000  # 1 Minute in ms

class LivePlotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live-Daten Visualisierung")
        self.root.geometry("1024x600")
        self.root.resizable(False, False)
        self.root.attributes("-fullscreen", True)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Fronius Tab
        self.fronius_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.fronius_frame, text="Fronius")
        self.fronius_fig, self.fronius_ax = plt.subplots(figsize=(8, 3))
        self.fronius_ax2 = self.fronius_ax.twinx()
        self.fronius_canvas = FigureCanvasTkAgg(self.fronius_fig, master=self.fronius_frame)
        self.fronius_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # BMK Tab (umbenannt)
        self.bmk_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.bmk_frame, text="Temperaturen 2 Tage")
        self.bmk_fig, self.bmk_ax = plt.subplots(figsize=(8, 3))
        self.bmk_canvas = FigureCanvasTkAgg(self.bmk_fig, master=self.bmk_frame)
        self.bmk_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 1. PV-Ertrag Tab (jetzt Liniendiagramm)
        self.pv_ertrag_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.pv_ertrag_frame, text="PV-Ertrag (Tage)")
        self.pv_ertrag_fig, self.pv_ertrag_ax = plt.subplots(figsize=(8, 3))
        self.pv_ertrag_canvas = FigureCanvasTkAgg(self.pv_ertrag_fig, master=self.pv_ertrag_frame)
        self.pv_ertrag_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 2. Batterie-Ladestand Verlauf Tab
        self.batt_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.batt_frame, text="Batterie Verlauf")
        self.batt_fig, self.batt_ax = plt.subplots(figsize=(8, 3))
        self.batt_canvas = FigureCanvasTkAgg(self.batt_fig, master=self.batt_frame)
        self.batt_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Zusammenfassung Tab (aktuelle Werte als große Zahlen)
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="Zusammenfassung")
        self.summary_fig, self.summary_ax = plt.subplots(figsize=(8, 3))
        self.summary_canvas = FigureCanvasTkAgg(self.summary_fig, master=self.summary_frame)
        self.summary_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Button-Frame
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(side=tk.BOTTOM, pady=10)

        # Button zum Beenden
        self.close_button = tk.Button(self.button_frame, text="Schließen", command=self.root.destroy, font=("Arial", 14), bg="red", fg="white")
        self.close_button.pack(side=tk.LEFT, padx=10)

        # Button zum Minimieren
        self.minimize_button = tk.Button(self.button_frame, text="Minimieren", command=self.minimize_window, font=("Arial", 14), bg="gray", fg="white")
        self.minimize_button.pack(side=tk.LEFT, padx=10)

        # Bilder einmal laden
        self.icons = {}
        self.offset_images_cache = {}
        for icon in ["temperature.png", "outdoor.png", "battery.png", "house.png", "power.png"]:
            path = os.path.join(WORKING_DIRECTORY, "icons", icon)
            if os.path.exists(path):
                self.icons[icon] = Image.open(path)
        bg_path = os.path.join(WORKING_DIRECTORY, "icons", "background.png")
        self.bg_img = Image.open(bg_path).resize((1024, 600), Image.LANCZOS) if os.path.exists(bg_path) else None

        # Zeitbereich Auswahl
        # self.time_range_var = StringVar(value="48h")
        # self.time_range_box = ttk.Combobox(
        #     root,
        #     textvariable=self.time_range_var,
        #     values=["24h", "48h", "7d", "30d"],
        #     state="readonly",
        #     font=("Arial", 12),
        #     width=7
        # )
        # self.time_range_box.pack(side=tk.TOP, pady=5)
        # self.time_range_box.bind("<<ComboboxSelected>>", lambda e: self.update_plots())

        # Direkt nach self.button_frame.pack(...) im Konstruktor einfügen:
        self.status_var = StringVar(value="Letztes Update: -")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, font=("Arial", 10), anchor="w")
        self.status_label.pack(side=tk.TOP, fill=tk.X)

        # Dann erst:
        self.update_plots()

    def new_method(self, icon):
        # Caching für OffsetImage, damit nicht jedes Mal neu erzeugt wird
        if not hasattr(self, "offset_images_cache"):
            self.offset_images_cache = {}
        if icon not in self.offset_images_cache:
            # Transparenz erhalten!
            self.offset_images_cache[icon] = OffsetImage(np.array(self.icons[icon].convert("RGBA")), zoom=0.07)
        return self.offset_images_cache[icon]

    def update_plots(self):
        self.status_var.set(f"Letztes Update: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        try:
            # Fronius-Daten plotten
            df = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
            # Immer die letzten 48h anzeigen
            hours = 48
            now = pd.Timestamp.now()
            df = df[df["Zeitstempel"] >= now - pd.Timedelta(hours=hours)]
            self.fronius_ax.clear()
            self.fronius_ax2.clear()
            pv_smooth = df["PV-Leistung (kW)"].rolling(window=20, min_periods=1, center=True).mean()
            haus_smooth = df["Hausverbrauch (kW)"].rolling(window=20, min_periods=1, center=True).mean()
            self.fronius_ax.plot(df["Zeitstempel"], pv_smooth, label="PV-Leistung (kW, geglättet)", color="orange")
            self.fronius_ax.plot(df["Zeitstempel"], haus_smooth, label="Hausverbrauch (kW, geglättet)", color="lightblue")
            self.fronius_ax.set_ylabel("Leistung (kW)")
            self.fronius_ax.set_xlabel("Zeit")
            self.fronius_ax.set_ylim(0, 10)
            self.fronius_ax.grid(True, which='major', linestyle='--', alpha=0.5)  
            self.fronius_ax.legend(loc="upper left")
            self.fronius_ax2.plot(df["Zeitstempel"], df["Batterieladestand (%)"], label="Batterieladestand (%)", color="purple", linestyle="--")
            self.fronius_ax2.set_ylabel("Batterieladestand (%)")
            self.fronius_ax2.set_ylim(0, 100)
            self.fronius_ax2.grid(False)
            self.fronius_ax2.legend(loc="upper right")
            self.fronius_fig.autofmt_xdate()
            for label in self.fronius_ax.get_xticklabels():
                label.set_fontsize(13)
            self.fronius_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.fronius_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
            self.fronius_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')
            self.fronius_canvas.draw()
        except Exception as e:
            self.fronius_ax.clear()
            self.fronius_ax.text(0.5, 0.5, f"Fehler beim Laden der Fronius-Daten:\n{e}", ha="center", va="center")
            self.fronius_canvas.draw()

        # BMK-Daten plotten
        try:
            df = pd.read_csv(BMK_CSV, parse_dates=["Zeitstempel"])
            now = pd.Timestamp.now()
            df = df[df["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
            self.bmk_ax.clear()
            self.bmk_ax.plot(df["Zeitstempel"], df["Kesseltemperatur"], label="Kesseltemperatur (°C)", color="red")
            self.bmk_ax.plot(df["Zeitstempel"], df["Außentemperatur"], label="Außentemperatur (°C)", color="cyan")
            if "Pufferspeicher Oben" in df.columns:
                self.bmk_ax.plot(df["Zeitstempel"], df["Pufferspeicher Oben"], label="Pufferspeicher Oben (°C)", color="orange")
            if "Warmwasser" in df.columns:
                self.bmk_ax.plot(df["Zeitstempel"], df["Warmwasser"], label="Warmwasser (°C)", color="green")
            self.bmk_ax.set_ylabel("Temperatur (°C)")
            self.bmk_ax.set_xlabel("Zeit")
            self.bmk_ax.grid(True, which='major', linestyle='--', alpha=0.5)  # <--- HIER
            self.bmk_ax.legend()
            self.bmk_fig.autofmt_xdate()
            # X-Achsen-Beschriftung größer
            for label in self.bmk_ax.get_xticklabels():
                label.set_fontsize(13)
            self.bmk_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.bmk_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
            self.bmk_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')
            self.bmk_canvas.draw()
        except Exception as e:
            self.bmk_ax.clear()
            self.bmk_ax.text(0.5, 0.5, f"Fehler beim Laden der BMK-Daten:\n{e}", ha="center", va="center")
            self.bmk_canvas.draw()

        # Zusammenfassung plotten (aktuelle Werte als große Zahlen)
        try:
            df_fronius = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
            df_bmk = pd.read_csv(BMK_CSV, parse_dates=["Zeitstempel"])
            now = pd.Timestamp.now()
            df_fronius = df_fronius[df_fronius["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
            df_bmk = df_bmk[df_bmk["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
            if not df_fronius.empty:
                last_fronius = df_fronius.sort_values("Zeitstempel").iloc[-1]
            else:
                last_fronius = {}
            if not df_bmk.empty:
                last_bmk = df_bmk.sort_values("Zeitstempel").iloc[-1]
            else:
                last_bmk = {}

            self.summary_ax.clear()
            self.summary_ax.axis('off')

            # Hintergrundbild (randlos)
            if self.bg_img is not None:
                self.summary_ax.imshow(self.bg_img, extent=[0, 1, -0.25, 1.05], aspect='auto', zorder=0)

            # Halbtransparenter Kasten
            rect = Rectangle(
                (0, -0.25), 1, 1.3,
                facecolor='white', alpha=0.3, zorder=1
            )
            self.summary_ax.add_patch(rect)

            # Werte extrahieren
            puffer_oben = last_bmk.get("Pufferspeicher Oben", "n/a")
            puffer_mitte = last_bmk.get("Pufferspeicher Mitte", "n/a")
            puffer_unten = last_bmk.get("Pufferspeicher Unten", "n/a")
            kessel = last_bmk.get("Kesseltemperatur", "n/a")
            aussen = last_bmk.get("Außentemperatur", "n/a")
            soc = last_fronius.get("Batterieladestand (%)", "n/a")

            haus = last_fronius.get("Hausverbrauch (kW)", "n/a")
            netz = last_fronius.get("Netz-Leistung (kW)", "n/a")

            # Auf 2 Nachkommastellen runden, falls Wert vorhanden und Zahl
            def fmt2(val):
                try:
                    return f"{float(val):.2f}"
                except:
                    return val

            haus = fmt2(haus)
            netz = fmt2(netz)

            icon_positions = [
                ("temperature.png", 0.18, 0.85, f"{puffer_oben} °C", "Puffertemperatur Oben"),
                ("temperature.png", 0.18, 0.70, f"{puffer_mitte} °C", "Puffertemperatur Mitte"),
                ("temperature.png", 0.18, 0.55, f"{puffer_unten} °C", "Puffertemperatur Unten"),
                ("temperature.png", 0.18, 0.40, f"{kessel} °C", "Kesseltemperatur"),
                ("outdoor.png",     0.18, 0.25, f"{aussen} °C", "Außentemperatur"),
                ("battery.png",     0.18, 0.10, f"{soc} %", "Batterieladestand"),
                ("house.png",       0.18, -0.05, f"{haus} kW", "Hausverbrauch"),
                ("power.png",       0.18, -0.20, f"{netz} kW", "Netz-Leistung"),
            ]

            for icon, x, y, value, label in icon_positions:
                if icon in self.icons:
                    oi = self.new_method(icon)
                    ab = AnnotationBbox(oi, (x, y), frameon=False, box_alignment=(0.5,0.5), zorder=2)
                    self.summary_ax.add_artist(ab)
                self.summary_ax.text(x + 0.11, y, label, fontsize=17, color="black", va="center", ha="left", weight="bold", zorder=3)
                self.summary_ax.text(x + 0.65, y, value, fontsize=19, color="black", va="center", ha="left", weight="bold", zorder=3)

            self.summary_ax.set_xlim(0, 1)
            self.summary_ax.set_ylim(-0.25, 1.05)
            self.summary_canvas.draw()
        except Exception as e:
            self.summary_ax.clear()
            self.summary_ax.text(0.5, 0.5, f"Fehler beim Laden der Zusammenfassung:\n{e}", ha="center", va="center", color="white")
            self.summary_canvas.draw()
        finally:
            # Automatisch nach Intervall neu laden
            self.root.after(UPDATE_INTERVAL, self.update_plots)

        # 1. PV-Ertrag (Tage) als Liniendiagramm
        try:
            df = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
            df = df.set_index("Zeitstempel")
            df["PV_kWh"] = df["PV-Leistung (kW)"] / 60  # kWh pro Minute
            pv_per_day = df["PV_kWh"].resample("D").sum()
            self.pv_ertrag_ax.clear()
            self.pv_ertrag_ax.plot(pv_per_day.index, pv_per_day.values, marker="o", color="orange", label="PV-Ertrag (kWh)")
            self.pv_ertrag_ax.set_ylabel("PV-Ertrag (kWh)")
            self.pv_ertrag_ax.set_title("PV-Ertrag pro Tag")
            self.pv_ertrag_ax.set_xlabel("Datum")
            self.pv_ertrag_ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            self.pv_ertrag_ax.legend()
            self.pv_ertrag_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.pv_ertrag_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
            self.pv_ertrag_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')  # <--- HIER
            self.pv_ertrag_fig.autofmt_xdate()
            self.pv_ertrag_canvas.draw()
        except Exception as e:
            self.pv_ertrag_ax.clear()
            self.pv_ertrag_ax.text(0.5, 0.5, f"Fehler beim Laden der PV-Ertragsdaten:\n{e}", ha="center", va="center")
            self.pv_ertrag_canvas.draw()

        # 2. Batterie-Ladestand Verlauf
        try:
            df = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
            self.batt_ax.clear()
            self.batt_ax.plot(df["Zeitstempel"], df["Batterieladestand (%)"], color="purple")
            self.batt_ax.set_ylabel("Batterieladestand (%)")
            self.batt_ax.set_title("Batterieladestand Verlauf")
            self.batt_ax.set_xlabel("Zeit")
            self.batt_ax.set_ylim(0, 100)
            self.batt_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.batt_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
            self.batt_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')  # <--- HIER
            self.batt_fig.autofmt_xdate()
            self.batt_canvas.draw()
        except Exception as e:
            self.batt_ax.clear()
            self.batt_ax.text(0.5, 0.5, f"Fehler beim Laden der Batterie-Daten:\n{e}", ha="center", va="center")
            self.batt_canvas.draw()

    def minimize_window(self):
        self.root.iconify()  # Fenster minimieren