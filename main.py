import threading
import Wechselrichter
import BMKDATEN
import visualisierung_tkinter  # Direkt importieren, nicht als Subprozess!
import grafiken
import time
from datetime import datetime
from PIL import Image, ImageTk

def run_wechselrichter():
    Wechselrichter.run()

def run_bmkdaten():
    BMKDATEN.main()

def show_image():
    global root, label
    if root is None or label is None:
        init_gui()
    try:
        image_path = grafik_pfade[current_index]
        img = Image.open(image_path)
        img = img.resize((root.winfo_screenwidth(), root.winfo_screenheight()), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        label.config(image=photo)
        label.image = photo
    except Exception as e:
        print(f"Fehler beim Laden der Grafik: {e}")

def main():
    wr_thread = threading.Thread(target=run_wechselrichter, daemon=True)
    bmk_thread = threading.Thread(target=run_bmkdaten, daemon=True)
    wr_thread.start()
    bmk_thread.start()

    # Starte die Visualisierung im Hauptthread!
    visualisierung_tkinter.init_gui()      # GUI initialisieren
    visualisierung_tkinter.show_image()    # Erst jetzt Bild anzeigen
    visualisierung_tkinter.root.mainloop() # Tkinter-Eventloop starten

if __name__ == "__main__":
    main()