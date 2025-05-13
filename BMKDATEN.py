import requests
import csv
import os
from datetime import datetime  # Für Zeitstempel

def abrufen_und_speichern():
    try:
        url = "http://192.168.1.85/daqdata.cgi"
        response = requests.get(url)

        if response.status_code == 200:
            lines = response.text.split("\n")
            values = [line.strip() for line in lines if line.strip()]

            # Relevante Werte extrahieren
            kesseltemperatur = values[1]
            aussentemperatur = values[2]
            puffer_oben = values[4]
            puffer_mitte = values[5]
            puffer_unten = values[6]
            warmwasser = values[12]

            # Zeitstempel hinzufügen
            zeitstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            daten = {
                "Zeitstempel": zeitstempel,
                "Kesseltemperatur": kesseltemperatur,
                "Außentemperatur": aussentemperatur,
                "Pufferspeicher Oben": puffer_oben,
                "Pufferspeicher Mitte": puffer_mitte,
                "Pufferspeicher Unten": puffer_unten,
                "Warmwasser": warmwasser
            }

            # Daten in CSV speichern
            csv_datei = "Heizungstemperaturen.csv"
            datei_existiert = os.path.exists(csv_datei)

            with open(csv_datei, "a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if not datei_existiert:
                    writer.writerow(daten.keys())  # Schreibe die Spaltenüberschriften
                writer.writerow(daten.values())  # Schreibe die Werte
    except Exception as e:
        print(f"Fehler beim Abrufen und Speichern der BMK-Daten: {e}")

# Hauptfunktion für den direkten Aufruf
def main():
    abrufen_und_speichern()

if __name__ == "__main__":
    main()
