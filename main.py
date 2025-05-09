import subprocess
import time
import os
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

# Setze den Arbeitsbereich explizit
WORKING_DIRECTORY = "/laurenz/Projekt1 " \
"1"
os.chdir(WORKING_DIRECTORY)  # Ändere das aktuelle Arbeitsverzeichnis
print(f"Aktuelles Arbeitsverzeichnis: {os.getcwd()}")  # Debug-Ausgabe

# Pfade zu den beiden Skripten
BMKDATEN_SCRIPT = "BMKDATEN.py"
WECHSELRICHTER_SCRIPT = "Wechselrichter.py"

# Funktion zum Starten eines Skripts
def start_script(script_path):
    print(f"Starte Skript: {script_path}")
    return subprocess.Popen(["python3", script_path])

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
    daten = filter_data_last_48_hours("FroniusDaten.csv")
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
    plt.savefig("FroniusDaten.png", dpi=300)  # Höhere Auflösung für bessere Qualität
    print("Aktualisierte Grafik 'FroniusDaten.png' gespeichert.")
    plt.close()

# Funktion zum Erstellen der aktualisierten Grafiken für Heizungstemperaturen
def update_bmk_graphics():
    print("Aktualisiere Heizungstemperaturen-Grafiken...")
    # Filtere die Daten der letzten 48 Stunden
    daten = filter_data_last_48_hours("Heizungstemperaturen.csv")
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
        plt.savefig("Heizungstemperaturen.png", dpi=300)
        print("Aktualisierte Grafik 'Heizungstemperaturen.png' gespeichert.")
        plt.close()

    except KeyError as e:
        print(f"Fehler: Die Spalte {e} existiert nicht in der CSV-Datei.")

# Funktion zum Erstellen einer Zusammenfassungsgrafik mit aktuellen Werten
def create_summary_graphic():
    print("Erstelle Zusammenfassungsgrafik...")

    # Lade die aktuellen Daten
    try:
        # Debug-Ausgabe des aktuellen Arbeitsverzeichnisses
        print(f"Aktuelles Arbeitsverzeichnis: {os.getcwd()}")

        # Heizungstemperaturen
        heizung_daten = pd.read_csv("Heizungstemperaturen.csv", parse_dates=["Zeitstempel"])
        aktuelle_temperatur = heizung_daten["Kesseltemperatur"].iloc[-1]  # Letzter Wert
        aktuelle_puffer_oben = heizung_daten["Pufferspeicher Oben"].iloc[-1]  # Letzter Wert

        # Batterieladestand aus FroniusDaten.csv
        fronius_daten = pd.read_csv("FroniusDaten.csv", parse_dates=["Zeitstempel"])

        # Filtere die Daten ab Mitternacht des aktuellen Tages
        jetzt = pd.Timestamp.now()
        mitternacht = jetzt.replace(hour=0, minute=0, second=0, microsecond=0)
        tagesdaten = fronius_daten[fronius_daten["Zeitstempel"] >= mitternacht]

        # Berechne die Tagesproduktion
        tagesproduktion = 0  # Initialisiere die Tagesproduktion
        if len(tagesdaten) > 1:  # Stelle sicher, dass genügend Daten vorhanden sind
            # Berechne die Zeitdifferenzen in Stunden
            tagesdaten["Zeitdifferenz"] = tagesdaten["Zeitstempel"].diff().dt.total_seconds() / 3600.0
            # Multipliziere die PV-Leistung (kW) mit der Zeitdifferenz (h) und summiere die Ergebnisse
            tagesproduktion = (tagesdaten["PV-Leistung (kW)"][:-1] * tagesdaten["Zeitdifferenz"][1:]).sum()

        # Aktueller Batterieladestand
        aktueller_batteriestand = fronius_daten["Batterieladestand (%)"].iloc[-1]  # Letzter Wert

        # Erstelle die Grafik
        plt.figure(figsize=(10, 8))
        plt.axis("off")  # Keine Achsen anzeigen

        # Werte als Text darstellen
        plt.text(0.5, 0.85, f"Aktuelle Kesseltemperatur: {aktuelle_temperatur:.1f} °C", 
                 fontsize=16, ha="center", color="red")
        plt.text(0.5, 0.7, f"Aktuelle Puffertemperatur oben: {aktuelle_puffer_oben:.1f} °C", 
                 fontsize=16, ha="center", color="orange")
        plt.text(0.5, 0.55, f"Aktueller Batterieladestand: {aktueller_batteriestand:.1f} %", 
                 fontsize=16, ha="center", color="blue")
        plt.text(0.5, 0.4, f"Tagesproduktion PV-Anlage: {tagesproduktion:.2f} kWh", 
                 fontsize=16, ha="center", color="green")

        # Titel
        plt.title("Zusammenfassung der aktuellen Werte", fontsize=18, fontweight="bold")

        # Grafik speichern
        plt.tight_layout()
        plt.savefig("Zusammenfassung.png", dpi=300)
        print("Zusammenfassungsgrafik 'Zusammenfassung.png' gespeichert.")
        plt.close()

    except FileNotFoundError as e:
        print(f"Fehler: Die Datei wurde nicht gefunden: {e.filename}")
    except Exception as e:
        print(f"Fehler beim Erstellen der Zusammenfassungsgrafik: {e}")

def main():
    # Starte die beiden Skripte
    bmkdaten_process = start_script(BMKDATEN_SCRIPT)
    wechselrichter_process = start_script(WECHSELRICHTER_SCRIPT)

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
            create_summary_graphic()  # Füge die Erstellung der Zusammenfassungsgrafik hinzu

            # Warte 10 Sekunden, bevor die nächste Aktualisierung erfolgt
            time.sleep(10)

    except KeyboardInterrupt:
        print("Programm wird beendet...")

        # Beende die gestarteten Prozesse
        bmkdaten_process.terminate()
        wechselrichter_process.terminate()

        # Warte, bis die Prozesse beendet sind
        bmkdaten_process.wait()
        wechselrichter_process.wait()

if __name__ == "__main__":
    main()