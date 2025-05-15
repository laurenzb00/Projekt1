import tkinter as tk
from PIL import Image, ImageTk  # ImageTk is used for converting images to a format compatible with Tkinter
import os
import signal

# Arbeitsverzeichnis setzen
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Liste der Grafiken (auf Modulebene!)
grafik_pfade = [
    os.path.join(WORKING_DIRECTORY, "Zusammenfassung.png"),
    os.path.join(WORKING_DIRECTORY, "FroniusDaten.png"),
    os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.png"),
]

# Index der aktuellen Grafik (auf Modulebene!)
current_index = 0

root = None
label = None

# Funktion zum Anzeigen der aktuellen Grafik
def show_image():
    try:
        # Lade die aktuelle Grafik
        image_path = grafik_pfade[current_index]
        img = Image.open(image_path)
        img = img.resize((root.winfo_screenwidth(), root.winfo_screenheight()), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        # Zeige die Grafik im Label an
        label.config(image=photo)
        label.image = photo
    except Exception as e:
        print(f"Fehler beim Laden der Grafik: {e}")

# Funktion zum Anzeigen der nächsten Grafik
def next_image(event=None):
    global current_index
    current_index = (current_index + 1) % len(grafik_pfade)  # Nächste Grafik (zyklisch)
    show_image()

# Funktion zum Anzeigen der vorherigen Grafik
def previous_image(event=None):
    global current_index
    current_index = (current_index - 1) % len(grafik_pfade)  # Vorherige Grafik (zyklisch)
    show_image()

def close_program():
    """Sendet ein Signal an das Hauptprogramm, um alles zu beenden."""
    print("Schließen-Button gedrückt.")
    os.kill(os.getppid(), signal.SIGINT)  # Sendet SIGINT an das Hauptprogramm

def init_gui():
    global root, label
    if root is None:
        root = tk.Tk()
        root.title("Grafik-Anzeige")
        root.attributes("-fullscreen", True)
        label = tk.Label(root, bg="black")
        label.pack(fill=tk.BOTH, expand=True)
        close_button = tk.Button(root, text="Schließen", command=close_program, font=("Arial", 14), bg="red", fg="white")
        close_button.place(relx=0.9, rely=0.9, anchor="center")
        root.bind("<Button-1>", next_image)
        root.bind("<Button-3>", previous_image)

# Hauptprogramm
if __name__ == "__main__":
    # Tkinter-Fenster erstellen
    init_gui()

    # Erste Grafik anzeigen
    show_image()

    # Tkinter-Hauptschleife starten
    root.mainloop()