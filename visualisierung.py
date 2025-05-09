import os
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer, Qt

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