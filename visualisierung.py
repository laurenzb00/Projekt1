import os
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer, Qt
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import pandas as pd

class GraphicViewer(QMainWindow):
    def __init__(self, graphics, update_interval=5000):
        super().__init__()
        self.graphics = graphics
        self.current_index = 0
        self.update_interval = update_interval  # Aktualisierungsintervall in Millisekunden

        # Hauptfenster konfigurieren
        self.setWindowTitle("Grafikanzeige")
        self.setGeometry(100, 100, 800, 600)

        # Layout erstellen
        self.layout = QVBoxLayout()

        # Label für die Grafik
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)

        # Button-Layout erstellen
        button_layout = QHBoxLayout()

        # Button "Zurück"
        self.prev_button = QPushButton("<< Zurück")
        self.prev_button.clicked.connect(self.previous_image)
        button_layout.addWidget(self.prev_button)

        # Button "Weiter"
        self.next_button = QPushButton("Weiter >>")
        self.next_button.clicked.connect(self.next_image)
        button_layout.addWidget(self.next_button)

        # Buttons zum Hauptlayout hinzufügen
        self.layout.addLayout(button_layout)

        # Widget setzen
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # Timer für die automatische Aktualisierung
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_image)
        self.timer.start(self.update_interval)

        # Erste Grafik anzeigen
        self.update_image()

    def update_image(self):
        # Lade die aktuelle Grafik
        image_path = self.graphics[self.current_index]
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), aspectRatioMode=1))
        else:
            self.image_label.setText(f"Datei nicht gefunden: {image_path}")

    def next_image(self):
        # Zeige die nächste Grafik
        self.current_index = (self.current_index + 1) % len(self.graphics)
        self.update_image()

    def previous_image(self):
        # Zeige die vorherige Grafik
        self.current_index = (self.current_index - 1) % len(self.graphics)
        self.update_image()

def update_summary_graphics():
    print("Aktualisiere Zusammenfassungs-Grafiken...")
    try:
        WORKING_DIRECTORY = os.getcwd()  # Setze das Arbeitsverzeichnis auf das aktuelle Verzeichnis
        # CSV-Dateien lesen
        fronius_daten = pd.read_csv(os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv"))
        heizung_daten = pd.read_csv(os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv"))
        
        # Spaltennamen bereinigen
        fronius_daten.columns = fronius_daten.columns.str.strip()
        heizung_daten.columns = heizung_daten.columns.str.strip()

        # Berechne die aktuellen Werte
        aktuelle_netz_leistung = fronius_daten["Netz-Leistung (kW)"].iloc[-1]
        aktuelle_batterieladestand = fronius_daten["Batterieladestand (%)"].iloc[-1]
        aktuelle_hausverbrauch = fronius_daten["Hausverbrauch (kW)"].iloc[-1]
        aktuelle_puffer_oben = heizung_daten["Pufferspeicher Oben"].iloc[-1]
        aktuelle_puffer_mitte = heizung_daten["Pufferspeicher Mitte"].iloc[-1]
        aktuelle_puffer_unten = heizung_daten["Pufferspeicher Unten"].iloc[-1]
        aktuelle_kesseltemperatur = heizung_daten["Kesseltemperatur"].iloc[-1]
        aktuelle_aussentemperatur = heizung_daten["Außentemperatur"].iloc[-1]

        # Erstelle die Grafik
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.axis("off")  # Keine Achsen anzeigen

        # Text und Piktogramme
        daten = [
            ("Puffertemperatur Oben", f"{aktuelle_puffer_oben:.1f} °C", "temperature.png"),
            ("Puffertemperatur Mitte", f"{aktuelle_puffer_mitte:.1f} °C", "temperature.png"),
            ("Puffertemperatur Unten", f"{aktuelle_puffer_unten:.1f} °C", "temperature.png"),
            ("Kesseltemperatur", f"{aktuelle_kesseltemperatur:.1f} °C", "boiler.png"),
            ("Außentemperatur", f"{aktuelle_aussentemperatur:.1f} °C", "outdoor.png"),
            ("Batterieladestand", f"{aktuelle_batterieladestand:.1f} %", "battery.png"),
            ("Hausverbrauch", f"{aktuelle_hausverbrauch:.1f} kW", "house.png"),
            ("Netz-Leistung", f"{aktuelle_netz_leistung:.1f} kW", "power.png"),
        ]

        # Zeichne die Daten mit Piktogrammen
        y_pos = 0.9
        for label, value, icon_name in daten:
            icon_path = os.path.join(WORKING_DIRECTORY, "icons", icon_name)
            if os.path.exists(icon_path):
                print(f"Piktogramm gefunden: {icon_path}")  # Debug-Ausgabe
                image = plt.imread(icon_path)
                imagebox = OffsetImage(image, zoom=0.1)
                ab = AnnotationBbox(imagebox, (0.2, y_pos), frameon=False)
                ax.add_artist(ab)
            else:
                print(f"Piktogramm fehlt: {icon_path}")  # Debug-Ausgabe
            ax.text(0.3, y_pos, label, fontsize=14, ha="left", va="center", color="black")
            ax.text(0.7, y_pos, value, fontsize=14, ha="right", va="center", color="blue")
            y_pos -= 0.1  # Abstand zwischen den Zeilen

        # Grafik speichern
        grafik_pfad = os.path.join(WORKING_DIRECTORY, "Zusammenfassung.png")
        plt.savefig(grafik_pfad, dpi=300, bbox_inches="tight")
        print(f"Zusammenfassungsgrafik '{grafik_pfad}' gespeichert.")
        plt.close()

    except Exception as e:
        print(f"Fehler beim Erstellen der Zusammenfassungs-Grafik: {e}")

def main():
    app = QApplication([])
    graphics = [
        os.path.join(os.getcwd(), "FroniusDaten.png"),
        os.path.join(os.getcwd(), "Heizungstemperaturen.png"),
        os.path.join(os.getcwd(), "Zusammenfassung.png"),
    ]
    viewer = GraphicViewer(graphics)
    viewer.show()
    app.exec_()


if __name__ == "__main__":
    main()