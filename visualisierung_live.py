import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('dark_background')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk
import tkinter as tk
import os
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
import numpy as np
import matplotlib.ticker as mticker
from tkinter import StringVar

WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")

UPDATE_INTERVAL = 60 * 1000  # 1 Minute


class LivePlotApp:
    def __init__(self, root, fullscreen=True):
        self.root = root
        self.root.title("Live-Daten Visualisierung")
        self.root.geometry("1024x600")
        self.root.configure(bg="#222")
        self.root.resizable(False, False)

        # ---------- Styles ----------
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#222", borderwidth=0)
        style.configure("TNotebook.Tab", background="#333", foreground="white", padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", "#555")], foreground=[("selected", "white")])
        style.configure("Dark.TFrame", background="#222")
        style.configure("Dark.TLabel", background="#222", foreground="white")
        style.configure("Dark.TButton", background="#333", foreground="white", padding=6, relief="flat")
        style.map("Dark.TButton", background=[("active", "#555")], foreground=[("active", "white")])

        # ---------- Notebook ----------
        self.notebook = ttk.Notebook(root, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Fronius Tab
        self.fronius_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.fronius_frame, text="Fronius")
        self.fronius_fig, self.fronius_ax = plt.subplots(figsize=(8, 3))
        self.fronius_ax2 = self.fronius_ax.twinx()
        self.fronius_canvas = FigureCanvasTkAgg(self.fronius_fig, master=self.fronius_frame)
        self.fronius_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # BMK Tab
        self.bmk_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.bmk_frame, text="Temperaturen 2 Tage")
        self.bmk_fig, self.bmk_ax = plt.subplots(figsize=(8, 3))
        self.bmk_canvas = FigureCanvasTkAgg(self.bmk_fig, master=self.bmk_frame)
        self.bmk_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # PV-Ertrag Tab
        self.pv_ertrag_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.pv_ertrag_frame, text="PV-Ertrag (Tage)")
        self.pv_ertrag_fig, self.pv_ertrag_ax = plt.subplots(figsize=(8, 3))
        self.pv_ertrag_canvas = FigureCanvasTkAgg(self.pv_ertrag_fig, master=self.pv_ertrag_frame)
        self.pv_ertrag_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Batterie Verlauf
        self.batt_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.batt_frame, text="Batterie Verlauf")
        self.batt_fig, self.batt_ax = plt.subplots(figsize=(8, 3))
        self.batt_canvas = FigureCanvasTkAgg(self.batt_fig, master=self.batt_frame)
        self.batt_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Zusammenfassung
        self.summary_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.summary_frame, text="Zusammenfassung")
        self.summary_fig, self.summary_ax = plt.subplots(figsize=(8, 3))
        self.summary_canvas = FigureCanvasTkAgg(self.summary_fig, master=self.summary_frame)
        self.summary_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Statuszeile
        self.status_var = StringVar(value="Letztes Update: -")
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, style="Dark.TLabel", anchor="w")
        self.status_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        # Button-Leiste
        self.button_frame = ttk.Frame(root, style="Dark.TFrame")
        self.button_frame.pack(side=tk.BOTTOM, pady=10)
        self.close_button = ttk.Button(self.button_frame, text="Schließen", command=self.root.destroy, style="Dark.TButton")
        self.close_button.pack(side=tk.LEFT, padx=10)
        self.minimize_button = ttk.Button(self.button_frame, text="Minimieren", command=self.minimize_window, style="Dark.TButton")
        self.minimize_button.pack(side=tk.LEFT, padx=10)

        # Bilder
        self.icons = {}
        self.offset_images_cache = {}
        for icon in ["temperature.png", "outdoor.png", "battery.png", "house.png", "power.png"]:
            path = os.path.join(WORKING_DIRECTORY, "icons", icon)
            if os.path.exists(path):
                self.icons[icon] = Image.open(path)
        bg_path = os.path.join(WORKING_DIRECTORY, "icons", "background.png")
        self.bg_img = Image.open(bg_path).resize((1024, 600), Image.LANCZOS) if os.path.exists(bg_path) else None

        self.update_plots()

    def new_method(self, icon):
        if not hasattr(self, "offset_images_cache"):
            self.offset_images_cache = {}
        if icon not in self.offset_images_cache and icon in self.icons:
            self.offset_images_cache[icon] = OffsetImage(np.array(self.icons[icon].convert("RGBA")), zoom=0.07)
        return self.offset_images_cache.get(icon)

    def update_plots(self):
        # --- Fronius ---
        try:
            if not os.path.exists(FRONIUS_CSV):
                raise FileNotFoundError(f"{FRONIUS_CSV} nicht gefunden")
            df_fronius = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"]).copy()
            hours = 48
            now = pd.Timestamp.now()
            df_fronius = df_fronius[df_fronius["Zeitstempel"] >= now - pd.Timedelta(hours=hours)]
            self.fronius_ax.clear()
            self.fronius_ax2.clear()
            if not df_fronius.empty:
                pv_smooth = df_fronius["PV-Leistung (kW)"].rolling(window=20, min_periods=1, center=True).mean()
                haus_smooth = df_fronius["Hausverbrauch (kW)"].rolling(window=20, min_periods=1, center=True).mean()
                self.fronius_ax.plot(df_fronius["Zeitstempel"], pv_smooth, label="PV-Leistung (kW, geglättet)", color="orange")
                self.fronius_ax.plot(df_fronius["Zeitstempel"], haus_smooth, label="Hausverbrauch (kW, geglättet)", color="lightblue")
                self.fronius_ax.set_ylabel("Leistung (kW)")
                self.fronius_ax.set_xlabel("Zeit")
                self.fronius_ax.set_ylim(0, max(10, float(pv_smooth.max() or 0) * 1.2))
                self.fronius_ax.grid(True, which='major', linestyle='--', alpha=0.5)
                self.fronius_ax.legend(loc="upper left")
                self.fronius_ax2.plot(df_fronius["Zeitstempel"], df_fronius["Batterieladestand (%)"], label="Batterieladestand (%)", color="purple", linestyle="--")
                self.fronius_ax2.set_ylabel("Batterieladestand (%)")
                self.fronius_ax2.set_ylim(0, 100)
                self.fronius_ax2.grid(False)
                self.fronius_ax2.legend(loc="upper right")
                self.fronius_fig.autofmt_xdate()
                self.fronius_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                self.fronius_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
                self.fronius_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')
            else:
                self.fronius_ax.clear()
                self.fronius_ax.text(0.5, 0.5, "Keine Fronius-Daten in den letzten 48h", ha="center", va="center")
            self.fronius_canvas.draw()
        except Exception as e:
            self.fronius_ax.clear()
            self.fronius_ax.text(0.5, 0.5, f"Fehler Fronius:\n{e}", ha="center", va="center")
            self.fronius_canvas.draw()

        # --- BMK ---
        try:
            if not os.path.exists(BMK_CSV):
                raise FileNotFoundError(f"{BMK_CSV} nicht gefunden")
            df_bmk = pd.read_csv(BMK_CSV, parse_dates=["Zeitstempel"]).copy()
            now = pd.Timestamp.now()
            df_bmk = df_bmk[df_bmk["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
            self.bmk_ax.clear()
            if not df_bmk.empty:
                if "Kesseltemperatur" in df_bmk.columns:
                    self.bmk_ax.plot(df_bmk["Zeitstempel"], df_bmk["Kesseltemperatur"], label="Kesseltemperatur (°C)", color="red")
                if "Außentemperatur" in df_bmk.columns:
                    self.bmk_ax.plot(df_bmk["Zeitstempel"], df_bmk["Außentemperatur"], label="Außentemperatur (°C)", color="cyan")
                if "Pufferspeicher Oben" in df_bmk.columns:
                    self.bmk_ax.plot(df_bmk["Zeitstempel"], df_bmk["Pufferspeicher Oben"], label="Pufferspeicher Oben (°C)", color="orange")
                if "Warmwasser" in df_bmk.columns:
                    self.bmk_ax.plot(df_bmk["Zeitstempel"], df_bmk["Warmwasser"], label="Warmwasser (°C)", color="green")
                self.bmk_ax.set_ylabel("Temperatur (°C)")
                self.bmk_ax.set_xlabel("Zeit")
                self.bmk_ax.grid(True, which='major', linestyle='--', alpha=0.5)
                self.bmk_ax.legend()
                self.bmk_fig.autofmt_xdate()
                self.bmk_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                self.bmk_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
                self.bmk_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')
            else:
                self.bmk_ax.text(0.5, 0.5, "Keine BMK-Daten in den letzten 48h", ha="center", va="center")
            self.bmk_canvas.draw()
        except Exception as e:
            self.bmk_ax.clear()
            self.bmk_ax.text(0.5, 0.5, f"Fehler BMK:\n{e}", ha="center", va="center")
            self.bmk_canvas.draw()

        # --- PV-Ertrag (Tage) ---
        try:
            if not os.path.exists(FRONIUS_CSV):
                raise FileNotFoundError(f"{FRONIUS_CSV} nicht gefunden")
            df = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
            df = df.set_index("Zeitstempel").sort_index()
            df = df[df.index >= pd.Timestamp.now() - pd.Timedelta(days=30)]
            pv_per_day = []
            for day, group in df.groupby(df.index.date):
                if len(group) > 1:
                    t = (group.index - group.index[0]).total_seconds() / 3600
                    y = group["PV-Leistung (kW)"].values
                    kwh = np.trapz(y, t)
                    pv_per_day.append((pd.Timestamp(day), kwh))
            self.pv_ertrag_ax.clear()
            if pv_per_day:
                days, kwhs = zip(*pv_per_day)
                self.pv_ertrag_ax.plot(days, kwhs, marker="o", color="orange", label="PV-Ertrag (kWh)")
                self.pv_ertrag_ax.legend()
            else:
                self.pv_ertrag_ax.text(0.5, 0.5, "Keine PV-Ertragsdaten (30 Tage)", ha="center", va="center")
            self.pv_ertrag_ax.set_ylabel("PV-Ertrag (kWh)")
            self.pv_ertrag_ax.set_title("PV-Ertrag pro Tag")
            self.pv_ertrag_ax.set_xlabel("Datum")
            self.pv_ertrag_ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            self.pv_ertrag_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.pv_ertrag_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
            self.pv_ertrag_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')
            self.pv_ertrag_fig.autofmt_xdate()
            self.pv_ertrag_canvas.draw()
        except Exception as e:
            self.pv_ertrag_ax.clear()
            self.pv_ertrag_ax.text(0.5, 0.5, f"Fehler PV-Ertrag:\n{e}", ha="center", va="center")
            self.pv_ertrag_canvas.draw()

        # --- Batterie Verlauf ---
        try:
            if not os.path.exists(FRONIUS_CSV):
                raise FileNotFoundError(f"{FRONIUS_CSV} nicht gefunden")
            df = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
            self.batt_ax.clear()
            if not df.empty and "Batterieladestand (%)" in df.columns:
                self.batt_ax.plot(df["Zeitstempel"], df["Batterieladestand (%)"], color="purple")
                self.batt_ax.set_ylim(0, 100)
            else:
                self.batt_ax.text(0.5, 0.5, "Keine Batteriedaten vorhanden", ha="center", va="center")
            self.batt_ax.set_ylabel("Batterieladestand (%)")
            self.batt_ax.set_title("Batterieladestand Verlauf")
            self.batt_ax.set_xlabel("Zeit")
            self.batt_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            self.batt_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
            self.batt_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')
            self.batt_fig.autofmt_xdate()
            self.batt_canvas.draw()
        except Exception as e:
            self.batt_ax.clear()
            self.batt_ax.text(0.5, 0.5, f"Fehler Batterie:\n{e}", ha="center", va="center")
            self.batt_canvas.draw()

        # --- Zusammenfassung ---
        try:
            fr_ok = os.path.exists(FRONIUS_CSV)
            bmk_ok = os.path.exists(BMK_CSV)
            self.summary_ax.clear()
            self.summary_ax.axis('off')
            if self.bg_img is not None:
                self.summary_ax.imshow(self.bg_img, extent=[0, 1, -0.25, 1.05], aspect='auto', zorder=0)
            rect = Rectangle((0, -0.25), 1, 1.3, facecolor='white', alpha=0.15, zorder=1)
            self.summary_ax.add_patch(rect)

            def fmt2(val):
                try:
                    return f"{float(val):.2f}"
                except Exception:
                    return val

            if fr_ok:
                df_f = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
                df_f = df_f.sort_values("Zeitstempel")
                last_f = df_f.iloc[-1] if not df_f.empty else {}
                soc = last_f.get("Batterieladestand (%)", "n/a")
                haus = fmt2(last_f.get("Hausverbrauch (kW)", "n/a"))
                netz = fmt2(last_f.get("Netz-Leistung (kW)", "n/a"))
            else:
                soc = haus = netz = "n/a"

            if bmk_ok:
                df_b = pd.read_csv(BMK_CSV, parse_dates=["Zeitstempel"])
                df_b = df_b.sort_values("Zeitstempel")
                last_b = df_b.iloc[-1] if not df_b.empty else {}
                puffer_oben = last_b.get("Pufferspeicher Oben", "n/a")
                puffer_mitte = last_b.get("Pufferspeicher Mitte", "n/a")
                puffer_unten = last_b.get("Pufferspeicher Unten", "n/a")
                kessel = last_b.get("Kesseltemperatur", "n/a")
                aussen = last_b.get("Außentemperatur", "n/a")
            else:
                puffer_oben = puffer_mitte = puffer_unten = kessel = aussen = "n/a"

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
                oi = self.new_method(icon)
                if oi is not None:
                    ab = AnnotationBbox(oi, (x, y), frameon=False, box_alignment=(0.5, 0.5), zorder=2)
                    self.summary_ax.add_artist(ab)
                self.summary_ax.text(x + 0.11, y, label, fontsize=17, color="white", va="center", ha="left", weight="bold", zorder=3)
                self.summary_ax.text(x + 0.65, y, value, fontsize=19, color="white", va="center", ha="left", weight="bold", zorder=3)

            self.summary_ax.set_xlim(0, 1)
            self.summary_ax.set_ylim(-0.25, 1.05)
            self.summary_canvas.draw()
        except Exception as e:
            self.summary_ax.clear()
            self.summary_ax.text(0.5, 0.5, f"Fehler Zusammenfassung:\n{e}", ha="center", va="center", color="white")
            self.summary_canvas.draw()
        finally:
            self.status_var.set(f"Letztes Update: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.root.after(UPDATE_INTERVAL, self.update_plots)

    def minimize_window(self):
        self.root.iconify()
