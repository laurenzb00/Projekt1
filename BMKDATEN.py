import requests
import csv
import os
from datetime import datetime

# Diese Funktion wird von main.py gesucht!
def abrufen_und_speichern():
    try:
        url = "http://192.168.1.201/daqdata.cgi"
        # Timeout verhindert Hänger, wenn Heizung nicht antwortet
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            lines = response.text.split("\n")
            values = [line.strip() for line in lines if line.strip()]

            if len(values) > 12:
                kesseltemperatur = values[1]
                aussentemperatur = values[2]
                puffer_oben = values[4]
                puffer_mitte = values[5]
                puffer_unten = values[6]
                warmwasser = values[12]

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

                csv_datei = "Heizungstemperaturen.csv"
                datei_existiert = os.path.exists(csv_datei)

                with open(csv_datei, "a", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    if not datei_existiert:
                        writer.writerow(daten.keys())
                    writer.writerow(daten.values())
    except Exception as e:
        print(f"Fehler bei BMK: {e}")

# Falls man es einzeln testen will
if __name__ == "__main__":
    abrufen_und_speichern()