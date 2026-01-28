import tkinter as tk
import os
import csv
import time
from datetime import datetime, timedelta
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.patches import FancyBboxPatch, Ellipse, Rectangle
from matplotlib.colors import LinearSegmentedColormap, Normalize
from ui.styles import (
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    COLOR_TITLE,
    COLOR_WARNING,
    COLOR_INFO,
    COLOR_DANGER,
)


class BufferStorageView(tk.Frame):
    """Zylindrischer Pufferspeicher mit geclippter Heatmap + Sparkline."""

    def __init__(self, parent: tk.Widget, height: int = 280):
        super().__init__(parent, bg=COLOR_CARD)
        self._start_time = time.time()
        self.height = height
        self.configure(height=self.height)
        self.pack_propagate(False)
        self.data = np.array([[60.0], [50.0], [40.0]])
        self._last_temps: tuple[float, float, float] | None = None
        self._last_spark_update = 0

        self.layout = tk.Frame(self, bg=COLOR_CARD)
        self.layout.pack(fill=tk.BOTH, expand=True)
        self.layout.grid_columnconfigure(0, weight=1)
        self.layout.grid_columnconfigure(1, weight=0)
        self.layout.grid_rowconfigure(0, weight=1)
        self.layout.grid_rowconfigure(1, weight=0)

        self.plot_frame = tk.Frame(self.layout, bg=COLOR_CARD)
        self.plot_frame.grid(row=0, column=0, sticky="nsew")

        self.val_texts = []

        self.spark_frame = tk.Frame(self.layout, bg=COLOR_CARD)
        self.spark_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        tk.Label(self.spark_frame, text="Puffer (24h)", fg=COLOR_TITLE, bg=COLOR_CARD, font=("Segoe UI", 10)).pack(anchor="w")

        fig_width = 3.2
        fig_height = max(1.8, self.height / 100)
        self._create_figure(fig_width, fig_height)
        self._setup_plot()
        self._create_sparkline()

    def resize(self, height: int):
        """FIXED: Don't recreate figure on resize - just update container height."""
        elapsed = time.time() - self._start_time
        print(f"[BUFFER] resize() called at {elapsed:.3f}s with height={height}")
        
        old_height = self.height
        self.height = max(160, int(height))
        
        # Only reconfigure container height, don't recreate matplotlib figure
        self.configure(height=self.height)
        """Create matplotlib figure and canvas - only called once at init."""
        elapsed = time.time() - self._start_time
        print(f"[BUFFER] _create_figure() at {elapsed:.3f}s: {fig_width}x{fig_height}")
        
        if hasattr(self, "canvas_widget") and self.canvas_widget.winfo_exists():
            print(f"[BUFFER] WARNING: Destroying existing canvas at {elapsed:.3f}s")
        # Log but DON'T recreate the entire plot
        print(f"[BUFFER] Height changed from {old_height} to {self.height}, NOT recreating figure")
        
        # If you MUST resize the figure (e.g., very large change), do it sparingly:
        # if abs(self.height - old_height) > 50:
        #     print(f"[BUFFER] Large height change, recreating figure")
        #     fig_width = 2.6
        #     fig_height = max(1.6, self.height / 100)
        #     self._create_figure(fig_width, fig_height)
        #     self._setup_plot()
        #     self.canvas.draw_idle()

    def _create_figure(self, fig_width: float, fig_height: float):
        """Create matplotlib figure and canvas - only called once at init."""
        elapsed = time.time() - self._start_time
        print(f"[BUFFER] _create_figure() at {elapsed:.3f}s: {fig_width}x{fig_height}")
        
        if hasattr(self, "canvas_widget") and self.canvas_widget.winfo_exists():
            print(f"[BUFFER] WARNING: Destroying existing canvas at {elapsed:.3f}s")
            self.canvas_widget.destroy()
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=100)
        self.fig.patch.set_alpha(0)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("none")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.configure(width=int(fig_width * 100), height=int(fig_height * 100))
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

    def _setup_plot(self):
        """Setup plot elements - only called once at init or after explicit recreate."""
        elapsed = time.time() - self._start_time
        print(f"[BUFFER] _setup_plot() at {elapsed:.3f}s")
        
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_axis_off()
        self.ax.set_facecolor("none")

        self.norm = Normalize(vmin=45, vmax=75)
        
        # Pufferspeicher heatmap (left cylinder)
        self.im = self.ax.imshow(
            self.data,
            aspect="auto",
            interpolation="gaussian",
            cmap=self._build_cmap(),
            norm=self.norm,
            origin="lower",
            extent=[0.05, 0.35, 0.08, 0.92],
        )

        # Pufferspeicher cylinder shape
        puffer_cyl = FancyBboxPatch(
            (0.08, 0.08), 0.24, 0.84,
            boxstyle="round,pad=0.02,rounding_size=0.10",
            transform=self.ax.transAxes,
            linewidth=1.3,
            edgecolor="#2A3446",
            facecolor="none",
            alpha=0.75,
        )
        self.im.set_clip_path(puffer_cyl)
        self.ax.add_patch(puffer_cyl)

        puffer_top = Ellipse((0.20, 0.92), 0.24, 0.08, transform=self.ax.transAxes,
                  edgecolor="#2A3446", facecolor="none", linewidth=1.0, alpha=0.7)
        puffer_bottom = Ellipse((0.20, 0.08), 0.24, 0.08, transform=self.ax.transAxes,
                     edgecolor="#2A3446", facecolor="none", linewidth=1.0, alpha=0.7)
        self.ax.add_patch(puffer_top)
        self.ax.add_patch(puffer_bottom)

        # Highlight on Pufferspeicher
        hl = Rectangle((0.10, 0.10), 0.03, 0.80, transform=self.ax.transAxes,
                   facecolor="#ffffff", alpha=0.07, linewidth=0)
        self.ax.add_patch(hl)

        # Labels for Pufferspeicher zones
        self.ax.text(0.20, 0.98, "Pufferspeicher", transform=self.ax.transAxes, color=COLOR_TITLE, fontsize=12, va="top", ha="center", weight="bold")

        # Boiler cylinder (right, single color with better styling) - much smaller height (about half Pufferspeicher), on same baseline
        self.boiler_rect = FancyBboxPatch(
            (0.58, 0.08), 0.22, 0.45,
            boxstyle="round,pad=0.02,rounding_size=0.10",
            transform=self.ax.transAxes,
            linewidth=1.1,
            edgecolor="#2A3446",
            facecolor=self._temp_color(60),
            alpha=0.95,
        )
        self.ax.add_patch(self.boiler_rect)
        
        # Boiler caps
        self.boiler_top = Ellipse((0.69, 0.53), 0.22, 0.08, transform=self.ax.transAxes,
                                  edgecolor="#2A3446", facecolor="none", linewidth=1.0, alpha=0.7)
        self.boiler_bottom = Ellipse((0.69, 0.08), 0.22, 0.08, transform=self.ax.transAxes,
                                     edgecolor="#2A3446", facecolor="none", linewidth=1.0, alpha=0.7)
        self.ax.add_patch(self.boiler_top)
        self.ax.add_patch(self.boiler_bottom)
        
        # Highlight on Boiler
        boiler_hl = Rectangle((0.60, 0.10), 0.03, 0.41, transform=self.ax.transAxes,
                   facecolor="#ffffff", alpha=0.06, linewidth=0)
        self.ax.add_patch(boiler_hl)
        
        self.ax.text(0.69, 0.60, "Boiler", transform=self.ax.transAxes, color=COLOR_TITLE, fontsize=12, va="top", ha="center", weight="bold")
        
        # Add colorbar on the right
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        divider = make_axes_locatable(self.ax)
        cax = divider.append_axes("right", size="4%", pad=0.15)
        cbar = self.fig.colorbar(self.im, cax=cax, orientation='vertical')
        cbar.set_label('°C', rotation=0, labelpad=10, color=COLOR_TEXT, fontsize=9)
        cbar.ax.tick_params(labelsize=8, colors=COLOR_TEXT)
        cbar.outline.set_edgecolor(COLOR_BORDER)
        cbar.outline.set_linewidth(0.8)

    def _build_cmap(self):
        colors = [COLOR_INFO, COLOR_WARNING, COLOR_DANGER]
        return LinearSegmentedColormap.from_list("buffer", colors, N=256)
    
    def _temp_color(self, temp: float) -> str:
        rgba = self._build_cmap()(self.norm(temp))
        r, g, b = [int(255 * c) for c in rgba[:3]]
        return f"#{r:02x}{g:02x}{b:02x}"

    def update_temperatures(self, top: float, mid: float, bottom: float, kessel_c: float | None = None):
        """Update temperature display - uses draw_idle() to avoid blocking."""
        temps = (top, mid, bottom)
        if self._last_temps == temps:
            return
        
        elapsed = time.time() - self._start_time
        print(f"[BUFFER] update_temperatures() at {elapsed:.3f}s: {top:.1f}/{mid:.1f}/{bottom:.1f}")
        
        self._last_temps = temps
        vmin = min(temps) - 3
        vmax = max(temps) + 3
        self.norm = Normalize(vmin=vmin, vmax=vmax)

        self.data = self._build_stratified_data(top, mid, bottom)
        self.im.set_data(self.data)
        self.im.set_norm(self.norm)

        c_top = self._temp_color(top)
        c_mid = self._temp_color(mid)
        c_bot = self._temp_color(bottom)

        for t in self.val_texts:
            t.remove()
        self.val_texts = [
            self.ax.text(0.04, 0.85, f"{top:.1f}°C", transform=self.ax.transAxes, color=c_top, fontsize=9, va="center", ha="right", weight="bold"),
            self.ax.text(0.04, 0.50, f"{mid:.1f}°C", transform=self.ax.transAxes, color=c_mid, fontsize=10, va="center", ha="right", weight="bold"),
            self.ax.text(0.04, 0.15, f"{bottom:.1f}°C", transform=self.ax.transAxes, color=c_bot, fontsize=9, va="center", ha="right", weight="bold"),
        ]

        if kessel_c is not None:
            c_kessel = self._temp_color(kessel_c)
            self.boiler_rect.set_facecolor(c_kessel)
            # Add boiler temperature text - smaller and without outline
            if hasattr(self, 'boiler_temp_text'):
                self.boiler_temp_text.remove()
            if hasattr(self, 'boiler_temp_outline'):
                for outline_text in self.boiler_temp_outline:
                    outline_text.remove()
            self.boiler_temp_text = self.ax.text(0.69, 0.30, f"{kessel_c:.1f}°C", 
                transform=self.ax.transAxes, color="#FFFFFF", fontsize=8, 
                va="center", ha="center", weight="bold", zorder=100)
        
        self._update_sparkline()
        
        # Use draw_idle() to defer redraw and avoid blocking
        print(f"[BUFFER] Calling canvas.draw_idle() at {time.time() - self._start_time:.3f}s")
        self.canvas.draw_idle()

    def _build_stratified_data(self, top: float, mid: float, bottom: float) -> np.ndarray:
        # Build smooth vertical stratification (bottom->mid->top)
        h = 120
        y = np.linspace(0, 1, h)
        vals = np.zeros_like(y)
        # Bottom zone (0-0.33), Mid zone (0.33-0.66), Top zone (0.66-1)
        for i, t in enumerate(y):
            if t < 0.33:
                vals[i] = bottom + (mid - bottom) * (t / 0.33)
            elif t < 0.66:
                vals[i] = mid + (top - mid) * ((t - 0.33) / 0.33)
            else:
                vals[i] = top
        return vals.reshape(h, 1)

    def _create_sparkline(self):
        self.spark_fig = Figure(figsize=(3.4, 1.1), dpi=100)
        self.spark_fig.patch.set_alpha(0)
        self.spark_ax = self.spark_fig.add_subplot(111)
        self.spark_ax.set_facecolor("none")
        self.spark_canvas = FigureCanvasTkAgg(self.spark_fig, master=self.spark_frame)
        self.spark_canvas.get_tk_widget().pack(fill=tk.X, expand=False)

    def _update_sparkline(self):
        if (datetime.now().timestamp() - self._last_spark_update) < 60:
            return
        self._last_spark_update = datetime.now().timestamp()
        series = self._load_puffer_series(hours=24, bin_minutes=15)
        self.spark_ax.clear()
        self.spark_ax.set_axis_off()
        if series:
            xs, ys = zip(*series)
            self.spark_ax.plot(xs, ys, color=COLOR_WARNING, linewidth=1.3)
            self.spark_ax.scatter([xs[-1]], [ys[-1]], color=COLOR_WARNING, s=8)
        self.spark_canvas.draw_idle()

    def _load_puffer_series(self, hours: int = 24, bin_minutes: int = 15) -> list[tuple[datetime, float]]:
        path = self._data_path("Heizungstemperaturen.csv")
        if not os.path.exists(path):
            return []
        cutoff = datetime.now() - timedelta(hours=hours)
        lines = self._read_lines_safe(path)
        if len(lines) < 2:
            return []
        rows = []
        for line in lines[-800:]:
            line = line.strip()
            if not line or line.lower().startswith("zeit"):
                continue
            try:
                row = next(csv.reader([line]))
                ts = datetime.fromisoformat(row[0])
                if ts < cutoff:
                    continue
                mid = float(row[4])
                ts_bin = ts - timedelta(minutes=ts.minute % bin_minutes, seconds=ts.second, microseconds=ts.microsecond)
                rows.append((ts_bin, mid))
            except Exception:
                continue
        if not rows:
            return []
        agg = {}
        for ts, val in rows:
            s, c = agg.get(ts, (0.0, 0))
            agg[ts] = (s + val, c + 1)
        out = [(ts, s / c) for ts, (s, c) in sorted(agg.items())]
        smoothed = []
        for i in range(len(out)):
            w = out[max(0, i-1):min(len(out), i+2)]
            smoothed.append((out[i][0], sum(v for _, v in w) / len(w)))
        return smoothed

    @staticmethod
    def _data_path(filename: str) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, filename)

    @staticmethod
    def _read_lines_safe(path: str) -> list[str]:
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                return f.readlines()
        except Exception:
            return []
