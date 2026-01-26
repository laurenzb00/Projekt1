import tkinter as tk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from ui.styles import (
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_INFO,
)


class BufferStorageView(tk.Frame):
    """Modernes Matplotlib-Heatmap Widget für Pufferspeicher."""

    def __init__(self, parent: tk.Widget, height: int = 360):
        super().__init__(parent, bg=COLOR_CARD)
        self.height = height
        self.data = np.array([[60.0], [50.0], [40.0]])
        self._chip_boxes: list[FancyBboxPatch] = []
        self._chip_stripes: list[Rectangle] = []

        self.fig, self.ax = plt.subplots(figsize=(3.4, 3.6), dpi=100)
        self.fig.patch.set_facecolor(COLOR_CARD)
        self.ax.set_facecolor(COLOR_CARD)

        for spine in ["right", "top", "bottom"]:
            self.ax.spines[spine].set_visible(False)
        self.ax.spines["left"].set_color(COLOR_BORDER)
        self.ax.spines["left"].set_linewidth(1)

        self.im = self.ax.imshow(self.data, aspect="auto", interpolation="gaussian", cmap=self._build_cmap())
        self.ax.set_xticks([])
        self.ax.set_yticks([0, 1, 2])
        self.ax.set_yticklabels(["Top", "Mid", "Bottom"], color=COLOR_SUBTEXT, fontsize=10)

        self.chip_texts = [self.ax.text(0.5, i, "", va="center", ha="center", color=COLOR_TEXT, fontsize=12) for i in range(3)]

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        self._draw_chips([60, 50, 40])
        self.fig.tight_layout(pad=0.3)

    def _build_cmap(self):
        from matplotlib.colors import LinearSegmentedColormap

        colors = [COLOR_BORDER, COLOR_WARNING, COLOR_SUCCESS]
        return LinearSegmentedColormap.from_list("buffer", colors, N=256)

    def _chip_color(self, temp: float) -> str:
        if temp >= 60:
            return COLOR_SUCCESS
        if temp >= 45:
            return COLOR_WARNING
        return COLOR_BORDER

    def _clear_chips(self):
        for patch in self._chip_boxes + self._chip_stripes:
            patch.remove()
        self._chip_boxes.clear()
        self._chip_stripes.clear()

    def _draw_chips(self, temps):
        self._clear_chips()
        # Chips rechts neben den Balken, dezente Flächen mit schmalem Farbstreifen
        for i, t in enumerate(temps):
            face = COLOR_CARD
            stripe = self._chip_color(t)
            bbox = FancyBboxPatch(
                (1.05, i - 0.35),
                1.0,
                0.7,
                boxstyle="round,pad=0.18,rounding_size=0.14",
                linewidth=1,
                edgecolor=COLOR_BORDER,
                facecolor=face,
                transform=self.ax.transData,
                clip_on=False,
                zorder=2,
            )
            self.ax.add_patch(bbox)
            stripe_patch = Rectangle(
                (1.05, i - 0.35),
                0.08,
                0.7,
                linewidth=0,
                facecolor=stripe,
                transform=self.ax.transData,
                clip_on=False,
                zorder=3,
            )
            self.ax.add_patch(stripe_patch)
            self._chip_boxes.append(bbox)
            self._chip_stripes.append(stripe_patch)

            self.chip_texts[i].set_text(f"{t:.0f} °C")
            self.chip_texts[i].set_color(COLOR_TEXT)
            self.chip_texts[i].set_position((1.6, i))

    def update_temperatures(self, top: float, mid: float, bottom: float, kessel_c: float | None = None):
        temps = [top, mid, bottom]
        self.data = np.array([[top], [mid], [bottom]])
        self.im.set_data(self.data)
        self._draw_chips(temps)
        self.canvas.draw_idle()
