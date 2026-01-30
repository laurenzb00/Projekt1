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
