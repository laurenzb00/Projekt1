import requests
import csv
import time
import schedule
import os
from datetime import datetime

def abrufen_und_speichern():
    print("Funktion abrufen_und_speichern wird ausgeführt...")
    try:
        # URL der Fronius API (ersetze die IP-Adresse durch die deines Wechselrichters)
        url = "http://192.168.1.87/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
        response = requests.get(url)
        print(f"Statuscode: {response.status_code}")  # Debug-Ausgabe

        if response.status_code == 200:
            data = response.json()
            print("API-Antwort:", data)  # Debug-Ausgabe der API-Antwort

            # Relevante Werte extrahieren
            zeitstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pv_leistung = abs(data["Body"]["Data"]["Site"]["P_PV"] / 1000)  # Umrechnung in kW, absoluter Wert
            netz_leistung = abs(data["Body"]["Data"]["Site"]["P_Grid"] / 1000)  # Umrechnung in kW, absoluter Wert
            batterie_leistung = abs(data["Body"]["Data"]["Site"]["P_Akku"] / 1000)  # Umrechnung in kW, absoluter Wert
            hausverbrauch = abs(data["Body"]["Data"]["Site"]["P_Load"] / 1000)  # Umrechnung in kW, absoluter Wert
            batterieladestand = data["Body"]["Data"]["Inverters"]["1"]["SOC"]  # Batterieladestand in %

            daten = {
                "Zeitstempel": zeitstempel,
                "PV-Leistung (kW)": pv_leistung,
                "Netz-Leistung (kW)": netz_leistung,
                "Batterie-Leistung (kW)": batterie_leistung,
                "Hausverbrauch (kW)": hausverbrauch,
                "Batterieladestand (%)": batterieladestand
            }

            # Daten in CSV speichern
            csv_datei = "FroniusDaten.csv"
            datei_existiert = os.path.exists(csv_datei)

            with open(csv_datei, "a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                # Schreibe die Spaltenüberschriften, wenn die Datei nicht existiert oder leer ist
                if not datei_existiert or os.stat(csv_datei).st_size == 0:
                    print("Die Datei existiert nicht oder ist leer. Schreibe Spaltenüberschriften...")
                    writer.writerow(daten.keys())  # Schreibe die Spaltenüberschriften
                print(f"Schreibe folgende Daten in die CSV-Datei: {daten}")
                writer.writerow(daten.values())  # Schreibe die Werte

            print(f"Daten wurden in '{csv_datei}' gespeichert.")
        else:
            print("Fehler beim Abrufen der Daten.")
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

# Scheduler einrichten
schedule.every(60).seconds.do(abrufen_und_speichern)  # Daten alle 10 Sekunden abrufen

print("Programm läuft erfolgreich.")

while True:
    print("Scheduler läuft...")  # Debug-Ausgabe
    schedule.run_pending()
    time.sleep(1)