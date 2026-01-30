import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw

# --- Farbpalette ---
BG_MAIN = "#1E1E1E"
BG_CONTAINER = "#282828"
WHITE = "#FFFFFF"
LIGHT_GRAY = "#A0A0A0"
DARK_GRAY = "#404040"
ACTIVE_BORDER = WHITE
INACTIVE_BORDER = BG_CONTAINER

class SpotifyDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1024x524")
        self.resizable(False, False)
        self.configure(bg=BG_MAIN)
        self.title("Spotify Dashboard Modern")
        self.init_ui()

    def init_ui(self):
        # Hauptcontainer
        self.container = ctk.CTkFrame(self, fg_color=BG_CONTAINER, corner_radius=20, border_width=2, border_color=LIGHT_GRAY)
        self.container.place(relx=0.5, rely=0.5, anchor="center", width=980, height=480)

        # Sektion 1: Album & Track Info
        self.album_frame = ctk.CTkFrame(self.container, fg_color=BG_CONTAINER, corner_radius=20)
        self.album_frame.place(x=20, y=20, width=360, height=440)
        # Album Cover
        self.cover_canvas = ctk.CTkCanvas(self.album_frame, width=320, height=320, bg=BG_CONTAINER, highlightthickness=0)
        self.cover_canvas.place(x=20, y=10)
        self.cover_canvas.create_rectangle(0, 0, 320, 320, outline=LIGHT_GRAY, width=2)
        self.cover_canvas.create_text(160, 160, text="320x320", fill=LIGHT_GRAY, font=("Arial", 28, "bold"))
        # Track Info
        self.track_title = ctk.CTkLabel(self.album_frame, text="Track Title", font=("Arial", 24, "bold"), text_color=WHITE)
        self.track_title.place(x=20, y=340, width=320, anchor="nw")
        self.artist_label = ctk.CTkLabel(self.album_frame, text="Artist Name", font=("Arial", 18), text_color=LIGHT_GRAY)
        self.artist_label.place(x=20, y=380, width=320, anchor="nw")

        # Sektion 2: Playback Controls & Lautstärke
        self.controls_frame = ctk.CTkFrame(self.container, fg_color=BG_CONTAINER, corner_radius=20)
        self.controls_frame.place(x=400, y=20, width=380, height=440)
        # Playback Buttons
        self.prev_btn = ctk.CTkButton(self.controls_frame, text="⏮", width=60, height=60, fg_color=DARK_GRAY, text_color=WHITE, corner_radius=30, font=("Arial", 28), command=self.prev_track)
        self.prev_btn.place(x=30, y=60)
        self.play_btn = ctk.CTkButton(self.controls_frame, text="▶", width=80, height=80, fg_color=DARK_GRAY, text_color=WHITE, corner_radius=40, font=("Arial", 36, "bold"), command=self.toggle_play_pause)
        self.play_btn.place(x=150, y=40)
        self.next_btn = ctk.CTkButton(self.controls_frame, text="⏭", width=60, height=60, fg_color=DARK_GRAY, text_color=WHITE, corner_radius=30, font=("Arial", 28), command=self.skip_track)
        self.next_btn.place(x=290, y=60)
        # Lautstärke Slider
        self.volume_var = ctk.DoubleVar(value=50)
        self.volume_slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100, variable=self.volume_var, width=300, height=15, fg_color=LIGHT_GRAY, progress_color=WHITE, button_color=WHITE, button_hover_color=LIGHT_GRAY, command=self.set_volume)
        self.volume_slider.place(x=40, y=180)

        # Sektion 3: Geräteauswahl
        self.devices_frame = ctk.CTkFrame(self.container, fg_color=BG_CONTAINER, corner_radius=20)
        self.devices_frame.place(x=800, y=20, width=160, height=440)
        self.devices_label = ctk.CTkLabel(self.devices_frame, text="Geräte", font=("Arial", 18, "bold"), text_color=WHITE)
        self.devices_label.place(x=10, y=10)
        self.devices_list_frame = ctk.CTkScrollableFrame(self.devices_frame, fg_color=BG_CONTAINER, corner_radius=0, width=140, height=370)
        self.devices_list_frame.place(x=10, y=50)
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
            btn = ctk.CTkButton(self.devices_list_frame, text=dev['name'], width=130, height=50, fg_color=DARK_GRAY, text_color=WHITE, corner_radius=10, font=("Arial", 16), border_width=2, border_color=border)
            btn.pack(pady=6)
            self.device_buttons.append(btn)

if __name__ == "__main__":
    app = SpotifyDashboard()
    app.mainloop()
