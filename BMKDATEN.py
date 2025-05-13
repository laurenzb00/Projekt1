import requests
import csv
import time
import schedule
import os
import pandas as pd
import matplotlib.pyplot as plt
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
    except Exception:
        pass

def daten_visualisieren():
    csv_datei = "Heizungstemperaturen.csv"
    try:
        daten = pd.read_csv(csv_datei, parse_dates=["Zeitstempel"], dtype={
            "Kesseltemperatur": float,
            "Außentemperatur": float,
            "Pufferspeicher Oben": float,
            "Pufferspeicher Mitte": float,
            "Pufferspeicher Unten": float,
            "Warmwasser": float
        })

        if daten.empty:
            return

        # Zeitlicher Verlauf aller Temperaturen darstellen
        plt.figure(figsize=(12, 8))
        plt.plot(daten["Zeitstempel"], daten["Kesseltemperatur"], label="Kesseltemperatur", marker="o")
        plt.plot(daten["Zeitstempel"], daten["Außentemperatur"], label="Außentemperatur", marker="x")
        plt.plot(daten["Zeitstempel"], daten["Pufferspeicher Oben"], label="Pufferspeicher Oben", marker="s")
        plt.plot(daten["Zeitstempel"], daten["Pufferspeicher Mitte"], label="Pufferspeicher Mitte", marker="^")
        plt.plot(daten["Zeitstempel"], daten["Pufferspeicher Unten"], label="Pufferspeicher Unten", marker="v")
        plt.plot(daten["Zeitstempel"], daten["Warmwasser"], label="Warmwasser", marker="d")

        # Diagramm beschriften
        plt.title("Zeitlicher Verlauf der Temperaturen")
        plt.xlabel("Zeit")
        plt.ylabel("Temperatur (°C)")
        plt.legend()
        plt.grid()

        # X-Achse rotieren für bessere Lesbarkeit
        plt.xticks(rotation=45)

        # Grafik speichern
        plt.savefig("Heizungstemperaturen.png")
        plt.close()

    except FileNotFoundError:
        pass
    except Exception:
        pass

# Scheduler einrichten
schedule.every(60).seconds.do(abrufen_und_speichern)  # Daten alle 60 Sekunden abrufen
schedule.every(10).minutes.do(daten_visualisieren)  # Grafik alle 10 Minuten aktualisieren

while True:
    schedule.run_pending()
    time.sleep(1)
