import threading
import time
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# --- KONFIGURATION ---
HUE_BRIDGE_IP = "192.168.1.111" # <--- HIER DEINE BRIDGE IP EINTRAGEN!

class HueTab:
    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True
        self.bridge = None
        self.lights_cache = [] # Cache für schnelleren Zugriff
        
        self.status_var = tk.StringVar(value="Initialisiere...")
        
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text=" Licht ")
        
        self._build_header()
        self._build_global_controls() # NEU: Alles An/Aus
        
        # Scrollbarer Bereich
        self.canvas = tk.Canvas(self.tab_frame, highlightthickness=0)
        self.canvas.configure(bg="#2b3e50")
        
        self.scrollbar = ttk.Scrollbar(self.tab_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)
        
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=1050) # Breite fixieren für Grid
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=(0,10))
        self.scrollbar.pack(side="right", fill="y")

        # Start Connection
        threading.Thread(target=self._connect_loop, daemon=True).start()

    def stop(self):
        self.alive = False

    def _build_header(self):
        header = ttk.Frame(self.tab_frame)
        header.pack(fill=X, padx=15, pady=(15, 5))
        ttk.Label(header, text="Philips Hue Steuerung", font=("Arial", 22, "bold"), bootstyle="inverse-dark").pack(side=LEFT)
        ttk.Label(header, textvariable=self.status_var, bootstyle="warning").pack(side=RIGHT)

    def _build_global_controls(self):
        # Leiste für "Alles An" / "Alles Aus"
        bar = ttk.Frame(self.tab_frame)
        bar.pack(fill=X, padx=15, pady=(0, 10))
        
        ttk.Label(bar, text="Zentralsteuerung:", font=("Arial", 10, "bold"), bootstyle="secondary").pack(side=LEFT, padx=(0,10))
        
        # Buttons senden Befehle in Threads für sofortige Reaktion
        ttk.Button(bar, text="☀ ALLE AN", bootstyle="warning", width=15, 
                   command=lambda: self._threaded_group_cmd(True)).pack(side=LEFT, padx=5)
        
        ttk.Button(bar, text="🌑 ALLE AUS", bootstyle="secondary", width=15, 
                   command=lambda: self._threaded_group_cmd(False)).pack(side=LEFT, padx=5)

    def _connect_loop(self):
        from phue import Bridge, PhueRegistrationException
        
        while self.alive and self.bridge is None:
            try:
                self.bridge = Bridge(HUE_BRIDGE_IP)
                self.bridge.connect()
                self.status_var.set("Verbunden")
                self.root.after(0, self._refresh_lights_ui)
                return 
            except PhueRegistrationException:
                self.status_var.set("BITTE KNOPF AUF BRIDGE DRÜCKEN!")
                time.sleep(2)
            except Exception as e:
                self.status_var.set(f"Verbindungsproblem...")
                time.sleep(5)
        
        # Hintergrund-Refresh alle 30s (damit Handy-Änderungen sichtbar werden)
        while self.alive:
            time.sleep(30)
            self.root.after(0, self._refresh_lights_ui)

    def _refresh_lights_ui(self):
        # UI neu bauen
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        try:
            # Liste holen und cachen
            self.lights_cache = self.bridge.get_light_objects()
            if not self.lights_cache:
                ttk.Label(self.scroll_frame, text="Keine Lampen gefunden.").pack(pady=20)
                return

            # Sortieren
            sorted_lights = sorted(self.lights_cache, key=lambda x: x.name)

            # Grid Layout (2 Spalten, responsive)
            row = 0
            col = 0
            
            for light in sorted_lights:
                self._create_light_card(light, row, col)
                col += 1
                if col > 1: 
                    col = 0
                    row += 1
                    
        except Exception as e:
            self.status_var.set("Fehler beim Laden der Lampen")

    def _create_light_card(self, light, row, col):
        # Status prüfen
        try:
            is_on = light.on
            bri = 0
            can_dim = False
            if hasattr(light, 'brightness') and light.brightness is not None:
                bri = light.brightness
                can_dim = True
        except:
            is_on = False
            can_dim = False

        # Style basierend auf Status (Grüner Rand wenn an)
        style_color = "success" if is_on else "secondary"
        
        # Labelframe als Karte
        card = ttk.Labelframe(self.scroll_frame, text=f" {light.name} ", padding=10, bootstyle=style_color)
        card.grid(row=row, column=col, sticky="ew", padx=10, pady=10, ipadx=5, ipady=5)
        
        # Wir zwingen die Spalten im Grid, sich auszudehnen
        self.scroll_frame.columnconfigure(0, weight=1)
        self.scroll_frame.columnconfigure(1, weight=1)

        # Icon (Text-Emoji)
        icon_lbl = ttk.Label(card, text="💡" if is_on else "⚫", font=("Arial", 20))
        icon_lbl.pack(side=LEFT, padx=(0, 15))

        # Inhalt Container
        content = ttk.Frame(card)
        content.pack(side=LEFT, fill=X, expand=YES)

        # Toggle Button
        btn_txt = "Ausschalten" if is_on else "Einschalten"
        btn_style = "success-outline" if is_on else "secondary"
        
        def toggle_worker():
            try:
                light.on = not light.on
                # UI Refresh nach kurzer Zeit, um Status zu bestätigen
                self.root.after(200, self._refresh_lights_ui)
            except: pass

        def on_click():
            # Optimistisches UI Feedback (sofort reagieren)
            if btn_txt == "Einschalten":
                icon_lbl.config(text="💡")
                btn.config(text="...", state="disabled")
            else:
                icon_lbl.config(text="⚫")
                btn.config(text="...", state="disabled")
            # Befehl im Hintergrund senden
            threading.Thread(target=toggle_worker, daemon=True).start()

        btn = ttk.Button(content, text=btn_txt, bootstyle=btn_style, command=on_click, width=12)
        btn.pack(anchor="w", pady=(0, 5))

        # Slider (nur wenn dimmbar)
        if can_dim:
            def slide_worker(val):
                try: light.brightness = int(float(val))
                except: pass
            
            def on_slide(val):
                # Senden in Thread auslagern, damit Slider nicht ruckelt
                threading.Thread(target=slide_worker, args=(val,), daemon=True).start()

            slider = ttk.Scale(content, from_=0, to=254, value=bri, command=on_slide, bootstyle=style_color)
            slider.pack(fill=X, expand=YES)
        else:
            ttk.Label(content, text="Nicht dimmbar", font=("Arial", 9, "italic"), bootstyle="secondary").pack(anchor="w")

    # --- HINTERGRUND BEFEHLE ---
    
    def _threaded_group_cmd(self, state):
        """Schaltet Gruppe 0 (Alle Lampen) an oder aus."""
        threading.Thread(target=self._worker_group, args=(state,), daemon=True).start()

    def _worker_group(self, state):
        if not self.bridge: return
        try:
            # Gruppe 0 ist bei Hue immer "Alle Lampen"
            self.bridge.set_group(0, 'on', state)
            # Kurz warten, dann UI neu laden
            time.sleep(0.5)
            self.root.after(0, self._refresh_lights_ui)
        except Exception as e:
            print(f"Global Schaltfehler: {e}")