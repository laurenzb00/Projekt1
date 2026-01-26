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

    # --- Thread-Safe Kalender-Funktion ---
    def _fetch_calendar_safe(self):
        """Fetch calendar and schedule on main thread if not already running."""
        if threading.current_thread() is threading.main_thread():
            self._fetch_calendar()
        else:
            # Don't call root.after from background thread - just call the function directly
            try:
                self._fetch_calendar()
            except Exception as e:
                print(f"Calendar update error: {e}")

    # --- Thread-Loop ---
    def _loop(self):
        while True:
            self._fetch_calendar_safe()
            time.sleep(60)  # Update every 60 seconds

    # --- Kalender-Funktion korrigieren ---
    def _build_calendar(self):
        # Clear existing widgets in scroll frame only
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # Tagesansicht mit Events (einfacher)
        now = datetime.datetime.now()
        
        if not self.events_data:
            ttk.Label(
                self.scroll_frame, 
                text="Keine Termine in den nächsten 30 Tagen", 
                font=("Arial", 14), 
                bootstyle="secondary"
            ).pack(pady=50)
            return
        
        # Zeige Termine an
        for idx, event in enumerate(self.events_data[:20]):  # Max 20 Termine
            event_frame = ttk.Labelframe(
                self.scroll_frame, 
                text=event["start"].strftime("%d.%m.%Y %H:%M"),
                bootstyle="primary",
                padding=15
            )
            event_frame.pack(fill=X, padx=10, pady=8)
            
            ttk.Label(
                event_frame, 
                text=event["summary"], 
                font=("Arial", 14, "bold"),
                wraplength=800
            ).pack(anchor="w")

    def _fetch_calendar(self):
        self.status_var.set("Kalender wird geladen...")
        self.events_data = []

        try:
            now_utc = datetime.datetime.now(pytz.UTC)
            end_date = now_utc + datetime.timedelta(days=30)
            
            for url in ICAL_URLS:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    cal = icalendar.Calendar.from_ical(response.content)
                    events = recurring_ical_events.of(cal).between(now_utc, end_date)
                    for event in events:
                        event_start = event.get("dtstart").dt
                        
                        # Konvertiere zu datetime wenn nötig
                        if isinstance(event_start, datetime.date) and not isinstance(event_start, datetime.datetime):
                            event_start = datetime.datetime.combine(event_start, datetime.time.min)
                        
                        # Stelle sicher, dass es timezone-aware ist
                        if event_start.tzinfo is None:
                            event_start = pytz.UTC.localize(event_start)
                        
                        self.events_data.append({
                            "start": event_start,
                            "summary": str(event.get("summary", "Unbenannt"))
                        })

            self.events_data.sort(key=lambda x: x["start"])
            self.status_var.set(f"{len(self.events_data)} Termine geladen")
        except Exception as e:
            self.status_var.set("Fehler beim Laden")
            print(f"Kalender Fehler: {e}")

        # Schedule UI update on main thread
        try:
            self.root.after(0, self._build_calendar)
        except:
            pass