import requests
import csv
import time
import schedule
import os
from datetime import datetime  # Für Zeitstempel

def abrufen_und_speichern():
    print("Funktion abrufen_und_speichern wird ausgeführt...")
    try:
        url = "http://192.168.1.85/daqdata.cgi"
        response = requests.get(url)
        print(f"Statuscode: {response.status_code}")  # Debug-Ausgabe

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
                print(f"Schreibe folgende Daten in die CSV-Datei: {daten}")
                writer.writerow(daten.values())  # Schreibe die Werte

            print(f"Daten wurden in '{csv_datei}' gespeichert.")
        else:
            print("Fehler beim Abrufen der Daten.")
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

# Scheduler einrichten
schedule.every(60).seconds.do(abrufen_und_speichern)  # Daten alle 60 Sekunden abrufen

print("Programm läuft erfolgreich.")

while True:
    print("Scheduler läuft...")  # Debug-Ausgabe
    schedule.run_pending()
    time.sleep(1)
