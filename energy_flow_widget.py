"""
ENERGIEFLUSS SANKEY WIDGET
============================
Visualisiert den Energiefluss zwischen PV, Batterie, Haus und Netz
mit Plotly Sankey Diagramm oder PIL-Fallback
"""

import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageDraw, ImageTk
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import FancyArrowPatch

try:
    import plotly.graph_objects as go
    from plotly.io import to_image
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("⚠ Plotly nicht installiert. Nutze Matplotlib-Fallback.")

class EnergyFlowWidget:
    """Energiefluss-Visualisierung mit Sankey-Diagramm"""
    
    def __init__(self, parent, width=400, height=300, style="sankey"):
        """
        Args:
            parent: Tkinter parent widget
            width, height: Größe des Widgets
            style: "sankey" (Plotly), "matplotlib" (MPL Arrows), "simple" (Canvas)
        """
        self.parent = parent
        self.width = width
        self.height = height
        self.style = style if (PLOTLY_AVAILABLE or style != "sankey") else "matplotlib"
        
        # Standardwerte
        self.pv_power = 0.0
        self.load_power = 0.0
        self.battery_power = 0.0
        self.grid_power = 0.0
        
        # Frame für Widget
        self.frame = tk.Frame(parent, width=width, height=height, bg="#0f172a")
        self.frame.pack_propagate(False)
        self.frame.pack()
        
        # Je nach Stil erstellen
        if self.style == "sankey" and PLOTLY_AVAILABLE:
            self._create_plotly_sankey()
        elif self.style == "matplotlib":
            self._create_matplotlib_arrows()
        else:
            self._create_simple_canvas()
    
    def _create_plotly_sankey(self):
        """Erstellt Plotly Sankey Diagramm"""
        self.canvas = Canvas(self.frame, width=self.width, height=self.height, 
                            bg="#0f172a", highlightthickness=0)
        self.canvas.pack()
        
        # Placeholder - wird bei update_flows() gerendert
        self.canvas.create_text(
            self.width // 2, self.height // 2,
            text="Energiefluss\nInitialisiere...",
            fill="#8ba2c7", font=("Segoe UI", 12), justify="center"
        )
    
    def _create_matplotlib_arrows(self):
        """Erstellt Matplotlib Pfeile"""
        self.fig, self.ax = plt.subplots(figsize=(self.width/100, self.height/100), dpi=100)
        self.fig.patch.set_facecolor("#0f172a")
        self.ax.set_facecolor("#0f172a")
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)
        self.ax.axis('off')
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack()
        
        # Initial zeichnen
        self._draw_matplotlib()
    
    def _create_simple_canvas(self):
        """Erstellt einfaches Canvas mit Rechtecken"""
        self.canvas = Canvas(self.frame, width=self.width, height=self.height,
                            bg="#0f172a", highlightthickness=0)
        self.canvas.pack()
        
        # Initial zeichnen
        self._draw_simple()
    
    def _draw_matplotlib(self):
        """Zeichnet Matplotlib Energiefluss"""
        self.ax.clear()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)
        self.ax.axis('off')
        
        # Nodes (Kreise)
        nodes = {
            "PV": (2, 8, "#38bdf8"),
            "Batterie": (2, 2, "#34d399"),
            "Haus": (8, 5, "#f472b6"),
            "Netz": (8, 8, "#ef4444")
        }
        
        for name, (x, y, color) in nodes.items():
            circle = plt.Circle((x, y), 0.6, color=color, alpha=0.7, zorder=3)
            self.ax.add_patch(circle)
            self.ax.text(x, y, name, ha='center', va='center', 
                        fontsize=8, fontweight='bold', color='white', zorder=4)
        
        # Arrows (Pfeile mit variabler Breite)
        arrows = []
        
        # PV → Haus
        if self.pv_power > 0:
            width = min(5, max(1, self.pv_power / 500))  # 1-5 basierend auf kW
            arrow = FancyArrowPatch(
                (2.6, 7.5), (7.4, 5.5),
                arrowstyle='->', mutation_scale=20, linewidth=width,
                color="#38bdf8", alpha=0.6, zorder=2
            )
            self.ax.add_patch(arrow)
            mid_x, mid_y = (2.6 + 7.4) / 2, (7.5 + 5.5) / 2
            self.ax.text(mid_x, mid_y + 0.3, f"{self.pv_power:.1f}W", 
                        fontsize=7, color="#38bdf8", ha='center')
        
        # Batterie → Haus (Entladung) oder Haus → Batterie (Ladung)
        if self.battery_power != 0:
            if self.battery_power < 0:  # Entladen
                width = min(5, max(1, abs(self.battery_power) / 500))
                arrow = FancyArrowPatch(
                    (2.6, 2.5), (7.4, 4.5),
                    arrowstyle='->', mutation_scale=20, linewidth=width,
                    color="#34d399", alpha=0.6, zorder=2
                )
                label = f"{abs(self.battery_power):.1f}W"
            else:  # Laden
                width = min(5, max(1, self.battery_power / 500))
                arrow = FancyArrowPatch(
                    (7.4, 4.5), (2.6, 2.5),
                    arrowstyle='->', mutation_scale=20, linewidth=width,
                    color="#34d399", alpha=0.6, zorder=2
                )
                label = f"{self.battery_power:.1f}W"
            self.ax.add_patch(arrow)
            mid_x, mid_y = (2.6 + 7.4) / 2, (2.5 + 4.5) / 2
            self.ax.text(mid_x, mid_y - 0.3, label, 
                        fontsize=7, color="#34d399", ha='center')
        
        # Netz ↔ Haus
        if self.grid_power != 0:
            if self.grid_power > 0:  # Bezug
                width = min(5, max(1, self.grid_power / 500))
                arrow = FancyArrowPatch(
                    (8, 7.4), (8, 5.6),
                    arrowstyle='->', mutation_scale=20, linewidth=width,
                    color="#ef4444", alpha=0.6, zorder=2
                )
                label = f"{self.grid_power:.1f}W"
            else:  # Einspeisung
                width = min(5, max(1, abs(self.grid_power) / 500))
                arrow = FancyArrowPatch(
                    (8, 5.6), (8, 7.4),
                    arrowstyle='->', mutation_scale=20, linewidth=width,
                    color="#ef4444", alpha=0.6, zorder=2
                )
                label = f"{abs(self.grid_power):.1f}W"
            self.ax.add_patch(arrow)
            self.ax.text(8.5, 6.5, label, 
                        fontsize=7, color="#ef4444", ha='left')
        
        self.canvas.draw()
    
    def _draw_simple(self):
        """Zeichnet einfaches Canvas-Flussdiagramm"""
        self.canvas.delete("all")
        
        # Nodes
        nodes = {
            "PV": (80, 50, "#38bdf8"),
            "Batterie": (80, 250, "#34d399"),
            "Haus": (320, 150, "#f472b6"),
            "Netz": (320, 50, "#ef4444")
        }
        
        for name, (x, y, color) in nodes.items():
            # Kreis
            self.canvas.create_oval(
                x - 30, y - 30, x + 30, y + 30,
                fill=color, outline="white", width=2
            )
            self.canvas.create_text(
                x, y, text=name, fill="white",
                font=("Segoe UI", 10, "bold")
            )
        
        # Pfeile (vereinfacht)
        if self.pv_power > 0:
            self._draw_arrow(110, 70, 290, 130, "#38bdf8", f"{self.pv_power:.0f}W")
        
        if self.battery_power < 0:  # Entladung
            self._draw_arrow(110, 230, 290, 170, "#34d399", f"{abs(self.battery_power):.0f}W")
        elif self.battery_power > 0:  # Ladung
            self._draw_arrow(290, 170, 110, 230, "#34d399", f"{self.battery_power:.0f}W")
        
        if self.grid_power > 0:  # Bezug
            self._draw_arrow(320, 80, 320, 120, "#ef4444", f"{self.grid_power:.0f}W")
        elif self.grid_power < 0:  # Einspeisung
            self._draw_arrow(320, 120, 320, 80, "#ef4444", f"{abs(self.grid_power):.0f}W")
    
    def _draw_arrow(self, x1, y1, x2, y2, color, label):
        """Hilfsfunktion für Canvas-Pfeil"""
        self.canvas.create_line(
            x1, y1, x2, y2,
            arrow=tk.LAST, fill=color, width=3, arrowshape=(10, 12, 5)
        )
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        self.canvas.create_text(
            mid_x, mid_y - 10, text=label,
            fill=color, font=("Segoe UI", 8)
        )
    
    def update_flows(self, pv_power, load_power, battery_power, grid_power):
        """
        Aktualisiert die Energiefluss-Visualisierung
        
        Args:
            pv_power: PV-Erzeugung in W
            load_power: Hausverbrauch in W
            battery_power: Batterieleistung in W (positiv=laden, negativ=entladen)
            grid_power: Netzleistung in W (positiv=bezug, negativ=einspeisung)
        """
        self.pv_power = pv_power
        self.load_power = load_power
        self.battery_power = battery_power
        self.grid_power = grid_power
        
        if self.style == "sankey" and PLOTLY_AVAILABLE:
            self._update_plotly_sankey()
        elif self.style == "matplotlib":
            self._draw_matplotlib()
        else:
            self._draw_simple()
    
    def _update_plotly_sankey(self):
        """Aktualisiert Plotly Sankey mit neuen Werten"""
        # Nodes: 0=PV, 1=Batterie, 2=Haus, 3=Netz
        node_labels = ["PV", "Batterie", "Haus", "Netz"]
        node_colors = ["#38bdf8", "#34d399", "#f472b6", "#ef4444"]
        
        # Links definieren basierend auf Leistungsfluss
        sources = []
        targets = []
        values = []
        colors = []
        
        # PV → Haus (wenn PV vorhanden)
        if self.pv_power > 0:
            sources.append(0)  # PV
            targets.append(2)  # Haus
            values.append(self.pv_power)
            colors.append("rgba(56, 189, 248, 0.4)")
        
        # Batterie ↔ Haus
        if self.battery_power < 0:  # Entladung (Batterie → Haus)
            sources.append(1)  # Batterie
            targets.append(2)  # Haus
            values.append(abs(self.battery_power))
            colors.append("rgba(52, 211, 153, 0.4)")
        elif self.battery_power > 0:  # Ladung (Haus → Batterie)
            sources.append(2)  # Haus
            targets.append(1)  # Batterie
            values.append(self.battery_power)
            colors.append("rgba(52, 211, 153, 0.4)")
        
        # Netz ↔ Haus
        if self.grid_power > 0:  # Bezug (Netz → Haus)
            sources.append(3)  # Netz
            targets.append(2)  # Haus
            values.append(self.grid_power)
            colors.append("rgba(239, 68, 68, 0.4)")
        elif self.grid_power < 0:  # Einspeisung (Haus → Netz)
            sources.append(2)  # Haus
            targets.append(3)  # Netz
            values.append(abs(self.grid_power))
            colors.append("rgba(239, 68, 68, 0.4)")
        
        # Sankey erstellen
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="white", width=2),
                label=node_labels,
                color=node_colors
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=colors
            )
        )])
        
        fig.update_layout(
            title=dict(
                text="Energiefluss",
                font=dict(size=14, color="white")
            ),
            font=dict(size=10, color="white"),
            plot_bgcolor="#0f172a",
            paper_bgcolor="#0f172a",
            margin=dict(l=10, r=10, t=40, b=10),
            width=self.width,
            height=self.height
        )
        
        # Als PNG rendern und in Canvas einfügen
        try:
            img_bytes = to_image(fig, format="png", width=self.width, height=self.height)
            img = Image.open(io.BytesIO(img_bytes))
            self.photo = ImageTk.PhotoImage(img)
            
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        except Exception as e:
            print(f"Plotly Sankey Render-Fehler: {e}")
            # Fallback zu Text
            self.canvas.delete("all")
            self.canvas.create_text(
                self.width // 2, self.height // 2,
                text=f"PV: {self.pv_power:.0f}W\nVerbrauch: {self.load_power:.0f}W\n"
                     f"Batterie: {self.battery_power:.0f}W\nNetz: {self.grid_power:.0f}W",
                fill="white", font=("Segoe UI", 10), justify="center"
            )

