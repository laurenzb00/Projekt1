import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('dark_background')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk
import tkinter as tk
import os
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
import numpy as np
import matplotlib.ticker as mticker
from tkinter import StringVar

WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

FRONIUS_CSV = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
BMK_CSV = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")

UPDATE_INTERVAL = 60 * 1000  # 1 Minute in ms


class LivePlotApp:
    def __init__(self, root, fullscreen=True):
        self.root = root
        self.root.title("Live-Daten Visualisierung")
        self.root.geometry("1024x600")
        self.root.configure(bg="#222")  # Hintergrund dunkel
        self.root.resizable(False, False)

        # ---------- Styles ----------
        style = ttk.Style()
        style.theme_use("clam")

        # Notebook (Tabs)
        style.configure("TNotebook", background="#222", borderwidth=0)
        style.configure("TNotebook.Tab",
                        background="#333", foreground="white",
                        padding=[10, 5])
        style.map("TNotebook.Tab",
                  background=[("selected", "#555")],
                  foreground=[("selected", "white")])

        # Dark Frame
        style.configure("Dark.TFrame", background="#222")

        # Dark Label
        style.configure("Dark.TLabel", background="#222", foreground="white")

        # Buttons (ttk)
        style.configure("Dark.TButton",
                        background="#333", foreground="white",
                        padding=6, relief="flat")
        style.map("Dark.TButton",
                  background=[("active", "#555")],
                  foreground=[("active", "white")])

        # ---------- Notebook ----------
        self.notebook = ttk.Notebook(root, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Fronius Tab
        self.fronius_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.fronius_frame, text="Fronius")
        self.fronius_fig, self.fronius_ax = plt.subplots(figsize=(8, 3))
        self.fronius_ax2 = self.fronius_ax.twinx()
        self.fronius_canvas = FigureCanvasTkAgg(self.fronius_fig, master=self.fronius_frame)
        self.fronius_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # BMK Tab
        self.bmk_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.bmk_frame, text="Temperaturen 2 Tage")
        self.bmk_fig, self.bmk_ax = plt.subplots(figsize=(8, 3))
        self.bmk_canvas = FigureCanvasTkAgg(self.bmk_fig, master=self.bmk_frame)
        self.bmk_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # PV-Ertrag Tab
        self.pv_ertrag_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.pv_ertrag_frame, text="PV-Ertrag (Tage)")
        self.pv_ertrag_fig, self.pv_ertrag_ax = plt.subplots(figsize=(8, 3))
        self.pv_ertrag_canvas = FigureCanvasTkAgg(self.pv_ertrag_fig, master=self.pv_ertrag_frame)
        self.pv_ertrag_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Batterie Verlauf
        self.batt_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.batt_frame, text="Batterie Verlauf")
        self.batt_fig, self.batt_ax = plt.subplots(figsize=(8, 3))
        self.batt_canvas = FigureCanvasTkAgg(self.batt_fig, master=self.batt_frame)
        self.batt_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Zusammenfassung
        self.summary_frame = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.summary_frame, text="Zusammenfassung")
        self.summary_fig, self.summary_ax = plt.subplots(figsize=(8, 3))
        self.summary_canvas = FigureCanvasTkAgg(self.summary_fig, master=self.summary_frame)
        self.summary_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # ---------- Statuszeile ----------
        self.status_var = StringVar(value="Letztes Update: -")
        self.status_label = ttk.Label(self.root,
                                      textvariable=self.status_var,
                                      style="Dark.TLabel",
                                      anchor="w")
        self.status_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        # ---------- Button-Leiste ----------
        self.button_frame = ttk.Frame(root, style="Dark.TFrame")
        self.button_frame.pack(side=tk.BOTTOM, pady=10)

        self.close_button = ttk.Button(self.button_frame,
                                       text="Schließen",
                                       command=self.root.destroy,
                                       style="Dark.TButton")
        self.close_button.pack(side=tk.LEFT, padx=10)

        self.minimize_button = ttk.Button(self.button_frame,
                                          text="Minimieren",
                                          command=self.minimize_window,
                                          style="Dark.TButton")
        self.minimize_button.pack(side=tk.LEFT, padx=10)

        # ---------- Bilder ----------
        self.icons = {}
        self.offset_images_cache = {}
        for icon in ["temperature.png", "outdoor.png", "battery.png", "house.png", "power.png"]:
            path = os.path.join(WORKING_DIRECTORY, "icons", icon)
            if os.path.exists(path):
                self.icons[icon] = Image.open(path)
        bg_path = os.path.join(WORKING_DIRECTORY, "icons", "background.png")
        self.bg_img = Image.open(bg_path).resize((1024, 600), Image.LANCZOS) if os.path.exists(bg_path) else None

        self.update_plots()

    def new_method(self, icon):
        if not hasattr(self, "offset_images_cache"):
            self.offset_images_cache = {}
        if icon not in self.offset_images_cache:
            self.offset_images_cache[icon] = OffsetImage(np.array(self.icons[icon].convert("RGBA")), zoom=0.07)
        return self.offset_images_cache[icon]

    def update_plots(self):
        # 👉 Dein Plot-Code wie gehabt (unverändert von vorher)
        pass

    def minimize_window(self):
        self.root.iconify()
