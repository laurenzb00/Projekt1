import requests
import csv
import time
import schedule
import os
from datetime import datetime  # Für Zeitstempel
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

            # ERWEITERTE Datenextraktion - ALLE PP-Daten erfassen
            daten = {
                "Zeitstempel": zeitstempel,
                "Kesseltemperatur": kesseltemperatur,
                "Außentemperatur": aussentemperatur,
                "Kesselrücklauf": values[3] if len(values) > 3 else "",
                "Pufferspeicher Oben": puffer_oben,
                "Pufferspeicher Mitte": puffer_mitte,
                "Pufferspeicher Unten": puffer_unten,
                "Speicher2_Oben": values[7] if len(values) > 7 else "",
                "Speicher2_Unten": values[8] if len(values) > 8 else "",
                "Warmwassertemperatur": values[9] if len(values) > 9 else "",
                "Wert_10": values[10] if len(values) > 10 else "",
                "Wert_11": values[11] if len(values) > 11 else "",
                "Warmwasser": warmwasser,
            }

            # Zusätzliche Werte wenn vorhanden
            for idx in range(13, min(len(values), 25)):
                daten[f"Wert_{idx}"] = values[idx]

            print(f"Extrahierte Daten ({len(values)} Werte total): {daten}")

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
            
            # Speichere auch Pufferanlage-Daten strukturiert
            _speichere_pufferdaten(values, zeitstempel)
        else:
            print("Fehler beim Abrufen der Daten.")
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")


def _speichere_pufferdaten(values, zeitstempel):
    """Speichert Pufferanlage-Daten strukturiert"""
    if len(values) < 7:
        return
    
    try:
        puffer_data = {
            "Zeitstempel": zeitstempel,
            "Oben": float(values[4]) if values[4] else None,
            "Mitte": float(values[5]) if values[5] else None,
            "Unten": float(values[6]) if values[6] else None,
            "Status": _bestimme_puffer_status(values)
        }
        
        json_datei = "Pufferspeicher.json"
        puffer_history = []
        
        if os.path.exists(json_datei):
            try:
                with open(json_datei, "r", encoding="utf-8") as f:
                    puffer_history = json.load(f)
            except:
                pass
        
        puffer_history.append(puffer_data)
        if len(puffer_history) > 1000:
            puffer_history = puffer_history[-1000:]
        
        with open(json_datei, "w", encoding="utf-8") as f:
            json.dump(puffer_history, f, indent=2)
        
        print(f"Pufferdaten gespeichert: {puffer_data}")
    except Exception as e:
        print(f"Fehler beim Speichern von Pufferdaten: {e}")


def _bestimme_puffer_status(values):
    """Bestimmt den Puffer-Status basierend auf Temperaturen"""
    try:
        temps = [float(values[4]), float(values[5]), float(values[6])]
        temps = [t for t in temps if t]  # Filtere None/0-Werte
        if not temps:
            return "FEHLER"
        avg = sum(temps) / len(temps)
        if avg > 70:
            return "GELADEN"
        elif avg > 50:
            return "TEILGELADEN"
        elif avg > 30:
            return "ENTLADEN"
        else:
            return "KALT"
    except:
        return "FEHLER"


# Scheduler einrichten
schedule.every(60).seconds.do(abrufen_und_speichern)  # Daten alle 60 Sekunden abrufen

print("Programm läuft erfolgreich.")

while True:
    print("Scheduler läuft...")  # Debug-Ausgabe
    schedule.run_pending()
    time.sleep(1)