import customtkinter as ctk
from PIL import Image, ImageTk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#121212"
WHITE = "#FFFFFF"
GRAY = "#B3B3B3"
SPOTIFY_GREEN = "#1DB954"

class SpotifyDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1024x600")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.title("Spotify Touch Dashboard")

        # --- LINKS: Album-Sektion ---
        album_frame = ctk.CTkFrame(self, width=360, height=600, fg_color=BG, corner_radius=0)
        album_frame.place(x=0, y=0)
        self.album_img = ctk.CTkLabel(album_frame, text="", width=320, height=320)
        self.album_img.place(x=20, y=40)
        self.set_album_cover()
        self.song_title = ctk.CTkLabel(album_frame, text="Song Title", font=("Arial", 28, "bold"), text_color=WHITE)
        self.song_title.place(x=20, y=380)
        self.artist = ctk.CTkLabel(album_frame, text="Artist Name", font=("Arial", 20), text_color=GRAY)
        self.artist.place(x=20, y=420)

        # --- MITTE: Control-Sektion ---
        control_frame = ctk.CTkFrame(self, width=380, height=600, fg_color=BG, corner_radius=0)
        control_frame.place(x=360, y=0)
        self.prev_btn = ctk.CTkButton(control_frame, text="⏮", width=60, height=60, font=("Arial", 32), command=self.prev_track)
        self.prev_btn.place(x=40, y=220)
        self.play_btn = ctk.CTkButton(control_frame, text="⏯", width=100, height=100, font=("Arial", 44), corner_radius=50, command=self.play_pause)
        self.play_btn.place(x=140, y=200)
        self.next_btn = ctk.CTkButton(control_frame, text="⏭", width=60, height=60, font=("Arial", 32), command=self.next_track)
        self.next_btn.place(x=260, y=220)
        self.volume_label = ctk.CTkLabel(control_frame, text="Lautstärke", font=("Arial", 18), text_color=WHITE)
        self.volume_label.place(x=40, y=340)
        self.volume_slider = ctk.CTkSlider(control_frame, from_=0, to=100, width=300, height=40, command=self.set_volume)
        self.volume_slider.set(50)
        self.volume_slider.place(x=40, y=370)

        # --- RECHTS: Device Picker Sidebar ---
        device_frame = ctk.CTkFrame(self, width=284, height=600, fg_color=BG, corner_radius=0)
        device_frame.place(x=740, y=0)
        self.device_title = ctk.CTkLabel(device_frame, text="Geräte", font=("Arial", 24, "bold"), text_color=WHITE)
        self.device_title.place(x=17, y=30)
        self.device_list_frame = ctk.CTkScrollableFrame(device_frame, width=250, height=480, fg_color=BG)
        self.device_list_frame.place(x=17, y=80)
        self.device_buttons = []
        self.update_devices()

    def set_album_cover(self):
        # Placeholder: Load and round image
        img = Image.new("RGB", (320, 320), color=SPOTIFY_GREEN)
        mask = Image.new("L", (320, 320), 0)
        ctk_radius = 20
        for x in range(320):
            for y in range(320):
                if (x-160)**2 + (y-160)**2 < (160-ctk_radius)**2:
                    mask.putpixel((x, y), 255)
        img.putalpha(mask)
        tk_img = ImageTk.PhotoImage(img)
        self.album_img.configure(image=tk_img)
        self.album_img.image = tk_img

    def play_pause(self):
        print("Play/Pause pressed")

    def next_track(self):
        print("Next Track pressed")

    def prev_track(self):
        print("Previous Track pressed")

    def set_volume(self, val):
        print(f"Volume set to {int(val)}")

    def update_devices(self):
        # Simulierte Geräteliste
        devices = [
            {"name": "Wohnzimmer", "type": "Speaker", "active": True},
            {"name": "Küche", "type": "TV", "active": False},
            {"name": "Bad", "type": "Speaker", "active": False},
        ]
        # Clear old buttons
        for btn in self.device_buttons:
            btn.destroy()
        self.device_buttons = []
        for i, dev in enumerate(devices):
            color = SPOTIFY_GREEN if dev["active"] else BG
            text_color = WHITE if dev["active"] else GRAY
            btn = ctk.CTkButton(self.device_list_frame, text=f"{dev['name']} ({dev['type']})", width=250, height=55, fg_color=color, text_color=text_color, font=("Arial", 18, "bold"), corner_radius=10)
            btn.grid(row=i, column=0, pady=8, padx=0)
            self.device_buttons.append(btn)

if __name__ == "__main__":
    app = SpotifyDashboard()
    app.mainloop()
