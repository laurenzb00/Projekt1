import subprocess
import time
from datetime import datetime, timedelta
import BMKDATEN
import Wechselrichter
import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import sys
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

# Setze den Arbeitsbereich auf das Verzeichnis, in dem das Skript liegt
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORKING_DIRECTORY)

# Funktion zum Filtern der Daten der letzten 48 Stunden (zwei Kalendertage)
def filter_data_last_48_hours(csv_file):
    try:
        daten = pd.read_csv(csv_file, parse_dates=["Zeitstempel"])
        jetzt = datetime.now()
        startzeit = (jetzt - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        daten = daten[(daten["Zeitstempel"] >= startzeit) & (daten["Zeitstempel"] <= jetzt)]
        return daten
    except Exception as e:
        print(f"Fehler beim Filtern der Daten: {e}")
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
    plt.savefig(grafik_pfad, dpi=600)
    plt.close()

# Funktion zum Erstellen der aktualisierten Grafiken für Heizungstemperaturen
def update_bmk_graphics():
    daten = filter_data_last_48_hours(os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv"))
    if daten is None or daten.empty:
        print("Keine Daten für Heizungstemperaturen verfügbar.")
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
        plt.savefig(grafik_pfad, dpi=600)
        plt.close()
        print("Heizungstemperaturen-Grafik aktualisiert.")
    except KeyError as e:
        print(f"Fehler beim Erstellen der Heizungstemperaturen-Grafik: {e}")

# Funktion zum Erstellen der aktualisierten Zusammenfassungs-Grafiken
def update_summary_graphics():
    try:
        fronius_path = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
        heizung_path = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")
        background_image_path = os.path.join(WORKING_DIRECTORY, "icons", "background.png")  # Hintergrundbild in icons-Ordner

        if not os.path.exists(fronius_path) or not os.path.exists(heizung_path):
            print("CSV-Dateien fehlen. Zusammenfassungsgrafik wird nicht aktualisiert.")
            return

        fronius_daten = pd.read_csv(fronius_path)
        heizung_daten = pd.read_csv(heizung_path)

        if fronius_daten.empty or heizung_daten.empty:
            print("CSV-Dateien sind leer. Zusammenfassungsgrafik wird nicht aktualisiert.")
            return

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

        # Hintergrundbild hinzufügen
        if os.path.exists(background_image_path):
            try:
                # Hintergrundbild nur einmal laden
                if not hasattr(update_summary_graphics, "background_image"):
                    update_summary_graphics.background_image = plt.imread(background_image_path)
                img = update_summary_graphics.background_image
                ax.imshow(img, extent=[0, 1, 0, 1], aspect='auto')  # Bild als Hintergrund setzen
                print("Hintergrundbild erfolgreich geladen.")
            except Exception as e:
                print(f"Fehler beim Laden des Hintergrundbilds: {e}")
        else:
            print(f"Hintergrundbild nicht gefunden: {background_image_path}")

        ax.axis("off")  # Keine Achsen anzeigen
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
            ax.text(0.3, y_pos, label, fontsize=14, fontweight="bold", ha="left", va="center", color="black")  # Fett und schwarz
            ax.text(0.85, y_pos, value, fontsize=14, fontweight="bold", ha="right", va="center", color="white")  # Fett u
            y_pos -= 0.1
        grafik_pfad = os.path.join(WORKING_DIRECTORY, "Zusammenfassung.png")
        plt.savefig(grafik_pfad, dpi=150, bbox_inches="tight")
        plt.close()
        print("Zusammenfassungsgrafik aktualisiert.")
    except Exception as e:
        print(f"Fehler beim Aktualisieren der Zusammenfassungsgrafik: {e}")

# Funktion zum Starten eines Skripts als separaten Prozess
def start_script(script_path):
    try:
        print(f"Starte Skript: {script_path}")
        return subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"Fehler beim Starten des Skripts {script_path}: {e}")
        return None

# Hauptprogramm
def main():
    # Starte die Visualisierung als separaten Prozess
    visualisierung_process = start_script(os.path.join(WORKING_DIRECTORY, "visualisierung.py"))

    start_time = datetime.now()
    last_bmk_update = start_time
    last_wechselrichter_update = start_time
    last_summary_update = start_time

    try:
        while True:
            current_time = datetime.now()

            # Aktualisiere BMK-Daten alle 1 Minute
            if (current_time - last_bmk_update).total_seconds() >= 60:
                print("BMK-Daten werden aktualisiert...")
                BMKDATEN.abrufen_und_speichern()
                last_bmk_update = current_time

            # Aktualisiere Wechselrichter-Daten alle 1 Minute
            if (current_time - last_wechselrichter_update).total_seconds() >= 60:
                print("Wechselrichter-Daten werden aktualisiert...")
                Wechselrichter.abrufen_und_speichern()
                last_wechselrichter_update = current_time

            # Aktualisiere die Zusammenfassungsgrafik alle 30 Sekunden
            if (current_time - last_summary_update).total_seconds() >= 30:
                print("Zusammenfassungsgrafik wird aktualisiert...")
                update_summary_graphics()
                last_summary_update = current_time

            # Warte 1 Sekunde, um die CPU-Auslastung zu reduzieren
            time.sleep(5)  # CPU-Auslastung reduzieren

    except KeyboardInterrupt:
        print("Programm wird beendet...")
        # Beende den Visualisierungsprozess
        if visualisierung_process:
            visualisierung_process.terminate()
            visualisierung_process.wait()

class FullscreenWindow(QMainWindow):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("Zusammenfassungsgrafik")
        self.setGeometry(0, 0, 800, 480)  # Standardgröße für Raspberry Pi

        # Bild anzeigen
        label = QLabel(self)
        pixmap = QPixmap(image_path)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

        # Vollbildmodus aktivieren
        self.showFullScreen()

if __name__ == "__main__":
    main()
    app = QApplication(sys.argv)
    grafik_pfad = "Zusammenfassung.png"  # Pfad zur Grafik
    window = FullscreenWindow(grafik_pfad)
    sys.exit(app.exec_())