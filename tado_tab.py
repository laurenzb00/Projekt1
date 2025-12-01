import threading
import time
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# --- KONFIGURATION ---
TADO_USER = "deine_email@adresse.de"  # <--- HIER ÄNDERN
TADO_PASS = "dein_passwort"           # <--- HIER ÄNDERN

class TadoTab:
    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True
        self.api = None
        self.zone_id = None
        
        # UI Variablen
        self.var_temp_ist = tk.StringVar(value="--.- °C")
        self.var_temp_soll = tk.StringVar(value="-- °C")
        self.var_humidity = tk.StringVar(value="-- %")
        self.var_status = tk.StringVar(value="Verbinde...")
        self.var_power = tk.IntVar(value=0) # Heizleistung 0-100%

        # Frame erstellen
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text=" Klima ")

        self._build_ui()
        
        # Start Thread
        threading.Thread(target=self._loop, daemon=True).start()

    def _build_ui(self):
        # Header
        header = ttk.Frame(self.tab_frame)
        header.pack(fill=X, pady=10, padx=10)
        ttk.Label(header, text="Schlafzimmer Klima", font=("Arial", 20, "bold"), bootstyle="inverse-dark").pack(side=LEFT)
        ttk.Label(header, textvariable=self.var_status, bootstyle="secondary").pack(side=RIGHT)

        # Content Grid
        content = ttk.Frame(self.tab_frame)
        content.pack(fill=BOTH, expand=YES, padx=20, pady=10)
        
        # Linke Seite: IST-Werte (Groß)
        left = ttk.Labelframe(content, text="Aktuell", padding=15, bootstyle="info")
        left.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))
        
        # Temperatur Groß
        ttk.Label(left, text="Temperatur:", font=("Arial", 12)).pack(anchor="w")
        ttk.Label(left, textvariable=self.var_temp_ist, font=("Arial", 48, "bold"), bootstyle="info").pack(pady=10)
        
        # Feuchtigkeit
        hum_row = ttk.Frame(left)
        hum_row.pack(fill=X, pady=10)
        ttk.Label(hum_row, text="Luftfeuchtigkeit:", font=("Arial", 12)).pack(side=LEFT)
        ttk.Label(hum_row, textvariable=self.var_humidity, font=("Arial", 16, "bold"), bootstyle="secondary").pack(side=RIGHT)

        # Rechte Seite: Steuerung
        right = ttk.Labelframe(content, text="Steuerung", padding=15, bootstyle="warning")
        right.pack(side=LEFT, fill=BOTH, expand=YES, padx=(10, 0))
        
        # Ziel-Temperatur mit +/- Buttons (Touch optimiert)
        ttk.Label(right, text="Ziel-Temperatur:", font=("Arial", 12)).pack(anchor="center")
        
        ctrl_frame = ttk.Frame(right)
        ctrl_frame.pack(pady=15)
        
        ttk.Button(ctrl_frame, text="-", width=4, bootstyle="outline", command=lambda: self._change_temp(-1)).pack(side=LEFT, padx=10)
        ttk.Label(ctrl_frame, textvariable=self.var_temp_soll, font=("Arial", 32, "bold"), bootstyle="warning").pack(side=LEFT, padx=10)
        ttk.Button(ctrl_frame, text="+", width=4, bootstyle="outline", command=lambda: self._change_temp(+1)).pack(side=LEFT, padx=10)

        # Heizleistung Balken
        ttk.Label(right, text="Heizleistung:", font=("Arial", 10)).pack(anchor="w", pady=(20, 5))
        ttk.Progressbar(right, variable=self.var_power, maximum=100, bootstyle="warning-striped").pack(fill=X)

    def _loop(self):
        # 1. Login
        try:
            from PyTado.interface import Tado
            self.api = Tado(TADO_USER, TADO_PASS)
            
            # Zone "Schlafzimmer" suchen (oder Zone 1 nehmen)
            zones = self.api.get_zones()
            target_zone = None
            for z in zones:
                if "Schlaf" in z['name'] or "Bed" in z['name']:
                    target_zone = z
                    break
            
            if not target_zone:
                target_zone = zones[0] # Fallback: Erste Zone
            
            self.zone_id = target_zone['id']
            self.var_status.set(f"Verbunden: {target_zone['name']}")
            
        except Exception as e:
            self.var_status.set(f"Login Fehler: {e}")
            return # Abbruch

        # 2. Update Loop
        while self.alive:
            try:
                state = self.api.get_zone_state(self.zone_id)
                
                # Daten parsen
                temp = state['sensorDataPoints']['insideTemperature']['celsius']
                hum = state['sensorDataPoints']['humidity']['percentage']
                power = state['activityDataPoints']['heatingPower']['percentage']
                target = state['setting']['temperature']['celsius'] if state['setting']['power'] == 'ON' else 0
                
                # GUI Update
                self.var_temp_ist.set(f"{temp:.1f} °C")
                self.var_humidity.set(f"{hum:.1f} %")
                self.var_power.set(int(power))
                
                if target > 0:
                    self.var_temp_soll.set(f"{target:.0f} °C")
                else:
                    self.var_temp_soll.set("AUS")
                    
            except Exception as e:
                self.var_status.set("Datenfehler...")
                print(f"Tado Error: {e}")
            
            time.sleep(60) # Alle 60s aktualisieren

    def _change_temp(self, delta):
        # Asynchron ändern, um UI nicht zu blockieren
        threading.Thread(target=self._set_temp_thread, args=(delta,), daemon=True).start()

    def _set_temp_thread(self, delta):
        try:
            current_str = self.var_temp_soll.get().replace(" °C", "").replace("AUS", "0")
            current = float(current_str)
            new_val = current + delta
            # Limits
            new_val = max(10, min(25, new_val))
            
            self.api.set_zone_overlay(self.zone_id, "MANUAL", new_val, termination="AUTO")
            self.var_status.set(f"Setze {new_val}°C...")
            # Schnelles UI Feedback
            self.var_temp_soll.set(f"{new_val:.0f} °C")
            
            time.sleep(2)
            self.var_status.set("Gespeichert")
        except Exception as e:
            self.var_status.set("Fehler beim Setzen")

    def stop(self):
        self.alive = False