# Demo
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Energy Flow Widget Demo")
    root.geometry("900x400")
    root.configure(bg="#0b1220")
    
    # Header
    header = tk.Label(root, text="Energiefluss Widget - 3 Stile im Vergleich", 
                     font=("Segoe UI", 16, "bold"), bg="#0b1220", fg="white")
    header.pack(pady=10)
    
    # Container für 3 Widgets
    container = tk.Frame(root, bg="#0b1220")
    container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 3 Spalten
    col1 = tk.Frame(container, bg="#0b1220")
    col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    tk.Label(col1, text="Matplotlib Arrows", font=("Segoe UI", 10, "bold"), 
            bg="#0b1220", fg="white").pack(pady=5)
    widget1 = EnergyFlowWidget(col1, width=280, height=280, style="matplotlib")
    
    col2 = tk.Frame(container, bg="#0b1220")
    col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    tk.Label(col2, text="Simple Canvas", font=("Segoe UI", 10, "bold"), 
            bg="#0b1220", fg="white").pack(pady=5)
    widget2 = EnergyFlowWidget(col2, width=280, height=280, style="simple")
    
    col3 = tk.Frame(container, bg="#0b1220")
    col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    style_name = "Plotly Sankey" if PLOTLY_AVAILABLE else "Matplotlib (Plotly fehlt)"
    tk.Label(col3, text=style_name, font=("Segoe UI", 10, "bold"), 
            bg="#0b1220", fg="white").pack(pady=5)
    widget3 = EnergyFlowWidget(col3, width=280, height=280, style="sankey")
    
    # Test-Daten
    def update_test():
        import random
        pv = random.uniform(1000, 5000)
        load = random.uniform(1500, 3000)
        battery = random.uniform(-1000, 1000)
        grid = load - pv - battery
        
        widget1.update_flows(pv, load, battery, grid)
        widget2.update_flows(pv, load, battery, grid)
        widget3.update_flows(pv, load, battery, grid)
        
        root.after(3000, update_test)
    
    update_test()
    
    root.mainloop()
