import logging
import threading
import queue
import os
import webbrowser
import time

import visualisierung_live


class SpotifyTab:
    """
    Spotify-Tab mit stabiler OAuth:
    - Kein automatisches Browser-Poppen mehr (open_browser=False)
    - Einmaliger Login via Button, Token in .cache-spotify gespeichert
    - Danach nie wieder Browser nötig
    - Suche Tracks/Alben/Playlists + korrektes Abspielen (mit device_id)
    - Lautstärke UI (Mute/±10/Debounce/Label)
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

        self.result_cache = {}

        # Tab-Placeholder
        self.tab_frame = visualisierung_live.ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.tab_frame, text="Spotify")
        self._build_prelogin_ui()

        # OAuth in separatem Thread initialisieren
        threading.Thread(target=self._oauth_init_thread, daemon=True).start()

    def stop(self):
        self.alive = False

    # ---------- UI-Abschnitte ----------
    def _clear_tab(self):
        for w in self.tab_frame.winfo_children():
            w.destroy()

    def _build_prelogin_ui(self, error_msg=None):
        self._clear_tab()
        wrapper = visualisierung_live.tk.Frame(self.tab_frame, bg="#222")
        wrapper.pack(fill="both", expand=True)
        title = visualisierung_live.ttk.Label(wrapper, text="Spotify", style="Dark.TLabel", font=("Arial", 18, "bold"))
        title.pack(pady=(24, 8))

        info_txt = "Noch nicht bei Spotify angemeldet."
        if error_msg:
            info_txt = f"Spotify-Login fehlgeschlagen:\n{error_msg}"

        info = visualisierung_live.ttk.Label(wrapper, text=info_txt, style="Dark.TLabel", anchor="center", justify="center")
        info.pack(pady=6)

        self.login_btn = visualisierung_live.ttk.Button(
            wrapper, text="🔐 Login im Browser öffnen", style="Dark.TButton",
            command=self._open_login_in_browser
        )
        self.login_btn.pack(pady=10)

        hint = visualisierung_live.ttk.Label(
            wrapper,
            text="Nach dem Login dieses Fenster geöffnet lassen.\nDer Token wird gespeichert und künftig automatisch verwendet.",
            style="Dark.TLabel"
        )
        hint.pack(pady=(4, 12))

        self.status_lbl_var = visualisierung_live.tk.StringVar(value="Status: warte auf Login…")
        status_lbl = visualisierung_live.ttk.Label(wrapper, textvariable=self.status_lbl_var, style="Dark.TLabel")
        status_lbl.pack(pady=(4, 10))

    def _build_ui(self):
        self._clear_tab()

        main = visualisierung_live.tk.Frame(self.tab_frame, bg="#222")
        main.pack(fill="both", expand=True)

        # Links: Cover
        left = visualisierung_live.tk.Frame(main, bg="#222")
        left.pack(side="left", fill="y", padx=30, pady=30)
        self.album_img_label = visualisierung_live.tk.Label(left, bg="#222")
        self.album_img_label.pack()

        # Rechts
        right = visualisierung_live.tk.Frame(main, bg="#222")
        right.pack(side="right", fill="both", expand=True, padx=30, pady=30)

        # Titel/Artist/Album
        song_label = visualisierung_live.ttk.Label(
            right, textvariable=self.song_var, style="Dark.TLabel",
            anchor="center", justify="center", font=("Arial", 20, "bold")
        )
        song_label.pack(pady=10, fill="x")

        # Fortschritt
        self.progress_bar = visualisierung_live.ttk.Progressbar(
            right, variable=self.progress_var, maximum=100, length=350
        )
        self.progress_bar.pack(pady=10)

        # Geräte
        self.device_box = visualisierung_live.ttk.Combobox(
            right, textvariable=self.device_var, font=("Arial", 14), width=30, state="readonly"
        )
        self.device_box.pack(pady=10)
        self.device_box.bind("<<ComboboxSelected>>", self.set_device)

        # Transport
        btns = visualisierung_live.tk.Frame(right, bg="#222")
        btns.pack(pady=16)
        self.prev_btn = visualisierung_live.ttk.Button(btns, text="⏮", style="Dark.TButton", width=6, command=self.prev_track)
        self.play_btn = visualisierung_live.ttk.Button(btns, text="⏯", style="Dark.TButton", width=6, command=self.play_pause)
        self.next_btn = visualisierung_live.ttk.Button(btns, text="⏭", style="Dark.TButton", width=6, command=self.next_track)
        self.shuffle_btn = visualisierung_live.ttk.Button(btns, text="🔀 Shuffle", style="Dark.TButton", width=10, command=self.set_shuffle)
        self.repeat_btn = visualisierung_live.ttk.Button(btns, text="🔁 Repeat", style="Dark.TButton", width=10, command=self.set_repeat)
        self.prev_btn.grid(row=0, column=0, padx=8)
        self.play_btn.grid(row=0, column=1, padx=8)
        self.next_btn.grid(row=0, column=2, padx=8)
        self.shuffle_btn.grid(row=1, column=0, columnspan=2, pady=8)
        self.repeat_btn.grid(row=1, column=2, pady=8)

        # Lautstärke
        vol_container = visualisierung_live.tk.Frame(right, bg="#222")
        vol_container.pack(pady=6, fill="x")
        self.mute_btn = visualisierung_live.ttk.Button(vol_container, text="🔇", style="Dark.TButton", width=4, command=self.toggle_mute)
        self.mute_btn.grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.vol_down_btn = visualisierung_live.ttk.Button(vol_container, text="−10", style="Dark.TButton", width=4, command=lambda: self.step_volume(-10))
        self.vol_down_btn.grid(row=0, column=1, padx=6, sticky="w")
        self.volume_scale = visualisierung_live.ttk.Scale(
            vol_container, from_=0, to=100, variable=self.volume_var,
            orient="horizontal", length=260, command=self._on_volume_slide
        )
        self.volume_scale.grid(row=0, column=2, padx=6, sticky="ew")
        self.vol_up_btn = visualisierung_live.ttk.Button(vol_container, text="+10", style="Dark.TButton", width=4, command=lambda: self.step_volume(+10))
        self.vol_up_btn.grid(row=0, column=3, padx=6, sticky="e")
        self.vol_label = visualisierung_live.ttk.Label(vol_container, textvariable=self.volume_label_var, style="Dark.TLabel", width=5, anchor="e")
        self.vol_label.grid(row=0, column=4, padx=(6, 0), sticky="e")
        vol_container.grid_columnconfigure(2, weight=1)
        self.volume_scale.bind("<ButtonPress-1>", self._vol_press)
        self.volume_scale.bind("<ButtonRelease-1>", self._vol_release)

        # Suche
        search_entry = visualisierung_live.ttk.Entry(right, textvariable=self.search_entry_var, font=("Arial", 14), width=30)
        search_entry.pack(pady=(14, 4))
        search_btn = visualisierung_live.ttk.Button(right, text="🔎 Suchen (Tracks/Alben/Playlists)", style="Dark.TButton", command=self.do_search)
        search_btn.pack(pady=4)
        self.result_box = visualisierung_live.ttk.Combobox(right, textvariable=self.search_var, font=("Arial", 14), width=48, state="readonly")
        self.result_box.pack(pady=8)
        self.result_box.bind("<<ComboboxSelected>>", self.play_selected)

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
                open_browser=False,    # <<< verhindert das flackernde Chromium-Fenster
                show_dialog=False
            )

            # 1) Token aus Cache?
            token_info = self.oauth.get_cached_token()
            if token_info:
                self.sp = spotipy.Spotify(auth_manager=self.oauth)
                self.ready = True
                logging.info("Spotify: Token aus Cache geladen.")
                self.root.after(0, self._build_ui)
                self.root.after(0, self.update_spotify)
                return

            # 2) Kein Token → Pre-Login-UI bleibt, wir warten asynchron auf Login
            #    (der User klickt den Button; wir blockieren hier nicht)
            logging.info("Spotify: kein Token im Cache. Warte auf Login…")

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
            if hasattr(self, "status_lbl_var"):
                self.status_lbl_var.set("Status: Browser geöffnet. Bitte Login abschließen…")

            # In Thread auf Token warten (blockiert nicht die GUI)
            threading.Thread(target=self._wait_for_token_thread, daemon=True).start()
        except Exception as e:
            logging.error(f"Login-URL öffnen fehlgeschlagen: {e}")
            if hasattr(self, "status_lbl_var"):
                self.status_lbl_var.set(f"Fehler: {e}")

    def _wait_for_token_thread(self):
        """Wartet auf den Access-Token (lokaler Callback nach Login)."""
        try:
            # get_access_token öffnet KEINEN Browser, startet aber den lokalen Callback-Server
            token_info = self.oauth.get_access_token(as_dict=True)
            if token_info and token_info.get("access_token"):
                import spotipy
                self.sp = spotipy.Spotify(auth_manager=self.oauth)
                self.ready = True
                logging.info("Spotify: Login erfolgreich, Token gespeichert.")
                self.root.after(0, self._build_ui)
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
            # in 5 s erneut probieren, falls ready später wird
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

        except Exception as e:
            logging.error(f"Spotify Update Fehler: {e}")
            self.song_var.set("Spotify Fehler")

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
            return
        try:
            if uris:
                self.sp.start_playback(device_id=device_id, uris=uris)
            elif context_uri:
                self.sp.start_playback(device_id=device_id, context_uri=context_uri)
            else:
                self.sp.start_playback(device_id=device_id)
        except Exception as e:
            logging.error(f"start_playback Fehler: {e}")
            self.song_var.set(f"Abspielen fehlgeschlagen ({e})")

    def play_pause(self):
        try:
            if not self.sp:
                return
            pb = self.sp.current_playback()
            if pb and pb.get("is_playing"):
                self.sp.pause_playback(device_id=self.current_device_id or None)
            else:
                self._start_playback()
        except Exception as e:
            logging.error(f"Spotify play/pause Fehler: {e}")

    def next_track(self):
        try:
            if self.sp:
                self.sp.next_track(device_id=self.current_device_id or None)
        except Exception as e:
            logging.error(f"Spotify next Fehler: {e}")

    def prev_track(self):
        try:
            if self.sp:
                self.sp.previous_track(device_id=self.current_device_id or None)
        except Exception as e:
            logging.error(f"Spotify prev Fehler: {e}")

    def set_shuffle(self):
        try:
            if not self.sp:
                return
            pb = self.sp.current_playback()
            state = pb.get("shuffle_state", False) if pb else False
            self.sp.shuffle(not state, device_id=self.current_device_id or None)
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
            return
        q = (self.search_entry_var.get() or "").strip()
        if not q:
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
            else:
                self.result_box["values"] = ["Kein Treffer"]
                self.search_var.set("Kein Treffer")

        except Exception as e:
            logging.error(f"Spotify Suche Fehler: {e}")
            self.result_box["values"] = ["Suche fehlgeschlagen (Netzwerk/Rate-Limit?)"]
            self.search_var.set("Suche fehlgeschlagen (Netzwerk/Rate-Limit?)")

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
