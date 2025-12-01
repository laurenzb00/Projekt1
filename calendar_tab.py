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
# Hier den "Privatadresse im iCal-Format" Link einfügen:
ICAL_URL = "https://calendar.google.com/calendar/ical/laurenzbandzauner%40gmail.com/private-ee12d630b1b19a7f6754768f56f1a76c/basic.ics" 

class CalendarTab:
    def __init__(self, root, notebook):
        self.root = root
        self.notebook = notebook
        self.alive = True
        
        # Variablen
        self.status_var = tk.StringVar(value="Lade Kalender...")
        self.events_data = [] # Liste der geladenen Termine
        
        # Tab erstellen
        self.tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_frame, text=" Kalender ")
        
        self._build_header()
        
        # Scrollbarer Bereich für die Termin-Liste
        self.canvas = tk.Canvas(self.tab_frame, bg="#2b3e50", highlightthickness=0)
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
        # Beim Start laden
        self._fetch_calendar()
        
        # Dann alle 15 Minuten aktualisieren
        while self.alive:
            for _ in range(900): # 15 min warten in 1s Schritten (für schnellen Stop)
                if not self.alive: return
                time.sleep(1)
            self._fetch_calendar()

    def _fetch_calendar(self):
        self.status_var.set("Aktualisiere...")
        try:
            if "google.com" not in ICAL_URL:
                self.status_var.set("Bitte iCal-Link in Code eintragen!")
                return

            response = requests.get(ICAL_URL)
            response.raise_for_status()
            
            cal = icalendar.Calendar.from_ical(response.content)
            
            # Zeitraum: Heute bis in 30 Tagen
            now = datetime.datetime.now(pytz.utc)
            end = now + datetime.timedelta(days=30)
            
            # Wiederkehrende Termine auflösen
            events = recurring_ical_events.of(cal).between(now, end)
            
            # Sortieren nach Startzeit
            events.sort(key=lambda x: x.get("DTSTART").dt)
            
            # UI Update im Hauptthread
            self.root.after(0, lambda: self._update_ui(events))
            self.status_var.set(f"Aktuell ({datetime.datetime.now().strftime('%H:%M')})")
            
        except Exception as e:
            print(f"Kalender Fehler: {e}")
            self.status_var.set("Verbindungsfehler")

    def _update_ui(self, events):
        # Liste leeren
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        if not events:
            ttk.Label(self.scroll_frame, text="Keine Termine in den nächsten 30 Tagen.", font=("Arial", 12)).pack(pady=20)
            return

        current_day_str = ""
        
        for event in events:
            # Daten extrahieren
            summary = str(event.get("SUMMARY"))
            start_dt = event.get("DTSTART").dt
            
            # Formatierung
            is_all_day = False
            if not isinstance(start_dt, datetime.datetime): # Es ist ein date (ganztägig)
                start_dt = datetime.datetime.combine(start_dt, datetime.time.min)
                is_all_day = True
            
            # Datum Gruppen-Header
            day_str = start_dt.strftime("%A, %d.%m.")
            # Deutsche Wochentage mappen (optional, sonst englisch vom System)
            days_map = {'Monday': 'Montag', 'Tuesday': 'Dienstag', 'Wednesday': 'Mittwoch', 'Thursday': 'Donnerstag', 'Friday': 'Freitag', 'Saturday': 'Samstag', 'Sunday': 'Sonntag'}
            eng_day = start_dt.strftime("%A")
            if eng_day in days_map:
                day_str = day_str.replace(eng_day, days_map[eng_day])

            if day_str != current_day_str:
                # Neuer Tag Header
                ttk.Label(self.scroll_frame, text=day_str, font=("Arial", 14, "bold", "underline"), bootstyle="warning").pack(anchor="w", pady=(15, 5))
                current_day_str = day_str
            
            # Termin Karte
            card = ttk.Frame(self.scroll_frame, style="Secondary.TFrame") # oder Labelframe
            card.pack(fill=X, pady=2, padx=5)
            
            # Uhrzeit
            if is_all_day:
                time_str = "Ganztägig"
                clr = "info"
            else:
                # Zeitzone anpassen (wichtig, da Google UTC liefert)
                local_dt = start_dt.astimezone(pytz.timezone("Europe/Berlin")) # Oder 'Europe/Vienna'
                time_str = local_dt.strftime("%H:%M")
                clr = "light"

            # Zeile bauen
            row = ttk.Frame(self.scroll_frame)
            row.pack(fill=X, pady=2)
            
            lbl_time = ttk.Label(row, text=time_str, font=("Arial", 12, "bold"), bootstyle=clr, width=10)
            lbl_time.pack(side=LEFT)
            
            lbl_text = ttk.Label(row, text=summary, font=("Arial", 12))
            lbl_text.pack(side=LEFT)
            
            ttk.Separator(self.scroll_frame).pack(fill=X, pady=2, padx=10)