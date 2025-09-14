import threading
import logging
import Wechselrichter
import BMKDATEN
import visualisierung_live
import signal
from datetime import datetime

# Logging einrichten
logging.basicConfig(
    filename="datenerfassung.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Shutdown-Signal für Threads
shutdown_event = threading.Event()


def run_wechselrichter():
    try:
        while not shutdown_event.is_set():
            Wechselrichter.run()
    except Exception as e:
        logging.error(f"Wechselrichter-Thread Fehler: {e}")


def run_bmkdaten():
    try:
        while not shutdown_event.is_set():
            BMKDATEN.main()
    except Exception as e:
        logging.error(f"BMKDATEN-Thread Fehler: {e}")


def main():
    # --- Backend-Threads starten ---
    threads = [
        threading.Thread(target=run_wechselrichter, daemon=True),
        threading.Thread(target=run_bmkdaten, daemon=True),
    ]
    for t in threads:
        t.start()

    # --- Live-Visualisierung im Hauptthread ---
    root = visualisierung_live.tk.Tk()
    root.geometry("1024x600")
    app = visualisierung_live.LivePlotApp(root)

    # --- Tkinter-Variablen für Spotify ---
    song_var = visualisierung_live.tk.StringVar(value="Kein Song läuft")
    progress_var = visualisierung_live.tk.DoubleVar(value=0.0)
    device_var = visualisierung_live.tk.StringVar(value="Kein Gerät gefunden")
    volume_var = visualisierung_live.tk.DoubleVar(value=50.0)

    # --- Spotify Integration ---
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    from PIL import Image, ImageTk
    import requests, io
    import queue

    # Queue für Cover-Bilder (asynchron)
    image_queue = queue.Queue()

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id="8cff12b3245a4e4088d5751360f62705",
        client_secret="af9ecfa466504d7795416a3f2c66f5c5",
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-read-currently-playing user-modify-playback-state user-read-playback-state"
    ))

    # Spotify-Tab anlegen
    spotify_frame = visualisierung_live.ttk.Frame(app.notebook)
    app.notebook.add(spotify_frame, text="Spotify")
    spotify_frame.configure(style="Dark.TFrame")

    main_spotify_container = visualisierung_live.tk.Frame(spotify_frame, bg="#222")
    main_spotify_container.pack(fill="both", expand=True)

    left_frame = visualisierung_live.tk.Frame(main_spotify_container, bg="#222")
    left_frame.pack(side="left", fill="y", padx=30, pady=30)
    album_img_label = visualisierung_live.tk.Label(left_frame, bg="#222")
    album_img_label.pack()

    right_frame = visualisierung_live.tk.Frame(main_spotify_container, bg="#222")
    right_frame.pack(side="right", fill="both", expand=True, padx=30, pady=30)

    # Widgets
    song_label = visualisierung_live.ttk.Label(
        right_frame, textvariable=song_var,
        style="Dark.TLabel", anchor="center",
        justify="center", font=("Arial", 20, "bold")
    )
    song_label.pack(pady=10, fill="x")

    progress_bar = visualisierung_live.ttk.Progressbar(
        right_frame, variable=progress_var, maximum=100, length=350
    )
    progress_bar.pack(pady=10)

    device_box = visualisierung_live.ttk.Combobox(
        right_frame, textvariable=device_var,
        font=("Arial", 14), width=30, state="readonly"
    )
    device_box.pack(pady=10)

    btn_frame = visualisierung_live.tk.Frame(right_frame, bg="#222")
    btn_frame.pack(pady=20)
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

    volume_label = visualisierung_live.ttk.Label(right_frame, text="Lautstärke", style="Dark.TLabel")
    volume_label.pack(pady=(10, 0))
    volume_scale = visualisierung_live.ttk.Scale(
        right_frame, from_=0, to=100, variable=volume_var,
        orient="horizontal", length=350
    )
    volume_scale.pack(pady=5)

    # --- Spotify-Funktionen ---
    def update_devices():
        try:
            devices = sp.devices().get("devices", [])
            names = [f"{d.get('name','?')} ({d.get('type','?')})" for d in devices]
            ids = [d.get("id") for d in devices]
            device_box["values"] = names
            if devices:
                device_var.set(names[0])
            spotify_frame.device_ids = ids
        except Exception as e:
            logging.error(f"Spotify-Geräte Fehler: {e}")
            device_box["values"] = []
            device_var.set("Kein Gerät gefunden")
            spotify_frame.device_ids = []

    def set_device(event=None):
        idx = device_box.current()
        if hasattr(spotify_frame, "device_ids") and idx >= 0:
            try:
                sp.transfer_playback(spotify_frame.device_ids[idx], force_play=True)
            except Exception as e:
                logging.error(f"Spotify set_device Fehler: {e}")

    device_box.bind("<<ComboboxSelected>>", set_device)

    def fetch_cover(img_url):
        try:
            img_data = requests.get(img_url, timeout=5).content
            pil_img = Image.open(io.BytesIO(img_data)).resize((350, 350))
            tk_img = ImageTk.PhotoImage(pil_img)
            image_queue.put(tk_img)
        except Exception as e:
            logging.error(f"Spotify Cover Fehler: {e}")

    def update_spotify():
        try:
            current = sp.current_user_playing_track()
            if current and current.get("item"):
                item = current["item"]
                name = item.get("name", "Unbekannt")
                artist = item["artists"][0]["name"] if item.get("artists") else "?"
                album = item["album"]["name"]
                song_var.set(f"{name}\n{artist}\nAlbum: {album}")

                # Cover asynchron laden
                img_url = item["album"]["images"][0]["url"]
                threading.Thread(target=fetch_cover, args=(img_url,), daemon=True).start()

                duration = item.get("duration_ms") or 0
                progress = current.get("progress_ms") or 0
                progress_var.set(progress / duration * 100 if duration else 0)
            else:
                song_var.set("Kein Song läuft")
                progress_var.set(0)
        except Exception as e:
            logging.error(f"Spotify Update Fehler: {e}")
            song_var.set("Spotify Fehler")

        # Falls neues Bild verfügbar → anzeigen
        if not image_queue.empty():
            tk_img = image_queue.get()
            album_img_label.configure(image=tk_img)
            album_img_label.image = tk_img

        update_devices()
        app.root.after(5000, update_spotify)

    # --- Steuerungsfunktionen ---
    def play_pause():
        try:
            pb = sp.current_playback()
            if pb and pb.get("is_playing"):
                sp.pause_playback()
            else:
                sp.start_playback()
        except Exception as e:
            logging.error(f"Spotify play/pause Fehler: {e}")

    def next_track():
        try:
            sp.next_track()
        except Exception as e:
            logging.error(f"Spotify next Fehler: {e}")

    def prev_track():
        try:
            sp.previous_track()
        except Exception as e:
            logging.error(f"Spotify prev Fehler: {e}")

    def set_shuffle():
        try:
            pb = sp.current_playback()
            state = pb.get("shuffle_state", False)
            sp.shuffle(not state)
        except Exception as e:
            logging.error(f"Spotify shuffle Fehler: {e}")

    def set_repeat():
        try:
            pb = sp.current_playback()
            state = pb.get("repeat_state", "off")
            new_state = "track" if state == "off" else "off"
            sp.repeat(new_state)
        except Exception as e:
            logging.error(f"Spotify repeat Fehler: {e}")

    def set_volume(val):
        try:
            sp.volume(int(float(val)))
        except Exception as e:
            logging.error(f"Spotify volume Fehler: {e}")

    # Buttons verbinden
    play_btn.config(command=play_pause)
    next_btn.config(command=next_track)
    prev_btn.config(command=prev_track)
    shuffle_btn.config(command=set_shuffle)
    repeat_btn.config(command=set_repeat)
    volume_scale.config(command=set_volume)

    # Starten
    update_spotify()

    # Sauberes Beenden
    def on_close():
        logging.info("Programm wird beendet...")
        shutdown_event.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Programm mit STRG+C beendet.")
        shutdown_event.set()
