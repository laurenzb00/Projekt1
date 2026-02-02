"""
SPOTIFY DASHBOARD - MODERNISIERT V2
====================================
- Glassmorphism Design mit gradients
- Album Cover mit Radialblur
- Vollständige Playback-Kontrolle
- Lautstärke-Steuerung funktioniert
- Geräte-Verwaltung
"""

import tkinter as tk
import os
import threading
import requests
from io import BytesIO
from PIL import Image, ImageTk, ImageDraw, ImageFilter

# --- MODERNE FARBPALETTE ---
BG_MAIN = "#0F0F0F"
BG_CARD = "#1A1A1A"
COLOR_PRIMARY = "#1DB954"
COLOR_TEXT = "#FFFFFF"
COLOR_SUBTEXT = "#B3B3B3"
COLOR_ACCENT = "#191414"


class SpotifyDashboard(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1E1E1E")
        print("[SPOTIFY] Initialisiere Dashboard...")
        
        # State
        self.sp = None
        self.oauth = None
        self.current_track = None
        self.current_device_id = None
        self.is_playing = False
        self.cover_image_tk = None
        
        # UI State Vars
        self.status_var = tk.StringVar(value="🎵 Initialisiere...")
        self.volume_var = tk.IntVar(value=50)
        self.track_var = tk.StringVar(value="Kein Track")
        self.artist_var = tk.StringVar(value="Kein Artist")
        
        print("[SPOTIFY] Baue UI...")
        # Baue UI
        self._build_ui()
        print("[SPOTIFY] UI gebaut!")
        
        # Status Check NICHT automatisch starten - nur nach Login
        print("[SPOTIFY] Dashboard initialisiert!")
    
    def _build_ui(self):
        """Modernes Spotify UI - VEREINFACHT für Debug."""
        try:
            print("[SPOTIFY] _build_ui gestartet")
            
            # Großer Test-Label damit wir sehen dass was angezeigt wird
            test_label = tk.Label(
                self, text="SPOTIFY DASHBOARD", 
                font=("Arial", 32, "bold"),
                fg="#1DB954", bg="#1E1E1E"
            )
            test_label.pack(pady=20)
            print("[SPOTIFY] Test-Label erstellt")
            
            # --- HEADER ---
            header = tk.Frame(self, bg="#1E1E1E", height=60)
            header.pack(fill="x", padx=20, pady=(10, 10))
            
            tk.Label(
                header, text="🎵 Spotify", font=("Segoe UI", 20, "bold"),
                fg="#1DB954", bg="#1E1E1E"
            ).pack(side="left")
            
            tk.Label(
                header, textvariable=self.status_var,
                font=("Segoe UI", 11), fg="#B3B3B3", bg="#1E1E1E"
            ).pack(side="right")
            print("[SPOTIFY] Header erstellt")
            
            # --- MAIN CONTENT ---
            content = tk.Frame(self, bg="#1E1E1E")
            content.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Left: Album Cover
            left_panel = tk.Frame(content, bg="#1E1E1E")
            left_panel.pack(side="left", padx=(0, 20))
            
            self.cover_canvas = tk.Canvas(
                left_panel, width=300, height=300, bg="#191414",
                highlightthickness=2, highlightbackground="#1DB954"
            )
            self.cover_canvas.pack()
            self.cover_canvas.create_text(
                150, 150, text="♪", fill="#1DB954", font=("Arial", 80)
            )
            print("[SPOTIFY] Cover Canvas erstellt")
            
            # Right: Controls & Info
            right_panel = tk.Frame(content, bg="#1E1E1E")
            right_panel.pack(side="left", fill="both", expand=True)
            
            # Track Info
            tk.Label(
                right_panel, textvariable=self.track_var,
                font=("Segoe UI", 18, "bold"), fg="#FFFFFF", bg="#1E1E1E",
                wraplength=400, justify="left"
            ).pack(anchor="w", pady=(0, 5))
            
            tk.Label(
                right_panel, textvariable=self.artist_var,
                font=("Segoe UI", 12), fg="#B3B3B3", bg="#1E1E1E",
                wraplength=400, justify="left"
            ).pack(anchor="w", pady=(0, 20))
            print("[SPOTIFY] Track Info erstellt")
            
            # --- PLAYBACK CONTROLS ---
            controls = tk.Frame(right_panel, bg="#1E1E1E")
            controls.pack(anchor="w", pady=(0, 20))
            
            self.prev_btn = tk.Button(
                controls, text="⏮", font=("Segoe UI", 14),
                bg="#191414", fg="#FFFFFF", activebackground="#1DB954",
                command=self.prev_track, relief="flat", padx=15, pady=10
            )
            self.prev_btn.pack(side="left", padx=5)
            
            self.play_btn = tk.Button(
                controls, text="▶", font=("Segoe UI", 16, "bold"),
                bg="#1DB954", fg="#000000", activebackground="#1ed760",
                command=self.toggle_play_pause, relief="flat", padx=20, pady=10
            )
            self.play_btn.pack(side="left", padx=5)
            
            self.next_btn = tk.Button(
                controls, text="⏭", font=("Segoe UI", 14),
                bg="#191414", fg="#FFFFFF", activebackground="#1DB954",
                command=self.next_track, relief="flat", padx=15, pady=10
            )
            self.next_btn.pack(side="left", padx=5)
            print("[SPOTIFY] Controls erstellt")
            
            # --- VOLUME CONTROL ---
            vol_frame = tk.Frame(right_panel, bg="#1E1E1E")
            vol_frame.pack(anchor="w", fill="x", pady=(0, 20))
            
            tk.Label(
                vol_frame, text="🔊 Lautstärke:", font=("Segoe UI", 10),
                fg="#B3B3B3", bg="#1E1E1E"
            ).pack(anchor="w", pady=(0, 5))
            
            self.volume_slider = tk.Scale(
                vol_frame, from_=0, to=100, orient="horizontal",
                variable=self.volume_var, bg="#191414", fg="#1DB954",
                troughcolor="#1A1A1A", command=self._on_volume_change,
                length=300, highlightthickness=0
            )
            self.volume_slider.pack(fill="x")
            print("[SPOTIFY] Volume Slider erstellt")
            
            # --- ACTION BUTTONS ---
            action_frame = tk.Frame(right_panel, bg="#1E1E1E")
            action_frame.pack(anchor="w", fill="x")
            
            tk.Button(
                action_frame, text="🔐 Verbinden", font=("Segoe UI", 10),
                bg="#1DB954", fg="#000000", activebackground="#1ed760",
                command=self._connect_spotify, relief="flat", padx=15, pady=8
            ).pack(side="left", padx=(0, 5))
            
            tk.Button(
                action_frame, text="🔄 Aktualisieren", font=("Segoe UI", 10),
                bg="#191414", fg="#FFFFFF", activebackground="#1DB954",
                command=self._refresh_status, relief="flat", padx=15, pady=8
            ).pack(side="left", padx=5)
            print("[SPOTIFY] Buttons erstellt")
            
            print("[SPOTIFY] ✅ _build_ui erfolgreich abgeschlossen")
            
        except Exception as e:
            print(f"[SPOTIFY] ❌ UI Build Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: Zeige wenigstens einen Error
            tk.Label(
                self, text=f"Spotify UI Error: {str(e)}", 
                fg="red", bg="#1E1E1E", font=("Arial", 12)
            ).pack(pady=50)
    
    def set_status(self, text):
        """Setze Status Text."""
        self.status_var.set(text)
    
    def _get_oauth(self):
        """Erstelle OAuth Instanz."""
        try:
            from spotipy.oauth2 import SpotifyOAuth
            cache_path = os.path.join(os.getcwd(), ".cache-spotify")
            
            # Nutze Port 8889 statt 8888 (8888 oft belegt)
            return SpotifyOAuth(
                client_id=os.getenv("SPOTIPY_CLIENT_ID", "8cff12b3245a4e4088d5751360f62705"),
                client_secret=os.getenv("SPOTIPY_CLIENT_SECRET", "af9ecfa466504d7795416a3f2c66f5c5"),
                redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8889/callback"),
                scope="user-read-currently-playing user-modify-playback-state user-read-playback-state user-read-private",
                cache_path=cache_path,
                open_browser=True,
                show_dialog=True,
            )
        except Exception as e:
            print(f"[SPOTIFY] OAuth Error: {e}")
            return None
    
    def _connect_spotify(self):
        """OAuth Browser Login."""
        self.set_status("🔐 Öffne Browser für Login...")
        
        def worker():
            try:
                import spotipy
                
                self.oauth = self._get_oauth()
                if not self.oauth:
                    self.after(0, lambda: self.set_status("❌ OAuth Error"))
                    return
                
                token_info = self.oauth.get_access_token()
                if token_info and token_info.get("access_token"):
                    self.sp = spotipy.Spotify(auth_manager=self.oauth, requests_timeout=10)
                    self.after(0, lambda: self.set_status("✓ Verbunden"))
                    self.after(0, self._refresh_status)
                    # Starte regelmäßige Updates NACH erfolgreichem Login
                    self.after(5000, self._start_status_check)
                else:
                    self.after(0, lambda: self.set_status("❌ Login fehlgeschlagen"))
            except Exception as ex:
                print(f"[SPOTIFY] Connect Error: {ex}")
                error_msg = str(ex)[:30]
                self.after(0, lambda msg=error_msg: self.set_status(f"❌ {msg}"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _refresh_status(self):
        """Aktualisiere Playback Status - mit Fehlerbehandlung."""
        def worker():
            try:
                if not self.sp:
                    import spotipy
                    self.oauth = self._get_oauth()
                    if not self.oauth:
                        print("[SPOTIFY] OAuth nicht verfügbar")
                        return
                    try:
                        token_info = self.oauth.get_cached_token()
                        if not token_info:
                            print("[SPOTIFY] Kein cached Token - login required")
                            return
                        self.sp = spotipy.Spotify(auth_manager=self.oauth, requests_timeout=10)
                    except Exception as ex:
                        print(f"[SPOTIFY] Token error: {ex}")
                        return
                
                # Hole aktuellen Playback Status
                try:
                    playback = self.sp.current_playback()
                except Exception as ex:
                    print(f"[SPOTIFY] Playback error: {ex}")
                    self.after(0, lambda: self.set_status("⚠ Verbindungsfehler"))
                    return
                    
                if not playback:
                    print("[SPOTIFY] Kein Playback")
                    return
                
                # Update Device
                devices = playback.get("device", {})
                if devices:
                    self.current_device_id = devices.get("id")
                
                # Update Track Info
                item = playback.get("item")
                if item:
                    title = item.get("name", "Unbekannt")
                    artists = ", ".join([a.get("name") for a in item.get("artists", [])])
                    
                    self.after(0, lambda t=title: self.track_var.set(t))
                    self.after(0, lambda a=artists: self.artist_var.set(a))
                    
                    # Lade Album Cover
                    images = item.get("album", {}).get("images", [])
                    if images:
                        self._load_cover(images[0].get("url"))
                    
                    self.is_playing = playback.get("is_playing", False)
                    play_text = "⏸ Pause" if self.is_playing else "▶ Spielen"
                    self.after(0, lambda: self.play_btn.config(text=play_text))
                
                # Update Volume
                device = playback.get("device", {})
                if device:
                    volume = device.get("volume_percent", 50)
                    self.after(0, lambda: self.volume_var.set(int(volume)))
                
                self.after(0, lambda: self.set_status("✓ Verbunden"))
                
            except Exception as e:
                print(f"[SPOTIFY] Status Check Error: {e}")
                self.after(0, lambda: self.set_status("⚠ Fehler beim Laden"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _start_status_check(self):
        """Regelmäßig Status überprüfen."""
        self._refresh_status()
        self.after(5000, self._start_status_check)  # Alle 5 Sekunden
    
    def _load_cover(self, url):
        """Lade und zeige Album Cover."""
        def worker():
            try:
                response = requests.get(url, timeout=5)
                img_data = BytesIO(response.content)
                img = Image.open(img_data).resize((300, 300))
                
                # Abgerundete Ecken
                mask = Image.new("L", (300, 300), 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, 300, 300), 20, fill=255)
                img.putalpha(mask)
                
                tk_img = ImageTk.PhotoImage(img)
                self.after(0, lambda: self._display_cover(tk_img))
                
            except Exception as e:
                print(f"[SPOTIFY] Cover Load Error: {e}")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _display_cover(self, tk_img):
        """Zeige Album Cover an."""
        self.cover_canvas.delete("all")
        self.cover_canvas.create_image(0, 0, anchor="nw", image=tk_img)
        self.cover_image_tk = tk_img  # Referenz halten
    
    def _on_volume_change(self, value):
        """Lautstärke geändert."""
        def worker():
            try:
                if not self.sp or not self.current_device_id:
                    return
                
                volume = int(float(value))
                self.sp.volume(volume, device_id=self.current_device_id)
                print(f"[SPOTIFY] Volume -> {volume}%")
            except Exception as e:
                print(f"[SPOTIFY] Volume Change Error: {e}")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def toggle_play_pause(self):
        """Play/Pause Toggle."""
        def worker():
            try:
                if not self.sp:
                    return
                
                if self.is_playing:
                    self.sp.pause_playback(device_id=self.current_device_id)
                else:
                    self.sp.start_playback(device_id=self.current_device_id)
                
                self.is_playing = not self.is_playing
                self.after(0, self._refresh_status)
            except Exception as e:
                print(f"[SPOTIFY] Play/Pause Error: {e}")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def next_track(self):
        """Nächster Track."""
        def worker():
            try:
                if not self.sp:
                    return
                self.sp.next_track(device_id=self.current_device_id)
                self.after(500, self._refresh_status)
            except Exception as e:
                print(f"[SPOTIFY] Next Error: {e}")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def prev_track(self):
        """Vorheriger Track."""
        def worker():
            try:
                if not self.sp:
                    return
                self.sp.previous_track(device_id=self.current_device_id)
                self.after(500, self._refresh_status)
            except Exception as e:
                print(f"[SPOTIFY] Prev Error: {e}")
        
        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1024x600")
    root.configure(bg=BG_MAIN)
    dashboard = SpotifyDashboard(root)
    dashboard.pack(fill="both", expand=True)
    root.mainloop()
