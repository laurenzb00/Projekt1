import logging
import threading
import queue
import os
import webbrowser
import time

import visualisierung_live


class SpotifyTab:
    """
    Spotify-Tab mit stabiler OAuth und aufgeräumtem UI:

    - Kein automatisches Browser-Poppen (open_browser=False)
    - Einmaliger Login via Button, Token in .cache-spotify
    - Danach kein Browser mehr nötig
    - Suche Tracks/Alben/Playlists + Abspielen (mit device_id)
    - Lautstärke-UI mit Mute/±10/Slider/Debounce
    - Optisch angepasst an das Dark/Light-Theme des Hauptprogramms
    """

    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook

        # Laufvariablen
        self.alive = True
        self.ready = False
        self.sp = None
        self.oauth = None
        self.device_ids = []
        self.current_device_id = None
        self.image_queue = queue.Queue()

        # Lautstärke/Debounce
        self._vol_after = None
        self._user_adjusting = False
        self._pre_mute_volume = 30
        self._last_volume_seen = None

        # Tk-Variablen
        self.song_var = visualisierung_live.tk.StringVar(value="Spotify nicht verbunden")
        self.progress_var = visualisierung_live.tk.DoubleVar(value=0.0)
        self.device_var = visualisierung_live.tk.StringVar(value="Kein Gerät gefunden")
        self.volume_var = visualisierung_live.tk.DoubleVar(value=50.0)
        self.volume_label_var = visualisierung_live.tk.StringVar(value="50%")
        self.search_entry_var = visualisierung_live.tk.StringVar()
        self.search_var = visualisierung_live.tk.StringVar()
        self.status_text_var = visualisierung_live.tk.StringVar(value="Status: Initialisiere Spotify…")

        self.result_cache = {}

        # Tab-Frame
        self.tab_frame = visualisierung_live.ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.tab_frame, text="Spotify")

        # Erstmal Pre-Login-Ansicht
        self._build_prelogin_ui()

        # OAuth in separatem Thread initialisieren
        threading.Thread(target=self._oauth_init_thread, daemon=True).start()

    def stop(self):
        self.alive = False

    # ---------- UI-Bausteine ----------

    def _clear_tab(self):
        for w in self.tab_frame.winfo_children():
            w.destroy()

    def _get_bg(self):
        """Aktuellen Hintergrund vom Tk-Root holen (Dark/Light Mode)."""
        try:
            return self.root.cget("bg")
        except Exception:
            return "#222222"

    def _build_header(self, parent, title_text="Spotify"):
        """Gemeinsame Kopfzeile mit Titel & Status."""
        bg = self._get_bg()
        header = visualisierung_live.tk.Frame(parent, bg=bg)
        header.pack(fill="x", pady=(10, 10), padx=10)

        title = visualisierung_live.ttk.Label(
            header,
            text=title_text,
            style="Dark.TLabel",
            font=("Arial", 20, "bold"),
        )
        title.pack(side="left")

        status_label = visualisierung_live.ttk.Label(
            header,
            textvariable=self.status_text_var,
            style="Dark.TLabel",
            anchor="e",
            justify="right"
        )
        status_label.pack(side="right")

    def _build_prelogin_ui(self, error_msg=None):
        self._clear_tab()
        bg = self._get_bg()

        wrapper = visualisierung_live.tk.Frame(self.tab_frame, bg=bg)
        wrapper.pack(fill="both", expand=True)

        self._build_header(wrapper, "Spotify – Anmeldung")

        info_frame = visualisierung_live.tk.Frame(wrapper, bg=bg)
        info_frame.pack(expand=True)

        info_txt = "Noch nicht bei Spotify angemeldet."
        if error_msg:
            info_txt = f"Spotify-Login fehlgeschlagen:\n{error_msg}"

        info = visualisierung_live.ttk.Label(
            info_frame,
            text=info_txt,
            style="Dark.TLabel",
            anchor="center",
            justify="center",
            font=("Arial", 12),
        )
        info.pack(pady=10)

        self.login_btn = visualisierung_live.ttk.Button(
            info_frame,
            text="🔐 Login im Browser öffnen",
            style="Dark.TButton",
            command=self._open_login_in_browser
        )
        self.login_btn.pack(pady=10)

        hint = visualisierung_live.ttk.Label(
            info_frame,
            text=(
                "Nach dem Login dieses Programm geöffnet lassen.\n"
                "Der Token wird gespeichert und künftig automatisch verwendet."
            ),
            style="Dark.TLabel",
            anchor="center",
            justify="center",
        )
        hint.pack(pady=(4, 12))

        self.status_text_var.set("Status: warte auf Login…")

    def _build_ui(self):
        self._clear_tab()
        bg = self._get_bg()

        main = visualisierung_live.tk.Frame(self.tab_frame, bg=bg)
        main.pack(fill="both", expand=True)

        # Kopfzeile
        self._build_header(main, "Spotify – Wiedergabe")

        # Hauptbereich (2 Spalten)
        content = visualisierung_live.tk.Frame(main, bg=bg)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        # Links: Cover + Now Playing
        left = visualisierung_live.tk.Frame(content, bg=bg)
        left.pack(side="left", fill="y", padx=(0, 20))

        cover_frame = visualisierung_live.tk.Frame(left, bg=bg)
        cover_frame.pack(pady=(0, 15))
        self.album_img_label = visualisierung_live.tk.Label(
            cover_frame,
            bg=bg,
            width=350,
            height=350
        )
        self.album_img_label.pack()

        now_playing_frame = visualisierung_live.tk.Frame(left, bg=bg)
        now_playing_frame.pack(fill="x", pady=(5, 0))

        lbl_np = visualisierung_live.ttk.Label(
            now_playing_frame,
            text="Aktueller Titel",
            style="Dark.TLabel",
            font=("Arial", 14, "bold")
        )
        lbl_np.pack(anchor="w", pady=(0, 3))

        self.song_label = visualisierung_live.ttk.Label(
            now_playing_frame,
            textvariable=self.song_var,
            style="Dark.TLabel",
            anchor="center",
            justify="center",
            font=("Arial", 12)
        )
        self.song_label.pack(fill="x")

        # Fortschritt
        progress_frame = visualisierung_live.tk.Frame(now_playing_frame, bg=bg)
        progress_frame.pack(fill="x", pady=(8, 0))

        self.progress_bar = visualisierung_live.ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=320
        )
        self.progress_bar.pack(side="left", fill="x", expand=True)

        self.progress_time_label = visualisierung_live.ttk.Label(
            progress_frame,
            text="",
            style="Dark.TLabel",
            font=("Arial", 9)
        )
        self.progress_time_label.pack(side="right", padx=(6, 0))

        # Rechts: Geräte, Transport, Lautstärke, Suche
        right = visualisierung_live.tk.Frame(content, bg=bg)
        right.pack(side="left", fill="both", expand=True)

        # Geräte
        device_frame = visualisierung_live.tk.LabelFrame(
            right,
            text="Ausgabegerät",
            bg=bg,
            fg=self.root.option_get("foreground", "Dark.TLabel") or "#ffffff",
            labelanchor="nw"
        )
        device_frame.pack(fill="x", pady=(0, 10))

        self.device_box = visualisierung_live.ttk.Combobox(
            device_frame,
            textvariable=self.device_var,
            font=("Arial", 12),
            width=35,
            state="readonly"
        )
        self.device_box.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        self.device_box.bind("<<ComboboxSelected>>", self.set_device)

        # Transport-Steuerung
        ctrl_frame = visualisierung_live.tk.LabelFrame(
            right,
            text="Steuerung",
            bg=bg,
            fg=self.root.option_get("foreground", "Dark.TLabel") or "#ffffff",
            labelanchor="nw"
        )
        ctrl_frame.pack(fill="x", pady=(0, 10))

        btn_row = visualisierung_live.tk.Frame(ctrl_frame, bg=bg)
        btn_row.pack(pady=5)

        self.prev_btn = visualisierung_live.ttk.Button(
            btn_row, text="⏮", style="Dark.TButton", width=6, command=self.prev_track
        )
        self.play_btn = visualisierung_live.ttk.Button(
            btn_row, text="⏯", style="Dark.TButton", width=6, command=self.play_pause
        )
        self.next_btn = visualisierung_live.ttk.Button(
            btn_row, text="⏭", style="Dark.TButton", width=6, command=self.next_track
        )

        self.prev_btn.grid(row=0, column=0, padx=4)
        self.play_btn.grid(row=0, column=1, padx=4)
        self.next_btn.grid(row=0, column=2, padx=4)

        btn_row2 = visualisierung_live.tk.Frame(ctrl_frame, bg=bg)
        btn_row2.pack(pady=(2, 5))

        self.shuffle_btn = visualisierung_live.ttk.Button(
            btn_row2, text="🔀 Shuffle", style="Dark.TButton", width=10, command=self.set_shuffle
        )
        self.repeat_btn = visualisierung_live.ttk.Button(
            btn_row2, text="🔁 Repeat", style="Dark.TButton", width=10, command=self.set_repeat
        )
        self.shuffle_btn.grid(row=0, column=0, padx=4)
        self.repeat_btn.grid(row=0, column=1, padx=4)

        # Lautstärke
        vol_frame = visualisierung_live.tk.LabelFrame(
            right,
            text="Lautstärke",
            bg=bg,
            fg=self.root.option_get("foreground", "Dark.TLabel") or "#ffffff",
            labelanchor="nw"
        )
        vol_frame.pack(fill="x", pady=(0, 10))

        inner_vol = visualisierung_live.tk.Frame(vol_frame, bg=bg)
        inner_vol.pack(fill="x", padx=5, pady=5)

        self.mute_btn = visualisierung_live.ttk.Button(
            inner_vol, text="🔇", style="Dark.TButton", width=4, command=self.toggle_mute
        )
        self.mute_btn.grid(row=0, column=0, padx=(0, 6), sticky="w")

        self.vol_down_btn = visualisierung_live.ttk.Button(
            inner_vol, text="−10", style="Dark.TButton", width=4,
            command=lambda: self.step_volume(-10)
        )
        self.vol_down_btn.grid(row=0, column=1, padx=4, sticky="w")

        self.volume_scale = visualisierung_live.ttk.Scale(
            inner_vol, from_=0, to=100, variable=self.volume_var,
            orient="horizontal", length=220, command=self._on_volume_slide
        )
        self.volume_scale.grid(row=0, column=2, padx=6, sticky="ew")

        self.vol_up_btn = visualisierung_live.ttk.Button(
            inner_vol, text="+10", style="Dark.TButton", width=4,
            command=lambda: self.step_volume(+10)
        )
        self.vol_up_btn.grid(row=0, column=3, padx=4, sticky="e")

        self.vol_label = visualisierung_live.ttk.Label(
            inner_vol,
            textvariable=self.volume_label_var,
            style="Dark.TLabel",
            width=5,
            anchor="e"
        )
        self.vol_label.grid(row=0, column=4, padx=(6, 0), sticky="e")

        inner_vol.grid_columnconfigure(2, weight=1)

        self.volume_scale.bind("<ButtonPress-1>", self._vol_press)
        self.volume_scale.bind("<ButtonRelease-1>", self._vol_release)

        # Suche
        search_frame = visualisierung_live.tk.LabelFrame(
            right,
            text="Suche",
            bg=bg,
            fg=self.root.option_get("foreground", "Dark.TLabel") or "#ffffff",
            labelanchor="nw"
        )
        search_frame.pack(fill="both", expand=True, pady=(0, 5))

        entry_row = visualisierung_live.tk.Frame(search_frame, bg=bg)
        entry_row.pack(fill="x", padx=5, pady=(5, 2))

        search_entry = visualisierung_live.ttk.Entry(
            entry_row,
            textvariable=self.search_entry_var,
            font=("Arial", 12),
        )
        search_entry.pack(side="left", fill="x", expand=True)

        search_btn = visualisierung_live.ttk.Button(
            entry_row,
            text="🔎 Suchen",
            style="Dark.TButton",
            command=self.do_search
        )
        search_btn.pack(side="left", padx=(6, 0))

        self.result_box = visualisierung_live.ttk.Combobox(
            search_frame,
            textvariable=self.search_var,
            font=("Arial", 12),
            width=48,
            state="readonly"
        )
        self.result_box.pack(fill="x", padx=5, pady=(4, 5))
        self.result_box.bind("<<ComboboxSelected>>", self.play_selected)

        helper_lbl = visualisierung_live.ttk.Label(
            search_frame,
            text="Tipp: Treffer mit [Track], [Album] oder [Playlist] auswählen und abspielen.",
            style="Dark.TLabel",
            font=("Arial", 9),
        )
        helper_lbl.pack(anchor="w", padx=5, pady=(0, 5))

    # ---------- OAuth / Login ----------

    def _oauth_init_thread(self):
        """Initialisiert SpotifyOAuth ohne Browser-Popup & prüft Cache."""
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
                open_browser=False,
                show_dialog=False,
            )

            token_info = self.oauth.get_cached_token()
            if token_info:
                self.sp = spotipy.Spotify(auth_manager=self.oauth)
                self.ready = True
                logging.info("Spotify: Token aus Cache geladen.")
                self.root.after(0, self._build_ui)
                self.status_text_var.set("Status: verbunden")
                self.root.after(0, self.update_spotify)
                return

            logging.info("Spotify: kein Token im Cache. Warte auf Login…")
            self.status_text_var.set("Status: kein Token – bitte einmalig einloggen.")

        except Exception as e:
            logging.error(f"Spotify-OAuth Initialisierung fehlgeschlagen: {e}")
            self.root.after(0, self._build_prelogin_ui, str(e))

    def _open_login_in_browser(self):
        """Öffnet die Login-Seite einmalig und wartet in einem Thread auf den Token."""
        if not self.oauth:
            return
        try:
            url = self.oauth.get_authorize_url()
            webbrowser.open_new(url)
            self.status_text_var.set("Status: Browser geöffnet. Bitte Login abschließen…")

            threading.Thread(target=self._wait_for_token_thread, daemon=True).start()
        except Exception as e:
            logging.error(f"Login-URL öffnen fehlgeschlagen: {e}")
            self.status_text_var.set(f"Fehler beim Öffnen des Browsers: {e}")

    def _wait_for_token_thread(self):
        """Wartet auf den Access-Token (lokaler Callback nach Login)."""
        try:
            token_info = self.oauth.get_access_token(as_dict=True)
            if token_info and token_info.get("access_token"):
                import spotipy
                self.sp = spotipy.Spotify(auth_manager=self.oauth)
                self.ready = True
                logging.info("Spotify: Login erfolgreich, Token gespeichert.")
                self.root.after(0, self._build_ui)
                self.status_text_var.set("Status: verbunden")
                self.root.after(0, self.update_spotify)
            else:
                raise RuntimeError("Konnte keinen Access-Token erhalten.")
        except Exception as e:
            logging.error(f"Spotify-Login fehlgeschlagen: {e}")
            self.root.after(0, self._build_prelogin_ui, str(e))

    # ---------- Geräte ----------

    def _update_devices(self):
        if not self.sp:
            return
        try:
            devices = self.sp.devices().get("devices", [])
            names = [f"{d.get('name','?')} ({d.get('type','?')})" for d in devices]
            ids = [d.get("id") for d in devices]
            self.device_ids = ids
            self.device_box["values"] = names

            try:
                pb = self.sp.current_playback()
                active_dev = (pb or {}).get("device") or {}
                active_id = active_dev.get("id")
                if active_id:
                    self.current_device_id = active_id
                    for i, did in enumerate(ids):
                        if did == active_id and i < len(names):
                            self.device_var.set(names[i])
                            break
            except Exception:
                pass

            if not self.current_device_id and ids:
                self.current_device_id = ids[0]
                if names:
                    self.device_var.set(names[0])

            if not names:
                self.device_var.set("Kein Gerät gefunden")

        except Exception as e:
            logging.error(f"Spotify Geräte Fehler: {e}")
            self.device_box["values"] = []
            self.device_var.set("Kein Gerät gefunden")
            self.device_ids = []
            self.current_device_id = None

    def _ensure_active_device(self):
        self._update_devices()
        if not self.current_device_id and self.device_ids:
            self.current_device_id = self.device_ids[0]
        if self.current_device_id and self.sp:
            try:
                self.sp.transfer_playback(self.current_device_id, force_play=True)
            except Exception as e:
                logging.debug(f"transfer_playback Hinweis: {e}")
        return self.current_device_id

    def set_device(self, event=None):
        idx = self.device_box.current()
        if 0 <= idx < len(self.device_ids) and self.device_ids[idx]:
            self.current_device_id = self.device_ids[idx]
            try:
                if self.sp:
                    self.sp.transfer_playback(self.current_device_id, force_play=True)
            except Exception as e:
                logging.error(f"Spotify set_device Fehler: {e}")

    # ---------- Cover laden ----------

    def fetch_cover(self, img_url):
        try:
            from PIL import Image, ImageTk
            import requests, io
            img_data = requests.get(img_url, timeout=5).content
            pil_img = Image.open(io.BytesIO(img_data)).resize((350, 350))
            tk_img = ImageTk.PhotoImage(pil_img)
            self.image_queue.put(tk_img)
        except Exception as e:
            logging.error(f"Spotify Cover Fehler: {e}")

    # ---------- Update ----------

    def update_spotify(self):
        if not self.alive or not self.ready or not self.sp:
            self.root.after(5000, self.update_spotify)
            return
        try:
            pb = self.sp.current_playback()
            if pb and pb.get("item"):
                item = pb["item"]
                name = item.get("name", "Unbekannt")
                artist = item.get("artists", [{}])[0].get("name", "?")
                album = item.get("album", {}).get("name", "?")
                self.song_var.set(f"{name}\n{artist}\nAlbum: {album}")

                images = item.get("album", {}).get("images", [])
                if images:
                    img_url = images[0].get("url")
                    if img_url:
                        threading.Thread(target=self.fetch_cover, args=(img_url,), daemon=True).start()

                duration = item.get("duration_ms") or 0
                progress = pb.get("progress_ms") or 0
                self.progress_var.set((progress / duration * 100) if duration else 0)

                # Fortschritt in mm:ss
                if duration:
                    total_s = int(duration / 1000)
                    pos_s = int(progress / 1000)
                    self.progress_time_label.config(
                        text=f"{pos_s//60:02d}:{pos_s%60:02d} / {total_s//60:02d}:{total_s%60:02d}"
                    )
                else:
                    self.progress_time_label.config(text="")

                dev = pb.get("device") or {}
                vol = dev.get("volume_percent")
                if vol is not None:
                    self._last_volume_seen = int(vol)
                    self.volume_label_var.set(f"{int(vol)}%")
                    if not self._user_adjusting:
                        self.volume_var.set(int(vol))
                    self._update_mute_icon(int(vol))
                    if int(vol) > 0:
                        self._pre_mute_volume = int(vol)

                did = (pb.get("device") or {}).get("id")
                if did:
                    self.current_device_id = did
            else:
                self.song_var.set("Kein Song läuft")
                self.progress_var.set(0.0)
                self.progress_time_label.config(text="")

        except Exception as e:
            logging.error(f"Spotify Update Fehler: {e}")
            self.song_var.set("Spotify Fehler")
            self.status_text_var.set("Status: Fehler beim Abrufen der Wiedergabe")

        if not self.image_queue.empty():
            tk_img = self.image_queue.get()
            self.album_img_label.configure(image=tk_img)
            self.album_img_label.image = tk_img

        self._update_devices()
        if self.alive:
            self.root.after(5000, self.update_spotify)

    # ---------- Controls ----------

    def _start_playback(self, *, uris=None, context_uri=None):
        device_id = self._ensure_active_device()
        if not device_id or not self.sp:
            self.song_var.set("Kein Gerät verfügbar – Spotify am Handy/PC öffnen.")
            self.status_text_var.set("Status: Kein Wiedergabegerät")
            return
        try:
            if uris:
                self.sp.start_playback(device_id=device_id, uris=uris)
            elif context_uri:
                self.sp.start_playback(device_id=device_id, context_uri=context_uri)
            else:
                self.sp.start_playback(device_id=device_id)
            self.status_text_var.set("Status: Wiedergabe gestartet")
        except Exception as e:
            logging.error(f"start_playback Fehler: {e}")
            self.song_var.set(f"Abspielen fehlgeschlagen ({e})")
            self.status_text_var.set("Status: Abspielen fehlgeschlagen")

    def play_pause(self):
        try:
            if not self.sp:
                return
            pb = self.sp.current_playback()
            if pb and pb.get("is_playing"):
                self.sp.pause_playback(device_id=self.current_device_id or None)
                self.status_text_var.set("Status: pausiert")
            else:
                self._start_playback()
        except Exception as e:
            logging.error(f"Spotify play/pause Fehler: {e}")

    def next_track(self):
        try:
            if self.sp:
                self.sp.next_track(device_id=self.current_device_id or None)
                self.status_text_var.set("Status: nächster Titel")
        except Exception as e:
            logging.error(f"Spotify next Fehler: {e}")

    def prev_track(self):
        try:
            if self.sp:
                self.sp.previous_track(device_id=self.current_device_id or None)
                self.status_text_var.set("Status: vorheriger Titel")
        except Exception as e:
            logging.error(f"Spotify prev Fehler: {e}")

    def set_shuffle(self):
        try:
            if not self.sp:
                return
            pb = self.sp.current_playback()
            state = pb.get("shuffle_state", False) if pb else False
            new_state = not state
            self.sp.shuffle(new_state, device_id=self.current_device_id or None)
            self.status_text_var.set(f"Status: Shuffle {'an' if new_state else 'aus'}")
        except Exception as e:
            logging.error(f"Spotify shuffle Fehler: {e}")

    def set_repeat(self):
        try:
            if not self.sp:
                return
            pb = self.sp.current_playback()
            state = pb.get("repeat_state", "off") if pb else "off"
            new_state = "track" if state == "off" else "off"
            self.sp.repeat(new_state, device_id=self.current_device_id or None)
            self.status_text_var.set(f"Status: Repeat {'Titel' if new_state == 'track' else 'aus'}")
        except Exception as e:
            logging.error(f"Spotify repeat Fehler: {e}")

    # ---------- Lautstärke ----------

    def _update_mute_icon(self, vol_int):
        self.mute_btn.config(text="🔇" if vol_int == 0 else "🔈")

    def _send_volume(self, vol_int):
        try:
            if self.sp:
                self.sp.volume(int(vol_int), device_id=self.current_device_id or None)
        except Exception as e:
            logging.error(f"Spotify volume Fehler: {e}")

    def _on_volume_slide(self, val):
        try:
            vol_int = int(float(val))
        except Exception:
            return
        self.volume_label_var.set(f"{vol_int}%")
        self._update_mute_icon(vol_int)
        if self._vol_after is not None:
            try:
                self.root.after_cancel(self._vol_after)
            except Exception:
                pass
        self._vol_after = self.root.after(200, lambda: self._send_volume(vol_int))

    def _vol_press(self, event):
        self._user_adjusting = True

    def _vol_release(self, event):
        self._user_adjusting = False
        try:
            vol_int = int(float(self.volume_var.get()))
            self.volume_label_var.set(f"{vol_int}%")
            self._update_mute_icon(vol_int)
            self._send_volume(vol_int)
        except Exception:
            pass

    def step_volume(self, delta):
        try:
            cur = int(float(self.volume_var.get()))
        except Exception:
            cur = self._last_volume_seen or 50
        new_v = max(0, min(100, cur + delta))
        self.volume_var.set(new_v)
        self.volume_label_var.set(f"{new_v}%")
        self._update_mute_icon(new_v)
        self._send_volume(new_v)

    def toggle_mute(self):
        try:
            cur = int(float(self.volume_var.get()))
        except Exception:
            cur = self._last_volume_seen or 50
        if cur == 0:
            target = self._pre_mute_volume or 30
            target = max(1, min(100, int(target)))
            self.volume_var.set(target)
            self.volume_label_var.set(f"{target}%")
            self._update_mute_icon(target)
            self._send_volume(target)
        else:
            self._pre_mute_volume = cur
            self.volume_var.set(0)
            self.volume_label_var.set("0%")
            self._update_mute_icon(0)
            self._send_volume(0)

    # ---------- Suche ----------

    def do_search(self):
        if not self.ready or not self.sp:
            self.status_text_var.set("Status: Spotify noch nicht verbunden")
            return
        q = (self.search_entry_var.get() or "").strip()
        if not q:
            self.status_text_var.set("Status: Suchbegriff fehlt")
            return
        try:
            res = self.sp.search(q=q, type="track,album,playlist", limit=10) or {}
            tracks = ((res.get("tracks") or {}).get("items")) or []
            albums = ((res.get("albums") or {}).get("items")) or []
            playlists = ((res.get("playlists") or {}).get("items")) or []

            items_display = []
            self.result_cache.clear()

            for it in tracks:
                if not it:
                    continue
                name = (it.get("name") or "?")
                artist = ((it.get("artists") or [{}])[0].get("name") or "?")
                disp = f"[Track] {name} – {artist}"
                uri = it.get("uri")
                if uri:
                    self.result_cache[disp] = {"type": "track", "uri": uri}
                    items_display.append(disp)

            for it in albums:
                if not it:
                    continue
                name = (it.get("name") or "?")
                artist = ((it.get("artists") or [{}])[0].get("name") or "?")
                disp = f"[Album] {name} – {artist}"
                ctx = it.get("uri")
                if ctx:
                    self.result_cache[disp] = {"type": "album", "context_uri": ctx}
                    items_display.append(disp)

            for it in playlists:
                if not it:
                    continue
                name = (it.get("name") or "?")
                owner = ((it.get("owner") or {}).get("display_name") or "?")
                disp = f"[Playlist] {name} – {owner}"
                ctx = it.get("uri")
                if ctx:
                    self.result_cache[disp] = {"type": "playlist", "context_uri": ctx}
                    items_display.append(disp)

            if items_display:
                self.result_box["values"] = items_display
                self.search_var.set(items_display[0])
                self.status_text_var.set(f"Status: {len(items_display)} Treffer gefunden")
            else:
                self.result_box["values"] = ["Kein Treffer"]
                self.search_var.set("Kein Treffer")
                self.status_text_var.set("Status: keine Treffer")
        except Exception as e:
            logging.error(f"Spotify Suche Fehler: {e}")
            self.result_box["values"] = ["Suche fehlgeschlagen (Netzwerk/Rate-Limit?)"]
            self.search_var.set("Suche fehlgeschlagen (Netzwerk/Rate-Limit?)")
            self.status_text_var.set("Status: Suche fehlgeschlagen")

    def play_selected(self, event=None):
        if not self.ready or not self.sp:
            return
        disp = self.search_var.get()
        meta = self.result_cache.get(disp)
        if not meta:
            return
        if meta["type"] == "track" and meta.get("uri"):
            self._start_playback(uris=[meta["uri"]])
            self.song_var.set(f"Spiele: {disp}")
        elif meta["type"] in ("album", "playlist") and meta.get("context_uri"):
            self._start_playback(context_uri=meta["context_uri"])
            self.song_var.set(f"Spiele aus: {disp}")
