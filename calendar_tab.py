import threading
import time
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import requests
import icalendar
import recurring_ical_events
import datetime
import calendar
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

        # Monatsübersicht
        now_local = datetime.datetime.now().astimezone()
        first_day = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        weekday_offset, days_in_month = calendar.monthrange(first_day.year, first_day.month)
        # calendar.monthrange: Monday=0, Sunday=6
        weekday_offset = (weekday_offset + 6) % 7  # Start bei Montag als erste Spalte

        today_date = now_local.date()
        month_title = first_day.strftime("%B %Y")

        ttk.Label(
            self.scroll_frame,
            text=month_title,
            font=("Arial", 18, "bold"),
            bootstyle="inverse-dark"
        ).grid(row=0, column=0, columnspan=7, pady=(5, 12))

        day_names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for idx, name in enumerate(day_names):
            ttk.Label(
                self.scroll_frame,
                text=name,
                font=("Arial", 10, "bold"),
                bootstyle="secondary"
            ).grid(row=1, column=idx, padx=4, pady=(0, 6))

        # Events nach Datum gruppieren
        events_by_date = {}
        for event in self.events_data:
            try:
                local_dt = event["start"].astimezone(now_local.tzinfo)
            except Exception:
                local_dt = event["start"]
            date_key = local_dt.date()
            events_by_date.setdefault(date_key, []).append(event["summary"])

        # Tage rendern
        row_base = 2
        for day in range(1, days_in_month + 1):
            col = (weekday_offset + day - 1) % 7
            row = row_base + (weekday_offset + day - 1) // 7
            cell_date = first_day.date().replace(day=day)

            cell_bg = "#0f172a"
            border_color = "#1f2a44"
            if cell_date == today_date:
                border_color = "#38bdf8"

            cell = tk.Frame(
                self.scroll_frame,
                bg=cell_bg,
                highlightbackground=border_color,
                highlightthickness=1,
                bd=0,
                padx=6,
                pady=4
            )
            cell.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

            # Datum-Kopf
            tk.Label(
                cell,
                text=str(day),
                font=("Segoe UI", 11, "bold"),
                fg="#e5e7eb",
                bg=cell_bg
            ).pack(anchor="nw")

            # Events auflisten (max 3)
            items = events_by_date.get(cell_date, [])
            if not items:
                tk.Label(
                    cell,
                    text="frei",
                    font=("Segoe UI", 9),
                    fg="#6b7280",
                    bg=cell_bg
                ).pack(anchor="nw", pady=(2, 0))
            else:
                for ev in items[:3]:
                    tk.Label(
                        cell,
                        text=f"• {ev}",
                        font=("Segoe UI", 9),
                        fg="#c7d2fe",
                        bg=cell_bg,
                        wraplength=120,
                        justify="left"
                    ).pack(anchor="nw", pady=(1, 0))

                # Hinweis auf mehr Einträge
                if len(items) > 3:
                    tk.Label(
                        cell,
                        text=f"+{len(items) - 3} mehr",
                        font=("Segoe UI", 8),
                        fg="#9ca3af",
                        bg=cell_bg
                    ).pack(anchor="nw", pady=(2, 0))

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