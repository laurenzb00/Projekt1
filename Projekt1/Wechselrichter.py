import requests
import csv
import time
import schedule
import os
import pandas as pd
import matplotlib.pyplot as plt
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

def daten_visualisieren():
    print("Funktion daten_visualisieren wurde aufgerufen.")
    csv_datei = "FroniusDaten.csv"
    try:
        print(f"CSV-Datei wird geladen: {csv_datei}")
        daten = pd.read_csv(csv_datei, parse_dates=["Zeitstempel"], dtype={
            "PV-Leistung (kW)": float,
            "Netz-Leistung (kW)": float,
            "Batterie-Leistung (kW)": float,
            "Hausverbrauch (kW)": float,
            "Batterieladestand (%)": float
        })

        if daten.empty:
            print("Die CSV-Datei ist leer. Keine Daten zum Visualisieren.")
            return

        print("Geladene Daten:")
        print(daten.head())

        # Berechne die kumulierte Produktion und den Verbrauch
        daten["Kumulative Produktion (kWh)"] = daten["PV-Leistung (kW)"].cumsum() / 60  # Annahme: 1 Minute Intervalle
        daten["Kumulativer Verbrauch (kWh)"] = daten["Hausverbrauch (kW)"].cumsum() / 60  # Annahme: 1 Minute Intervalle

        # Zeitlicher Verlauf aller Werte darstellen (ohne Batterieladestand)
        print("Erstelle Diagramm für Leistungsdaten...")
        plt.figure(figsize=(12, 8))
        plt.plot(daten["Zeitstempel"], abs(daten["PV-Leistung (kW)"]), label="PV-Leistung (kW)", marker="o")
        plt.plot(daten["Zeitstempel"], abs(daten["Netz-Leistung (kW)"]), label="Netz-Leistung (kW)", marker="x")
        plt.plot(daten["Zeitstempel"], abs(daten["Batterie-Leistung (kW)"]), label="Batterie-Leistung (kW)", marker="s")
        plt.plot(daten["Zeitstempel"], abs(daten["Hausverbrauch (kW)"]), label="Hausverbrauch (kW)", marker="^")

        # Diagramm beschriften
        plt.title("Fronius GEN24 Leistungsdaten (positiver Bereich)")
        plt.xlabel("Zeit")
        plt.ylabel("Leistung (kW)")
        plt.legend()
        plt.grid()

        # X-Achse rotieren für bessere Lesbarkeit
        plt.xticks(rotation=45)

        # Grafik speichern
        print("Speichere Diagramm als 'FroniusDaten.png'...")
        plt.savefig("FroniusDaten.png")
        print("Diagramm wurde als 'FroniusDaten.png' gespeichert.")

        # Kumulative Produktion und Verbrauch darstellen
        print("Erstelle Diagramm für kumulative Daten...")
        plt.figure(figsize=(12, 8))
        plt.plot(daten["Zeitstempel"], daten["Kumulative Produktion (kWh)"], label="Kumulative Produktion (kWh)", marker="o")
        plt.plot(daten["Zeitstempel"], daten["Kumulativer Verbrauch (kWh)"], label="Kumulativer Verbrauch (kWh)", marker="x")

        # Diagramm beschriften
        plt.title("Kumulative Produktion und Verbrauch")
        plt.xlabel("Zeit")
        plt.ylabel("Energie (kWh)")
        plt.legend()
        plt.grid()

        # X-Achse rotieren für bessere Lesbarkeit
        plt.xticks(rotation=45)

        # Grafik speichern
        print("Speichere Diagramm als 'KumulativeDaten.png'...")
        plt.savefig("KumulativeDaten.png")
        print("Diagramm wurde als 'KumulativeDaten.png' gespeichert.")

        # Erstelle eine Batterie-Grafik für den Batterieladestand
        print("Erstelle Diagramm für Batterieladestand...")
        aktueller_batterieladestand = daten["Batterieladestand (%)"].iloc[-1]  # Letzter Wert
        plt.figure(figsize=(4, 8))
        plt.barh([0], aktueller_batterieladestand, color="green", height=0.5)
        plt.xlim(0, 100)
        plt.title("Batterieladestand")
        plt.xlabel("Ladestand (%)")
        plt.yticks([])
        plt.grid(axis="x")

        # Grafik speichern
        print("Speichere Diagramm als 'Batterieladestand.png'...")
        plt.savefig("Batterieladestand.png")
        print("Diagramm wurde als 'Batterieladestand.png' gespeichert.")

    except FileNotFoundError:
        print(f"Die Datei '{csv_datei}' wurde nicht gefunden.")
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

# Scheduler einrichten
schedule.every(10).seconds.do(abrufen_und_speichern)  # Daten alle 60 Sekunden abrufen
schedule.every(1).minutes.do(daten_visualisieren)  # Grafik alle 10 Minuten aktualisieren

print("Programm läuft erfolgreich.")

while True:
    print("Scheduler läuft...")  # Debug-Ausgabe
    schedule.run_pending()
    time.sleep(1)