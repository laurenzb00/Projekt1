import tkinter as tk
from datetime import datetime
import math
from ui.styles import (
    init_style,
    COLOR_ROOT,
    COLOR_CARD,
)
from ui.components.card import Card
from ui.components.header import HeaderBar
from ui.components.statusbar import StatusBar
from ui.views.energy_flow import EnergyFlowView
from ui.views.buffer_storage import BufferStorageView


class MainApp:
    """1024x600 Dashboard mit Grid-Layout, Cards, Header und Statusbar."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Smart Home Dashboard")
        self.root.geometry("1024x600")
        self.root.resizable(False, False)
        init_style(self.root)

        # Grid Setup: rows 0/1/2, cols 0 (full width)
        self.root.grid_rowconfigure(0, minsize=72)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, minsize=32)
        self.root.grid_columnconfigure(0, weight=1)

        # Header
        self.header = HeaderBar(self.root, on_toggle_a=self.on_toggle_a, on_toggle_b=self.on_toggle_b)
        self.header.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 6))

        # Body
        self.body = tk.Frame(self.root, bg=COLOR_ROOT)
        self.body.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        self.body.grid_columnconfigure(0, weight=7)
        self.body.grid_columnconfigure(1, weight=3)
        self.body.grid_rowconfigure(0, weight=1)

        # Statusbar
        self.status = StatusBar(self.root, on_exit=self.root.quit)
        self.status.grid(row=2, column=0, sticky="nsew", padx=12, pady=(6, 12))

        # Energy Card (70%)
        self.energy_card = Card(self.body)
        self.energy_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        self.energy_card.add_title("Energiefluss", icon="⚡")
        self.energy_view = EnergyFlowView(self.energy_card.content())
        self.energy_view.pack(fill=tk.BOTH, expand=True)

        # Buffer Card (30%)
        self.buffer_card = Card(self.body)
        self.buffer_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        self.buffer_card.add_title("Pufferspeicher", icon="🔥")
        self.buffer_view = BufferStorageView(self.buffer_card.content())
        self.buffer_view.pack(fill=tk.BOTH, expand=True)

        # State for demo updates
        self._tick = 0
        self._loop()

    # --- Callbacks ---
    def on_toggle_a(self):
        pass

    def on_toggle_b(self):
        pass

    # --- Update Loop ---
    def _loop(self):
        self._tick += 1

        # Header every 1s
        now = datetime.now()
        if self._tick % 2 == 0:
            date_text = now.strftime("%d.%m.%Y")
            weekday = now.strftime("%A")
            time_text = now.strftime("%H:%M:%S")
            self.header.update_header(date_text, weekday, time_text, "5 °C")
            self.status.update_status(f"Updated {time_text}")
            self.status.update_center("SOC 62%   Grid Import")

        # Energy every 500ms
        pv = 2200 + 600 * math.sin(self._tick / 10)
        load = 1900 + 260 * math.sin(self._tick / 14)
        batt = 300 * math.sin(self._tick / 8)
        grid = load - pv - batt  # erlaubt Import/Export
        soc = 55 + 18 * math.sin(self._tick / 28)
        self.energy_view.update_flows(pv, load, grid, batt, soc)

        # Buffer every 2s
        if self._tick % 4 == 0:
            top = 65 + 2 * math.sin(self._tick / 25)
            mid = 55 + 1 * math.sin(self._tick / 30)
            bot = 45 + 1 * math.sin(self._tick / 35)
            self.buffer_view.update_temperatures(top, mid, bot)

        self.root.after(500, self._loop)


def run():
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()
