import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageTk
from ui.styles import (
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_TEXT,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_INFO,
    COLOR_DANGER,
)


class EnergyFlowView(tk.Frame):
    """PIL-basierter, flimmerfreier Energiefluss. Ein Canvas-Image pro Update."""

    def __init__(self, parent: tk.Widget, width: int = 620, height: int = 360):
        super().__init__(parent, bg=COLOR_CARD)
        self.canvas = tk.Canvas(self, width=width, height=height, highlightthickness=0, bg=COLOR_CARD)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.width = width
        self.height = height
        self.node_radius = 52
        self._tk_img = None
        self._font_big = ImageFont.truetype("arial.ttf", 32) if self._has_font("arial.ttf") else None
        self._font_small = ImageFont.truetype("arial.ttf", 14) if self._has_font("arial.ttf") else None

        self.nodes = self._define_nodes()
        self._base_img = self._render_background()
        self._canvas_img = self.canvas.create_image(0, 0, anchor="nw")

    def _has_font(self, name: str) -> bool:
        try:
            ImageFont.truetype(name, 12)
            return True
        except Exception:
            return False

    def _define_nodes(self):
        w, h = self.width, self.height
        margin_x = int(w * 0.06)
        margin_top = 36
        margin_bottom = 170  # Noch mehr Platz unten für Batterie/SOC
        usable_h = h - margin_top - margin_bottom
        return {
            "pv": (margin_x + int((w - 2 * margin_x) * 0.28), margin_top + int(usable_h * 0.05)),
            "grid": (w - margin_x - int((w - 2 * margin_x) * 0.28), margin_top + int(usable_h * 0.05)),
            "home": (w // 2, margin_top + int(usable_h * 0.42)),
            "battery": (w // 2, margin_top + int(usable_h * 0.96)),
        }

    def _render_background(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), COLOR_CARD)
        draw = ImageDraw.Draw(img)
        # Card border
        draw.rounded_rectangle([4, 4, self.width - 4, self.height - 4], radius=18, outline=COLOR_BORDER, width=2, fill=COLOR_CARD)
        for name, (x, y) in self.nodes.items():
            self._draw_node(draw, x, y, name)
        return img

    def _draw_node(self, draw: ImageDraw.ImageDraw, x: int, y: int, name: str):
        r = self.node_radius
        fill = COLOR_BORDER
        if name == "home":
            fill = COLOR_PRIMARY
        elif name == "pv":
            fill = COLOR_SUCCESS
        elif name == "grid":
            fill = COLOR_INFO
        elif name == "battery":
            fill = COLOR_WARNING
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=COLOR_CARD, width=3)
        label = {
            "pv": "PV",
            "grid": "GRID",
            "home": "HAUS",
            "battery": "BAT",
        }[name]
        self._text_center(draw, label, x, y, size=16)

    def _text_center(self, draw: ImageDraw.ImageDraw, text: str, x: int, y: int, size: int, color: str = COLOR_TEXT):
        font = self._font_big if size > 20 and self._font_big else ImageFont.load_default()
        if size <= 20:
            font = self._font_small if self._font_small else ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x - tw / 2, y - th / 2), text, font=font, fill=color)

    def _edge_points(self, src, dst, offset: float):
        x0, y0 = src
        x1, y1 = dst
        vx, vy = x1 - x0, y1 - y0
        length = max((vx ** 2 + vy ** 2) ** 0.5, 1e-3)
        ux, uy = vx / length, vy / length
        return (
            (x0 + ux * offset, y0 + uy * offset),
            (x1 - ux * offset, y1 - uy * offset),
        )

    def _draw_arrow(self, draw: ImageDraw.ImageDraw, src, dst, color: str, width: float):
        start, end = self._edge_points(src, dst, self.node_radius)
        x0, y0 = start
        x1, y1 = end
        draw.line((x0, y0, x1, y1), fill=color, width=int(width))
        # Arrow head
        vx, vy = x1 - x0, y1 - y0
        length = max((vx ** 2 + vy ** 2) ** 0.5, 1e-3)
        ux, uy = vx / length, vy / length
        size = 12 + width
        left = (x1 - ux * size + uy * size * 0.6, y1 - uy * size - ux * size * 0.6)
        right = (x1 - ux * size - uy * size * 0.6, y1 - uy * size + ux * size * 0.6)
        draw.polygon([left, right, (x1, y1)], fill=color)

    def _format_power(self, watts: float) -> str:
        if abs(watts) < 1000:
            return f"{watts:.0f} W"
        return f"{watts/1000:.2f} kW"

    def _draw_soc_ring(self, draw: ImageDraw.ImageDraw, center, soc: float):
        x, y = center
        r = self.node_radius + 10
        bbox = [x - r, y - r, x + r, y + r]
        extent = max(0, min(360, 360 * soc / 100))
        color = COLOR_SUCCESS if soc >= 70 else (COLOR_WARNING if soc >= 35 else COLOR_DANGER)
        draw.arc(bbox, start=-90, end=-90 + extent, fill=color, width=6)

    def render_frame(self, pv_w: float, load_w: float, grid_w: float, batt_w: float, soc: float) -> Image.Image:
        img = self._base_img.copy()
        draw = ImageDraw.Draw(img)

        pv = self.nodes["pv"]
        grid = self.nodes["grid"]
        home = self.nodes["home"]
        bat = self.nodes["battery"]

        def clamp(val, lo, hi):
            return max(lo, min(hi, val))

        def thickness(watts):
            return clamp(2 + abs(watts) / 1500, 2, 8)

        # PV -> Haus
        if pv_w > 0:
            self._draw_arrow(draw, pv, home, COLOR_SUCCESS, thickness(pv_w))

        # Grid Import/Export
        if grid_w > 0:
            self._draw_arrow(draw, grid, home, COLOR_INFO, thickness(grid_w))
        elif grid_w < 0:
            self._draw_arrow(draw, home, grid, COLOR_INFO, thickness(grid_w))

        # Batterie Laden/Entladen (batt_w > 0 = laden)
        if batt_w > 0:
            self._draw_arrow(draw, home, bat, COLOR_WARNING, thickness(batt_w))
        elif batt_w < 0:
            self._draw_arrow(draw, bat, home, COLOR_SUCCESS, thickness(batt_w))

        # SoC Ring um Batterie
        self._draw_soc_ring(draw, bat, soc)

        # Werte anzeigen mit Einheiten
        self._text_center(draw, f"PV {self._format_power(pv_w)}", pv[0], pv[1] + 70, size=16)
        self._text_center(draw, f"Netz {self._format_power(grid_w)}", grid[0], grid[1] + 70, size=16)
        self._text_center(draw, f"Haus {self._format_power(load_w)}", home[0], home[1] + 70, size=16)
        self._text_center(draw, f"Batt {self._format_power(batt_w)}", bat[0], bat[1] + 70, size=16)
        self._text_center(draw, f"SoC {soc:.0f}%", bat[0], bat[1] + 100, size=16)
        return img

    def update_flows(self, pv_w: float, load_w: float, grid_w: float, batt_w: float, soc: float):
        # Recompute layout if canvas size changed (keeps nodes centered)
        cw = max(200, self.canvas.winfo_width())
        ch = max(200, self.canvas.winfo_height())
        if cw != self.width or ch != self.height:
            self.width, self.height = cw, ch
            self.nodes = self._define_nodes()
            self._base_img = self._render_background()

        frame = self.render_frame(pv_w, load_w, grid_w, batt_w, soc)
        self._tk_img = ImageTk.PhotoImage(frame)
        self.canvas.itemconfig(self._canvas_img, image=self._tk_img)
