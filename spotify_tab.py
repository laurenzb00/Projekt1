import logging
import threading
import queue
import os
import webbrowser
import time
import tkinter as tk
import ttkbootstrap as ttk # WICHTIG: ttkbootstrap nutzen für bootstyle
from ttkbootstrap.constants import *

class SpotifyTab:
    """
    Vollständige Spotify-Integration für ttkbootstrap Dark Theme.
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
        
        ttk.Button(
            info_frame, 
            text="Login im Browser", 
            bootstyle="success", 
            command=self._open_login_in_browser
        ).pack(pady=10)
        
        ttk.Label(info_frame, text="Nach dem Login bleibt der Token gespeichert.", bootstyle="secondary").pack()

    def _build_ui(self):
        self._clear_tab()
        main = ttk.Frame(self.tab_frame)
        main.pack(fill="both", expand=True)
        
        self._build_header(main, "Spotify Player")
        
        content = ttk.Frame(main)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        # --- LINKS: Cover & Info ---
        left = ttk.Frame(content)
        left.pack(side="left", fill="y", padx=(0, 20))

        self.album_img_label = ttk.Label(left, text="[Cover]", anchor="center", width=40) 
        self.album_img_label.pack(pady=(0, 15))

        now_playing_frame = ttk.Frame(left)
        now_playing_frame.pack(fill="x")
        
        ttk.Label(now_playing_frame, text="Aktueller Titel", font=("Arial", 12, "bold"), bootstyle="info").pack(anchor="w")
        
        # Songtitel
        ttk.Label(
            now_playing_frame, 
            textvariable=self.song_var, 
            font=("Arial", 12), 
            justify="center", 
            bootstyle="inverse-dark"
        ).pack(fill="x", pady=5)

        # Progress Bar
        progress_frame = ttk.Frame(now_playing_frame)
        progress_frame.pack(fill="x", pady=5)
        
        ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            maximum=100, 
            bootstyle="success-striped"
        ).pack(side="left", fill="x", expand=True)
        
        self.progress_time_label = ttk.Label(progress_frame, text="--:--", font=("Arial", 9))
        self.progress_time_label.pack(side="right", padx=5)

        # --- RECHTS: Steuerung ---
        right = ttk.Frame(content)
        right.pack(side="left", fill="both", expand=True)

        # 1. Gerät Auswahl
        dev_frame = ttk.Labelframe(right, text="Gerät", padding=10, bootstyle="secondary")
        dev_frame.pack(fill="x", pady=(0, 10))
        
        self.device_box = ttk.Combobox(
            dev_frame, 
            textvariable=self.device_var, 
            state="readonly", 
            font=("Arial", 11)
        )
        self.device_box.pack(fill="x")
        self.device_box.bind("<<ComboboxSelected>>", self.set_device)

        # 2. Player Buttons
        ctrl_frame = ttk.Labelframe(right, text="Steuerung", padding=10, bootstyle="secondary")
        ctrl_frame.pack(fill="x", pady=(0, 10))
        
        btn_row = ttk.Frame(ctrl_frame)
        btn_row.pack(pady=5)
        
        # Zeile 1: Prev, Play, Next
        ttk.Button(btn_row, text="<<", width=5, bootstyle="outline", command=self.prev_track).grid(row=0, column=0, padx=5)
        ttk.Button(btn_row, text="PLAY / PAUSE", width=15, bootstyle="primary", command=self.play_pause).grid(row=0, column=1, padx=5)
        ttk.Button(btn_row, text=">>", width=5, bootstyle="outline", command=self.next_track).grid(row=0, column=2, padx=5)
        
        # Zeile 2: Shuffle, Repeat
        btn_row2 = ttk.Frame(ctrl_frame)
        btn_row2.pack(pady=5)
        ttk.Button(btn_row2, text="Shuffle", width=10, bootstyle="outline", command=self.set_shuffle).grid(row=0, column=0, padx=5)
        ttk.Button(btn_row2, text="Repeat", width=10, bootstyle="outline", command=self.set_repeat).grid(row=0, column=1, padx=5)

        # 3. Lautstärke
        vol_frame = ttk.Labelframe(right, text="Lautstärke", padding=10, bootstyle="secondary")
        vol_frame.pack(fill="x", pady=(0, 10))
        
        inner_vol = ttk.Frame(vol_frame)
        inner_vol.pack(fill="x")
        
        self.mute_btn = ttk.Button(inner_vol, text="Mute", width=6, bootstyle="danger-outline", command=self.toggle_mute)
        self.mute_btn.pack(side="left", padx=5)
        
        ttk.Scale(
            inner_vol, 
            from_=0, 
            to=100, 
            variable=self.volume_var, 
            command=self._on_volume_slide
        ).pack(side="left", fill="x", expand=True, padx=10)
        
        ttk.Label(inner_vol, textvariable=self.volume_label_var, width=5).pack(side="right")

        # 4. Suche
        search_frame = ttk.Labelframe(right, text="Suche", padding=10, bootstyle="secondary")
        search_frame.pack(fill="both", expand=True)
        
        entry_row = ttk.Frame(search_frame)
        entry_row.pack(fill="x", pady=5)
        
        ttk.Entry(
            entry_row, 
            textvariable=self.search_entry_var, 
            font=("Arial", 11)
        ).pack(side="left", fill="x", expand=True, padx=(0,5))
        
        ttk.Button(entry_row, text="Suchen", bootstyle="info", command=self.do_search).pack(side="right")
        
        self.result_box = ttk.Combobox(
            search_frame, 
            textvariable=self.search_var, 
            state="readonly", 
            font=("Arial", 11)
        )
        self.result_box.pack(fill="x", pady=5)
        self.result_box.bind("<<ComboboxSelected>>", self.play_selected)

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
                open_browser=False,
                show_dialog=False,
            )
            token_info = self.oauth.get_cached_token()
            if token_info:
                self.sp = spotipy.Spotify(auth_manager=self.oauth)
                self.ready = True
                self.root.after(0, self._build_ui)
                self.status_text_var.set("Verbunden")
                self.root.after(0, self.update_spotify)
                return
            self.status_text_var.set("Login erforderlich")
        except Exception as e:
            self.root.after(0, self._build_prelogin_ui, str(e))

    def _open_login_in_browser(self):
        if not self.oauth: return
        try:
            url = self.oauth.get_authorize_url()
            webbrowser.open_new(url)
            self.status_text_var.set("Browser geöffnet...")
            threading.Thread(target=self._wait_for_token_thread, daemon=True).start()
        except Exception as e:
            self.status_text_var.set(f"Fehler: {e}")

    def _wait_for_token_thread(self):
        try:
            token_info = self.oauth.get_access_token(as_dict=True)
            if token_info and token_info.get("access_token"):
                import spotipy
                self.sp = spotipy.Spotify(auth_manager=self.oauth)
                self.ready = True
                self.root.after(0, self._build_ui)
                self.status_text_var.set("Verbunden")
                self.root.after(0, self.update_spotify)
        except Exception as e:
            self.root.after(0, self._build_prelogin_ui, str(e))

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

    def fetch_cover(self, img_url):
        try:
            from PIL import Image, ImageTk
            import requests, io
            img_data = requests.get(img_url, timeout=5).content
            pil_img = Image.open(io.BytesIO(img_data)).resize((300, 300))
            tk_img = ImageTk.PhotoImage(pil_img)
            self.image_queue.put(tk_img)
        except: pass

    def update_spotify(self):
        if not self.alive or not self.ready: return
        try:
            pb = self.sp.current_playback()
            if pb and pb.get("item"):
                item = pb["item"]
                name = item.get("name", "?")
                artist = item.get("artists", [{}])[0].get("name", "?")
                self.song_var.set(f"{name}\n{artist}")
                
                imgs = item.get("album", {}).get("images", [])
                if imgs:
                    threading.Thread(target=self.fetch_cover, args=(imgs[0]["url"],), daemon=True).start()
                
                dur = item.get("duration_ms", 1)
                prog = pb.get("progress_ms", 0)
                self.progress_var.set((prog/dur)*100)
                self.progress_time_label.config(text=f"{int(prog/1000)//60}:{int(prog/1000)%60:02d}")
                
                vol = (pb.get("device") or {}).get("volume_percent")
                if vol is not None and not self._user_adjusting:
                    self.volume_var.set(vol)
                    self.volume_label_var.set(f"{vol}%")
            else:
                self.song_var.set("Pause / Leer")
        except: pass
        
        if not self.image_queue.empty():
            tk_img = self.image_queue.get()
            self.album_img_label.configure(image=tk_img, text="")
            self.album_img_label.image = tk_img
            
        self._update_devices()
        if self.alive: self.root.after(5000, self.update_spotify)

    def play_pause(self):
        try:
            if self.sp.current_playback().get('is_playing'): self.sp.pause_playback()
            else: self.sp.start_playback(device_id=self.current_device_id)
        except: pass

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
        try: self.sp.volume(0 if self.volume_var.get() > 0 else 30)
        except: pass

    def _on_volume_slide(self, val):
        self.volume_label_var.set(f"{int(float(val))}%")
        if self._vol_after: self.root.after_cancel(self._vol_after)
        self._vol_after = self.root.after(200, lambda: self._send_vol(int(float(val))))
        
    def _send_vol(self, v):
        try: self.sp.volume(v)
        except: pass

    def do_search(self):
        q = self.search_entry_var.get()
        if not q or not self.sp: return
        try:
            res = self.sp.search(q, limit=5, type="track,album,playlist")
            items = []
            self.result_cache = {}
            # Tracks
            for t in (res.get("tracks",{}).get("items") or []):
                disp = f"[Song] {t['name']} - {t['artists'][0]['name']}"
                items.append(disp)
                self.result_cache[disp] = {"uri": t["uri"], "type": "track"}
            # Albums
            for a in (res.get("albums",{}).get("items") or []):
                disp = f"[Album] {a['name']} - {a['artists'][0]['name']}"
                items.append(disp)
                self.result_cache[disp] = {"uri": a["uri"], "type": "album"}
            self.result_box["values"] = items
            if items: self.result_box.current(0)
        except: pass

    def play_selected(self, event=None):
        sel = self.search_var.get()
        meta = self.result_cache.get(sel)
        if meta and self.sp:
            try:
                if meta["type"] == "track": self.sp.start_playback(uris=[meta["uri"]])
                else: self.sp.start_playback(context_uri=meta["uri"])
            except: pass