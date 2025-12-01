import logging
import threading
import queue
import os
import webbrowser
import time
import tkinter as tk
from tkinter import ttk 

class SpotifyTab:
    """
    Spotify-Tab angepasst für ttkbootstrap Dark Theme.
    Icons durch Textzeichen ersetzt für bessere Kompatibilität.
    """

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

        self._vol_after = None
        self._user_adjusting = False
        self._pre_mute_volume = 30
        self._last_volume_seen = None

        self.song_var = tk.StringVar(value="Spotify nicht verbunden")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.device_var = tk.StringVar(value="Kein Gerät gefunden")
        self.volume_var = tk.DoubleVar(value=50.0)
        self.volume_label_var = tk.StringVar(value="50%")
        self.search_entry_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.status_text_var = tk.StringVar(value="Status: Initialisiere...")

        self.result_cache = {}

        # Tab Frame
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text="Spotify")

        self._build_prelogin_ui()
        threading.Thread(target=self._oauth_init_thread, daemon=True).start()

    def stop(self):
        self.alive = False

    def _clear_tab(self):
        for w in self.tab_frame.winfo_children():
            w.destroy()

    def _build_header(self, parent, title_text="Spotify"):
        header = ttk.Frame(parent)
        header.pack(fill="x", pady=10, padx=10)

        # Nutze inverse-dark oder inverse-primary für gute Lesbarkeit auf dunkel
        title = ttk.Label(header, text=title_text, font=("Arial", 20, "bold"), bootstyle="inverse-dark")
        title.pack(side="left")

        status_label = ttk.Label(header, textvariable=self.status_text_var, bootstyle="secondary")
        status_label.pack(side="right")

    def _build_prelogin_ui(self, error_msg=None):
        self._clear_tab()
        wrapper = ttk.Frame(self.tab_frame)
        wrapper.pack(fill="both", expand=True)

        self._build_header(wrapper, "Spotify – Anmeldung")

        info_frame = ttk.Frame(wrapper)
        info_frame.pack(expand=True)

        info_txt = "Noch nicht angemeldet."
        if error_msg:
            info_txt = f"Login Fehler:\n{error_msg}"

        ttk.Label(info_frame, text=info_txt, font=("Arial", 12)).pack(pady=10)

        ttk.Button(info_frame, text="Login im Browser", bootstyle="success", command=self._open_login_in_browser).pack(pady=10)
        
        ttk.Label(info_frame, text="Nach dem Login bleibt der Token gespeichert.", bootstyle="secondary").pack()

    def _build_ui(self):
        self._clear_tab()
        main = ttk.Frame(self.tab_frame)
        main.pack(fill="both", expand=True)

        self._build_header(main, "Spotify Player")

        content = ttk.Frame(main)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        # Links: Cover
        left = ttk.Frame(content)
        left.pack(side="left", fill="y", padx=(0, 20))

        self.album_img_label = ttk.Label(left, text="[Cover]", anchor="center", width=40) 
        self.album_img_label.pack(pady=(0, 15))

        # Song Info
        now_playing_frame = ttk.Frame(left)
        now_playing_frame.pack(fill="x")

        ttk.Label(now_playing_frame, text="Aktueller Titel", font=("Arial", 12, "bold"), bootstyle="info").pack(anchor="w")
        
        # Songtitel groß und weiß (inverse)
        ttk.Label(now_playing_frame, textvariable=self.song_var, font=("Arial", 12), justify="center", bootstyle="inverse-dark").pack(fill="x", pady=5)

        # Progress
        progress_frame = ttk.Frame(now_playing_frame)
        progress_frame.pack(fill="x", pady=5)
        
        ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, bootstyle="success-striped").pack(side="left", fill="x", expand=True)
        self.progress_time_label = ttk.Label(progress_frame, text="--:--", font=("Arial", 9))
        self.progress_time_label.pack(side="right", padx=5)

        # Rechts: Steuerung
        right = ttk.Frame(content)
        right.pack(side="left", fill="both", expand=True)

        # 1. Geräte
        dev_frame = ttk.Labelframe(right, text="Gerät", padding=10, bootstyle="secondary")
        dev_frame.pack(fill="x", pady=(0, 10))
        
        self.device_box = ttk.Combobox(dev_frame, textvariable=self.device_var, state="readonly", font=("Arial", 11))
        self.device_box.pack(fill="x")
        self.device_box.bind("<<ComboboxSelected>>", self.set_device)

        # 2. Buttons (Text statt Icons für Kompatibilität)
        ctrl_frame = ttk.Labelframe(right, text="Steuerung", padding=10, bootstyle="secondary")
        ctrl_frame.pack(fill="x", pady=(0, 10))

        btn_row = ttk.Frame(ctrl_frame)
        btn_row.pack(pady=5)

        # Text-Symbole: <<, Play, >>, Shuffle, Repeat
        ttk.Button(btn_row, text="<<", width=5, bootstyle="outline", command=self.prev_track).grid(row=0, column=0, padx=5)
        ttk.Button(btn_row, text="PLAY / PAUSE", width=15, bootstyle="primary", command=self.play_pause).grid(row=0, column=1, padx=5)
        ttk.Button(btn_row, text=">>", width=5, bootstyle="outline", command=self.next_track).grid(row=0, column=2, padx=5)

        btn_row2 = ttk.Frame(ctrl_frame)
        btn_row2.pack(pady=5)
        ttk.Button(btn_row2, text="Shuffle", width=10, bootstyle="outline", command=self.set_shuffle).grid(row=0, column=0, padx=5)
        ttk.Button(btn_row2,