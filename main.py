import threading
import logging
import time
import Wechselrichter
import BMKDATEN
import visualisierung_live  

logging.basicConfig(filename="datenerfassung.log", level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_wechselrichter():
    try:
        Wechselrichter.run()
    except Exception as e:
        logging.error(f"Wechselrichter-Thread Fehler: {e}")

def run_bmkdaten():
    try:
        BMKDATEN.main()
    except Exception as e:
        logging.error(f"BMKDATEN-Thread Fehler: {e}")

def main():
    threads = [
        threading.Thread(target=run_wechselrichter, daemon=True),
        threading.Thread(target=run_bmkdaten, daemon=True)
    ]
    for t in threads:
        t.start()

    # Starte die Live-Visualisierung im Hauptthread
    root = visualisierung_live.tk.Tk()
    app = visualisierung_live.LivePlotApp(root)

    # --- Spotify Integration ---
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id="8cff12b3245a4e4088d5751360f62705",
        client_secret="af9ecfa466504d7795416a3f2c66f5c5",
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-read-currently-playing user-modify-playback-state user-read-playback-state"
    ))

    # --- Spotify Tab ---
    spotify_frame = visualisierung_live.ttk.Frame(app.notebook)
    app.notebook.add(spotify_frame, text="Spotify")
    spotify_frame.configure(style="Dark.TFrame")
    style = visualisierung_live.ttk.Style()
    style.configure("Dark.TFrame", background="#222")
    style.configure("Dark.TLabel", background="#222", foreground="#fff", font=("Arial", 20, "bold"))
    style.configure("White.TButton", background="#333", foreground="#fff", font=("Arial", 18, "bold"), padding=12)
    style.configure("TProgressbar", troughcolor="#333", background="#4caf50", bordercolor="#222", lightcolor="#222", darkcolor="#222")

    song_var = visualisierung_live.tk.StringVar(value="Kein Song läuft")
    song_label = visualisierung_live.ttk.Label(spotify_frame, textvariable=song_var, style="Dark.TLabel", anchor="center", justify="center", font=("Arial", 20, "bold"))
    song_label.pack(pady=30, fill="x")

    album_img_label = visualisierung_live.tk.Label(spotify_frame, bg="#222")
    album_img_label.pack(pady=10, anchor="center")

    progress_var = visualisierung_live.tk.DoubleVar()
    progress_bar = visualisierung_live.ttk.Progressbar(spotify_frame, variable=progress_var, maximum=100, length=350)
    progress_bar.pack(pady=10)

    # Wiedergabegerät-Auswahl
    device_var = visualisierung_live.tk.StringVar()
    device_box = visualisierung_live.ttk.Combobox(spotify_frame, textvariable=device_var, font=("Arial", 14), width=30, state="readonly")
    device_box.pack(pady=10)

    btn_frame = visualisierung_live.tk.Frame(spotify_frame, bg="#222")
    btn_frame.pack(pady=30)
    prev_btn = visualisierung_live.ttk.Button(btn_frame, text="⏮", style="White.TButton", width=6)
    play_btn = visualisierung_live.ttk.Button(btn_frame, text="⏯", style="White.TButton", width=6)
    next_btn = visualisierung_live.ttk.Button(btn_frame, text="⏭", style="White.TButton", width=6)
    shuffle_btn = visualisierung_live.ttk.Button(btn_frame, text="🔀 Shuffle", style="White.TButton", width=10)
    repeat_btn = visualisierung_live.ttk.Button(btn_frame, text="🔁 Repeat", style="White.TButton", width=10)
    prev_btn.grid(row=0, column=0, padx=10)
    play_btn.grid(row=0, column=1, padx=10)
    next_btn.grid(row=0, column=2, padx=10)
    shuffle_btn.grid(row=1, column=0, columnspan=2, pady=10)
    repeat_btn.grid(row=1, column=2, pady=10)

    # Lautstärkeregler
    volume_var = visualisierung_live.tk.IntVar(value=50)
    volume_label = visualisierung_live.ttk.Label(spotify_frame, text="Lautstärke", style="Dark.TLabel")
    volume_label.pack(pady=(10,0))
    volume_scale = visualisierung_live.ttk.Scale(spotify_frame, from_=0, to=100, variable=volume_var, orient="horizontal", length=350)
    volume_scale.pack(pady=5)

    from PIL import Image, ImageTk
    import requests
    import io

    def update_devices():
        try:
            devices = sp.devices()["devices"]
            names = [f"{d['name']} ({d['type']})" for d in devices]
            ids = [d["id"] for d in devices]
            device_box["values"] = names
            if devices:
                device_var.set(names[0])
            spotify_frame.device_ids = ids
        except Exception:
            device_box["values"] = []
            device_var.set("Kein Gerät gefunden")
            spotify_frame.device_ids = []

    def set_device(event=None):
        idx = device_box.current()
        if hasattr(spotify_frame, "device_ids") and idx >= 0:
            try:
                sp.transfer_playback(spotify_frame.device_ids[idx], force_play=True)
            except Exception as e:
                song_var.set(f"Fehler: {e}")

    device_box.bind("<<ComboboxSelected>>", set_device)

    def update_spotify():
        try:
            current = sp.current_user_playing_track()
            if current and current["item"]:
                name = current["item"]["name"]
                artist = current["item"]["artists"][0]["name"]
                album = current["item"]["album"]["name"]
                song_var.set(f"{name}\n{artist}\nAlbum: {album}")
                img_url = current["item"]["album"]["images"][0]["url"]
                img_data = requests.get(img_url).content
                pil_img = Image.open(io.BytesIO(img_data)).resize((350, 350))
                tk_img = ImageTk.PhotoImage(pil_img)
                album_img_label.configure(image=tk_img)
                album_img_label.image = tk_img
                duration = current["item"]["duration_ms"]
                progress = current["progress_ms"]
                progress_var.set(progress / duration * 100 if duration else 0)
            else:
                song_var.set("Kein Song läuft")
                album_img_label.configure(image="")
                album_img_label.image = None
                progress_var.set(0)
        except Exception as e:
            song_var.set(f"Fehler: {e}")
            album_img_label.configure(image="")
            album_img_label.image = None
            progress_var.set(0)
        update_devices()
        app.root.after(5000, update_spotify)

    def play_pause():
        try:
            playback = sp.current_playback()
            if playback and playback["is_playing"]:
                sp.pause_playback()
            else:
                sp.start_playback()
        except Exception as e:
            song_var.set(f"Fehler: {e}")

    def next_track():
        try:
            sp.next_track()
        except Exception as e:
            song_var.set(f"Fehler: {e}")

    def prev_track():
        try:
            sp.previous_track()
        except Exception as e:
            song_var.set(f"Fehler: {e}")

    def set_shuffle():
        try:
            playback = sp.current_playback()
            shuffle_state = playback["shuffle_state"] if playback else False
            sp.shuffle(not shuffle_state)
        except Exception as e:
            song_var.set(f"Fehler: {e}")

    def set_repeat():
        try:
            playback = sp.current_playback()
            repeat_state = playback["repeat_state"] if playback else "off"
            new_state = "track" if repeat_state == "off" else "off"
            sp.repeat(new_state)
        except Exception as e:
            song_var.set(f"Fehler: {e}")

    def set_volume(val):
        try:
            sp.volume(int(float(val)))
        except Exception as e:
            song_var.set(f"Fehler: {e}")

    play_btn.config(command=play_pause)
    next_btn.config(command=next_track)
    prev_btn.config(command=prev_track)
    shuffle_btn.config(command=set_shuffle)
    repeat_btn.config(command=set_repeat)
    volume_scale.config(command=set_volume)

    update_spotify()
    # --- Ende Spotify Integration ---

    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Programm wurde beendet.")