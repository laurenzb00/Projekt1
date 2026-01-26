import tkinter as tk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from ui.styles import COLOR_CARD, COLOR_BORDER, COLOR_TEXT, COLOR_SUBTEXT, COLOR_SUCCESS, COLOR_WARNING


class BufferStorageView(tk.Frame):
    """Modernes Matplotlib-Heatmap Widget für Pufferspeicher."""

    def __init__(self, parent: tk.Widget, height: int = 360):
        super().__init__(parent, bg=COLOR_CARD)
        self.height = height
        self.data = np.array([[60.0], [50.0], [40.0]])

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

    def _draw_chips(self, temps):
        # Chips rechts neben den Balken
        for i, t in enumerate(temps):
            # Hintergrund-FancyBox
            bbox = FancyBboxPatch(
                (1.1, i - 0.35),
                0.8,
                0.7,
                boxstyle="round,pad=0.15,rounding_size=0.12",
                linewidth=1,
                edgecolor=COLOR_BORDER,
                facecolor=self._chip_color(t),
                transform=self.ax.transData,
                clip_on=False,
                zorder=3,
            )
            self.ax.add_patch(bbox)
            self.chip_texts[i].set_text(f"{t:.0f} °C")
            self.chip_texts[i].set_color(COLOR_TEXT)
            self.chip_texts[i].set_position((1.5, i))

    def update_temperatures(self, top: float, mid: float, bottom: float):
        temps = [top, mid, bottom]
        self.data = np.array([[top], [mid], [bottom]])
        self.im.set_data(self.data)
        self._draw_chips(temps)
        self.canvas.draw_idle()
