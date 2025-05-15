import threading
import Wechselrichter
import BMKDATEN
import visualisierung_tkinter  # Direkt importieren, nicht als Subprozess!
import grafiken
import time
from datetime import datetime

def run_wechselrichter():
    Wechselrichter.run()

def run_bmkdaten():
    BMKDATEN.main()

def main():
    wr_thread = threading.Thread(target=run_wechselrichter, daemon=True)
    bmk_thread = threading.Thread(target=run_bmkdaten, daemon=True)
    wr_thread.start()
    bmk_thread.start()

    # Starte die Visualisierung im Hauptthread!
    visualisierung_tkinter.main()  # oder wie deine Startfunktion dort heißt

if __name__ == "__main__":
    main()