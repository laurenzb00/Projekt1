import threading
import time
import tkinter as tk
from tkinter import ttk
import psutil
import platform
import os
from datetime import datetime, timedelta
from ui.styles import (
    COLOR_ROOT,
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    emoji,
)
from ui.components.card import Card
from modern_widgets import CircularProgressWidget

class SystemTab:
    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True
        self.start_time = datetime.now()
        
        # Variablen
        self.var_cpu = tk.IntVar(value=0)
        self.var_ram = tk.IntVar(value=0)
        self.var_disk = tk.IntVar(value=0)
        self.var_temp = tk.StringVar(value="-- °C")
        self.var_uptime = tk.StringVar(value="00:00:00")
        self.var_status = tk.StringVar(value="Läuft stabil")
        
        self.tab_frame = tk.Frame(self.notebook, bg=COLOR_ROOT)
        self.notebook.add(self.tab_frame, text=emoji("⚙️ System", "System"))
        
        self._build_ui()
        self.root.after(0, lambda: threading.Thread(target=self._loop, daemon=True).start())

    def stop(self):
        self.alive = False

    def _build_ui(self):
        # Header
        header = ttk.Frame(self.tab_frame)
        header.pack(fill=tk.X, pady=15, padx=15)
        ttk.Label(header, text="Systemstatus (Raspberry Pi)", font=("Arial", 22, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.var_uptime, font=("Arial", 14)).pack(side=tk.RIGHT)

        # Hauptbereich Grid
        content = ttk.Frame(self.tab_frame)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # Oben: 3 Kacheln (CPU, RAM, Disk) mit modernen Circular Progress
        row1 = ttk.Frame(content)
        row1.pack(fill=tk.X, expand=True)
        
        # CPU
        card_cpu = ttk.Labelframe(row1, text="CPU Last", padding=10)
        card_cpu.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        self.cpu_widget = CircularProgressWidget(card_cpu, size=140, title="CPU")
        self.cpu_widget.pack()

        # RAM
        card_ram = ttk.Labelframe(row1, text="RAM Nutzung", padding=10)
        card_ram.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.ram_widget = CircularProgressWidget(card_ram, size=140, title="RAM")
        self.ram_widget.pack()

        # Disk mit Circular Progress
        card_disk = ttk.Labelframe(row1, text="SD-Karte", padding=10)
        card_disk.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0))
        self.disk_widget = CircularProgressWidget(card_disk, size=140, title="Disk")
        self.disk_widget.pack()
        
        # Temperatur-Anzeige darunter
        temp_frame = ttk.Frame(content)
        temp_frame.pack(fill=tk.X, pady=10)
        ttk.Label(temp_frame, text="CPU Temperatur:", font=("Arial", 12, "bold")).pack()
        ttk.Label(temp_frame, textvariable=self.var_temp, font=("Arial", 28, "bold")).pack(pady=5)

        # Unten: App Info / Logs
        row2 = ttk.Labelframe(content, text="Programm Information", padding=10)
        row2.pack(fill=tk.BOTH, expand=True, pady=10)
        
        info_txt = (
            f"OS: {platform.system()} {platform.release()}\n"
            f"Python: {platform.python_version()}\n"
            f"Prozess ID: {os.getpid()}"
        )
        ttk.Label(row2, text=info_txt, font=("Consolas", 10), justify=tk.LEFT).pack(side=tk.LEFT, padx=10)
        
        # Status Box rechts
        stat_box = ttk.Frame(row2)
        stat_box.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Label(stat_box, text="App Status:", font=("Arial", 12, "bold")).pack(anchor="e")
        ttk.Label(stat_box, textvariable=self.var_status, font=("Arial", 12)).pack(anchor="e")

    def _get_cpu_temp(self):
        # Versucht Temperatur auf Raspberry Pi zu lesen
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return float(f.read()) / 1000.0
        except:
            # Fallback für Windows/andere Linuxe
            try:
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps: return temps['coretemp'][0].current
                if 'cpu_thermal' in temps: return temps['cpu_thermal'][0].current
                return 0.0
            except:
                return 0.0

    def _loop(self):
        while self.alive:
            try:
                # 1. Hardware Stats
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                temp = self._get_cpu_temp()
                
                # 2. Uptime berechnen
                delta = datetime.now() - self.start_time
                uptime_str = str(delta).split('.')[0] # Mikrosekunden abschneiden

                # 3. GUI Update mit modernen Widgets
                def _update_ui():
                    self.var_cpu.set(int(cpu))
                    self.cpu_widget.update_value(int(cpu), "CPU")
                    
                    self.var_ram.set(int(ram))
                    self.ram_widget.update_value(int(ram), "RAM")
                    
                    self.var_disk.set(int(disk))
                    self.disk_widget.update_value(int(disk), "Disk")
                    
                    self.var_temp.set(f"{temp:.1f} °C")
                    self.var_uptime.set(f"Laufzeit: {uptime_str}")
                    
                    # App Status Logik (Simpel)
                    if cpu > 90: self.var_status.set("Warnung: Hohe CPU Last")
                    elif ram > 90: self.var_status.set("Warnung: Wenig RAM")
                    elif temp > 80: self.var_status.set("KRITISCH: Überhitzung!")
                    else: self.var_status.set("Alles OK - System läuft stabil")

                self.root.after(0, _update_ui)

            except Exception as e:
                print(f"System Monitor Fehler: {e}")
            
            time.sleep(2)