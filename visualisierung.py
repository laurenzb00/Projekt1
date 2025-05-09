import os
from tkinter import Tk, Label, Button, PhotoImage

# Setze den Arbeitsbereich auf das Verzeichnis, in dem das Skript liegt
WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORKING_DIRECTORY)  # Ändere das aktuelle Arbeitsverzeichnis
print(f"Aktuelles Arbeitsverzeichnis: {os.getcwd()}")  # Debug-Ausgabe

# Pfade zu den Grafiken
GRAPHICS = [
    os.path.join(WORKING_DIRECTORY, "FroniusDaten.png"),
    os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.png"),
]

# Klasse für die Grafikanzeige
class GraphicViewer:
    def __init__(self, root, graphics):
        self.root = root
        self.graphics = graphics
        self.current_index = 0

        # Fenster konfigurieren
        self.root.title("Grafikanzeige")
        self.root.geometry("800x600")

        # Label für die Grafik
        self.image_label = Label(self.root)
        self.image_label.pack(expand=True)

        # Buttons zum Wechseln der Grafiken
        self.prev_button = Button(self.root, text="<< Zurück", command=self.show_prev)
        self.prev_button.pack(side="left", padx=10, pady=10)

        self.next_button = Button(self.root, text="Weiter >>", command=self.show_next)
        self.next_button.pack(side="right", padx=10, pady=10)

        # Erste Grafik anzeigen
        self.show_image()

    def show_image(self):
        # Lade die aktuelle Grafik
        image_path = self.graphics[self.current_index]
        if os.path.exists(image_path):
            photo = PhotoImage(file=image_path)
            self.image_label.config(image=photo)
            self.image_label.image = photo
        else:
            self.image_label.config(text=f"Datei nicht gefunden: {image_path}")
            self.image_label.image = None

    def show_prev(self):
        # Zeige die vorherige Grafik
        self.current_index = (self.current_index - 1) % len(self.graphics)
        self.show_image()

    def show_next(self):
        # Zeige die nächste Grafik
        self.current_index = (self.current_index + 1) % len(self.graphics)
        self.show_image()

# Hauptprogramm
def main():
    # Starte die Benutzeroberfläche
    root = Tk()
    viewer = GraphicViewer(root, GRAPHICS)
    root.mainloop()

if __name__ == "__main__":
    main()