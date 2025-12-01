import threading
import logging
import visualisierung_live
import Wechselrichter
import BMKDATEN
import tkinter as tk 
from ttkbootstrap import Window 
from spotify_tab import SpotifyTab
from tado_tab import TadoTab   # <--- NEU
from hue_tab import HueTab     # <--- NEU
import time 

# --- Logging ---
logging.basicConfig(
    filename="datenerfassung.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(console)

shutdown_event = threading.Event()

def run_wechselrichter():
    try:
        while not shutdown_event.is_set():
            Wechselrichter.run()
    except Exception as e:
        logging.error(f"Wechselrichter-Thread Fehler: {e}")

def run_bmkdaten():
    try:
        while not shutdown_event.is_set():
            BMKDATEN.abrufen_und_speichern() 
            time.sleep(60)
    except Exception as e:
        logging.error(f"BMKDATEN-Thread Fehler: {e}")

def main():
    threads = [
        threading.Thread(target=run_wechselrichter, daemon=True),
        threading.Thread(target=run_bmkdaten, daemon=True),
    ]
    for t in threads:
        t.start()

    # --- GUI START ---
    root = Window(themename="superhero") 
    root.geometry("1100x650") 
    root.resizable(False, False)
    root.title("Smart Energy Dashboard") # Titel angepasst
    
    # 1. Haupt-App (Energie Tabs)
    app = visualisierung_live.LivePlotApp(root) 

    # 2. Smart Home Tabs hinzufügen
    # Die Reihenfolge hier bestimmt die Reihenfolge der Tabs
    tado = TadoTab(root, app.notebook)
    hue = HueTab(root, app.notebook)
    spotify = SpotifyTab(root, app.notebook) 
    
    app.spotify_instance = spotify 

    def on_close():
        logging.info("Programm wird beendet…")
        shutdown_event.set()
        try:
            spotify.stop()
            tado.stop() # Neu
            hue.stop()  # Neu
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Programm mit STRG+C beendet.")
        shutdown_event.set()