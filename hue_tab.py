import threading
import time
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# --- KONFIGURATION ---
HUE_BRIDGE_IP = "192.168.1.68" # <--- HIER BITTE IHRE ECHTE IP WIEDER EINTRAGEN!

class HueTab:
    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True
        self.bridge = None
        
        self.status_var = tk.StringVar(value="Initialisiere...")
        
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text=" Licht ")
        
        self._build_header()
        
        # Scrollbarer Bereich
        self.canvas = tk.Canvas(self.tab_frame, highlightthickness=0)
        # Hintergrundfarbe anpassen ans Theme (dunkelgrau)
        self.canvas.configure(bg="#2b3e50")
        
        self.scrollbar = ttk.Scrollbar(self.tab_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)
        
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.scrollbar.pack(side="right", fill="y")

        # Start Connection Thread
        threading.Thread(target=self._connect_loop, daemon=True).start()

    def stop(self):
        self.alive = False

    def _build_header(self):
        header = ttk.Frame(self.tab_frame)
        header.pack(fill=X, padx=10, pady=10)
        ttk.Label(header, text="Philips Hue Steuerung", font=("Arial", 20, "bold"), bootstyle="inverse-dark").pack(side=LEFT)
        ttk.Label(header, textvariable=self.status_var, bootstyle="warning").pack(side=RIGHT)

    def _connect_loop(self):
        from phue import Bridge, PhueRegistrationException
        
        while self.alive and self.bridge is None:
            try:
                self.bridge = Bridge(HUE_BRIDGE_IP)
                self.bridge.connect() 
                self.status_var.set("Verbunden")
                self.root.after(0, self._refresh_lights_ui)
                return # Verbindung steht, Loop beenden
            except PhueRegistrationException:
                self.status_var.set("BITTE KNOPF AUF BRIDGE DRÜCKEN!")
                time.sleep(2)
            except Exception as e:
                self.status_var.set(f"Verbindungsfehler: {e}")
                time.sleep(5)
        
        # Wenn verbunden, Status aktuell halten (optional)
        while self.alive:
            time.sleep(10)

    def _refresh_lights_ui(self):
        # Alte Widgets löschen
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        try:
            lights = self.bridge.get_light_objects()
            
            if not lights:
                ttk.Label(self.scroll_frame, text="Keine Lampen gefunden.").pack(pady=20)
                return

            row = 0
            col = 0
            
            # Sortieren nach Namen
            sorted_lights = sorted(lights, key=lambda x: x.name)

            for light in sorted_lights:
                self._create_light_card(light, row, col)
                col += 1
                if col > 1: # 2 Spalten
                    col = 0
                    row += 1
                    
        except Exception as e:
            self.status_var.set(f"Fehler beim Laden: {e}")

    def _create_light_card(self, light, row, col):
        card = ttk.Labelframe(self.scroll_frame, text=light.name, padding=10, bootstyle="secondary")
        card.grid(row=row, column=col, sticky="ew", padx=10, pady=10, ipadx=10)
        
        # --- FIX: Prüfen ob Lampe dimmbar ist ---
        is_on = False
        bri = 0
        can_dim = False
        
        try:
            is_on = light.on
            # Wir versuchen auf Helligkeit zuzugreifen
            if hasattr(light, 'brightness'):
                # Manchmal ist brightness None, wenn aus
                val = light.brightness
                if val is not None:
                    bri = val
                    can_dim = True
        except Exception:
            # Wenn Zugriff fehlschlägt (z.B. Smart Plug), ist es nicht dimmbar
            can_dim = False

        # AN/AUS Button
        btn_txt = "AN" if is_on else "AUS"
        btn_style = "success" if is_on else "dark" # dark ist dezenter für AUS
        
        def toggle_cmd(l=light):
            try:
                l.on = not l.on
                # Kleines UI Update nach kurzer Zeit
                self.root.after(200, self._refresh_lights_ui)
            except Exception as e:
                print(f"Schaltfehler: {e}")

        btn = ttk.Button(card, text=btn_txt, bootstyle=btn_style, command=toggle_cmd, width=8)
        btn.pack(side=LEFT, padx=(0, 15))
        
        # Slider nur anzeigen, wenn Lampe das kann
        if can_dim:
            def slide_cmd(val, l=light):
                try:
                    l.brightness = int(float(val))
                except: pass

            slider = ttk.Scale(card, from_=0, to=254, value=bri, command=lambda v: slide_cmd(v))
            slider.pack(side=LEFT, fill=X, expand=YES)
        else:
            ttk.Label(card, text="(Nur Schalter)", font=("Arial", 9, "italic")).pack(side=LEFT)