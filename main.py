import subprocess
import time
from datetime import datetime
import os
import grafiken  
import Wechselrichter
import BMKDATEN


def main():
    start_time = datetime.now()
    last_bmk_update = start_time
    last_fronius_update = start_time
    last_summary_update = start_time

    # Starte visualisierung_tkinter.py als separaten Prozess
    visualisierung_process = subprocess.Popen(
        ["python", "visualisierung_tkinter.py"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    print("Visualisierung gestartet...")

    try:
        while True:
            current_time = datetime.now()

            # Aktualisiere Fronius-Grafik alle 30 Sekunden
            if (current_time - last_fronius_update).total_seconds() >= 30:
                print("Fronius-Grafik wird aktualisiert...")
                grafiken.update_fronius_graphics()
                last_fronius_update = current_time

            # Aktualisiere BMK-Grafik alle 30 Sekunden
            if (current_time - last_bmk_update).total_seconds() >= 30:
                print("BMK-Grafik wird aktualisiert...")
                grafiken.update_bmk_graphics()
                last_bmk_update = current_time

            # Aktualisiere die Zusammenfassungsgrafik alle 30 Sekunden
            if (current_time - last_summary_update).total_seconds() >= 30:
                print("Zusammenfassungsgrafik wird aktualisiert...")
                grafiken.update_summary_graphics()
                last_summary_update = current_time

            # Warte 5 Sekunden, um die CPU-Auslastung zu reduzieren
            time.sleep(5)

    except KeyboardInterrupt:
        print("Programm wird beendet...")
        # Beende den Visualisierungsprozess
        visualisierung_process.terminate()
        visualisierung_process.wait()
        print("Visualisierung beendet.")

if __name__ == "__main__":
    main()