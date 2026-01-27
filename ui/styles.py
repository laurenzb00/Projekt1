import tkinter as tk
import tkinter.font as tkfont
from ttkbootstrap import Style

# Farbpalette gemäß Vorgabe
COLOR_ROOT = "#070B12"       # Hintergrund/root
COLOR_HEADER = "#0B1220"     # Header/Notebook
COLOR_BG = COLOR_HEADER       # alias für bestehende Verwendungen
COLOR_CARD = "#111827"
COLOR_BORDER = "#1F2A3A"
COLOR_PRIMARY = "#3B82F6"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_INFO = "#38BDF8"
COLOR_DANGER = "#EF4444"
COLOR_TEXT = "#E5E7EB"
COLOR_SUBTEXT = "#94A3B8"

# Emoji support flag (set in init_style)
EMOJI_OK = True


def detect_emoji_support(root: tk.Misc) -> bool:
    """Checks if a known emoji font is available in Tk."""
    try:
        families = set(tkfont.families(root))
        emoji_fonts = [
            "Segoe UI Emoji",
            "Noto Color Emoji",
            "Apple Color Emoji",
            "Noto Emoji",
            "Symbola",
        ]
        return any(name in families for name in emoji_fonts)
    except Exception:
        return False


def emoji(text: str, fallback: str = "") -> str:
    """Always return emoji text; keep fallback for optional use elsewhere."""
    return text


def configure_styles(style: Style) -> None:
    """Applies notebook + button styles on an existing ttkbootstrap Style."""
    # Notebook (Tabs)
    nb = "TNotebook"
    style.configure(nb, background=COLOR_HEADER, borderwidth=0, padding=0)
    style.configure(
        "TNotebook.Tab",
        background=COLOR_HEADER,
        foreground=COLOR_SUBTEXT,
        padding=[14, 10],
        borderwidth=0
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLOR_PRIMARY)],
        foreground=[("selected", "#ffffff")]
    )

    # Toggle-like Buttons (touch-friendly height via padding)
    style.configure(
        "Card.TButton",
        background=COLOR_BORDER,
        foreground=COLOR_TEXT,
        borderwidth=0,
        padding=(14, 10),
    )
    style.map(
        "Card.TButton",
        background=[("active", COLOR_PRIMARY)],
        foreground=[("active", "#ffffff")]
    )


def init_style(root: tk.Tk) -> Style:
    """Initialisiert ttkbootstrap Styles, setzt Palette und ruft configure_styles."""
    style = Style(theme="darkly")
    root.configure(bg=COLOR_ROOT)
    global EMOJI_OK
    EMOJI_OK = detect_emoji_support(root)
    configure_styles(style)
    return style
