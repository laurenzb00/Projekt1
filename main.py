import threading
import logging
import time
import Wechselrichter
import BMKDATEN
import visualisierung_live  # <--- NEU: Live-Visualisierung importieren

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

def main():
    threads = [
        threading.Thread(target=run_wechselrichter, daemon=True),
        threading.Thread(target=run_bmkdaten, daemon=True)
    ]
    for t in threads:
        t.start()

    # Starte die Live-Visualisierung im Hauptthread
    root = visualisierung_live.tk.Tk()
    app = visualisierung_live.LivePlotApp(root)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Programm wurde beendet.")