"""
MODERNER SPOTIFY TAB
====================
Features:
- Großes Album-Cover mit PIL (300x300)
- Glasmorphism Design
- Touch-optimierte Buttons
- Now Playing mit Gradient
- Moderne Animationen
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

# Only show warnings and errors in terminal
logging.basicConfig(level=logging.WARNING)

# --- FARBEN aus ui/styles ---
from ui.styles import (
    COLOR_ROOT,
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    emoji,
)
from ui.components.card import Card

# Aliases für alte Code-Kompatibilität
COLOR_DARK_BG = COLOR_ROOT
COLOR_CARD_BG = COLOR_CARD
COLOR_ACCENT = COLOR_BORDER

class SpotifyTab:
    """
    Moderner Spotify-Player mit Album-Art und Glass-Design
    """
    def _clear_tab(self):
        for w in self.tab_frame.winfo_children():
            w.destroy()

    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook

        self.alive = True
        self.ready = False
        self.sp = None
        self.oauth = None
        self.device_ids = []
        self.current_device_id = None
        self.image_queue = queue.Queue()
        self._ui_queue = queue.Queue()

        self._vol_after = None
        self._user_adjusting = False
        self._pre_mute_volume = 30
        self._last_volume_seen = None

        self.song_var = tk.StringVar(value="Spotify nicht verbunden")
        self.artist_var = tk.StringVar(value="")
        self.album_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="0:00 / 0:00")
        self.device_var = tk.StringVar(value="Kein Gerät")
        self.volume_var = tk.DoubleVar(value=50.0)
        self.volume_label_var = tk.StringVar(value="50%")
        self.search_entry_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.status_text_var = tk.StringVar(value="Initialisiere...")
        self.is_playing_var = tk.StringVar(value=emoji("⏸", "Pause"))

        self.result_cache = {}
        self.current_album_cover = None
        self._last_cover_url = None

        self.tab_frame = tk.Frame(self.notebook, bg=COLOR_DARK_BG)
        self.notebook.add(self.tab_frame, text=emoji(" 🎵 Spotify ", "Spotify"))

        self._build_prelogin_ui()
        threading.Thread(target=self._oauth_init_thread, daemon=True).start()

    def stop(self):
        self.alive = False

    def _build_player_bar(self):
        # Album-Cover
        self.cover_img = tk.Label(self.player_bar, width=96, height=96, bg=COLOR_CARD)
        self.cover_img.place(x=16, y=22)
        # Songinfos
        self.song_title = tk.Label(self.player_bar, text="Songtitel", font=("Segoe UI", 20, "bold"), fg="white", bg=COLOR_CARD, anchor="w")
        self.song_title.place(x=128, y=22)
        self.song_artist = tk.Label(self.player_bar, text="Interpret", font=("Segoe UI", 14), fg=COLOR_SUBTEXT, bg=COLOR_CARD, anchor="w")
        self.song_artist.place(x=128, y=56)
        # Fortschrittsbalken
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Scale(self.player_bar, from_=0, to=100, variable=self.progress_var, orient="horizontal", length=520, bootstyle="info")
        self.progress_bar.place(x=128, y=96, height=18)
        # Player-Buttons
        btn_y = 100
        btn_x = 700
        self.btn_prev = tk.Button(self.player_bar, text=emoji("⏮", "Prev"), font=("Segoe UI", 28), bg=COLOR_ACCENT, fg="white", activebackground=COLOR_PRIMARY, relief=tk.FLAT, width=3, height=2, command=self._on_prev)
        self.btn_prev.place(x=btn_x, y=btn_y)
        self.btn_play = tk.Button(self.player_bar, text=emoji("⏯", "Play/Pause"), font=("Segoe UI", 32, "bold"), bg=COLOR_PRIMARY, fg="white", activebackground=COLOR_SUCCESS, relief=tk.FLAT, width=4, height=2, command=self._on_play_pause)
        self.btn_play.place(x=btn_x+90, y=btn_y-6)
        self.btn_next = tk.Button(self.player_bar, text=emoji("⏭", "Next"), font=("Segoe UI", 28), bg=COLOR_ACCENT, fg="white", activebackground=COLOR_PRIMARY, relief=tk.FLAT, width=3, height=2, command=self._on_next)
        self.btn_next.place(x=btn_x+210, y=btn_y)
        # Geräteauswahl-Button
        self.device_btn = tk.Button(self.player_bar, text=emoji("🔊 Gerät: Wohnzimmer ▾", "Gerät"), font=("Segoe UI", 16, "bold"), bg=COLOR_CARD, fg=COLOR_PRIMARY, activebackground=COLOR_ACCENT, relief=tk.RAISED, width=18, height=2, command=self._toggle_device_panel)
        self.device_btn.place(x=900, y=22)
        # Inline-Gerätepanel (zunächst versteckt)
        self.device_panel = tk.Frame(self.player_bar, bg=COLOR_CARD, bd=2, relief=tk.RIDGE)
        self.device_panel.place(x=700, y=0, width=320, height=140)
        self.device_panel.lower()
        self.device_panel_visible = False
        self._build_device_panel()

    def _build_device_panel(self):
        for w in self.device_panel.winfo_children():
            w.destroy()
        tk.Label(self.device_panel, text="Gerät auswählen", font=("Segoe UI", 16, "bold"), fg=COLOR_PRIMARY, bg=COLOR_CARD).pack(pady=(10, 8))
        # Dummy-Geräteliste
        for i, name in enumerate(["Wohnzimmer", "Küche", "Bad"]):
            row = tk.Frame(self.device_panel, bg=COLOR_CARD, height=60)
            row.pack(fill=tk.X, padx=12, pady=2)
            icon = tk.Label(row, text=emoji("🔊", "Gerät"), font=("Segoe UI", 20), bg=COLOR_CARD)
            icon.pack(side=tk.LEFT, padx=8)
            tk.Label(row, text=name, font=("Segoe UI", 14), fg="white", bg=COLOR_CARD).pack(side=tk.LEFT, padx=8)
            if i == 0:
                tk.Label(row, text="✅", font=("Segoe UI", 18), fg=COLOR_SUCCESS, bg=COLOR_CARD).pack(side=tk.RIGHT, padx=8)
            row.bind("<Button-1>", lambda e, n=name: self._select_device(n))
        close_btn = tk.Button(self.device_panel, text="Schließen", font=("Segoe UI", 14, "bold"), bg=COLOR_ACCENT, fg="white", activebackground=COLOR_PRIMARY, relief=tk.FLAT, height=2, command=self._toggle_device_panel)
        close_btn.pack(fill=tk.X, padx=12, pady=(10, 8))

    def _toggle_device_panel(self):
        if self.device_panel_visible:
            self.device_panel.lower()
            self.device_panel_visible = False
        else:
            self.device_panel.lift()
            self.device_panel_visible = True

    def _select_device(self, name):
        # Hier: Gerät wechseln, Panel schließen
        self.device_btn.config(text=emoji(f"🔊 Gerät: {name} ▾", "Gerät"))
        self._toggle_device_panel()

    # --- Dummy-Callbacks ---
    def _on_home(self): pass
    def _on_playlists(self): pass
    def _on_favorites(self): pass
    def _on_downloads(self): pass
    def _on_prev(self): pass
    def _on_play_pause(self): pass
    def _on_next(self): pass
    def _create_card(self, parent, title=""):
        """Erstellt moderne Karte mit Glass-Look"""
        outer = tk.Frame(parent, bg="#0a0f1a")
        
        card = tk.Frame(
            outer,
            bg=COLOR_CARD_BG,
            relief=tk.FLAT,
            highlightbackground=COLOR_ACCENT,
            highlightthickness=1
        )
        card.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        if title:
            header = tk.Frame(card, bg="#142038")
            header.pack(fill=tk.X)
            tk.Label(
                header, text=title,
                font=("Segoe UI", 11, "bold"),
                bg="#142038", fg="white",
                pady=8, padx=12
            ).pack(anchor="w")
        
        return outer, card

    # ========== PRELOGIN UI ==========
    def _build_prelogin_ui(self, error_msg=None):
        self._clear_tab()
        wrapper = tk.Frame(self.tab_frame, bg=COLOR_DARK_BG)
        wrapper.pack(fill="both", expand=True)
        
        # Header
        header = tk.Frame(wrapper, bg=COLOR_DARK_BG)
        header.pack(fill="x", pady=(20, 10))
        
        tk.Label(
            header, text=emoji("🎵 Spotify", "Spotify"),
            font=("Segoe UI", 26, "bold"),
            fg="white", bg=COLOR_DARK_BG
        ).pack(side=tk.LEFT, padx=20)
        
        tk.Label(
            header, textvariable=self.status_text_var,
            font=("Segoe UI", 10),
            fg=COLOR_SUBTEXT, bg=COLOR_DARK_BG
        ).pack(side=tk.RIGHT, padx=20)
        
        # Info Card
        outer, card = self._create_card(wrapper, "Anmeldung erforderlich")
        outer.pack(fill="both", expand=True, padx=20, pady=20)
        
        info = tk.Frame(card, bg=COLOR_CARD_BG)
        info.pack(expand=True, pady=40)
        
        msg = "Noch nicht angemeldet."
        if error_msg:
            msg = f"Login Fehler:\n{error_msg}"
        
        tk.Label(
            info, text=msg,
            font=("Segoe UI", 12),
            fg=COLOR_TEXT, bg=COLOR_CARD_BG,
            justify="center"
        ).pack(pady=15)
        
        # Login-URL erzeugen
        login_url = None
        if self.oauth:
            try:
                login_url = self.oauth.get_authorize_url()
            except Exception:
                login_url = None

        # Login Button (modern)
        btn = tk.Button(
            info,
            text=emoji("🔐 Login im Browser", "Login im Browser"),
            font=("Segoe UI", 12, "bold"),
            bg=COLOR_SUCCESS, fg="white",
            activebackground="#059669",
            relief=tk.FLAT,
            cursor="hand2",
            padx=30, pady=12,
            command=self._open_login_in_browser
        )
        btn.pack(pady=10)

        # Login-Link anzeigen
        if login_url:
            link_label = tk.Entry(info, width=60, font=("Segoe UI", 10), fg="#2563eb", bg=COLOR_CARD_BG, borderwidth=0, relief=tk.FLAT)
            link_label.insert(0, login_url)
            link_label.config(state="readonly")
            link_label.pack(pady=(5, 0))

            def copy_link():
                self.root.clipboard_clear()
                self.root.clipboard_append(login_url)
                self.root.update()
                self.status_text_var.set("Link kopiert!")

            copy_btn = tk.Button(
                info,
                text=emoji("📋 Link kopieren", "Link kopieren"),
                font=("Segoe UI", 10),
                bg="#2563eb", fg="white",
                activebackground="#1e40af",
                relief=tk.FLAT,
                cursor="hand2",
                command=copy_link
            )
            copy_btn.pack(pady=(2, 10))

        tk.Label(
            info, text="Nach dem Login bleibt der Token gespeichert.",
            font=("Segoe UI", 9),
            fg=COLOR_SUBTEXT, bg=COLOR_CARD_BG
        ).pack()

    # ========== HAUPT UI ==========
    def _build_ui(self):
        self._clear_tab()
        main = tk.Frame(self.tab_frame, bg=COLOR_DARK_BG)
        main.pack(fill="both", expand=True)
        
        # Header mit Status
        self._build_header(main)
        
        # Content Container
        content = tk.Frame(main, bg=COLOR_DARK_BG)
        content.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        # 2 Spalten: Links Cover+Info, Rechts Controls
        content.grid_columnconfigure(0, weight=1, minsize=360)
        content.grid_columnconfigure(1, weight=2, minsize=600)
        content.grid_rowconfigure(0, weight=1)
        
        # === LINKS: NOW PLAYING ===
        self._build_now_playing_section(content)
        
        # === RECHTS: CONTROLS ===
        self._build_controls_section(content)

    def _build_header(self, parent):
        """Moderner Header mit Gradient-Effekt"""
        header = tk.Frame(parent, bg=COLOR_PRIMARY, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Titel
        tk.Label(
            header, text=emoji("🎵 Spotify Player", "Spotify Player"),
            font=("Segoe UI", 24, "bold"),
            fg="white", bg=COLOR_PRIMARY
        ).pack(side=tk.LEFT, padx=20, pady=15)
        
        # Status + Play Icon
        status_frame = tk.Frame(header, bg=COLOR_PRIMARY)
        status_frame.pack(side=tk.RIGHT, padx=20)
        
        tk.Label(
            status_frame, textvariable=self.is_playing_var,
            font=("Segoe UI", 28),
            fg="white", bg=COLOR_PRIMARY
        ).pack(side=tk.RIGHT, padx=10)
        
        tk.Label(
            status_frame, textvariable=self.status_text_var,
            font=("Segoe UI", 11),
            fg="#dbeafe", bg=COLOR_PRIMARY
        ).pack(side=tk.RIGHT)

    def _build_now_playing_section(self, parent):
        """Now Playing mit großem Album-Cover"""
        outer, card = self._create_card(parent, "")
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)
        
        # Album Cover (groß)
        self.album_img_label = tk.Label(
            card,
            text=emoji("🎵", "ALBUM"),
            font=("Segoe UI", 64),
            bg=COLOR_CARD_BG,
            fg=COLOR_SUBTEXT,
            relief=tk.FLAT
        )
        self.album_img_label.pack(pady=(20, 15), padx=20)
        
        # Song Info mit Gradient-Hintergrund
        info_gradient = tk.Frame(card, bg=COLOR_PRIMARY, height=140)
        info_gradient.pack(fill="x", padx=0, pady=0)
        info_gradient.pack_propagate(False)
        
        info_inner = tk.Frame(info_gradient, bg=COLOR_PRIMARY)
        info_inner.pack(expand=True, fill="both", padx=20, pady=15)
        
        # Song Title
        tk.Label(
            info_inner,
            textvariable=self.song_var,
            font=("Segoe UI", 16, "bold"),
            fg="white", bg=COLOR_PRIMARY,
            wraplength=280,
            justify="center"
        ).pack(pady=(5, 2))
        
        # Artist
        tk.Label(
            info_inner,
            textvariable=self.artist_var,
            font=("Segoe UI", 12),
            fg="#dbeafe", bg=COLOR_PRIMARY,
            wraplength=280,
            justify="center"
        ).pack(pady=2)
        
        # Album
        tk.Label(
            info_inner,
            textvariable=self.album_var,
            font=("Segoe UI", 9),
            fg="#93c5fd", bg=COLOR_PRIMARY,
            wraplength=280,
            justify="center"
        ).pack(pady=(2, 5))
        
        # Progress Bar (modern)
        progress_frame = tk.Frame(card, bg=COLOR_CARD_BG)
        progress_frame.pack(fill="x", padx=20, pady=(15, 20))
        
        # Custom Progress Bar
        self.progress_canvas = tk.Canvas(
            progress_frame,
            height=8,
            bg="#1e293b",
            highlightthickness=0
        )
        self.progress_canvas.pack(fill="x", pady=(0, 8))
        
        # Time Labels
        tk.Label(
            progress_frame,
            textvariable=self.progress_text_var,
            font=("Segoe UI", 9),
            fg=COLOR_SUBTEXT, bg=COLOR_CARD_BG
        ).pack()

    def _build_controls_section(self, parent):
        """Control Panel mit Buttons, Devices, Suche"""
        right_container = tk.Frame(parent, bg=COLOR_DARK_BG)
        right_container.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)
        
        # === 1. PLAYBACK CONTROLS ===
        outer1, card1 = self._create_card(right_container, "Wiedergabe")
        outer1.pack(fill="x", pady=(0, 12))
        
        ctrl = tk.Frame(card1, bg=COLOR_CARD_BG)
        ctrl.pack(pady=20)
        
        # Button Style Helper
        def create_control_btn(parent, text, cmd, width=12, primary=False):
            bg = COLOR_PRIMARY if primary else COLOR_ACCENT
            active_bg = "#0284c7" if primary else "#2d3a5f"
            return tk.Button(
                parent, text=text,
                font=("Segoe UI", 18, "bold"),
                bg=bg, fg="white",
                activebackground=active_bg,
                relief=tk.FLAT,
                cursor="hand2",
                width=width,
                height=2,
                padx=16, pady=12,
                command=cmd
            )
        
        # Button Row (Touch-optimiert, große Buttons)
        btn_row = tk.Frame(ctrl, bg=COLOR_CARD_BG)
        btn_row.pack(pady=18)
        create_control_btn(btn_row, emoji("⏮", "Prev"), self.prev_track, 6).pack(side=tk.LEFT, padx=18)
        create_control_btn(btn_row, emoji("▶ / ⏸", "Play/Pause"), self.play_pause, 16, True).pack(side=tk.LEFT, padx=18)
        create_control_btn(btn_row, emoji("⏭", "Next"), self.next_track, 6).pack(side=tk.LEFT, padx=18)
        
        # Secondary Controls (Touch-optimiert)
        btn_row2 = tk.Frame(ctrl, bg=COLOR_CARD_BG)
        btn_row2.pack(pady=14)
        create_control_btn(btn_row2, emoji("🔀 Shuffle", "Shuffle"), self.set_shuffle, 12).pack(side=tk.LEFT, padx=12)
        create_control_btn(btn_row2, emoji("🔁 Repeat", "Repeat"), self.set_repeat, 12).pack(side=tk.LEFT, padx=12)
        
        # === 2. LAUTSTÄRKE ===
        outer2, card2 = self._create_card(right_container, "Lautstärke")
        outer2.pack(fill="x", pady=(0, 12))
        
        vol_inner = tk.Frame(card2, bg=COLOR_CARD_BG)
        vol_inner.pack(fill="x", padx=20, pady=15)
        
        # Mute Button (Touch-optimiert)
        mute_btn = create_control_btn(vol_inner, emoji("🔇", "Mute"), self.toggle_mute, 6)
        mute_btn.pack(side=tk.LEFT, padx=(0, 20))

        # Lautstärke Minus Button
        vol_minus = create_control_btn(vol_inner, "-", lambda: self._on_volume_btn(-5), 4)
        vol_minus.pack(side=tk.LEFT, padx=(0, 8))

        # Slider (Touch-optimiert, dicker)
        style = ttk.Style()
        style.configure("TScale", thickness=32)
        vol_slider = ttk.Scale(
            vol_inner,
            from_=0, to=100,
            variable=self.volume_var,
            command=self._on_volume_slide,
            style="TScale"
        )
        vol_slider.pack(side=tk.LEFT, fill="x", expand=True, padx=10, ipadx=20)

        # Lautstärke Plus Button
        vol_plus = create_control_btn(vol_inner, "+", lambda: self._on_volume_btn(5), 4)
        vol_plus.pack(side=tk.LEFT, padx=(8, 0))

        # Volume Label (größer)
        tk.Label(
            vol_inner,
            textvariable=self.volume_label_var,
            font=("Segoe UI", 16, "bold"),
            fg="white", bg=COLOR_CARD_BG,
            width=6
        ).pack(side=tk.RIGHT, padx=(12, 0))
        
        # === 3. GERÄTE ===
        outer3, card3 = self._create_card(right_container, "Gerät")
        outer3.pack(fill="x", pady=(0, 12))
        
        dev_inner = tk.Frame(card3, bg=COLOR_CARD_BG)
        dev_inner.pack(fill="x", padx=20, pady=15)
        
        # Geräteauswahl (Touch-optimiert, große Combobox)
        self.device_box = ttk.Combobox(
            dev_inner,
            textvariable=self.device_var,
            state="readonly",
            font=("Segoe UI", 16),
            height=3
        )
        self.device_box.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 18), ipadx=12, ipady=8)
        self.device_box.bind("<<ComboboxSelected>>", self.set_device)

        create_control_btn(dev_inner, "✓ Setzen", self.set_device, 10).pack(side=tk.RIGHT, padx=(12, 0))
        
        # === 4. SUCHE ===
        outer4, card4 = self._create_card(right_container, "Suche")
        outer4.pack(fill="both", expand=True, pady=(0, 0))
        
        search_inner = tk.Frame(card4, bg=COLOR_CARD_BG)
        search_inner.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Search Entry
        search_row = tk.Frame(search_inner, bg=COLOR_CARD_BG)
        search_row.pack(fill="x", pady=(0, 12))
        
        # Suchfeld (Touch-optimiert)
        search_entry = ttk.Entry(
            search_row,
            textvariable=self.search_entry_var,
            font=("Segoe UI", 16)
        )
        search_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 18), ipadx=12, ipady=8)
        search_entry.bind("<Return>", lambda e: self.do_search())

        create_control_btn(search_row, emoji("🔍 Suchen", "Suchen"), self.do_search, 14, True).pack(side=tk.RIGHT, padx=(12, 0))
        
        # Results
        result_row = tk.Frame(search_inner, bg=COLOR_CARD_BG)
        result_row.pack(fill="x")
        
        # Ergebnisliste (Touch-optimiert)
        self.result_box = ttk.Combobox(
            result_row,
            textvariable=self.search_var,
            state="readonly",
            font=("Segoe UI", 16),
            height=3
        )
        self.result_box.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 18), ipadx=12, ipady=8)
        self.result_box.bind("<<ComboboxSelected>>", self.play_selected)

        create_control_btn(result_row, emoji("▶ Starten", "Starten"), self.play_selected, 12, True).pack(side=tk.RIGHT, padx=(12, 0))
    def _on_volume_btn(self, delta):
        v = self.volume_var.get() + delta
        v = max(0, min(100, v))
        self.volume_var.set(v)
        self._on_volume_slide(None)

    # ========== OAUTH FLOW ==========
    def _oauth_init_thread(self):
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
            cache_path = os.path.join(os.path.abspath(os.getcwd()), ".cache-spotify")
            self.oauth = SpotifyOAuth(
                client_id="8cff12b3245a4e4088d5751360f62705",
                client_secret="af9ecfa466504d7795416a3f2c66f5c5",
                redirect_uri="http://127.0.0.1:8888/callback",
                scope="user-read-currently-playing user-modify-playback-state user-read-playback-state",
                cache_path=cache_path,
                open_browser=True,
                show_dialog=True,  # Dialog immer zeigen, damit manuelle Eingabe möglich ist
                requests_timeout=10,
            )
            token_info = self.oauth.get_cached_token()
            if token_info:
                # Configure spotipy with increased timeout
                self.sp = spotipy.Spotify(auth_manager=self.oauth, requests_timeout=10)
                self.ready = True
                self._ui_call(self._build_ui)
                self._ui_call(self.status_text_var.set, "Verbunden")
                self._ui_call(self.update_spotify)
                return
            # OAuth ist jetzt initialisiert, UI mit Link neu bauen
            import logging
            logging.warning("SpotifyTab: OAuth initialisiert, baue Login-UI mit Link.")
            self._ui_call(self.status_text_var.set, "Login-Link bereit")
            self._ui_call(self._build_prelogin_ui)
        except Exception as e:
            self._ui_call(self._build_prelogin_ui, str(e))

    def _open_login_in_browser(self):
        if not self.oauth:
            return
        def browser_and_token():
            try:
                url = self.oauth.get_authorize_url()
                try:
                    webbrowser.get("chromium-browser").open_new(url)
                except Exception:
                    webbrowser.open_new(url)
                self.root.after(0, lambda: self.status_text_var.set("Browser geöffnet..."))
                self._wait_for_token_thread()
            except Exception as e:
                self.root.after(0, lambda err=e: self.status_text_var.set(f"Fehler: {err}"))
        threading.Thread(target=browser_and_token, daemon=True).start()

    def _wait_for_token_thread(self):
        try:
            token_info = None
            try:
                token_info = self.oauth.get_access_token(as_dict=True)
            except Exception as e:
                # Fallback: Manuelle Code-Eingabe anbieten
                self._ui_call(self._build_manual_code_ui)
                return
            if token_info and token_info.get("access_token"):
                import spotipy
                self.sp = spotipy.Spotify(auth_manager=self.oauth, requests_timeout=10)
                self.ready = True
                self._ui_call(self._build_ui)
                self._ui_call(self.status_text_var.set, "Verbunden")
                self._ui_call(self.update_spotify)
        except Exception as e:
            self._ui_call(self._build_prelogin_ui, str(e))

    def _build_manual_code_ui(self):
        self._clear_tab()
        wrapper = tk.Frame(self.tab_frame, bg=COLOR_DARK_BG)
        wrapper.pack(fill="both", expand=True)
        tk.Label(wrapper, text="Spotify Login - Manuelle Code-Eingabe", font=("Segoe UI", 18, "bold"), fg="white", bg=COLOR_DARK_BG).pack(pady=20)
        tk.Label(wrapper, text="Bitte öffne den Link im Browser, logge dich ein und kopiere den Code hierher:", font=("Segoe UI", 12), fg=COLOR_TEXT, bg=COLOR_DARK_BG).pack(pady=10)
        url = self.oauth.get_authorize_url()
        url_entry = tk.Entry(wrapper, width=80, font=("Segoe UI", 10), fg="#2563eb", bg=COLOR_CARD_BG, borderwidth=0, relief=tk.FLAT)
        url_entry.insert(0, url)
        url_entry.config(state="readonly")
        url_entry.pack(pady=(5, 0))
        code_var = tk.StringVar()
        code_entry = tk.Entry(wrapper, textvariable=code_var, width=60, font=("Segoe UI", 12))
        code_entry.pack(pady=20)
        def submit_code():
            code = code_var.get().strip()
            if not code:
                return
            try:
                token_info = self.oauth.get_access_token(code, as_dict=True)
                if token_info and token_info.get("access_token"):
                    import spotipy
                    self.sp = spotipy.Spotify(auth_manager=self.oauth, requests_timeout=10)
                    self.ready = True
                    self._build_ui()
                    self.status_text_var.set("Verbunden")
                    self.update_spotify()
            except Exception as e:
                self.status_text_var.set(f"Fehler: {e}")
        tk.Button(wrapper, text="Code einreichen", font=("Segoe UI", 12, "bold"), bg=COLOR_SUCCESS, fg="white", command=submit_code).pack(pady=10)

    # ========== DEVICE MANAGEMENT ==========
    def _update_devices(self):
        if not self.sp: return
        try:
            devices = self.sp.devices().get("devices", [])
            names = [f"{d.get('name','?')} ({d.get('type','?')})" for d in devices]
            ids = [d.get("id") for d in devices]
            self.device_ids = ids
            self.device_box["values"] = names
            try:
                pb = self.sp.current_playback()
                active_id = (pb or {}).get("device", {}).get("id")
                if active_id:
                    self.current_device_id = active_id
                    if active_id in ids:
                        self.device_var.set(names[ids.index(active_id)])
            except: pass
            if not self.device_var.get() and names: self.device_var.set(names[0])
        except: pass

    def set_device(self, event=None):
        idx = self.device_box.current()
        if 0 <= idx < len(self.device_ids):
            self.current_device_id = self.device_ids[idx]
            try: self.sp.transfer_playback(self.current_device_id, force_play=True)
            except: pass

    # ========== ALBUM ART ==========
    def fetch_cover(self, img_url):
        """Lädt Album-Cover mit PIL und erstellt rounded corners"""
        try:
            import requests, io
            
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(img_url, timeout=8, headers=headers)
            resp.raise_for_status()
            pil_img = Image.open(io.BytesIO(resp.content))
            pil_img.load()
            
            # Simple resize (legacy style)
            pil_img = pil_img.resize((220, 220), Image.Resampling.LANCZOS)
            pil_img = pil_img.convert("RGB")
            self.image_queue.put(pil_img)
        except Exception as e:
            print(f"Cover Fehler: {e}")
            self.image_queue.put(None)

    # ========== UPDATE LOOP ==========
    def update_spotify(self):
        if not self.alive or not self.ready: return
        try:
            # Add timeout to prevent blocking and memory corruption
            import requests
            pb = None
            try:
                pb = self.sp.current_playback()
            except requests.exceptions.Timeout:
                print(f"Spotify Update: Timeout (retry in 3s)")
                if self.alive: self.root.after(3000, self.update_spotify)
                return
            except requests.exceptions.RequestException as e:
                print(f"Spotify Update: Connection error: {e}")
                if self.alive: self.root.after(5000, self.update_spotify)
                return
            
            if pb and pb.get("item"):
                item = pb["item"]
                
                # Song Info
                name = item.get("name", "?")
                artist = item.get("artists", [{}])[0].get("name", "?")
                album = item.get("album", {}).get("name", "?")
                
                self.song_var.set(name)
                self.artist_var.set(artist)
                self.album_var.set(album)
                
                # Playing Status
                is_playing = pb.get("is_playing", False)
                self.is_playing_var.set(emoji("▶", "Play") if is_playing else emoji("⏸", "Pause"))
                
                # Cover
                imgs = item.get("album", {}).get("images", [])
                if imgs:
                    # Use the largest image for better quality
                    imgs_sorted = sorted(imgs, key=lambda i: i.get("width") or 0, reverse=True)
                    cover_url = imgs_sorted[0].get("url")
                    if cover_url and cover_url != self._last_cover_url:
                        self._last_cover_url = cover_url
                        threading.Thread(target=self.fetch_cover, args=(cover_url,), daemon=True).start()
                
                # Progress
                dur = item.get("duration_ms", 1)
                prog = pb.get("progress_ms", 0)
                
                if dur > 0:
                    percent = (prog / dur) * 100
                    self.progress_var.set(percent)
                    
                    # Draw custom progress bar
                    try:
                        w = self.progress_canvas.winfo_width()
                        h = self.progress_canvas.winfo_height()
                        if w > 1:
                            self.progress_canvas.delete("all")
                            # Background
                            self.progress_canvas.create_rectangle(0, 0, w, h, fill="#1e293b", outline="")
                            # Progress
                            prog_w = int((percent / 100) * w)
                            self.progress_canvas.create_rectangle(0, 0, prog_w, h, fill=COLOR_PRIMARY, outline="")
                    except:
                        pass
                    
                    # Time text
                    prog_sec = int(prog / 1000)
                    dur_sec = int(dur / 1000)
                    self.progress_text_var.set(f"{prog_sec//60}:{prog_sec%60:02d} / {dur_sec//60}:{dur_sec%60:02d}")
                
                # Volume
                vol = (pb.get("device") or {}).get("volume_percent")
                if vol is not None and not self._user_adjusting:
                    self.volume_var.set(vol)
                    self.volume_label_var.set(f"{vol}%")
            else:
                self.song_var.set("Nichts wird abgespielt")
                self.artist_var.set("")
                self.album_var.set("")
                self.is_playing_var.set(emoji("⏸", "Pause"))
        except Exception as e:
            import traceback
            print(f"Spotify Update Fehler: {e}")
            # Don't spam errors - increase retry interval on failure
            if self.alive: self.root.after(5000, self.update_spotify)
            return
        
        # Album Art update
        if not self.image_queue.empty():
            pil_img = self.image_queue.get()
            if pil_img:
                tk_img = ImageTk.PhotoImage(pil_img)
                self.album_img_label.configure(image=tk_img, text="", bg=COLOR_CARD_BG)
                self.album_img_label.image = tk_img
                self.current_album_cover = tk_img
            else:
                self.album_img_label.configure(image="", text=emoji("🎵", "ALBUM"), bg=COLOR_CARD_BG)
                self.album_img_label.image = None
                self.current_album_cover = None
            
        self._update_devices()
        if self.alive: self.root.after(3000, self.update_spotify)

    # ========== PLAYBACK CONTROLS ==========
    def play_pause(self):
        try:
            pb = self.sp.current_playback()
            if pb and pb.get('is_playing'):
                self.sp.pause_playback()
            else:
                self.sp.start_playback(device_id=self.current_device_id)
        except Exception as e:
            print(f"Play/Pause Fehler: {e}")

    def next_track(self):
        try: self.sp.next_track()
        except: pass

    def prev_track(self):
        try: self.sp.previous_track()
        except: pass

    def set_shuffle(self):
        try: self.sp.shuffle(True)
        except: pass

    def set_repeat(self):
        try: self.sp.repeat("context")
        except: pass
    
    def toggle_mute(self):
        try:
            current = self.volume_var.get()
            if current > 0:
                self._pre_mute_volume = current
                self.sp.volume(0)
            else:
                self.sp.volume(int(self._pre_mute_volume))
        except: pass

    def _on_volume_slide(self, val):
        self.volume_label_var.set(f"{int(float(val))}%")
        if self._vol_after: self.root.after_cancel(self._vol_after)
        self._vol_after = self.root.after(300, lambda: self._send_vol(int(float(val))))
        
    def _send_vol(self, v):
        try: self.sp.volume(v)
        except: pass

    # ========== SEARCH ==========
    def do_search(self):
        q = self.search_entry_var.get()
        if not q or not self.sp: return
        try:
            res = self.sp.search(q, limit=8, type="track,album,playlist")
            items = []
            self.result_cache = {}
            
            for t in (res.get("tracks",{}).get("items") or []):
                disp = emoji(f"🎵 {t['name']} - {t['artists'][0]['name']}", f"Track: {t['name']} - {t['artists'][0]['name']}")
                items.append(disp)
                self.result_cache[disp] = {"uri": t["uri"], "type": "track"}
                
            for a in (res.get("albums",{}).get("items") or []):
                disp = emoji(f"💿 {a['name']} - {a['artists'][0]['name']}", f"Album: {a['name']} - {a['artists'][0]['name']}")
                items.append(disp)
                self.result_cache[disp] = {"uri": a["uri"], "type": "album"}
                
            for p in (res.get("playlists",{}).get("items") or []):
                disp = emoji(f"📃 {p['name']}", f"Playlist: {p['name']}")
                items.append(disp)
                self.result_cache[disp] = {"uri": p["uri"], "type": "playlist"}
                
            self.result_box["values"] = items
            if items: self.result_box.current(0)
        except Exception as e:
            print(f"Search Fehler: {e}")

    def play_selected(self, event=None):
        sel = self.search_var.get()
        meta = self.result_cache.get(sel)
        if meta and self.sp:
            try:
                if meta["type"] == "track":
                    self.sp.start_playback(uris=[meta["uri"]])
                else:
                    self.sp.start_playback(context_uri=meta["uri"])
            except Exception as e:
                print(f"Play Selected Fehler: {e}")
