import threading
import logging
import time
import tkinter as tk
import subprocess
import sys
import platform

import BMKDATEN
import Wechselrichter
from ui.app import MainApp

# --- Ensure Emoji Font is installed ---
def ensure_emoji_font():
    """Install emoji font if not available (for Raspberry Pi compatibility)."""
    system = platform.system()
    try:
        if system == "Linux":
            # Try to install fonts-noto-color-emoji on Linux/Raspberry Pi
            try:
                subprocess.run(["dpkg", "-l"], capture_output=True, check=True, timeout=5)
                # apt is available, check if emoji font is installed
                result = subprocess.run(
                    ["dpkg", "-l", "|", "grep", "fonts-noto-color-emoji"],
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if result.returncode != 0:
                    print("[EMOJI] Installing fonts-noto-color-emoji...")
                    subprocess.run(
                        ["sudo", "apt-get", "install", "-y", "fonts-noto-color-emoji"],
                        timeout=60, capture_output=True
                    )
            except Exception:
                pass
    except Exception as e:
        print(f"[EMOJI] Could not ensure emoji font: {e}")

ensure_emoji_font()

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

    root = tk.Tk()
    root.title("Smart Energy Dashboard Pro")
    app = MainApp(root)

    def on_close():
        logging.info("Programm wird beendet…")
        shutdown_event.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Programm mit STRG+C beendet.")
        shutdown_event.set()