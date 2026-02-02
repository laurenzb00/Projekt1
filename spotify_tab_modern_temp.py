"""
Spotify Tab Modern - Restored Version
Based on spotify_dashboard_modern.py with font safety fixes
"""
import logging
import threading
import queue
import os
import webbrowser
import time
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk, ImageDraw

logging.basicConfig(level=logging.WARNING)

from ui.styles import (
    COLOR_ROOT,
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    emoji,
    get_safe_font,
)

_UI_SCALE = float(os.getenv("UI_SCALING_EFFECTIVE") or os.getenv("UI_SCALING", "1.0"))
_BTN_SCALE = min(_UI_SCALE, 1.0)

def _s(val: float) -> int:
    return int(round(val * _UI_SCALE))

def _sb(val: float) -> int:
    return int(round(val * _BTN_SCALE))

def _font(family: str, size: int, style: str = "") -> tuple:
    """Safe font getter"""
    return get_safe_font(family, size, style)

from ui.components.card import Card

COLOR_DARK_BG = COLOR_ROOT
COLOR_CARD_BG = COLOR_CARD
COLOR_ACCENT = COLOR_BORDER


class SpotifyTab:
    """Spotify Tab - Minimal Working Version"""
    
    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True
        self.ready = False
        
        self.tab_frame = tk.Frame(self.notebook, bg=COLOR_DARK_BG)
        self.notebook.add(self.tab_frame, text=emoji("🎵 Spotify", "Spotify"))
        
        # Placeholder content
        info_frame = tk.Frame(self.tab_frame, bg=COLOR_DARK_BG)
        info_frame.pack(expand=True, fill=tk.BOTH)
        
        tk.Label(
            info_frame,
            text="Spotify Integration",
            font=_font("Arial", 18, "bold"),
            bg=COLOR_DARK_BG,
            fg=COLOR_PRIMARY
        ).pack(pady=20)
        
        tk.Label(
            info_frame,
            text="Module wird initialisiert...",
            font=_font("Arial", 12),
            bg=COLOR_DARK_BG,
            fg=COLOR_TEXT
        ).pack(pady=10)
        
        self.root.after(0, lambda: threading.Thread(target=self._init_oauth, daemon=True).start())
    
    def _init_oauth(self):
        """Dummy OAuth init to prevent crashes"""
        try:
            import spotifylogin
            self.ready = True
        except Exception as e:
            print(f"[SPOTIFY] OAuth init skipped: {e}")
    
    def stop(self):
        self.alive = False
