import logging
import threading
import queue
import time

# Wir benutzen die Tk/ttk/Styles aus deinem visualisierung_live-Modul
import visualisierung_live


class SpotifyTab:
    """
    Kapselt den gesamten Spotify-Tab:
    - Authentifizierung asynchron
    - Anzeige von Cover/Titel/Künstler/Album + Fortschritt
    - Gerätewahl, Play/Pause, Next/Prev, Shuffle/Repeat
    - Schöne Lautstärke-Steuerung (Mute, +/-10, Prozentanzeige, Debounce)
    - Suche über Tracks/Alben/Playlists und korrektes Abspielen
    """

    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook

        # Laufvariablen
        self.alive = True
        self.ready = False
        self.sp = None
        self.device_ids = []
        self.image_queue = queue.Queue()

        # Lautstärke-Steuerung / Debounce
        self._vol_after = None
        self._user_adjusting = False
        self._pre_mute_volume = 30  # wird beim ersten Sync überschrieben
        self._last_volume_seen = None

        # Tk-Variablen (gehören in den GUI-Thread!)
        self.song_var = visualisierung_live.tk.StringVar(value="Spotify nicht verbunden")
        self.progress_var = visualisierung_live.tk.DoubleVar(value=0.0)
        self.device_var = visualisierung_live.tk.StringVar(value="Kein Gerät gefunden")
        self.volume_var = visualisierung_live.tk.DoubleVar(value=50.0)  # 0..100
        self.volume_label_var = visualisierung_live.tk.StringVar(value="50%")
        self.search_entry_var = visualisierung_live.tk.StringVar()
        self.search_var = visualisierung_live.tk.StringVar()

        # Ergebnis-Cache: Anzeigename -> {type, uri/context_uri}
        self.result_cache = {}

        # Tab-Placeholder
        self.tab_frame = visualisierung_live.ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(self.tab_frame, text="Spotify")

        info = visualisierung_live.ttk.Label(
            self.tab_frame,
            text="Spotify wird verbunden…",
            style="Dark.TLabel",
            anchor="center",
            justify="center"
        )
        info.pack(padx=20, pady=20, fill="x")

        # Auth in separatem Thread, damit die GUI sofort sichtbar ist
        threading.Thread(target=self._auth_thread, daemon=True).start()

    # ---------- Lebenszyklus ----------
    def stop(self):
        """Sauber beenden: Update-Schleifen stoppen."""
        self.alive = False

    # ---------- Auth ----------
    def _auth_thread(self):
        try:
            try:
                import spotipy
                from spotipy.oauth2 import SpotifyOAuth
            except Exception as e:
                raise RuntimeError(
                    "spotipy ist nicht installiert. Bitte im (venv) ausführen: pip install spotipy"
                ) from e

            # Hinweis: open_browser=True öffnet den Standardbrowser für OAuth.
            # Falls das auf dem System nicht geht, setze auf False und folge der URL im Terminal.
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id="8cff12b3245a4e4088d5751360f62705",
                client_secret="af9ecfa466504d7795416a3f2c66f5c5",
                redirect_uri="http://127.0.0.1:8888/callback",
                scope="user-read-currently-playing user-modify-playback-state user-read-playback-state",
                open_browser=True
            ))
            self.ready = True
            logging.info("Spotify: Authentifizierung erfolgreich.")
            self.root.after(0, self._build_ui)
            self.root.after(0, self.update_spotify)
        except Exception as e:
            logging.error(f"Spotify-Authentifizierung fehlgeschlagen: {e}")
            self.root.after(0, self._auth_failed_ui, str(e))

    def _auth_failed_ui(self, msg):
        for w in self.tab_frame.winfo_children():
            w.destroy()
        label = visualisierung_live.ttk.Label(
            self.tab_frame,
            text=f"Spotify-Login fehlgeschlagen:\n{msg}\nGUI läuft weiter.",
            style="Dark.TLabel",
            anchor="center",
            justify="center"
        )
        label.pack(padx=20, pady=20, fill="x")

    # ---------- UI ----------
    def _build_ui(self):
        # Tab-Inhalt ersetzen
        for w in self.tab_frame.winfo_children():
            w.destroy()

        # Imports hier, damit tkinter schon initialisiert ist
        from PIL import Image, ImageTk  # noqa: F401
        import requests, io  # noqa: F401

        main = visualisierung_live.tk.Frame(self.tab_frame, bg="#222")
        main.pack(fill="both", expand=True)

        # Links: Cover
        left = visualisierung_live.tk.Frame(main, bg="#222")
        left.pack(side="left", fill="y", padx=30, pady=30)
        self.album_img_label = visualisierung_live.tk.Label(left, bg="#222")
        self.album_img_label.pack()

        # Rechts: Infos/Controls
        right = visualisierung_live.tk.Frame(main, bg="#222")
        right.pack(side="right", fill="both", expand=True, padx=30, pady=30)

        # Titel/Artist/Album
        song_label = visualisierung_live.ttk.Label(
            right,
            textvariable=self.song_var,
            style="Dark.TLabel",
            anchor="center",
            justify="center",
            font=("Arial", 20, "bold")
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

        # Buttons (Transport)
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

        # ======= Lautstärke (schön) =======
        vol_container = visualisierung_live.tk.Frame(right, bg="#222")
        vol_container.pack(pady=6, fill="x")

        # Mute/Unmute Button
        self.mute_btn = visualisierung_live.ttk.Button(
            vol_container, text="🔇", style="Dark.TButton", width=4, command=self.toggle_mute
        )
        self.mute_btn.grid(row=0, column=0, padx=(0, 6), sticky="w")

        # -10 Button
        self.vol_down_btn = visualisierung_live.ttk.Button(
            vol_container, text="−10", style="Dark.TButton", width=4, command=lambda: self.step_volume(-10)
        )
        self.vol_down_btn.grid(row=0, column=1, padx=6, sticky="w")

        # Scale
        self.volume_scale = visualisierung_live.ttk.Scale(
            vol_container, from_=0, to=100, variable=self.volume_var,
            orient="horizontal", length=260, command=self._on_volume_slide
        )
        self.volume_scale.grid(row=0, column=2, padx=6, sticky="ew")

        # +10 Button
        self.vol_up_btn = visualisierung_live.ttk.Button(
            vol_container, text="+10", style="Dark.TButton", width=4, command=lambda: self.step_volume(+10)
        )
        self.vol_up_btn.grid(row=0, column=3, padx=6, sticky="e")

        # Prozentanzeige
        self.vol_label = visualisierung_live.ttk.Label(
            vol_container, textvariable=self.volume_label_var, style="Dark.TLabel", width=5, anchor="e"
        )
        self.vol_label.grid(row=0, column=4, padx=(6, 0), sticky="e")

        vol_container.grid_columnconfigure(2, weight=1)

        # Maus-Events für „Benutzer zieht Regler“
        self.volume_scale.bind("<ButtonPress-1>", self._vol_press)
        self.volume_scale.bind("<ButtonRelease-1>", self._vol_release)

        # ======= Suche (Eingabe + Button + Ergebnis-Combobox) =======
        search_entry = visualisierung_live.ttk.Entry(
            right, textvariable=self.search_entry_var, font=("Arial", 14), width=30
        )
        search_entry.pack(pady=(14, 4))

        search_btn = visualisierung_live.ttk.Button(
            right, text="🔎 Suchen (Tracks/Alben/Playlists)", style="Dark.TButton", command=self.do_search
        )
        search_btn.pack(pady=4)

        self.result_box = visualisierung_live.ttk.Combobox(
            right, textvariable=self.search_var, font=("Arial", 14), width=48, state="readonly"
        )
        self.result_box.pack(pady=8)
        self.result_box.bind("<<ComboboxSelected>>", self.play_selected)

        # Responsiv
        def resize(event):
            w = event.width
            self.progress_bar.config(length=int(w * 0.4))
            # Scale passt sich über grid_columnconfigure an; bei extrem schmalem Layout ggf. anpassen

        self.root.bind("<Configure>", resize)

    # ---------- Geräte ----------
    def _update_devices(self):
        try:
            devices = self.sp.devices().get("devices", [])
            names = [f"{d.get('name','?')} ({d.get('type','?')})" for d in devices]
            self.device_ids = [d.get("id") for d in devices]
            self.device_box["values"] = names
            if names and (self.device_var.get() not in names):
                self.device_var.set(names[0])
            if not names:
                self.device_var.set("Kein Gerät gefunden")
        except Exception as e:
            logging.error(f"Spotify Geräte Fehler: {e}")
            self.device_box["values"] = []
            self.device_var.set("Kein Gerät gefunden")
            self.device_ids = []

    def set_device(self, event=None):
        idx = self.device_box.current()
        if 0 <= idx < len(self.device_ids) and self.device_ids[idx]:
            try:
                self.sp.transfer_playback(self.device_ids[idx], force_play=True)
            except Exception as e:
                logging.error(f"Spotify set_device Fehler: {e}")

    # ---------- Cover laden (asynchron) ----------
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

    # ---------- Periodisches Update ----------
    def update_spotify(self):
        if not self.alive or not self.ready:
            return
        try:
            pb = self.sp.current_playback()
            if pb and pb.get("item"):
                item = pb["item"]
                name = item.get("name", "Unbekannt")
                artist = item.get("artists", [{}])[0].get("name", "?")
                album = item.get("album", {}).get("name", "?")
                self.song_var.set(f"{name}\n{artist}\nAlbum: {album}")

                # Cover
                images = item.get("album", {}).get("images", [])
                if images:
                    img_url = images[0].get("url")
                    if img_url:
                        threading.Thread(target=self.fetch_cover, args=(img_url,), daemon=True).start()

                # Fortschritt
                duration = item.get("duration_ms") or 0
                progress = pb.get("progress_ms") or 0
                self.progress_var.set((progress / duration * 100) if duration else 0)

                # Gerätesync: Lautstärke
                dev = pb.get("device") or {}
                vol = dev.get("volume_percent")
                if vol is not None:
                    self._last_volume_seen = int(vol)
                    self.volume_label_var.set(f"{int(vol)}%")
                    # Skalenwert nur aktualisieren, wenn der Benutzer den Regler NICHT gerade zieht
                    if not self._user_adjusting:
                        self.volume_var.set(int(vol))
                    # Mute-Icon aktualisieren
                    self._update_mute_icon(int(vol))
                    # Für Unmute-Vormerkung nur übernehmen, wenn >0
                    if int(vol) > 0:
                        self._pre_mute_volume = int(vol)
            else:
                self.song_var.set("Kein Song läuft")
                self.progress_var.set(0.0)
        except Exception as e:
            logging.error(f"Spotify Update Fehler: {e}")
            self.song_var.set("Spotify Fehler")

        # neues Cover anzeigen?
        if not self.image_queue.empty():
            tk_img = self.image_queue.get()
            self.album_img_label.configure(image=tk_img)
            self.album_img_label.image = tk_img

        self._update_devices()

        # nächstes Update planen
        if self.alive:
            self.root.after(5000, self.update_spotify)

    # ---------- Playback Controls ----------
    def play_pause(self):
        try:
            pb = self.sp.current_playback()
            if pb and pb.get("is_playing"):
                self.sp.pause_playback()
            else:
                self.sp.start_playback()
        except Exception as e:
            logging.error(f"Spotify play/pause Fehler: {e}")

    def next_track(self):
        try:
            self.sp.next_track()
        except Exception as e:
            logging.error(f"Spotify next Fehler: {e}")

    def prev_track(self):
        try:
            self.sp.previous_track()
        except Exception as e:
            logging.error(f"Spotify prev Fehler: {e}")

    def set_shuffle(self):
        try:
            pb = self.sp.current_playback()
            state = pb.get("shuffle_state", False) if pb else False
            self.sp.shuffle(not state)
        except Exception as e:
            logging.error(f"Spotify shuffle Fehler: {e}")

    def set_repeat(self):
        try:
            pb = self.sp.current_playback()
            state = pb.get("repeat_state", "off") if pb else "off"
            new_state = "track" if state == "off" else "off"
            self.sp.repeat(new_state)
        except Exception as e:
            logging.error(f"Spotify repeat Fehler: {e}")

    # ---------- Lautstärke: schöne Steuerung ----------
    def _update_mute_icon(self, vol_int):
        # 0 -> Muted, >0 -> Laut
        self.mute_btn.config(text="🔇" if vol_int == 0 else "🔈")

    def _send_volume(self, vol_int):
        try:
            self.sp.volume(int(vol_int))
        except Exception as e:
            logging.error(f"Spotify volume Fehler: {e}")

    def _schedule_send_volume(self, vol_int, delay_ms=200):
        # debounce: letzten geplanten Call abbrechen
        if self._vol_after is not None:
            try:
                self.root.after_cancel(self._vol_after)
            except Exception:
                pass
            self._vol_after = None
        self._vol_after = self.root.after(delay_ms, lambda: self._send_volume(vol_int))

    def _on_volume_slide(self, val):
        """
        Wird bei jeder Bewegung des Reglers aufgerufen.
        -> Sofort Prozentanzeige + Icon aktualisieren
        -> API-Call nur debounced senden
        """
        try:
            vol_int = int(float(val))
        except Exception:
            return
        self.volume_label_var.set(f"{vol_int}%")
        self._update_mute_icon(vol_int)
        # Debounced Senden
        self._schedule_send_volume(vol_int, delay_ms=200)

    def _vol_press(self, event):
        self._user_adjusting = True

    def _vol_release(self, event):
        self._user_adjusting = False
        # Beim Loslassen sofort senden (finaler Wert)
        try:
            vol_int = int(float(self.volume_var.get()))
            self.volume_label_var.set(f"{vol_int}%")
            self._update_mute_icon(vol_int)
            self._send_volume(vol_int)
        except Exception:
            pass

    def step_volume(self, delta):
        """-10/+10 Buttons."""
        try:
            cur = int(float(self.volume_var.get()))
        except Exception:
            cur = self._last_volume_seen if self._last_volume_seen is not None else 50
        new_v = max(0, min(100, cur + delta))
        self.volume_var.set(new_v)
        self.volume_label_var.set(f"{new_v}%")
        self._update_mute_icon(new_v)
        self._send_volume(new_v)

    def toggle_mute(self):
        """Mute/Unmute: merkt sich letzte >0 Lautstärke."""
        try:
            cur = int(float(self.volume_var.get()))
        except Exception:
            cur = self._last_volume_seen if self._last_volume_seen is not None else 50

        if cur == 0:
            # Unmute -> auf gemerkte Lautstärke (falls 0/None, fallback 30)
            target = self._pre_mute_volume or 30
            if target <= 0:
                target = 30
            target = max(0, min(100, int(target)))
            self.volume_var.set(target)
            self.volume_label_var.set(f"{target}%")
            self._update_mute_icon(target)
            self._send_volume(target)
        else:
            # Mute -> aktuellen Wert merken und auf 0 setzen
            self._pre_mute_volume = cur
            self.volume_var.set(0)
            self.volume_label_var.set("0%")
            self._update_mute_icon(0)
            self._send_volume(0)

    # ---------- Suche / Auswahl ----------
    def do_search(self):
        """Suche Tracks, Alben und Playlists und fülle die Combobox."""
        if not self.ready:
            return
        q = self.search_entry_var.get().strip()
        if not q:
            return
        try:
            # getrennte Limits geben eine gute Mischung
            tracks = self.sp.search(q=q, type="track", limit=10).get("tracks", {}).get("items", [])
            albums = self.sp.search(q=q, type="album", limit=5).get("albums", {}).get("items", [])
            playlists = self.sp.search(q=q, type="playlist", limit=5).get("playlists", {}).get("items", [])

            items_display = []
            self.result_cache.clear()

            # Tracks
            for it in tracks:
                name = it.get("name", "?")
                artist = it.get("artists", [{}])[0].get("name", "?")
                disp = f"[Track] {name} – {artist}"
                self.result_cache[disp] = {"type": "track", "uri": it.get("uri")}
                items_display.append(disp)

            # Alben
            for it in albums:
                name = it.get("name", "?")
                artist = (it.get("artists") or [{}])[0].get("name", "?")
                disp = f"[Album] {name} – {artist}"
                self.result_cache[disp] = {"type": "album", "context_uri": it.get("uri")}
                items_display.append(disp)

            # Playlists
            for it in playlists:
                name = it.get("name", "?")
                owner = (it.get("owner") or {}).get("display_name", "?")
                disp = f"[Playlist] {name} – {owner}"
                self.result_cache[disp] = {"type": "playlist", "context_uri": it.get("uri")}
                items_display.append(disp)

            if items_display:
                self.result_box["values"] = items_display
                self.search_var.set(items_display[0])
            else:
                self.result_box["values"] = ["Kein Treffer"]
                self.search_var.set("Kein Treffer")

        except Exception as e:
            logging.error(f"Spotify Suche Fehler: {e}")
            self.result_box["values"] = ["Fehler bei der Suche"]
            self.search_var.set("Fehler bei der Suche")

    def play_selected(self, event=None):
        """Abspielen je nach Typ (Track via uris=…, Album/Playlist via context_uri=…)."""
        if not self.ready:
            return
        disp = self.search_var.get()
        meta = self.result_cache.get(disp)
        if not meta:
            return
        try:
            if meta["type"] == "track" and meta.get("uri"):
                self.sp.start_playback(uris=[meta["uri"]])
                self.song_var.set(f"Spiele: {disp}")
            elif meta["type"] in ("album", "playlist") and meta.get("context_uri"):
                self.sp.start_playback(context_uri=meta["context_uri"])
                self.song_var.set(f"Spiele aus: {disp}")
        except Exception as e:
            logging.error(f"Spotify Play Fehler: {e}")
