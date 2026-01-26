"""
ENERGIEFLUSS WIDGET V2 - OpenHAB Style
======================================
Visualisiert Energiefluss mit echten PNG-Icons und abgerundeten Kästen
"""

import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageDraw, ImageFont
import io
import os

class EnergyFlowWidgetV2:
    """OpenHAB-Style Energiefluss-Visualisierung"""
    
    def __init__(self, parent, width=700, height=280, style="modern"):
        self.parent = parent
        self.width = width
        self.height = height
        self.style = style
        
        # Standardwerte
        self.pv_power = 0
        self.load_power = 0
        self.battery_power = 0
        self.grid_power = 0
        self.battery_soc = 50
        
        # kWh Werte (Tagesertrag)
        self.pv_kwh = 0
        self.grid_kwh = 0
        self.battery_kwh = 0
        self.load_kwh = 0
        
        # Frame
        self.frame = tk.Frame(parent, width=width, height=height, bg="#0f172a")
        self.frame.pack_propagate(False)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas
        self.canvas = Canvas(self.frame, width=width, height=height,
                            bg="#0f172a", highlightthickness=0)
        self.canvas.pack()
        
        # Icons laden
        self._load_icons()
        
        self.photo_image = None
        self._draw()
    
    def _load_icons(self):
        """Lädt PNG-Icons oder erstellt Fallbacks"""
        icon_path = os.path.join(os.path.dirname(__file__), "icons")
        self.icons = {}
        
        try:
            # Versuche Icons zu laden (mit den richtigen Dateinamen!)
            pv_path = os.path.join(icon_path, "pv-icnon.png")  # Mit Tippfehler!
            grid_path = os.path.join(icon_path, "grid.jpg")  # JPG statt PNG!
            house_path = os.path.join(icon_path, "house.png")
            battery_path = os.path.join(icon_path, "battery.png")
            
            if os.path.exists(pv_path):
                self.icons['pv'] = self._load_and_remove_background(pv_path, (60, 60))
                print("✓ PV-Icon geladen")
            if os.path.exists(grid_path):
                self.icons['grid'] = self._load_and_remove_background(grid_path, (60, 60))
                print("✓ Grid-Icon geladen")
            if os.path.exists(house_path):
                self.icons['house'] = self._load_and_remove_background(house_path, (80, 80))
                print("✓ House-Icon geladen")
            if os.path.exists(battery_path):
                self.icons['battery'] = self._load_and_remove_background(battery_path, (60, 60))
                print("✓ Battery-Icon geladen")
        except Exception as e:
            print(f"Info: Icons werden gezeichnet (Fallback): {e}")
    
    def _load_and_remove_background(self, path, size):
        """Lädt Icon und entfernt weißen/grauen Hintergrund"""
        img = Image.open(path)
        
        # Konvertiere zu RGBA wenn nicht bereits
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Entferne weißen/hellgrauen Hintergrund durch Alpha-Transparency
        # Pixel die sehr hell sind (> 200 in allen Kanälen) werden transparent
        data = img.getdata()
        new_data = []
        for item in data:
            # Wenn RGB-Werte alle > 200 (sehr hell), mach es transparent
            if len(item) >= 3:
                r, g, b = item[0], item[1], item[2]
                if r > 200 and g > 200 and b > 200:
                    new_data.append((255, 255, 255, 0))  # Transparent
                else:
                    if len(item) == 4:
                        new_data.append(item)  # Behalte Alpha wenn vorhanden
                    else:
                        new_data.append((item[0], item[1], item[2], 255))  # Volles Alpha
        
        img.putdata(new_data)
        return img.resize(size)
    
    def _draw(self):
        """Zeichnet OpenHAB-Style Energiefluss"""
        # PIL Image erstellen mit RGBA für Transparenzunterstützung
        img = Image.new('RGBA', (self.width, self.height), color=(15, 23, 42, 255))
        draw = ImageDraw.Draw(img)
        
        # Layout-Positionen (wie OpenHAB)
        # Oben links: PV (x=100, y=40)
        # Oben rechts: Grid (x=550, y=40)
        # Mitte: Haus (x=325, y=140)
        # Unten links: Batterie (x=100, y=180)
        
        # ===== KÄSTEN MIT ICONS =====
        
        # 1. PV KASTEN (Gelb)
        self._draw_box(draw, 30, 20, 170, 100, "#fbbf24", "#fbbf24")
        if 'pv' in self.icons:
            img.paste(self.icons['pv'], (70, 30), mask=self.icons['pv'])
        else:
            # Zeichne Sonne
            self._draw_sun(draw, 90, 55)
        draw.text((100, 105), f"▶ {int(self.pv_power)}W", fill="#fbbf24", anchor="mm")
        
        # 2. GRID KASTEN (Blau/Rot)
        grid_color = "#ef4444" if self.grid_power > 0 else "#38bdf8"
        self._draw_box(draw, 480, 20, 620, 100, grid_color, grid_color)
        if 'grid' in self.icons:
            img.paste(self.icons['grid'], (520, 30), mask=self.icons['grid'])
        else:
            # Zeichne Blitz
            self._draw_lightning(draw, 550, 55, grid_color)
        draw.text((550, 105), f"▶ {int(abs(self.grid_power))}W", fill=grid_color, anchor="mm")
        
        # 3. HAUS (Mitte)
        self._draw_box(draw, 270, 120, 380, 180, "#f472b6", "#f472b6")
        if 'house' in self.icons:
            img.paste(self.icons['house'], (285, 110), mask=self.icons['house'])
        else:
            # Zeichne Haus
            self._draw_house(draw, 325, 145)
        draw.text((325, 195), f"{int(self.load_power)}W", fill="#ffffff", anchor="mm", font=None)
        draw.text((325, 210), "Verbrauch", fill="#8ba2c7", anchor="mm")
        
        # 4. BATTERIE KASTEN (Orange)
        batt_color = "#f59e0b"
        self._draw_box(draw, 30, 180, 170, 260, batt_color, batt_color)
        if 'battery' in self.icons:
            img.paste(self.icons['battery'], (70, 190), mask=self.icons['battery'])
        else:
            # Zeichne Batterie
            self._draw_battery(draw, 100, 220, self.battery_soc)
        draw.text((100, 265), f"{int(self.battery_soc)}%", fill="#ffffff", anchor="mm")
        draw.text((100, 175), f"◀ {int(abs(self.battery_power))}W", fill=batt_color, anchor="mm")
        
        # ===== PFEILE MIT LEISTUNGSWERTEN =====
        
        # PV → Haus
        if self.pv_power > 10:
            self._draw_connection(draw, 170, 60, 270, 150, "#fbbf24", int(self.pv_power / 500) + 1)
        
        # Grid → Haus oder Haus → Grid
        if self.grid_power > 10:
            self._draw_connection(draw, 480, 60, 380, 150, "#ef4444", int(self.grid_power / 500) + 1)
        elif self.grid_power < -10:
            self._draw_connection(draw, 380, 150, 480, 60, "#38bdf8", int(abs(self.grid_power) / 500) + 1)
        
        # Batterie → Haus oder Haus → Batterie
        if self.battery_power > 10:  # Entladen
            self._draw_connection(draw, 170, 220, 270, 150, "#34d399", int(self.battery_power / 500) + 1)
        elif self.battery_power < -10:  # Laden
            self._draw_connection(draw, 270, 150, 170, 220, "#34d399", int(abs(self.battery_power) / 500) + 1)
        
        # Speichern als PhotoImage (RGBA → RGB für Tkinter)
        img_rgb = img.convert('RGB')
        self.photo_image = tk.PhotoImage(data=self._pil_to_ppm(img_rgb))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
    
    def _draw_box(self, draw, x1, y1, x2, y2, border_color, fill_color=None):
        """Zeichnet abgerundeten Kasten"""
        radius = 15
        
        # Hintergrund (schwarz mit Transparenz)
        if fill_color is None:
            fill_color = "#1f2937"
        else:
            fill_color = "#1f2937"  # Dunkler Hintergrund
        
        # Abgerundetes Rechteck
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill_color, outline=border_color, width=3)
    
    def _draw_connection(self, draw, x1, y1, x2, y2, color, width=2):
        """Zeichnet Verbindungslinie mit Pfeil"""
        import math
        
        # Linie
        draw.line([(x1, y1), (x2, y2)], fill=color, width=int(width))
        
        # Pfeilspitze
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_size = 12
        
        p1_x = x2 - arrow_size * math.cos(angle - math.pi / 6)
        p1_y = y2 - arrow_size * math.sin(angle - math.pi / 6)
        p2_x = x2 - arrow_size * math.cos(angle + math.pi / 6)
        p2_y = y2 - arrow_size * math.sin(angle + math.pi / 6)
        
        draw.polygon([(x2, y2), (p1_x, p1_y), (p2_x, p2_y)], fill=color)
    
    def _draw_sun(self, draw, x, y):
        """Zeichnet Sonne"""
        import math
        # Strahlen
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = x + 15 * math.cos(rad)
            y1 = y + 15 * math.sin(rad)
            x2 = x + 25 * math.cos(rad)
            y2 = y + 25 * math.sin(rad)
            draw.line([(x1, y1), (x2, y2)], fill="#fbbf24", width=2)
        # Kreis
        draw.ellipse([x-12, y-12, x+12, y+12], fill="#fbbf24")
    
    def _draw_lightning(self, draw, x, y, color):
        """Zeichnet Blitz"""
        points = [
            (x-6, y-15), (x-1, y-3), (x-10, y-1),
            (x, y+15), (x+6, y+3), (x, y-1), (x-6, y-15)
        ]
        draw.polygon(points, fill=color)
    
    def _draw_house(self, draw, x, y):
        """Zeichnet Haus"""
        # Körper
        draw.rectangle([x-20, y-10, x+20, y+20], fill="#f472b6")
        # Dach
        draw.polygon([(x-20, y-10), (x, y-25), (x+20, y-10)], fill="#c2410c")
        # Fenster
        draw.rectangle([x-12, y-5, x-5, y+2], fill="#1f2937")
        draw.rectangle([x+5, y-5, x+12, y+2], fill="#1f2937")
        # Tür
        draw.rectangle([x-5, y+5, x+5, y+18], fill="#1f2937")
    
    def _draw_battery(self, draw, x, y, soc):
        """Zeichnet Batterie mit Ladestand - Orange Stil"""
        # Äußeres Rechteck (Batterie-Körper)
        draw.rectangle([x-14, y-22, x+14, y+22], fill="#1f2937", outline="#f59e0b", width=3)
        
        # Batterie-Kopf (kleine Ausbuchtung oben)
        draw.rectangle([x-7, y-28, x+7, y-22], fill="#1f2937", outline="#f59e0b", width=3)
        
        # Innenfüllung basierend auf SOC
        fill_height = int(40 * (soc / 100))
        if soc < 20:
            fill_color = "#ef4444"  # Rot
        elif soc < 50:
            fill_color = "#f59e0b"  # Orange
        else:
            fill_color = "#34d399"  # Grün
        
        # Füllung von unten nach oben
        draw.rectangle([x-11, y+18-fill_height, x+11, y+18], fill=fill_color, outline=None)
    
    def _pil_to_ppm(self, img):
        """Konvertiert PIL Image zu PPM String für PhotoImage"""
        with io.BytesIO() as output:
            img.save(output, format="PPM")
            data = output.getvalue()
        return data.decode('latin-1')
    
    def update_flows(self, pv_power, load_power, battery_power, grid_power, battery_soc=None):
        """Aktualisiert Energiewerte"""
        self.pv_power = float(pv_power)
        self.load_power = float(load_power)
        self.battery_power = float(battery_power)
        self.grid_power = float(grid_power)
        if battery_soc is not None:
            self.battery_soc = float(max(0, min(100, battery_soc)))
        
        self._draw()
    
    def update_kwh_values(self, pv_kwh=0, grid_kwh=0, battery_kwh=0, load_kwh=0):
        """Aktualisiert kWh-Werte (Tagesertrag)"""
        self.pv_kwh = float(pv_kwh)
        self.grid_kwh = float(grid_kwh)
        self.battery_kwh = float(battery_kwh)
        self.load_kwh = float(load_kwh)
