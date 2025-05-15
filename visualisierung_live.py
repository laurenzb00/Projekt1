import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import os
import datetime

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
        self.fronius_canvas = FigureCanvasTkAgg(self.fronius_fig, master=self.fronius_frame)
        self.fronius_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # BMK Tab
        self.bmk_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.bmk_frame, text="Heizung")
        self.bmk_fig, self.bmk_ax = plt.subplots(figsize=(8, 3))
        self.bmk_canvas = FigureCanvasTkAgg(self.bmk_fig, master=self.bmk_frame)
        self.bmk_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Zusammenfassung Tab
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="Zusammenfassung")
        self.summary_fig, self.summary_ax = plt.subplots(figsize=(8, 3))
        self.summary_canvas = FigureCanvasTkAgg(self.summary_fig, master=self.summary_frame)
        self.summary_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Button zum Beenden
        self.close_button = tk.Button(root, text="Schließen", command=self.root.destroy, font=("Arial", 14), bg="red", fg="white")
        self.close_button.pack(side=tk.BOTTOM, pady=10)

        self.update_plots()

    def update_plots(self):
        # Fronius-Daten plotten
        try:
            df = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
            # Nur die letzten 48h
            now = pd.Timestamp.now()
            df = df[df["Zeitstempel"] >= now - pd.Timedelta(hours=48)]
            self.fronius_ax.clear()
            self.fronius_ax.plot(df["Zeitstempel"], df["PV-Leistung (kW)"], label="PV-Leistung (kW)", color="gold")
            self.fronius_ax.plot(df["Zeitstempel"], df["Hausverbrauch (kW)"], label="Hausverbrauch (kW)", color="blue")
            self.fronius_ax.set_ylabel("Leistung (kW)")
            self.fronius_ax.set_xlabel("Zeit")
            self.fronius_ax.set_ylim(0, 10)
            self.fronius_ax.grid(True, which='both', linestyle='--', alpha=0.5)
            self.fronius_ax.legend(loc="upper left")
            self.fronius_ax2 = self.fronius_ax.twinx()
            self.fronius_ax2.plot(df["Zeitstempel"], df["Batterieladestand (%)"], label="Batterieladestand (%)", color="purple", linestyle="--")
            self.fronius_ax2.set_ylabel("Batterieladestand (%)")
            self.fronius_ax2.set_ylim(0, 100)
            self.fronius_ax2.grid(False)
            self.fronius_ax2.legend(loc="upper right")
            self.fronius_fig.autofmt_xdate()
            # X-Achsen-Beschriftung größer
            for label in self.fronius_ax.get_xticklabels():
                label.set_fontsize(13)
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
            self.bmk_ax.set_ylabel("Temperatur (°C)")
            self.bmk_ax.set_xlabel("Zeit")
            self.bmk_ax.grid(True, which='both', linestyle='--', alpha=0.5)
            self.bmk_ax.legend()
            self.bmk_fig.autofmt_xdate()
            # X-Achsen-Beschriftung größer
            for label in self.bmk_ax.get_xticklabels():
                label.set_fontsize(13)
            self.bmk_canvas.draw()
        except Exception as e:
            self.bmk_ax.clear()
            self.bmk_ax.text(0.5, 0.5, f"Fehler beim Laden der BMK-Daten:\n{e}", ha="center", va="center")
            self.bmk_canvas.draw()

        # Zusammenfassung plotten (aktuelle Werte als große Zahlen)
        try:
            df_fronius = pd.read_csv(FRONIUS_CSV, parse_dates=["Zeitstempel"])
            df_bmk = pd.read_csv(BMK_CSV, parse_dates=["Zeitstempel"])
            last_fronius = df_fronius.sort_values("Zeitstempel").iloc[-1]
            last_bmk = df_bmk.sort_values("Zeitstempel").iloc[-1]
            self.summary_ax.clear()
            self.summary_ax.axis('off')

            # Hintergrundbild
            bg_path = os.path.join(WORKING_DIRECTORY, "icons", "background.png")
            if os.path.exists(bg_path):
                bg_img = Image.open(bg_path)
                bg_img = bg_img.resize((1024, 600), Image.LANCZOS)
                self.summary_ax.imshow(bg_img, extent=[-0.5, 1.5, -0.5, 1.3], aspect='auto', zorder=0)

            # Werte extrahieren
            puffer_oben = last_bmk.get("Pufferspeicher Oben", 0)
            puffer_mitte = last_bmk.get("Pufferspeicher Mitte", 0)
            puffer_unten = last_bmk.get("Pufferspeicher Unten", 0)
            kessel = last_bmk.get("Kesseltemperatur", 0)
            aussen = last_bmk.get("Außentemperatur", 0)
            soc = last_fronius.get("Batterieladestand (%)", 0)
            haus = last_fronius.get("Hausverbrauch (kW)", 0)
            netz = last_fronius.get("Netz-Leistung (kW)", 0)
            warmwasser = last_bmk.get("Warmwasser", 0)

            # Positionen für Icons und Werte (x, y)
            icon_positions = [
                ("temperature.png", 0.18, 0.85, f"{puffer_oben:.1f} °C", "Puffertemperatur Oben"),
                ("temperature.png", 0.18, 0.70, f"{puffer_mitte:.1f} °C", "Puffertemperatur Mitte"),
                ("temperature.png", 0.18, 0.55, f"{puffer_unten:.1f} °C", "Puffertemperatur Unten"),
                ("temperature.png", 0.18, 0.40, f"{kessel:.1f} °C", "Kesseltemperatur"),
                ("outdoor.png",     0.18, 0.25, f"{aussen:.1f} °C", "Außentemperatur"),
                ("battery.png",     0.18, 0.10, f"{soc:.1f} %", "Batterieladestand"),
                ("house.png",       0.18, -0.05, f"{haus:.1f} kW", "Hausverbrauch"),
                ("power.png",       0.18, -0.20, f"{netz:.1f} kW", "Netz-Leistung"),
            ]

            for i, (icon, x, y, value, label) in enumerate(icon_positions):
                # Icon
                icon_path = os.path.join(WORKING_DIRECTORY, "icons", icon)
                if os.path.exists(icon_path):
                    img = Image.open(icon_path)
                    oi = OffsetImage(img, zoom=0.07)
                    ab = AnnotationBbox(oi, (x, y), frameon=False, box_alignment=(0.5,0.5), zorder=2)
                    self.summary_ax.add_artist(ab)
                # Label und Wert (Wert weiter rechts)
                self.summary_ax.text(x + 0.11, y, label, fontsize=17, color="black", va="center", ha="left", weight="bold", zorder=3)
                self.summary_ax.text(x + 0.65, y, value, fontsize=19, color="black", va="center", ha="left", weight="bold", zorder=3)

            self.summary_ax.set_xlim(0, 1)
            self.summary_ax.set_ylim(-0.25, 1.05)
            self.summary_canvas.draw()
        except Exception as e:
            self.summary_ax.clear()
            self.summary_ax.text(0.5, 0.5, f"Fehler beim Laden der Zusammenfassung:\n{e}", ha="center", va="center", color="white")
            self.summary_canvas.draw()

        # Automatisch nach Intervall neu laden
        self.root.after(UPDATE_INTERVAL, self.update_plots)

if __name__ == "__main__":
    root = tk.Tk()
    app = LivePlotApp(root)
    root.mainloop()