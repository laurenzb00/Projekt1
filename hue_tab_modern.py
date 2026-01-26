"""
MODERNER HUE LICHT TAB
======================
Features:
- Grid-Layout (3 Spalten)
- RGB Color Picker für fähige Lampen
- Touch-optimierte Buttons
- Glasmorphism Design
- Echtzeit-Updates
- Helligkeits-Slider mit Live-Feedback
"""

import threading
import time
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# --- FARBEN ---
COLOR_DARK_BG = "#0b1220"
COLOR_CARD_BG = "#0f172a"
COLOR_ACCENT = "#1f2a44"
COLOR_PRIMARY = "#38bdf8"
COLOR_SUCCESS = "#10b981"
COLOR_WARNING = "#f59e0b"
COLOR_TEXT = "#e5e7eb"
COLOR_SUBTEXT = "#8ba2c7"

# --- KONFIGURATION ---
HUE_BRIDGE_IP = "192.168.1.111"  # <--- HIER DEINE BRIDGE IP EINTRAGEN!

class HueTab:
    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True
        self.bridge = None
        self.lights_cache = []
        self.color_picker_windows = {}
        
        self.status_var = tk.StringVar(value="Initialisiere...")
        
        self.tab_frame = tk.Frame(self.notebook, bg=COLOR_DARK_BG)
        self.notebook.add(self.tab_frame, text=" 💡 Licht ")
        
        self._build_header()
        self._build_global_controls()
        
        # Scrollbarer Bereich
        canvas_container = tk.Frame(self.tab_frame, bg=COLOR_DARK_BG)
        canvas_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        
        self.canvas = tk.Canvas(canvas_container, bg=COLOR_DARK_BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=COLOR_DARK_BG)
        
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Grid-Konfiguration (3 Spalten)
        for i in range(3):
            self.scroll_frame.columnconfigure(i, weight=1, minsize=310)

        # Start Connection
        threading.Thread(target=self._connect_loop, daemon=True).start()

    def stop(self):
        self.alive = False

    def _build_header(self):
        """Moderner Header mit Gradient"""
        header = tk.Frame(self.tab_frame, bg=COLOR_WARNING, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header, text="💡 Philips Hue",
            font=("Segoe UI", 24, "bold"),
            fg="white", bg=COLOR_WARNING
        ).pack(side=tk.LEFT, padx=20, pady=15)
        
        tk.Label(
            header, textvariable=self.status_var,
            font=("Segoe UI", 11),
            fg="#fef3c7", bg=COLOR_WARNING
        ).pack(side=tk.RIGHT, padx=20)

    def _build_global_controls(self):
        """Zentrale Steuerung"""
        bar = tk.Frame(self.tab_frame, bg=COLOR_DARK_BG)
        bar.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        tk.Label(
            bar, text="Zentrale Steuerung:",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_TEXT, bg=COLOR_DARK_BG
        ).pack(side=tk.LEFT, padx=(0, 15))
        
        # Modern Buttons
        def create_btn(parent, text, cmd, bg):
            return tk.Button(
                parent, text=text,
                font=("Segoe UI", 11, "bold"),
                bg=bg, fg="white",
                activebackground=bg,
                relief=tk.FLAT,
                cursor="hand2",
                padx=25, pady=10,
                command=cmd
            )
        
        create_btn(bar, "☀ ALLE AN", lambda: self._threaded_group_cmd(True), COLOR_SUCCESS).pack(side=tk.LEFT, padx=5)
        create_btn(bar, "🌑 ALLE AUS", lambda: self._threaded_group_cmd(False), COLOR_ACCENT).pack(side=tk.LEFT, padx=5)

    def _connect_loop(self):
        from phue import Bridge, PhueRegistrationException
        
        while self.alive and self.bridge is None:
            try:
                self.bridge = Bridge(HUE_BRIDGE_IP)
                self.bridge.connect()
                self.status_var.set("✓ Verbunden")
                self.root.after(0, self._refresh_lights_ui)
                break
            except PhueRegistrationException:
                self.status_var.set("⚠ BITTE KNOPF AUF BRIDGE DRÜCKEN!")
                time.sleep(2)
            except Exception as e:
                self.status_var.set(f"⚠ Verbindungsproblem...")
                time.sleep(5)
        
        # Background refresh (alle 20s)
        while self.alive and self.bridge:
            time.sleep(20)
            self.root.after(0, self._refresh_lights_ui)

    def _refresh_lights_ui(self):
        """Baut das Grid neu"""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        try:
            self.lights_cache = self.bridge.get_light_objects()
            if not self.lights_cache:
                tk.Label(
                    self.scroll_frame,
                    text="Keine Lampen gefunden.",
                    font=("Segoe UI", 12),
                    fg=COLOR_SUBTEXT, bg=COLOR_DARK_BG
                ).grid(row=0, column=0, columnspan=3, pady=40)
                return

            sorted_lights = sorted(self.lights_cache, key=lambda x: x.name)

            # Grid Layout (3 Spalten)
            row = 0
            col = 0
            
            for light in sorted_lights:
                self._create_light_card(light, row, col)
                col += 1
                if col > 2:
                    col = 0
                    row += 1
                    
        except Exception as e:
            self.status_var.set(f"Fehler: {e}")

    def _create_light_card(self, light, row, col):
        """Erstellt moderne Lichtkarte"""
        try:
            is_on = light.on
            bri = 0
            can_dim = False
            can_color = False
            hue = 0
            sat = 0
            
            if hasattr(light, 'brightness') and light.brightness is not None:
                bri = light.brightness
                can_dim = True
                
            if hasattr(light, 'hue') and hasattr(light, 'saturation'):
                can_color = True
                hue = getattr(light, 'hue', 0)
                sat = getattr(light, 'saturation', 0)
        except:
            is_on = False
            can_dim = False
            can_color = False

        # Outer Frame (Shadow simulation)
        outer = tk.Frame(self.scroll_frame, bg="#0a0f1a")
        outer.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        
        # Card
        border_color = COLOR_SUCCESS if is_on else COLOR_ACCENT
        card = tk.Frame(
            outer,
            bg=COLOR_CARD_BG,
            relief=tk.FLAT,
            highlightbackground=border_color,
            highlightthickness=2
        )
        card.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Header
        header = tk.Frame(card, bg="#142038", height=45)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Icon + Name
        icon_color = "#fbbf24" if is_on else COLOR_SUBTEXT
        tk.Label(
            header, text="💡",
            font=("Segoe UI", 20),
            fg=icon_color, bg="#142038"
        ).pack(side=tk.LEFT, padx=(12, 8))
        
        tk.Label(
            header, text=light.name,
            font=("Segoe UI", 12, "bold"),
            fg="white", bg="#142038",
            anchor="w"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, pady=12)

        # Content
        content = tk.Frame(card, bg=COLOR_CARD_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # === Toggle Button ===
        btn_txt = "Ausschalten" if is_on else "Einschalten"
        btn_bg = COLOR_SUCCESS if is_on else COLOR_ACCENT
        
        def toggle_worker():
            try:
                light.on = not light.on
                self.root.after(300, self._refresh_lights_ui)
            except: pass

        def on_toggle():
            threading.Thread(target=toggle_worker, daemon=True).start()

        toggle_btn = tk.Button(
            content, text=btn_txt,
            font=("Segoe UI", 10, "bold"),
            bg=btn_bg, fg="white",
            activebackground=btn_bg,
            relief=tk.FLAT,
            cursor="hand2",
            command=on_toggle
        )
        toggle_btn.pack(fill=tk.X, pady=(0, 12))

        # === Helligkeit ===
        if can_dim:
            bright_frame = tk.Frame(content, bg=COLOR_CARD_BG)
            bright_frame.pack(fill=tk.X, pady=(0, 10))
            
            tk.Label(
                bright_frame, text="Helligkeit",
                font=("Segoe UI", 9),
                fg=COLOR_SUBTEXT, bg=COLOR_CARD_BG
            ).pack(side=tk.LEFT)
            
            bri_label = tk.Label(
                bright_frame, text=f"{int((bri/254)*100)}%",
                font=("Segoe UI", 9, "bold"),
                fg="white", bg=COLOR_CARD_BG
            )
            bri_label.pack(side=tk.RIGHT)
            
            def slide_worker(val):
                try:
                    light.brightness = int(float(val))
                    percent = int((float(val)/254)*100)
                    bri_label.config(text=f"{percent}%")
                except: pass
            
            def on_slide(val):
                threading.Thread(target=slide_worker, args=(val,), daemon=True).start()

            slider = ttk.Scale(
                content,
                from_=0, to=254,
                value=bri,
                command=on_slide,
                bootstyle="warning"
            )
            slider.pack(fill=tk.X, pady=(0, 10))
        else:
            tk.Label(
                content, text="Nicht dimmbar",
                font=("Segoe UI", 9, "italic"),
                fg=COLOR_SUBTEXT, bg=COLOR_CARD_BG
            ).pack(pady=5)

        # === Farbe ===
        if can_color:
            def open_color_picker():
                self._show_color_picker(light, hue, sat)
            
            color_btn = tk.Button(
                content, text="🎨 Farbe wählen",
                font=("Segoe UI", 10, "bold"),
                bg=COLOR_PRIMARY, fg="white",
                activebackground="#0284c7",
                relief=tk.FLAT,
                cursor="hand2",
                command=open_color_picker
            )
            color_btn.pack(fill=tk.X)

    def _show_color_picker(self, light, current_hue, current_sat):
        """Öffnet Farbwähler-Fenster"""
        if light.light_id in self.color_picker_windows:
            try:
                self.color_picker_windows[light.light_id].lift()
                return
            except:
                pass
        
        win = tk.Toplevel(self.root)
        win.title(f"Farbe: {light.name}")
        win.geometry("400x500")
        win.configure(bg=COLOR_CARD_BG)
        win.transient(self.root)
        
        self.color_picker_windows[light.light_id] = win
        
        # Header
        header = tk.Frame(win, bg=COLOR_PRIMARY, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header, text=f"🎨 {light.name}",
            font=("Segoe UI", 16, "bold"),
            fg="white", bg=COLOR_PRIMARY
        ).pack(pady=15)
        
        content = tk.Frame(win, bg=COLOR_CARD_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Preview
        preview_frame = tk.Frame(content, bg=COLOR_CARD_BG)
        preview_frame.pack(pady=(0, 20))
        
        preview_canvas = tk.Canvas(
            preview_frame,
            width=200, height=200,
            bg=COLOR_DARK_BG,
            highlightthickness=0
        )
        preview_canvas.pack()
        
        # Hue Slider
        tk.Label(
            content, text="Farbton (Hue)",
            font=("Segoe UI", 10, "bold"),
            fg="white", bg=COLOR_CARD_BG
        ).pack(anchor="w", pady=(10, 5))
        
        hue_var = tk.IntVar(value=current_hue)
        hue_slider = ttk.Scale(
            content,
            from_=0, to=65535,
            variable=hue_var,
            bootstyle="danger",
            command=lambda v: self._update_preview(preview_canvas, hue_var.get(), sat_var.get())
        )
        hue_slider.pack(fill=tk.X, pady=(0, 15))
        
        # Saturation Slider
        tk.Label(
            content, text="Sättigung (Saturation)",
            font=("Segoe UI", 10, "bold"),
            fg="white", bg=COLOR_CARD_BG
        ).pack(anchor="w", pady=(10, 5))
        
        sat_var = tk.IntVar(value=current_sat)
        sat_slider = ttk.Scale(
            content,
            from_=0, to=254,
            variable=sat_var,
            bootstyle="info",
            command=lambda v: self._update_preview(preview_canvas, hue_var.get(), sat_var.get())
        )
        sat_slider.pack(fill=tk.X, pady=(0, 20))
        
        # Initial preview
        self._update_preview(preview_canvas, current_hue, current_sat)
        
        # Schnellfarben
        tk.Label(
            content, text="Schnellfarben:",
            font=("Segoe UI", 10, "bold"),
            fg="white", bg=COLOR_CARD_BG
        ).pack(anchor="w", pady=(10, 8))
        
        quick_colors = tk.Frame(content, bg=COLOR_CARD_BG)
        quick_colors.pack(fill=tk.X, pady=(0, 20))
        
        presets = [
            ("Rot", 0, 254),
            ("Grün", 25500, 254),
            ("Blau", 46920, 254),
            ("Gelb", 12750, 254),
            ("Lila", 56100, 254),
            ("Weiß", 0, 0)
        ]
        
        for name, h, s in presets:
            tk.Button(
                quick_colors, text=name,
                font=("Segoe UI", 9),
                bg=COLOR_ACCENT, fg="white",
                relief=tk.FLAT,
                cursor="hand2",
                width=10,
                command=lambda h=h, s=s: self._set_preset(light, h, s, hue_var, sat_var, preview_canvas, win)
            ).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        
        # Apply Button
        def apply_color():
            def worker():
                try:
                    light.hue = hue_var.get()
                    light.saturation = sat_var.get()
                    win.destroy()
                    del self.color_picker_windows[light.light_id]
                except: pass
            threading.Thread(target=worker, daemon=True).start()
        
        apply_btn = tk.Button(
            content, text="✓ Farbe anwenden",
            font=("Segoe UI", 12, "bold"),
            bg=COLOR_SUCCESS, fg="white",
            activebackground="#059669",
            relief=tk.FLAT,
            cursor="hand2",
            command=apply_color
        )
        apply_btn.pack(fill=tk.X, pady=(10, 0))
        
        win.protocol("WM_DELETE_WINDOW", lambda: self._close_picker(win, light.light_id))

    def _update_preview(self, canvas, hue, sat):
        """Aktualisiert Farbvorschau"""
        import colorsys
        
        # Hue: 0-65535 -> 0-1, Sat: 0-254 -> 0-1
        h = hue / 65535
        s = sat / 254
        v = 1.0
        
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        r, g, b = int(r*255), int(g*255), int(b*255)
        
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        
        canvas.delete("all")
        canvas.create_oval(20, 20, 180, 180, fill=hex_color, outline="white", width=3)

    def _set_preset(self, light, hue, sat, hue_var, sat_var, canvas, win):
        """Setzt Schnellfarbe"""
        hue_var.set(hue)
        sat_var.set(sat)
        self._update_preview(canvas, hue, sat)

    def _close_picker(self, win, light_id):
        """Schließt Farbwähler"""
        try:
            win.destroy()
            if light_id in self.color_picker_windows:
                del self.color_picker_windows[light_id]
        except:
            pass

    # === GRUPPEN-BEFEHLE ===
    def _threaded_group_cmd(self, state):
        threading.Thread(target=self._worker_group, args=(state,), daemon=True).start()

    def _worker_group(self, state):
        if not self.bridge: return
        try:
            self.bridge.set_group(0, 'on', state)
            time.sleep(0.4)
            self.root.after(0, self._refresh_lights_ui)
        except Exception as e:
            print(f"Gruppe Fehler: {e}")
