import tkinter as tk
from ttkbootstrap import Style

# Farbpalette
COLOR_BG = "#0b1220"
COLOR_CARD = "#111a2b"
COLOR_BORDER = "#1d2738"
COLOR_PRIMARY = "#3b82f6"
COLOR_SUCCESS = "#10b981"
COLOR_WARNING = "#f59e0b"
COLOR_INFO = "#38bdf8"
COLOR_DANGER = "#ef4444"
COLOR_TEXT = "#e5e7eb"
COLOR_SUBTEXT = "#94a3b8"


def init_style(root: tk.Tk) -> Style:
    """Initialisiert ttkbootstrap Styles und setzt Notebook/Buttons modern."""
    style = Style(theme="darkly")
    root.configure(bg=COLOR_BG)

    # Notebook (Tabs)
    nb = "TNotebook"
    style.configure(nb, background=COLOR_BG, borderwidth=0, padding=0)
    style.configure(
        "TNotebook.Tab",
        background=COLOR_BG,
        foreground=COLOR_SUBTEXT,
        padding=[14, 10],
        borderwidth=0
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLOR_PRIMARY)],
        foreground=[("selected", "#ffffff")]
    )

    # Toggle-like Buttons
    style.configure(
        "Card.TButton",
        background=COLOR_BORDER,
        foreground=COLOR_TEXT,
        borderwidth=0,
        padding=(12, 8)
    )
    style.map(
        "Card.TButton",
        background=[("active", COLOR_PRIMARY)],
        foreground=[("active", "#ffffff")]
    )
    return style
