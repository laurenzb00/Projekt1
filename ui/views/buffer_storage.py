import tkinter as tk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap, Normalize
from ui.styles import (
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_INFO,
    COLOR_DANGER,
)


class BufferStorageView(tk.Frame):
    """Modernes Matplotlib-Heatmap Widget für Pufferspeicher."""

    def __init__(self, parent: tk.Widget, height: int = 280):
        super().__init__(parent, bg=COLOR_CARD)
        self.height = height
        self.configure(height=self.height)
        self.pack_propagate(False)
        self.data = np.array([[60.0], [50.0], [40.0]])
        self._chip_boxes: list = []
        self._chip_stripes: list[Rectangle] = []
        self._last_temps: tuple[float, float, float] | None = None

        fig_width = 2.6
        fig_height = max(1.6, self.height / 100)
        self.fig, self.ax = plt.subplots(figsize=(fig_width, fig_height), dpi=100)
        self.fig.patch.set_facecolor(COLOR_CARD)
        self.ax.set_facecolor(COLOR_CARD)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.configure(width=int(fig_width * 100), height=int(fig_height * 100))
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        self._setup_plot()

    def resize(self, height: int):
        self.height = max(160, int(height))
        self.configure(height=self.height)
        fig_width = 2.6
        fig_height = max(1.6, self.height / 100)
        self.fig.set_size_inches(fig_width, fig_height, forward=True)
        self.canvas_widget.configure(width=int(fig_width * 100), height=int(fig_height * 100))
        self._setup_plot()
        self.canvas.draw_idle()

    def _setup_plot(self):
        # Clear axes to avoid stacked heatmaps
        self.fig.clear()
        self.fig.patch.set_facecolor(COLOR_CARD)

        gs = self.fig.add_gridspec(1, 2, width_ratios=[12, 1], wspace=0.15)
        self.ax = self.fig.add_subplot(gs[0, 0])
        self.cbar_ax = self.fig.add_subplot(gs[0, 1])
        self.ax.set_facecolor(COLOR_CARD)
        self.cbar_ax.set_facecolor(COLOR_CARD)

        for spine in ["right", "top", "bottom"]:
            self.ax.spines[spine].set_visible(False)
        self.ax.spines["left"].set_color(COLOR_BORDER)
        self.ax.spines["left"].set_linewidth(1)

        self.norm = Normalize(vmin=45, vmax=75)
        self.im = self.ax.imshow(
            self.data,
            aspect="auto",
            interpolation="gaussian",
            cmap=self._build_cmap(),
            norm=self.norm,
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([0, 1, 2])
        self.ax.set_yticklabels(["Top", "Mid", "Bottom"], color=COLOR_SUBTEXT, fontsize=10)

        self.overlay_texts = [self.ax.text(0, i, "", va="center", ha="center", color=COLOR_TEXT, fontsize=12) for i in range(3)]

        # Single colorbar axis
        self.cbar = self.fig.colorbar(self.im, cax=self.cbar_ax)
        self.cbar.set_label("°C", color=COLOR_SUBTEXT, fontsize=9)
        self.cbar.ax.yaxis.set_tick_params(color=COLOR_SUBTEXT, labelcolor=COLOR_SUBTEXT, labelsize=9)
        self.cbar.outline.set_edgecolor(COLOR_BORDER)
        self.cbar.set_ticks([45, 55, 65, 75])
        self.cbar.ax.set_facecolor(COLOR_CARD)

    def _build_cmap(self):
        colors = [COLOR_INFO, COLOR_WARNING, COLOR_DANGER]
        return LinearSegmentedColormap.from_list("buffer", colors, N=256)

    def _clear_chips(self):
        for patch in self._chip_boxes + self._chip_stripes:
            patch.remove()
        self._chip_boxes.clear()
        self._chip_stripes.clear()

    def update_temperatures(self, top: float, mid: float, bottom: float, kessel_c: float | None = None):
        temps = (top, mid, bottom)
        if self._last_temps == temps:
            return
        self._last_temps = temps
        self.data = np.array([[top], [mid], [bottom]])
        self.im.set_data(self.data)
        self.im.set_norm(self.norm)
        for i, t in enumerate(temps):
            self.overlay_texts[i].set_text(f"{t:.1f}°C")
            self.overlay_texts[i].set_color(COLOR_TEXT)
            self.overlay_texts[i].set_position((0, i))
        self.canvas.draw_idle()
