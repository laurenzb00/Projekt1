
import threading
import logging
import queue
import visualisierung_live
import Wechselrichter
import BMKDATEN

from spotify_tab import SpotifyTab  # <--- NEU

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
            BMKDATEN.main()
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

    # --- GUI ---
    root = visualisierung_live.tk.Tk()
    root.geometry("1024x600")  # feste Auflösung
    app = visualisierung_live.LivePlotApp(root)

    # --- Spotify-Tab (eigene Datei) ---
    spotify = SpotifyTab(root, app.notebook)

    def on_close():
        logging.info("Programm wird beendet…")
        shutdown_event.set()
        try:
            spotify.stop()  # Update-Schleifen sauber beenden
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
