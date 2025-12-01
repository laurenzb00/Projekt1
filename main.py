import threading
import logging
import visualisierung_live
import Wechselrichter
import BMKDATEN
import tkinter as tk # KORRIGIERTER IMPORT
from ttkbootstrap import Window # Importiert nur Window
from spotify_tab import SpotifyTab
import time 

# --- Logging: Datei + Konsole ---
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
            # Ruft die Einzelfunktion ab und schläft danach
            BMKDATEN.abrufen_und_speichern() 
            time.sleep(60)
    except Exception as e:
        logging.error(f"BMKDATEN-Thread Fehler: {e}")


def main():
    # --- Backend-Threads ---
    threads = [
        threading.Thread(target=run_wechselrichter, daemon=True),
        threading.Thread(target=run_bmkdaten, daemon=True),
    ]
    for t in threads:
        t.start()

    # --- GUI FIX: WINDOW MIT THEME STARTEN ---
    root = Window(themename="superhero") # Nutzt ttkbootstrap.Window für Dark Mode
    root.geometry("1100x650") 
    root.resizable(False, False)
    
    app = visualisierung_live.LivePlotApp(root) 

    # --- Spotify-Tab (eigene Datei) ---
    spotify = SpotifyTab(root, app.notebook) 
    
    app.spotify_instance = spotify 

    def on_close():
        logging.info("Programm wird beendet…")
        shutdown_event.set()
        try:
            spotify.stop() 
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