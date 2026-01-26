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
        # Clear existing widgets
        for widget in self.tab_frame.winfo_children():
            widget.destroy()

        # Create a calendar grid
        calendar_frame = ttk.Frame(self.tab_frame)
        calendar_frame.pack(fill=BOTH, expand=YES, padx=15, pady=10)

        # Days of the week
        days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for col, day in enumerate(days):
            ttk.Label(calendar_frame, text=day, font=("Arial", 12, "bold"), anchor="center", bootstyle="secondary").grid(row=0, column=col, sticky="nsew", padx=5, pady=5)

        # Generate dates for the current month
        now = datetime.datetime.now()
        first_day = datetime.date(now.year, now.month, 1)
        start_day = first_day - datetime.timedelta(days=first_day.weekday())
        end_day = first_day + datetime.timedelta(days=32)
        end_day = end_day.replace(day=1) - datetime.timedelta(days=1)

        current_date = start_day
        row = 1
        while current_date <= end_day:
            for col in range(7):
                if current_date.month == now.month:
                    day_frame = ttk.Frame(calendar_frame, bootstyle="light")
                    day_frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
                    ttk.Label(day_frame, text=str(current_date.day), font=("Arial", 10)).pack(anchor="nw")

                    # Highlight the current day
                    if current_date == now.date():
                        day_frame.configure(bootstyle="primary")

                    # Add events for the day
                    for event in self.events_data:
                        event_date = event.get("start").date()
                        if event_date == current_date:
                            # Adjust event display
                            ttk.Label(day_frame, text=event.get("summary"), font=("Arial", 8), wraplength=80, anchor="w", bootstyle="info").pack(anchor="w")

                current_date += datetime.timedelta(days=1)
            row += 1

        # Adjust column weights
        for col in range(7):
            calendar_frame.columnconfigure(col, weight=1)
        for r in range(row):
            calendar_frame.rowconfigure(r, weight=1)

    def _fetch_calendar(self):
        self.status_var.set("Kalender wird geladen...")
        self.events_data = []

        try:
            for url in ICAL_URLS:
                response = requests.get(url)
                if response.status_code == 200:
                    cal = icalendar.Calendar.from_ical(response.content)
                    events = recurring_ical_events.of(cal).between(datetime.datetime.now(pytz.UTC), datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=30))
                    for event in events:
                        self.events_data.append({
                            "start": event.get("dtstart").dt,
                            "summary": event.get("summary")
                        })

            self.events_data.sort(key=lambda x: x["start"])
            self.status_var.set("Kalender aktualisiert.")
        except Exception as e:
            self.status_var.set("Fehler beim Laden des Kalenders.")
            print(f"Kalender Fehler: {e}")

        self._build_calendar()