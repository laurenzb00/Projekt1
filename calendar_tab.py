import threading
import time
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import requests
import icalendar
import recurring_ical_events
import datetime
import pytz

# --- KONFIGURATION ---
# Tragen Sie hier alle Ihre Kalender-Links ein (durch Kommas getrennt):
ICAL_URLS = [
    "https://calendar.google.com/calendar/ical/laurenzbandzauner%40gmail.com/private-ee12d630b1b19a7f6754768f56f1a76c/basic.ics",
      "https://calendar.google.com/calendar/ical/ukrkc67kki9lm9lllj6l0je1ag%40group.calendar.google.com/public/basic.ics",
        "https://calendar.google.com/calendar/ical/h53q4om49cgioc2gff7j5r5pi4%40group.calendar.google.com/public/basic.ics",
          "https://calendar.google.com/calendar/ical/pehhg3u2a6ha539oql87fuao0j9aqteu%40import.calendar.google.com/public/basic.ics"  # Hauptkalender



]

class CalendarTab:
    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True
        
        # Variablen
        self.status_var = tk.StringVar(value="Lade Kalender...")
        self.events_data = [] 
        
        # Tab erstellen
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text=" Kalender ")
        
        self._build_header()
        
        # Scrollbarer Bereich
        self.canvas = tk.Canvas(self.tab_frame, highlightthickness=0)
        self.canvas.configure(bg="#2b3e50") # Hintergrund anpassen
        
        self.scrollbar = ttk.Scrollbar(self.tab_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)
        
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=1000)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        self.scrollbar.pack(side="right", fill="y")

        # Start Update Loop
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.alive = False

    def _build_header(self):
        header = ttk.Frame(self.tab_frame)
        header.pack(fill=X, padx=15, pady=(15, 5))
        ttk.Label(header, text="Nächste Termine", font=("Arial", 22, "bold"), bootstyle="inverse-dark").pack(side=LEFT)
        ttk.Label(header, textvariable=self.status_var, bootstyle="info").pack(side=RIGHT)
        
        # Refresh Button
        ttk.Button(header, text="↻", bootstyle="secondary-outline", command=lambda: threading.Thread(target=self._fetch_calendar, daemon=True).start()).pack(side=RIGHT, padx=10)

    def _loop(self):
        self._fetch_calendar()
        while self.alive:
            for _ in range(900): # 15 min
                if not self.alive: return
                time.sleep(1)
            self._fetch_calendar()

    def _fetch_calendar(self):
        self.status_var.set("Aktualisiere...")
        all_events = []
        error_occurred = False

        # Zeitraum: Heute bis in 60 Tagen
        now = datetime.datetime.now(pytz.utc)
        end = now + datetime.timedelta(days=60)

        for url in ICAL_URLS:
            if "http" not in url: continue
            try:
                response = requests.get(url.strip())
                response.raise_for_status()
                
                cal = icalendar.Calendar.from_ical(response.content)
                # Events auflösen
                events = recurring_ical_events.of(cal).between(now, end)
                all_events.extend(events)
                
            except Exception as e:
                print(f"Fehler bei Kalender-URL '{url}': {e}")
                error_occurred = True

        # Sortieren nach Startzeit (wichtig, da Events jetzt aus versch. Quellen kommen)
        try:
            all_events.sort(key=lambda x: x.get("DTSTART").dt)
        except:
            pass # Fallback falls Sortierung fehlschlägt

        # UI Update
        self.root.after(0, lambda: self._update_ui(all_events))
        
        timestamp = datetime.datetime.now().strftime('%H:%M')
        if error_occurred:
            self.status_var.set(f"Teilweise Fehler ({timestamp})")
        else:
            self.status_var.set(f"Aktuell ({timestamp})")

    def _update_ui(self, events):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        if not events:
            ttk.Label(self.scroll_frame, text="Keine Termine gefunden (oder URL fehlt).", font=("Arial", 12)).pack(pady=20)
            return

        current_day_str = ""
        
        # Limit auf z.B. 15 Termine, damit die Liste nicht explodiert
        for event in events[:20]:
            # Daten extrahieren
            summary = str(event.get("SUMMARY"))
            start_dt = event.get("DTSTART").dt
            
            # Ganztägig Check
            is_all_day = False
            if not isinstance(start_dt, datetime.datetime):
                start_dt = datetime.datetime.combine(start_dt, datetime.time.min)
                is_all_day = True
            
            # Datum Header
            day_str = start_dt.strftime("%A, %d.%m.")
            days_map = {'Monday': 'Montag', 'Tuesday': 'Dienstag', 'Wednesday': 'Mittwoch', 'Thursday': 'Donnerstag', 'Friday': 'Freitag', 'Saturday': 'Samstag', 'Sunday': 'Sonntag'}
            eng_day = start_dt.strftime("%A")
            if eng_day in days_map:
                day_str = day_str.replace(eng_day, days_map[eng_day])

            if day_str != current_day_str:
                # Kleiner Abstand vor neuem Tag
                pad_top = 15 if current_day_str != "" else 5
                ttk.Label(self.scroll_frame, text=day_str, font=("Arial", 14, "bold", "underline"), bootstyle="warning").pack(anchor="w", pady=(pad_top, 5))
                current_day_str = day_str
            
            # Termin Zeile
            row = ttk.Frame(self.scroll_frame)
            row.pack(fill=X, pady=2)
            
            if is_all_day:
                time_str = "Ganztag"
                clr = "info"
            else:
                # Zeitzone
                try:
                    local_dt = start_dt.astimezone(pytz.timezone("Europe/Berlin"))
                except:
                    local_dt = start_dt # Fallback wenn naiv
                time_str = local_dt.strftime("%H:%M")
                clr = "light"

            lbl_time = ttk.Label(row, text=time_str, font=("Arial", 12, "bold"), bootstyle=clr, width=9)
            lbl_time.pack(side=LEFT)
            
            lbl_text = ttk.Label(row, text=summary, font=("Arial", 12))
            lbl_text.pack(side=LEFT)
            
            # Dünne Trennlinie
            ttk.Separator(self.scroll_frame).pack(fill=X, pady=2, padx=10)