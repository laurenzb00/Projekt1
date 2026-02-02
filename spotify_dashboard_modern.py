import tkinter as tk
from PIL import Image, ImageTk, ImageDraw

# --- Farbpalette ---
BG_MAIN = "#1E1E1E"
BG_CONTAINER = "#282828"
WHITE = "#FFFFFF"
LIGHT_GRAY = "#A0A0A0"
DARK_GRAY = "#404040"
ACTIVE_BORDER = WHITE
INACTIVE_BORDER = BG_CONTAINER

class SpotifyDashboard(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.configure(width=1024, height=524)
        self.pack_propagate(False)
        self.init_ui()

    def init_ui(self):
        # Hauptcontainer
        self.container = tk.Frame(self, bg=BG_CONTAINER, highlightthickness=2, highlightbackground=LIGHT_GRAY)
        self.container.place(relx=0.5, rely=0.5, anchor="center", width=980, height=480)

        # Sektion 1: Album & Track Info
        self.album_frame = tk.Frame(self.container, bg=BG_CONTAINER)
        self.album_frame.place(x=20, y=20, width=360, height=440)
        # Album Cover
        self.cover_canvas = tk.Canvas(self.album_frame, width=320, height=320, bg=BG_CONTAINER, highlightthickness=0)
        self.cover_canvas.place(x=20, y=10)
        self.cover_canvas.create_rectangle(0, 0, 320, 320, outline=LIGHT_GRAY, width=2)
        self.cover_canvas.create_text(160, 160, text="320x320", fill=LIGHT_GRAY, font=("Arial", 28, "bold"))
        # Track Info
        self.track_title = tk.Label(self.album_frame, text="Track Title", font=("Arial", 24, "bold"), fg=WHITE, bg=BG_CONTAINER, wraplength=320)
        self.track_title.place(x=20, y=340, anchor="nw", width=320)
        self.artist_label = tk.Label(self.album_frame, text="Artist Name", font=("Arial", 18), fg=LIGHT_GRAY, bg=BG_CONTAINER, wraplength=320)
        self.artist_label.place(x=20, y=380, anchor="nw", width=320)

        # Sektion 2: Playback Controls & Lautstärke
        self.controls_frame = tk.Frame(self.container, bg=BG_CONTAINER)
        self.controls_frame.place(x=400, y=20, width=380, height=440)
        # Playback Buttons exakt wie im Screenshot
        btn_size = 60
        play_size = 70
        btn_radius = 10
        # Prev
        self.prev_btn = tk.Button(self.controls_frame, text="⏮", width=8, height=3, bg=DARK_GRAY, fg=WHITE, font=("Arial", 24), command=self.prev_track, relief=tk.FLAT, activebackground=LIGHT_GRAY)
        self.prev_btn.place(x=40, y=60, width=btn_size, height=btn_size)
        # Play
        self.play_btn = tk.Button(self.controls_frame, text="▶", width=8, height=3, bg=DARK_GRAY, fg=WHITE, font=("Arial", 28, "bold"), command=self.toggle_play_pause, relief=tk.FLAT, activebackground=LIGHT_GRAY)
        self.play_btn.place(x=155, y=55, width=play_size, height=play_size)
        # Next
        self.next_btn = tk.Button(self.controls_frame, text="⏭", width=8, height=3, bg=DARK_GRAY, fg=WHITE, font=("Arial", 24), command=self.skip_track, relief=tk.FLAT, activebackground=LIGHT_GRAY)
        self.next_btn.place(x=270, y=60, width=btn_size, height=btn_size)
        # Lautstärke Slider
        self.volume_var = tk.DoubleVar(value=50)
        self.volume_slider = tk.Scale(self.controls_frame, from_=0, to=100, variable=self.volume_var, orient=tk.HORIZONTAL, bg=DARK_GRAY, fg=LIGHT_GRAY, troughcolor=LIGHT_GRAY, command=self.set_volume, highlightthickness=0)
        self.volume_slider.place(x=60, y=160, width=260, height=20)

        # Shuffle/Repeat Buttons (klein, unterhalb)
        self.shuffle_btn = tk.Button(self.controls_frame, text="⏪ Shuffle", width=15, height=2, bg=DARK_GRAY, fg=WHITE, font=("Arial", 14), command=lambda: None, relief=tk.FLAT, activebackground=LIGHT_GRAY)
        self.shuffle_btn.place(x=40, y=210, width=120, height=36)
        self.repeat_btn = tk.Button(self.controls_frame, text="⏩ Repeat", width=15, height=2, bg=DARK_GRAY, fg=WHITE, font=("Arial", 14), command=lambda: None, relief=tk.FLAT, activebackground=LIGHT_GRAY)
        self.repeat_btn.place(x=220, y=210, width=120, height=36)

        # Sektion 3: Geräteauswahl
        self.devices_frame = tk.Frame(self.container, bg=BG_CONTAINER)
        self.devices_frame.place(x=800, y=20, width=160, height=440)
        self.devices_label = tk.Label(self.devices_frame, text="Geräte", font=("Arial", 18, "bold"), fg=WHITE, bg=BG_CONTAINER)
        self.devices_label.place(x=10, y=10)
        self.devices_list_frame = tk.Frame(self.devices_frame, bg=BG_CONTAINER)
        self.devices_list_frame.place(x=0, y=50, width=140, height=370)
        self.device_buttons = []

    def update_track_info(self, title, artist, cover_url=None):
        self.track_title.configure(text=title)
        self.artist_label.configure(text=artist)
        # Cover laden (optional)
        if cover_url:
            try:
                img = Image.open(cover_url).resize((320, 320))
                img = img.convert("RGBA")
                # Runde Ecken
                mask = Image.new("L", (320, 320), 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, 320, 320), 15, fill=255)
                img.putalpha(mask)
                tk_img = ImageTk.PhotoImage(img)
                self.cover_canvas.delete("all")
                self.cover_canvas.create_image(0, 0, anchor="nw", image=tk_img)
                self.cover_canvas.image = tk_img
            except Exception:
                pass
        else:
            self.cover_canvas.delete("all")
            self.cover_canvas.create_rectangle(0, 0, 320, 320, outline=LIGHT_GRAY, width=2)
            self.cover_canvas.create_text(160, 160, text="320x320", fill=LIGHT_GRAY, font=("Arial", 28, "bold"))

    def toggle_play_pause(self):
        # Platzhalter für Play/Pause
        if self.play_btn.cget("text") == "▶":
            self.play_btn.configure(text="⏸")
        else:
            self.play_btn.configure(text="▶")

    def skip_track(self):
        # Platzhalter für Next
        pass

    def prev_track(self):
        # Platzhalter für Previous
        pass

    def set_volume(self, value):
        # Platzhalter für Lautstärke
        pass

    def update_device_list(self, devices):
        # devices: [{'name': '...', 'id': '...', 'is_active': False}]
        for btn in self.device_buttons:
            btn.destroy()
        self.device_buttons = []
        for dev in devices:
            border = ACTIVE_BORDER if dev.get('is_active') else INACTIVE_BORDER
            btn = tk.Button(
                self.devices_list_frame,
                text=dev['name'],
                bg=DARK_GRAY, fg=WHITE,
                font=("Arial", 16),
                relief=tk.FLAT, activebackground=LIGHT_GRAY,
                anchor="w"
            )
            btn.pack(pady=6, padx=2, fill=tk.BOTH, expand=True)
            self.device_buttons.append(btn)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1024x524")
    dashboard = SpotifyDashboard(root)
    dashboard.pack(fill="both", expand=True)
    root.mainloop()

