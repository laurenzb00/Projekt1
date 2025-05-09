import subprocess
import time
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import sys

# Setze den Arbeitsbereich auf das Verzeichnis, in dem das Skript liegt
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORKING_DIRECTORY)  # Ändere das aktuelle Arbeitsverzeichnis
print(f"Aktuelles Arbeitsverzeichnis: {os.getcwd()}")  # Debug-Ausgabe

# Pfade zu den Skripten
BMKDATEN_SCRIPT = os.path.join(WORKING_DIRECTORY, "BMKDATEN.py")
WECHSELRICHTER_SCRIPT = os.path.join(WORKING_DIRECTORY, "Wechselrichter.py")
VISUALISIERUNG_SCRIPT = os.path.join(WORKING_DIRECTORY, "visualisierung.py")  # Neuer Pfad

# Funktion zum Starten eines Skripts
def start_script(script_path):
    print(f"Starte Skript: {script_path}")
    try:
        process = subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Prozess gestartet: {process.pid}")
        return process
    except Exception as e:
        print(f"Fehler beim Starten des Skripts {script_path}: {e}")
        return None

# Funktion zum Filtern der Daten der letzten 48 Stunden (zwei Kalendertage)
def filter_data_last_48_hours(csv_file):
    try:
        # Lade die CSV-Datei
        daten = pd.read_csv(csv_file, parse_dates=["Zeitstempel"])
        # Berechne den Startzeitpunkt (Mitternacht vor zwei Tagen)
        jetzt = datetime.now()
        startzeit = (jetzt - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        print(f"Startzeit: {startzeit}, Jetzt: {jetzt}")  # Debug-Ausgabe
        # Filtere die Daten zwischen startzeit und jetzt
        daten = daten[(daten["Zeitstempel"] >= startzeit) & (daten["Zeitstempel"] <= jetzt)]
        print(f"Gefilterte Daten:\n{daten}")  # Debug-Ausgabe
        return daten
    except Exception as e:
        print(f"Fehler beim Filtern der Daten: {e}")
        return None

# Funktion zum Erstellen der aktualisierten Grafiken für Fronius-Daten
def update_fronius_graphics():
    print("Aktualisiere Fronius-Grafiken...")
    # Filtere die Daten der letzten 48 Stunden
    daten = filter_data_last_48_hours(os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv"))
    if daten is None or daten.empty:
        print("Keine Fronius-Daten für die letzten 48 Stunden verfügbar.")
        return

    # Beispiel: Berechne die Daten für das gestapelte Flächendiagramm
    produktion = daten["PV-Leistung (kW)"] * 1000  # Umrechnung in Watt
    eigenverbrauch = daten["Hausverbrauch (kW)"] * 1000  # Umrechnung in Watt
    verbrauch = daten["Netz-Leistung (kW)"] * 1000  # Umrechnung in Watt

    # Erstelle die Grafik
    plt.figure(figsize=(14, 8))  # Größere Grafik
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

    # Titel und Achsenbeschriftungen
    plt.title("Fronius GEN24 Leistungsdaten (Letzte 48 Stunden)", fontsize=16, fontweight="bold")
    plt.xlabel("Zeit", fontsize=14)
    plt.ylabel("Leistung (W)", fontsize=14)

    # Anpassung der Achsen
    plt.xticks(rotation=45, fontsize=12)
    plt.yticks(fontsize=12)
    plt.ylim(0, max(produktion.max(), eigenverbrauch.max(), verbrauch.max()) * 1.1)  # Dynamische Skalierung
    plt.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)

    # Legende
    plt.legend(fontsize=12, loc="upper left", frameon=True, shadow=True)

    # Hintergrundfarbe
    plt.gca().set_facecolor("white")
    plt.tight_layout()

    # Grafik speichern
    grafik_pfad = os.path.join(WORKING_DIRECTORY, "FroniusDaten.png")
    plt.savefig(grafik_pfad, dpi=300)  # Höhere Auflösung für bessere Qualität
    print(f"Aktualisierte Grafik '{grafik_pfad}' gespeichert.")
    plt.close()

# Funktion zum Erstellen der aktualisierten Grafiken für Heizungstemperaturen
def update_bmk_graphics():
    print("Aktualisiere Heizungstemperaturen-Grafiken...")
    # Filtere die Daten der letzten 48 Stunden
    daten = filter_data_last_48_hours(os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv"))
    if daten is None or daten.empty:
        print("Keine Heizungstemperaturen-Daten für die letzten 48 Stunden verfügbar.")
        return

    # Debug-Ausgabe der Spaltennamen
    print(f"Spalten in der CSV-Datei: {daten.columns}")

    # Beispiel: Aktualisiere die Grafik für Heizungstemperaturen
    try:
        # Passe die Spaltennamen an die tatsächlichen Namen in der CSV-Datei an
        plt.figure(figsize=(12, 8))
        plt.plot(daten["Zeitstempel"], daten["Kesseltemperatur"], label="Kesseltemperatur (°C)", color="red", linewidth=2)
        plt.plot(daten["Zeitstempel"], daten["Außentemperatur"], label="Außentemperatur (°C)", color="blue", linewidth=2)

        # Titel und Achsenbeschriftungen
        plt.title("Heizungstemperaturen (Letzte 48 Stunden)", fontsize=16, fontweight="bold")
        plt.xlabel("Zeit", fontsize=14)
        plt.ylabel("Temperatur (°C)", fontsize=14)

        # Anpassung der Achsen
        plt.xticks(rotation=45, fontsize=12)
        plt.yticks(fontsize=12)
        plt.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)

        # Legende
        plt.legend(fontsize=12, loc="upper left", frameon=True, shadow=True)

        # Hintergrundfarbe
        plt.gca().set_facecolor("white")
        plt.tight_layout()

        # Grafik speichern
        grafik_pfad = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.png")
        plt.savefig(grafik_pfad, dpi=300)
        print(f"Aktualisierte Grafik '{grafik_pfad}' gespeichert.")
        plt.close()

    except KeyError as e:
        print(f"Fehler: Die Spalte {e} existiert nicht in der CSV-Datei.")

# Funktion zum Erstellen der aktualisierten Zusammenfassungs-Grafiken
def update_summary_graphics():
    print("Aktualisiere Zusammenfassungs-Grafiken...")
    try:
        # CSV-Dateien lesen
        fronius_daten = pd.read_csv(os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv"))
        heizung_daten = pd.read_csv(os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv"))
        
        # Debug-Ausgabe der Spaltennamen
        print(f"Spalten in FroniusDaten.csv: {list(fronius_daten.columns)}")
        print(f"Spalten in Heizungstemperaturen.csv: {list(heizung_daten.columns)}")

        # Spaltennamen bereinigen
        fronius_daten.columns = fronius_daten.columns.str.strip()
        heizung_daten.columns = heizung_daten.columns.str.strip()

        # Überprüfen, ob die benötigten Spalten existieren
        fronius_required_columns = ["Netz-Leistung (kW)", "Batterieladestand (%)", "Hausverbrauch (kW)"]
        heizung_required_columns = [
            "Pufferspeicher Oben",
            "Pufferspeicher Mitte",
            "Pufferspeicher Unten",
            "Kesseltemperatur",
            "Außentemperatur"
        ]

        for col in fronius_required_columns:
            if col not in fronius_daten.columns:
                print(f"Fehler: Die Spalte '{col}' existiert nicht in FroniusDaten.csv.")
                print(f"Vorhandene Spalten: {list(fronius_daten.columns)}")
                return

        for col in heizung_required_columns:
            if col not in heizung_daten.columns:
                print(f"Fehler: Die Spalte '{col}' existiert nicht in Heizungstemperaturen.csv.")
                print(f"Vorhandene Spalten: {list(heizung_daten.columns)}")
                return

        # Berechne die aktuellen Werte aus FroniusDaten.csv
        aktuelle_netz_leistung = fronius_daten["Netz-Leistung (kW)"].iloc[-1]
        aktuelle_batterieladestand = fronius_daten["Batterieladestand (%)"].iloc[-1]
        aktuelle_hausverbrauch = fronius_daten["Hausverbrauch (kW)"].iloc[-1]

        # Berechne die aktuellen Werte aus Heizungstemperaturen.csv
        aktuelle_puffer_oben = heizung_daten["Pufferspeicher Oben"].iloc[-1]
        aktuelle_puffer_mitte = heizung_daten["Pufferspeicher Mitte"].iloc[-1]
        aktuelle_puffer_unten = heizung_daten["Pufferspeicher Unten"].iloc[-1]
        aktuelle_kesseltemperatur = heizung_daten["Kesseltemperatur"].iloc[-1]
        aktuelle_aussentemperatur = heizung_daten["Außentemperatur"].iloc[-1]

        # Erstelle die Grafik
        plt.figure(figsize=(10, 6))
        plt.axis("off")  # Keine Achsen anzeigen

        # Textinhalt für die Zusammenfassung
        text = (
            f"Puffertemperatur Oben: {aktuelle_puffer_oben:.1f} °C\n"
            f"Puffertemperatur Mitte: {aktuelle_puffer_mitte:.1f} °C\n"
            f"Puffertemperatur Unten: {aktuelle_puffer_unten:.1f} °C\n"
            f"Kesseltemperatur: {aktuelle_kesseltemperatur:.1f} °C\n"
            f"Außentemperatur: {aktuelle_aussentemperatur:.1f} °C\n"
            f"Batterieladestand: {aktuelle_batterieladestand:.1f} %\n"
            f"Hausverbrauch: {aktuelle_hausverbrauch:.1f} kW\n"
            f"Netz-Leistung: {aktuelle_netz_leistung:.1f} kW"
        )

        # Text in die Grafik einfügen
        plt.text(0.5, 0.5, text, fontsize=18, ha="center", va="center", wrap=True)

        # Grafik speichern
        grafik_pfad = os.path.join(WORKING_DIRECTORY, "Zusammenfassung.png")
        plt.savefig(grafik_pfad, dpi=300, bbox_inches="tight")
        print(f"Zusammenfassungsgrafik '{grafik_pfad}' gespeichert.")
        plt.close()

    except Exception as e:
        print(f"Fehler beim Erstellen der Zusammenfassungs-Grafik: {e}")

# Hauptprogramm
def main():
    # Starte die drei Skripte
    bmkdaten_process = start_script(BMKDATEN_SCRIPT)
    wechselrichter_process = start_script(WECHSELRICHTER_SCRIPT)
    visualisierung_process = start_script(VISUALISIERUNG_SCRIPT)  # Visualisierung starten

    # Speichere die Startzeit des Programms
    start_time = datetime.now()

    try:
        # Endlosschleife zum Aktualisieren der Grafiken
        while True:
            # Berechne die aktuelle Laufzeit
            current_time = datetime.now()
            elapsed_time = current_time - start_time

            # Gib die Laufzeit alle 2 Minuten (beginnend 10 Sekunden nach Start) aus
            if elapsed_time.total_seconds() > 10 and int(elapsed_time.total_seconds()) % 120 == 0:
                print(f"Programmlaufzeit: {elapsed_time}")

            # Aktualisiere die Grafiken
            update_fronius_graphics()
            update_bmk_graphics()
            update_summary_graphics()  # Zusammenfassung aktualisieren

            # Warte 10 Sekunden, bevor die nächste Aktualisierung erfolgt
            time.sleep(10)

    except KeyboardInterrupt:
        print("Programm wird beendet...")

        # Beende die gestarteten Prozesse
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