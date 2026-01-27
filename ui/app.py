import tkinter as tk
import os
import platform
import shutil
import subprocess
from datetime import datetime
import json
import logging
from tkinter import ttk
from ui.styles import (
    init_style,
    COLOR_ROOT,
    COLOR_CARD,
    emoji,
    EMOJI_OK,
)
from ui.components.card import Card
from ui.components.header import HeaderBar
from ui.components.statusbar import StatusBar
from ui.views.energy_flow import EnergyFlowView
from ui.views.buffer_storage import BufferStorageView

_UI_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_ROOT = os.path.dirname(_UI_DIR)


def _data_path(filename: str) -> str:
    return os.path.join(_DATA_ROOT, filename)


def _read_lines_safe(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return f.readlines()
    except Exception:
        return []
try:
    from historical_tab import HistoricalTab
except ImportError:
    HistoricalTab = None
try:
    from ertrag_tab import ErtragTab
except ImportError:
    ErtragTab = None

# Import Tab Modules (alte Tabs in neuem Design)
try:
    from spotify_tab_modern import SpotifyTab
except ImportError:
    SpotifyTab = None
    
try:
    from tado_tab import TadoTab
except ImportError:
    TadoTab = None
    
try:
    from hue_tab_modern import HueTab
except ImportError:
    HueTab = None
    
try:
    from system_tab import SystemTab
except ImportError:
    SystemTab = None
    
try:
    from calendar_tab import CalendarTab
except ImportError:
    CalendarTab = None



class MainApp:
    """1024x600 Dashboard mit Grid-Layout, Cards, Header und Statusbar + Tabs."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Smart Home Dashboard")
        # Fix DPI scaling and force a true 1024x600 borderless fullscreen
        try:
            self.root.tk.call("tk", "scaling", 1.0)
        except Exception:
            pass
        sw = max(1, self.root.winfo_screenwidth())
        sh = max(1, self.root.winfo_screenheight())
        target_w = min(sw, 1024)
        target_h = min(sh, 600)
        # Minimaler Offset, aber maximale nutzbare Höhe
        offset_y = 0
        usable_h = max(200, target_h - offset_y)
        self.is_fullscreen = True
        self._apply_fullscreen(target_w, usable_h, offset_y)
        self.root.resizable(False, False)
        try:
            self.root.attributes("-fullscreen", True)
            self.root.attributes("-zoomed", True)
        except Exception:
            pass
        init_style(self.root)
        self._ensure_emoji_font()

        # Grid Setup: rows 0/1/2/3, cols 0 (full width)
        self.root.grid_rowconfigure(0, minsize=68)
        self.root.grid_rowconfigure(1, minsize=28)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, minsize=28)
        self.root.grid_columnconfigure(0, weight=1)

        # Header
        self.header = HeaderBar(
            self.root,
            on_toggle_a=self.on_toggle_a,
            on_toggle_b=self.on_toggle_b,
            on_exit=self.on_exit,
        )
        self.header.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 6))

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 4))

        # Energy Dashboard Tab
        self.dashboard_tab = tk.Frame(self.notebook, bg=COLOR_ROOT)
        self.notebook.add(self.dashboard_tab, text=emoji("⚡ Energie", "Energie"))

        # Body (Energy + Buffer)
        self.body = tk.Frame(self.dashboard_tab, bg=COLOR_ROOT)
        # minimal padding to win vertical space on 600px height
        self.body.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.body.grid_columnconfigure(0, weight=7)
        self.body.grid_columnconfigure(1, weight=3)
        self.body.grid_rowconfigure(0, weight=1)

        # Energy Card (70%)
        self.energy_card = Card(self.body, padding=12)
        self.energy_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        self.energy_card.add_title("Energiefluss", icon="⚡")
        self.energy_view = EnergyFlowView(self.energy_card.content(), width=580, height=320)
        # Fill to nutzen: sorgt dafür, dass Energie- und Puffer-Card die gleiche Höhe bekommen
        self.energy_view.pack(fill=tk.BOTH, expand=True, pady=4)

        # Buffer Card (30%)
        self.buffer_card = Card(self.body, padding=12)
        self.buffer_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        self.buffer_card.add_title("Pufferspeicher", icon="🔥")
        self.buffer_view = BufferStorageView(self.buffer_card.content(), height=260)
        self.buffer_view.pack(fill=tk.BOTH, expand=True)

        # Statusbar
        self.status = StatusBar(self.root, on_exit=self.root.quit, on_toggle_fullscreen=self.toggle_fullscreen)
        self.status.grid(row=3, column=0, sticky="nsew", padx=12, pady=(4, 8))

        # Add other tabs
        self._add_other_tabs()

        # State
        self._tick = 0
        self._last_data = {
            "pv": 0,
            "load": 0,
            "grid": 0,
            "batt": 0,
            "soc": 0,
            "out_temp": 0,
            "puffer_top": 0,
            "puffer_mid": 0,
            "puffer_bot": 0,
        }
        
        self._loop()

    def _add_other_tabs(self):
        """Integriert Spotify, Tado, Hue, System und Calendar Tabs."""
        if SpotifyTab:
            self.spotify_tab = SpotifyTab(self.root, self.notebook)
        if TadoTab:
            self.tado_tab = TadoTab(self.root, self.notebook)
        if HueTab:
            self.hue_tab = HueTab(self.root, self.notebook)
        if SystemTab:
            self.system_tab = SystemTab(self.root, self.notebook)
        if CalendarTab:
            self.calendar_tab = CalendarTab(self.root, self.notebook)
        if HistoricalTab:
            self.historical_tab = HistoricalTab(self.root, self.notebook)
        if ErtragTab:
            self.ertrag_tab = ErtragTab(self.root, self.notebook)

    # --- Callbacks ---
    def on_toggle_a(self):
        self.status.update_status("Hue: Alle an")
        try:
            if hasattr(self, "hue_tab") and self.hue_tab:
                self.hue_tab._threaded_group_cmd(True)
        except Exception:
            pass

    def on_toggle_b(self):
        self.status.update_status("Hue: Alle aus")
        try:
            if hasattr(self, "hue_tab") and self.hue_tab:
                self.hue_tab._threaded_group_cmd(False)
        except Exception:
            pass

    def on_exit(self):
        self.status.update_status("Beende...")
        self.root.after(100, self.root.quit)

    def _apply_fullscreen(self, target_w: int, target_h: int, offset_y: int):
        self.root.overrideredirect(True)
        self.root.geometry(f"{target_w}x{target_h}+0+{offset_y}")
        try:
            self.root.attributes("-fullscreen", True)
        except Exception:
            pass

    def _apply_windowed(self, w: int = 1024, h: int = 600, x: int = 50, y: int = 50):
        try:
            self.root.attributes("-fullscreen", False)
        except Exception:
            pass
        self.root.overrideredirect(False)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def toggle_fullscreen(self):
        sw = max(1, self.root.winfo_screenwidth())
        sh = max(1, self.root.winfo_screenheight())
        target_w = min(sw, 1024)
        target_h = min(sh, 600)
        if self.is_fullscreen:
            self.is_fullscreen = False
            self._apply_windowed()
            self.status.update_status("Fenster-Modus")
        else:
            self.is_fullscreen = True
            self._apply_fullscreen(target_w, target_h, 0)
            self.status.update_status("Fullscreen")

    def _ensure_emoji_font(self):
        """Prüft Emoji-Font und versucht Installation auf Linux (apt-get)."""
        if EMOJI_OK:
            return
        # Nur Linux: optional Auto-Install, wenn apt-get verfügbar und root
        if platform.system().lower() != "linux":
            self.status.update_status("Emoji-Font fehlt (Pi: fonts-noto-color-emoji)")
            return
        if not shutil.which("apt-get"):
            self.status.update_status("Emoji-Font fehlt (apt-get nicht gefunden)")
            return
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            self.status.update_status("Emoji-Font fehlt (sudo nötig): fonts-noto-color-emoji")
            return
        try:
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", "fonts-noto-color-emoji"], check=True)
            self.status.update_status("Emoji-Font installiert, bitte neu starten")
        except Exception:
            self.status.update_status("Emoji-Font Installation fehlgeschlagen")

    # --- Update Loop mit echten Daten ---
    def _loop(self):
        self._tick += 1

        # Versuche echte Daten zu laden
        try:
            self._fetch_real_data()
        except Exception as e:
            logging.debug(f"Fehler beim Abrufen echter Daten: {e}")

        # Header every 1s
        now = datetime.now()
        if self._tick % 2 == 0:
            date_text = now.strftime("%d.%m.%Y")
            weekday = now.strftime("%A")
            time_text = now.strftime("%H:%M")
            out_temp = f"{self._last_data['out_temp']:.1f} °C"
            self.header.update_header(date_text, weekday, time_text, out_temp)
            self.status.update_status(f"Updated {time_text}")
            soc = self._last_data["soc"]
            self.status.update_center(f"SOC {soc:.0f}%")

        # Energy every 500ms
        self.energy_view.update_flows(
            self._last_data["pv"],
            self._last_data["load"],
            self._last_data["grid"],
            self._last_data["batt"],
            self._last_data["soc"],
        )

        # Buffer every 2s
        if self._tick % 4 == 0:
            self.buffer_view.update_temperatures(
                self._last_data["puffer_top"],
                self._last_data["puffer_mid"],
                self._last_data["puffer_bot"],
            )

        self.root.after(500, self._loop)

    def _fetch_real_data(self):
        """Versucht, echte Daten aus CSV/APIs zu laden."""
        import csv

        fronius_csv = _data_path("FroniusDaten.csv")
        bmk_csv = _data_path("Heizungstemperaturen.csv")

        # Fronius Daten (letzter Eintrag)
        if os.path.exists(fronius_csv):
            try:
                lines = _read_lines_safe(fronius_csv)
                    if len(lines) > 1:
                        last_line = lines[-1].strip()
                        reader = csv.reader([last_line])
                        row = next(reader)
                        if len(row) >= 6:
                            self._last_data["pv"] = float(row[1]) * 1000  # kW -> W
                            self._last_data["grid"] = float(row[2]) * 1000
                            self._last_data["batt"] = float(row[3]) * 1000
                            self._last_data["load"] = float(row[4]) * 1000
                            self._last_data["soc"] = float(row[5])
            except Exception as e:
                logging.debug(f"Fronius CSV Fehler: {e}")

        # BMK Daten (letzter Eintrag)
        if os.path.exists(bmk_csv):
            try:
                lines = _read_lines_safe(bmk_csv)
                    if len(lines) > 1:
                        last_line = lines[-1].strip()
                        reader = csv.reader([last_line])
                        row = next(reader)
                        if len(row) >= 7:
                            self._last_data["out_temp"] = float(row[2])
                            self._last_data["puffer_top"] = float(row[3])
                            self._last_data["puffer_mid"] = float(row[4])
                            self._last_data["puffer_bot"] = float(row[5])
            except Exception as e:
                logging.debug(f"BMK CSV Fehler: {e}")


def run():
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()

