import threading
import Wechselrichter
import BMKDATEN
import visualisierung_tkinter  # Direkt importieren, nicht als Subprozess!
import grafiken
import time

def run_wechselrichter():
    Wechselrichter.run()

def run_bmkdaten():
    BMKDATEN.main()

def main():
    wr_thread = threading.Thread(target=run_wechselrichter, daemon=True)
    bmk_thread = threading.Thread(target=run_bmkdaten, daemon=True)
    grafik_thread = threading.Thread(target=run_grafik_updates, daemon=True)
    wr_thread.start()
    bmk_thread.start()
    grafik_thread.start()

    # Starte die Visualisierung im Hauptthread!
    visualisierung_tkinter.init_gui()
    visualisierung_tkinter.show_image()
    visualisierung_tkinter.root.mainloop()

def run_grafik_updates():
    while True:
        try:
            grafiken.update_fronius_graphics()
            grafiken.update_bmk_graphics()
            grafiken.update_summary_graphics()
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Grafiken: {e}")
        time.sleep(60)  # 1 Minute warten

if __name__ == "__main__":
    main()