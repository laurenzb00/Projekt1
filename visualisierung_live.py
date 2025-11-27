import os
from tkinter import StringVar
import tkinter as tk
from tkinter import ttk

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.style.use("dark_background")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from PIL import Image

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

    # Icon-Caching für die Zusammenfassung
    def new_method(self, icon):
        if not hasattr(self, "offset_images_cache"):
            self.offset_images_cache = {}
        if icon not in self.offset_images_cache and icon in self.icons:
            self.offset_images_cache[icon] = OffsetImage(np.array(self.icons[icon].convert("RGBA")), zoom=0.07)
        return self.offset_images_cache.get(icon)

    def _downsample(self, df, time_col, max_points=2000):
        """Reduziert die Anzahl der Datenpunkte für schnelleres Plotten."""
        if df is None or df.empty:
            return df
        if len(df) <= max_points:
            return df
        step = max(len(df) // max_points, 1)
        return df.iloc[::step].reset_index(drop=True)

    def update_plots(self):
        now = pd.Timestamp.now()

        # ---------- CSVs nur EINMAL einlesen ----------
        fronius_df = None
        bmk_df = None
        fronius_error = None
        bmk_error = None

        # Fronius-Daten
        if os.path.exists(FRONIUS_CSV):
            try:
                fronius_df = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
                fronius_df = fronius_df.sort_values("Zeitstempel")
                # Begrenzung auf die letzten 30 Tage
                fronius_df = fronius_df[fronius_df["Zeitstempel"] >= now - pd.Timedelta(days=30)]
            except Exception as e:
                fronius_df = None
                fronius_error = e
        else:
            fronius_error = FileNotFoundError(f"{FRONIUS_CSV} nicht gefunden")

        # BMK-Daten
        if os.path.exists(BMK_CSV):
            try:
                bmk_df = pd.read_csv(BMK_CSV, parse_dates=["Zeitstempel"])
                bmk_df = bmk_df.sort_values("Zeitstempel")
                # optional: auf 30 Tage begrenzen
                bmk_df = bmk_df[bmk_df["Zeitstempel"] >= now - pd.Timedelta(days=30)]
            except Exception as e:
                bmk_df = None
                bmk_error = e
        else:
            bmk_error = FileNotFoundError(f"{BMK_CSV} nicht gefunden")

        # ---------- Fronius-Tab (48h) ----------
        try:
            self.fronius_ax.clear()
            self.fronius_ax2.clear()

            if fronius_error is not None:
                self.fronius_ax.text(0.5, 0.5, f"Fehler Fronius:\n{fronius_error}", ha="center", va="center")
            elif fronius_df is None or fronius_df.empty:
                self.fronius_ax.text(0.5, 0.5, "Keine Fronius-Daten in den letzten 48h", ha="center", va="center")
            else:
                df_48 = fronius_df[fronius_df["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
                if df_48.empty:
                    self.fronius_ax.text(0.5, 0.5, "Keine Fronius-Daten in den letzten 48h", ha="center", va="center")
                else:
                    # Downsampling für schnellere Plots
                    df_48 = self._downsample(df_48, "Zeitstempel", max_points=2000)

                    pv_smooth = df_48["PV-Leistung (kW)"].rolling(window=20, min_periods=1, center=True).mean()
                    haus_smooth = df_48["Hausverbrauch (kW)"].rolling(window=20, min_periods=1, center=True).mean()

                    self.fronius_ax.plot(df_48["Zeitstempel"], pv_smooth,
                                         label="PV-Leistung (kW, geglättet)", color="orange")
                    self.fronius_ax.plot(df_48["Zeitstempel"], haus_smooth,
                                         label="Hausverbrauch (kW, geglättet)", color="lightblue")
                    self.fronius_ax.set_ylabel("Leistung (kW)")
                    self.fronius_ax.set_xlabel("Zeit")

                    max_pv_value = pv_smooth.max()
                    if pd.isna(max_pv_value):
                        max_pv_value = 0.0
                    self.fronius_ax.set_ylim(0, max(10, float(max_pv_value) * 1.2))

                    self.fronius_ax.grid(True, which='major', linestyle='--', alpha=0.5)
                    self.fronius_ax.legend(loc="upper left")

                    if "Batterieladestand (%)" in df_48.columns:
                        self.fronius_ax2.plot(df_48["Zeitstempel"], df_48["Batterieladestand (%)"],
                                              label="Batterieladestand (%)", color="purple", linestyle="--")
                        self.fronius_ax2.set_ylabel("Batterieladestand (%)")
                        self.fronius_ax2.set_ylim(0, 100)
                        self.fronius_ax2.grid(False)
                        self.fronius_ax2.legend(loc="upper right")

                    self.fronius_fig.autofmt_xdate()
                    self.fronius_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    self.fronius_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
                    self.fronius_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')

            self.fronius_canvas.draw()
        except Exception as e:
            self.fronius_ax.clear()
            self.fronius_ax.text(0.5, 0.5, f"Fehler Fronius:\n{e}", ha="center", va="center")
            self.fronius_canvas.draw()

        # ---------- BMK-Tab (48h) ----------
        try:
            self.bmk_ax.clear()

            if bmk_error is not None:
                self.bmk_ax.text(0.5, 0.5, f"Fehler BMK:\n{bmk_error}", ha="center", va="center")
            elif bmk_df is None or bmk_df.empty:
                self.bmk_ax.text(0.5, 0.5, "Keine BMK-Daten in den letzten 48h", ha="center", va="center")
            else:
                df_bmk_48 = bmk_df[bmk_df["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
                if df_bmk_48.empty:
                    self.bmk_ax.text(0.5, 0.5, "Keine BMK-Daten in den letzten 48h", ha="center", va="center")
                else:
                    # Downsampling
                    df_bmk_48 = self._downsample(df_bmk_48, "Zeitstempel", max_points=2000)

                    if "Kesseltemperatur" in df_bmk_48.columns:
                        self.bmk_ax.plot(df_bmk_48["Zeitstempel"], df_bmk_48["Kesseltemperatur"],
                                         label="Kesseltemperatur (°C)", color="red")
                    if "Außentemperatur" in df_bmk_48.columns:
                        self.bmk_ax.plot(df_bmk_48["Zeitstempel"], df_bmk_48["Außentemperatur"],
                                         label="Außentemperatur (°C)", color="cyan")
                    if "Pufferspeicher Oben" in df_bmk_48.columns:
                        self.bmk_ax.plot(df_bmk_48["Zeitstempel"], df_bmk_48["Pufferspeicher Oben"],
                                         label="Pufferspeicher Oben (°C)", color="orange")
                    if "Warmwasser" in df_bmk_48.columns:
                        self.bmk_ax.plot(df_bmk_48["Zeitstempel"], df_bmk_48["Warmwasser"],
                                         label="Warmwasser (°C)", color="green")

                    self.bmk_ax.set_ylabel("Temperatur (°C)")
                    self.bmk_ax.set_xlabel("Zeit")
                    self.bmk_ax.grid(True, which='major', linestyle='--', alpha=0.5)
                    self.bmk_ax.legend()
                    self.bmk_fig.autofmt_xdate()
                    self.bmk_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    self.bmk_ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
                    self.bmk_ax.grid(True, which='major', linestyle='--', alpha=0.7, color='#444444')

            self.bmk_canvas.draw()
        except Exception as e:
            self.bmk_ax.clear()
            self.bmk_ax.text(0.5, 0.5, f"Fehler BMK:\n{e}", ha="center", va="center")
            self.bmk_canvas.draw()

        # ---------- PV-Ertrag (Tage, aus Fronius) ----------
        try:
            self.pv_ertrag_ax.clear()

            if fronius_error is not None or fronius_df is None or fronius_df.empty:
                self.pv_ertrag_ax.text(0.5, 0.5, "Keine PV-Ertragsdaten (30 Tage)", ha="center", va="center")
            else:
                df_pv = fronius_df.set_index("Zeitstempel")
                df_pv = df_pv[df_pv.index >= now - pd.Timedelta(days=30)]

                pv_per_day = []
                if not df_pv.empty:
                    for day, group in df_pv.groupby(df_pv.index.date):
                        if len(group) > 1:
                            t = (group.index - group.index[0]).total_seconds() / 3600
                            y = group["PV-Leistung (kW)"].values
                            kwh = np.trapz(y, t)
                            pv_per_day.append((pd.Timestamp(day), kwh))

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

        # ---------- Batterie-Verlauf ----------
        try:
            self.batt_ax.clear()

            if fronius_error is not None or fronius_df is None or fronius_df.empty:
                self.batt_ax.text(0.5, 0.5, "Keine Batteriedaten vorhanden", ha="center", va="center")
            else:
                if "Batterieladestand (%)" in fronius_df.columns:
                    df_batt = self._downsample(fronius_df, "Zeitstempel", max_points=2000)
                    self.batt_ax.plot(df_batt["Zeitstempel"], df_batt["Batterieladestand (%)"], color="purple")
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

        # ---------- Zusammenfassung ----------
        try:
            self.summary_ax.clear()
            self.summary_ax.axis("off")

            if self.bg_img is not None:
                self.summary_ax.imshow(self.bg_img, extent=[0, 1, -0.25, 1.05], aspect="auto", zorder=0)
            rect = Rectangle((0, -0.25), 1, 1.3, facecolor="white", alpha=0.15, zorder=1)
            self.summary_ax.add_patch(rect)

            def fmt2(val):
                try:
                    return f"{float(val):.2f}"
                except Exception:
                    return val

            soc = haus = netz = "n/a"
            puffer_oben = puffer_mitte = puffer_unten = kessel = aussen = "n/a"

            if fronius_df is not None and not fronius_df.empty:
                last_f = fronius_df.iloc[-1]
                soc = last_f.get("Batterieladestand (%)", "n/a")
                haus = fmt2(last_f.get("Hausverbrauch (kW)", "n/a"))
                netz = fmt2(last_f.get("Netz-Leistung (kW)", "n/a"))

            if bmk_df is not None and not bmk_df.empty:
                last_b = bmk_df.iloc[-1]
                puffer_oben = last_b.get("Pufferspeicher Oben", "n/a")
                puffer_mitte = last_b.get("Pufferspeicher Mitte", "n/a")
                puffer_unten = last_b.get("Pufferspeicher Unten", "n/a")
                kessel = last_b.get("Kesseltemperatur", "n/a")
                aussen = last_b.get("Außentemperatur", "n/a")

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
                self.summary_ax.text(
                    x + 0.11, y, label,
                    fontsize=17, color="white",
                    va="center", ha="left", weight="bold", zorder=3
                )
                self.summary_ax.text(
                    x + 0.65, y, value,
                    fontsize=19, color="white",
                    va="center", ha="left", weight="bold", zorder=3
                )

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


if __name__ == "__main__":
    root = tk.Tk()
    app = LivePlotApp(root)
    root.mainloop()
