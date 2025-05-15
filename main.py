import threading
import logging
import time
import Wechselrichter
import BMKDATEN
import visualisierung_tkinter
import grafiken
import requests  # Hinzugefügt für die Verwendung von requests

logging.basicConfig(filename="datenerfassung.log", level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_wechselrichter():
    try:
        Wechselrichter.run()
    except Exception as e:
        logging.error(f"Wechselrichter-Thread Fehler: {e}")

def run_bmkdaten():
    try:
        BMKDATEN.main()
    except Exception as e:
        logging.error(f"BMKDATEN-Thread Fehler: {e}")

def run_grafik_updates():
    while True:
        try:
            grafiken.update_fronius_graphics()
            grafiken.update_bmk_graphics()
            grafiken.update_summary_graphics()
        except Exception as e:
            logging.error(f"Fehler beim Aktualisieren der Grafiken: {e}")
        time.sleep(20)  # z.B. alle 20 Sekunden

def fetch_data(url):
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException as e:
        logging.error(f"Fehler beim Abrufen der Daten: {e}", exc_info=True)
        return
    # Verarbeite die Antwort hier weiter...

def main():
    threads = [
        threading.Thread(target=run_wechselrichter, daemon=True),
        threading.Thread(target=run_bmkdaten, daemon=True),
        threading.Thread(target=run_grafik_updates, daemon=True)
    ]
    for t in threads:
        t.start()

    visualisierung_tkinter.init_gui()
    visualisierung_tkinter.show_image()
    visualisierung_tkinter.root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Programm wurde beendet.")