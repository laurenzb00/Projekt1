import subprocess
import time
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import sys
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# Setze den Arbeitsbereich auf das Verzeichnis, in dem das Skript liegt
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORKING_DIRECTORY)

# Pfade zu den Skripten
BMKDATEN_SCRIPT = os.path.join(WORKING_DIRECTORY, "BMKDATEN.py")
WECHSELRICHTER_SCRIPT = os.path.join(WORKING_DIRECTORY, "Wechselrichter.py")
VISUALISIERUNG_SCRIPT = os.path.join(WORKING_DIRECTORY, "visualisierung.py")

# Funktion zum Starten eines Skripts
def start_script(script_path):
    try:
        process = subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process
    except Exception:
        return None

# Funktion zum Filtern der Daten der letzten 48 Stunden (zwei Kalendertage)
def filter_data_last_48_hours(csv_file):
    try:
        daten = pd.read_csv(csv_file, parse_dates=["Zeitstempel"])
        jetzt = datetime.now()
        startzeit = (jetzt - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        daten = daten[(daten["Zeitstempel"] >= startzeit) & (daten["Zeitstempel"] <= jetzt)]
        return daten
    except Exception:
        return None

# Funktion zum Erstellen der aktualisierten Grafiken für Fronius-Daten
def update_fronius_graphics():
    daten = filter_data_last_48_hours(os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv"))
    if daten is None or daten.empty:
        return

    produktion = daten["PV-Leistung (kW)"] * 1000
    eigenverbrauch = daten["Hausverbrauch (kW)"] * 1000
    verbrauch = daten["Netz-Leistung (kW)"] * 1000

    plt.figure(figsize=(14, 8))
    plt.stackplot(
        daten["Zeitstempel"],
        produktion,
        eigenverbrauch,
        labels=["Produktion", "Eigenverbrauch"],
        colors=["yellow", "orange"],
        alpha=0.8,
    )
    plt.plot(
        daten["Zeitstempel"],
        verbrauch,
        label="Verbrauch",
        color="blue",
        linewidth=2,
    )
    plt.title("Fronius GEN24 Leistungsdaten (Letzte 48 Stunden)", fontsize=16, fontweight="bold")
    plt.xlabel("Zeit", fontsize=14)
    plt.ylabel("Leistung (W)", fontsize=14)
    plt.xticks(rotation=45, fontsize=12)
    plt.yticks(fontsize=12)
    plt.ylim(0, max(produktion.max(), eigenverbrauch.max(), verbrauch.max()) * 1.1)
    plt.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)
    plt.legend(fontsize=12, loc="upper left", frameon=True, shadow=True)
    plt.gca().set_facecolor("white")
    plt.tight_layout()
    grafik_pfad = os.path.join(WORKING_DIRECTORY, "FroniusDaten.png")
    plt.savefig(grafik_pfad, dpi=300)
    plt.close()

# Funktion zum Erstellen der aktualisierten Grafiken für Heizungstemperaturen
def update_bmk_graphics():
    daten = filter_data_last_48_hours(os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv"))
    if daten is None or daten.empty:
        return

    try:
        plt.figure(figsize=(12, 8))
        plt.plot(daten["Zeitstempel"], daten["Kesseltemperatur"], label="Kesseltemperatur (°C)", color="red", linewidth=2)
        plt.plot(daten["Zeitstempel"], daten["Außentemperatur"], label="Außentemperatur (°C)", color="blue", linewidth=2)
        plt.title("Heizungstemperaturen (Letzte 48 Stunden)", fontsize=16, fontweight="bold")
        plt.xlabel("Zeit", fontsize=14)
        plt.ylabel("Temperatur (°C)", fontsize=14)
        plt.xticks(rotation=45, fontsize=12)
        plt.yticks(fontsize=12)
        plt.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)
        plt.legend(fontsize=12, loc="upper left", frameon=True, shadow=True)
        plt.gca().set_facecolor("white")
        plt.tight_layout()
        grafik_pfad = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.png")
        plt.savefig(grafik_pfad, dpi=300)
        plt.close()
    except KeyError:
        pass

# Funktion zum Erstellen der aktualisierten Zusammenfassungs-Grafiken
def update_summary_graphics():
    try:
        fronius_daten = pd.read_csv(os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv"))
        heizung_daten = pd.read_csv(os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv"))
        fronius_daten.columns = fronius_daten.columns.str.strip()
        heizung_daten.columns = heizung_daten.columns.str.strip()

        aktuelle_netz_leistung = fronius_daten["Netz-Leistung (kW)"].iloc[-1]
        aktuelle_batterieladestand = fronius_daten["Batterieladestand (%)"].iloc[-1]
        aktuelle_hausverbrauch = fronius_daten["Hausverbrauch (kW)"].iloc[-1]
        aktuelle_puffer_oben = heizung_daten["Pufferspeicher Oben"].iloc[-1]
        aktuelle_puffer_mitte = heizung_daten["Pufferspeicher Mitte"].iloc[-1]
        aktuelle_puffer_unten = heizung_daten["Pufferspeicher Unten"].iloc[-1]
        aktuelle_kesseltemperatur = heizung_daten["Kesseltemperatur"].iloc[-1]
        aktuelle_aussentemperatur = heizung_daten["Außentemperatur"].iloc[-1]

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.axis("off")
        daten = [
            ("Puffertemperatur Oben", f"{aktuelle_puffer_oben:.1f} °C", "temperature.png"),
            ("Puffertemperatur Mitte", f"{aktuelle_puffer_mitte:.1f} °C", "temperature.png"),
            ("Puffertemperatur Unten", f"{aktuelle_puffer_unten:.1f} °C", "temperature.png"),
            ("Kesseltemperatur", f"{aktuelle_kesseltemperatur:.1f} °C", "boiler.png"),
            ("Außentemperatur", f"{aktuelle_aussentemperatur:.1f} °C", "outdoor.png"),
            ("Batterieladestand", f"{aktuelle_batterieladestand:.1f} %", "battery.png"),
            ("Hausverbrauch", f"{aktuelle_hausverbrauch:.1f} kW", "house.png"),
            ("Netz-Leistung", f"{aktuelle_netz_leistung:.1f} kW", "power.png"),
        ]
        icon_zoom = 0.1
        y_pos = 0.9
        for label, value, icon_name in daten:
            icon_path = os.path.join(WORKING_DIRECTORY, "icons", icon_name)
            if os.path.exists(icon_path):
                image = plt.imread(icon_path)
                imagebox = OffsetImage(image, zoom=icon_zoom)
                ab = AnnotationBbox(imagebox, (0.2, y_pos), frameon=False)
                ax.add_artist(ab)
            ax.text(0.3, y_pos, label, fontsize=14, ha="left", va="center", color="black")
            ax.text(0.7, y_pos, value, fontsize=14, ha="right", va="center", color="blue")
            y_pos -= 0.1
        grafik_pfad = os.path.join(WORKING_DIRECTORY, "Zusammenfassung.png")
        plt.savefig(grafik_pfad, dpi=300, bbox_inches="tight")
        plt.close()
    except Exception:
        pass

# Hauptprogramm
def main():
    bmkdaten_process = start_script(BMKDATEN_SCRIPT)
    wechselrichter_process = start_script(WECHSELRICHTER_SCRIPT)
    visualisierung_process = start_script(VISUALISIERUNG_SCRIPT)

    start_time = datetime.now()
    try:
        while True:
            current_time = datetime.now()
            elapsed_time = current_time - start_time
            if elapsed_time.total_seconds() > 10 and int(elapsed_time.total_seconds()) % 120 == 0:
                pass
            update_fronius_graphics()
            update_bmk_graphics()
            update_summary_graphics()
            time.sleep(60)
    except KeyboardInterrupt:
        if bmkdaten_process:
            bmkdaten_process.terminate()
            bmkdaten_process.wait()
        if wechselrichter_process:
            wechselrichter_process.terminate()
            wechselrichter_process.wait()
        if visualisierung_process:
            visualisierung_process.terminate()
            visualisierung_process.wait()

if __name__ == "__main__":
    main()