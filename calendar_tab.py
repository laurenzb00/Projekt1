import threading
import time
import tkinter as tk
from tkinter import ttk
import requests
import icalendar
import recurring_ical_events
import datetime
import calendar
import pytz
from ui.styles import (
    COLOR_ROOT,
    COLOR_CARD,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    emoji,
)
from ui.components.card import Card

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
        self.displayed_month = datetime.datetime.now().date().replace(day=1)  # Aktueller Monat
        
        # Variablen
        self.status_var = tk.StringVar(value="Lade Kalender...")
        self.events_data = [] 
        
        # Tab erstellen
        self.tab_frame = tk.Frame(self.notebook, bg=COLOR_ROOT)
        self.notebook.add(self.tab_frame, text=emoji("📅 Kalender", "Kalender"))
        
        self._build_header()
        
        # Scrollbarer Bereich
        self.canvas = tk.Canvas(self.tab_frame, highlightthickness=0, bg=COLOR_ROOT)
        self.canvas.configure(bg=COLOR_ROOT)
        
        self.scrollbar = ttk.Scrollbar(self.tab_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=COLOR_ROOT)
        
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.window_id = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        # Stretch inner frame to canvas width so der Kalender nutzt den Platz
        def _resize_inner(event):
            try:
                self.canvas.itemconfigure(self.window_id, width=event.width)
            except Exception:
                pass
        self.canvas.bind("<Configure>", _resize_inner)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        self.scrollbar.pack(side="right", fill="y")

        # Start Update Loop
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.alive = False

    def _ui_set(self, var: tk.StringVar, value: str):
        try:
            self.root.after(0, var.set, value)
        except Exception:
            pass

    def _build_header(self):
        header = ttk.Frame(self.tab_frame)
        header.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        # Linker Button (Monat zurück)
        ttk.Button(
            header, text="◀ Vorheriger",
            command=self._prev_month, width=12
        ).pack(side=tk.LEFT, padx=5)
        
        # Titel
        ttk.Label(header, text="Kalender", font=("Arial", 18, "bold")).pack(side=tk.LEFT, padx=20)
        
        # Rechter Button (Monat vor)
        ttk.Button(
            header, text="Nächster ▶",
            command=self._next_month, width=12
        ).pack(side=tk.LEFT, padx=5)
        
        # Refresh Button
        ttk.Button(
            header, text=emoji("↻", "Aktualisieren"),
            command=lambda: threading.Thread(target=self._fetch_calendar, daemon=True).start()
        ).pack(side=tk.RIGHT, padx=10)
        
        # Status
        ttk.Label(header, textvariable=self.status_var).pack(side=tk.RIGHT)

    def _prev_month(self):
        """Monat zurück"""
        first = self.displayed_month
        self.displayed_month = (first - datetime.timedelta(days=1)).replace(day=1)
        self._build_calendar()

    def _next_month(self):
        """Monat vor"""
        first = self.displayed_month
        last = first.replace(day=28) + datetime.timedelta(days=4)
        self.displayed_month = (last + datetime.timedelta(days=1)).replace(day=1)
        self._build_calendar()

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

        # Nutze self.displayed_month statt aktuellem Datum
        now_local = datetime.datetime.now().astimezone()
        first_day = datetime.datetime.combine(self.displayed_month, datetime.time.min).astimezone()
        weekday_offset, days_in_month = calendar.monthrange(first_day.year, first_day.month)
        # monthrange liefert Montag=0..Sonntag=6, passt zu "Mo..So"

        today_date = now_local.date()
        month_title = first_day.strftime("%B %Y")

        # Dunkles Hintergrund für Label
        label_frame = tk.Frame(self.scroll_frame, bg="#0f172a")
        label_frame.grid(row=0, column=0, columnspan=7, sticky="nsew", pady=(4, 8))
        
        tk.Label(
            label_frame,
            text=month_title,
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg="#0f172a"
        ).pack(pady=5)

        day_names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for idx, name in enumerate(day_names):
            tk.Label(
                self.scroll_frame,
                text=name,
                font=("Segoe UI", 9, "bold"),
                fg="#8ba2c7",
                bg="#0f172a"
            ).grid(row=1, column=idx, padx=3, pady=(0, 4))

        # Grid-Spalten gleichmäßig verteilen
        for c in range(7):
            self.scroll_frame.grid_columnconfigure(c, weight=1, uniform="cal")

        # Events nach Datum gruppieren (mit Uhrzeiten)
        events_by_date = {}
        for event in self.events_data:
            try:
                local_dt = event["start"].astimezone(now_local.tzinfo)
            except Exception:
                local_dt = event["start"]
            date_key = local_dt.date()
            time_str = local_dt.strftime("%H:%M") if hasattr(local_dt, 'hour') else ""
            events_by_date.setdefault(date_key, []).append({
                "summary": event["summary"],
                "time": time_str
            })

        # Tage rendern
        row_base = 2
        last_row = row_base + (weekday_offset + days_in_month - 1) // 7
        for r in range(row_base, last_row + 1):
            self.scroll_frame.grid_rowconfigure(r, weight=1, uniform="calrow")
        for day in range(1, days_in_month + 1):
            col = (weekday_offset + day - 1) % 7
            row = row_base + (weekday_offset + day - 1) // 7
            cell_date = first_day.date().replace(day=day)

            cell_bg = "#0a0f1a"
            border_color = "#1f2a44"
            if cell_date == today_date:
                border_color = "#38bdf8"
                cell_bg = "#0f172a"

            cell = tk.Frame(
                self.scroll_frame,
                bg=cell_bg,
                highlightbackground=border_color,
                highlightthickness=1,
                bd=0,
                padx=5,
                pady=3
            )
            cell.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")

            # Datum-Kopf
            tk.Label(
                cell,
                text=str(day),
                font=("Segoe UI", 10, "bold"),
                fg="#e5e7eb",
                bg=cell_bg
            ).pack(anchor="nw", pady=(0, 1))

            # Events auflisten mit Uhrzeiten (max 3)
            items = events_by_date.get(cell_date, [])
            if not items:
                tk.Label(
                    cell,
                    text="frei",
                    font=("Segoe UI", 8),
                    fg="#6b7280",
                    bg=cell_bg
                ).pack(anchor="nw", pady=(1, 0))
            else:
                for ev in items[:3]:
                    time_str = f"[{ev['time']}] " if ev['time'] else ""
                    tk.Label(
                        cell,
                        text=f"• {time_str}{ev['summary']}",
                        font=("Segoe UI", 7),
                        fg="#c7d2fe",
                        bg=cell_bg,
                        wraplength=110,
                        justify="left"
                    ).pack(anchor="nw", pady=(1, 0))

                # Hinweis auf mehr Einträge
                if len(items) > 3:
                    tk.Label(
                        cell,
                        text=f"+{len(items) - 3} mehr",
                        font=("Segoe UI", 7),
                        fg="#9ca3af",
                        bg=cell_bg
                    ).pack(anchor="nw", pady=(1, 0))

    def _fetch_calendar(self):
        self._ui_set(self.status_var, "Kalender wird geladen...")
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
            self._ui_set(self.status_var, f"{len(self.events_data)} Termine geladen")
        except Exception as e:
            self._ui_set(self.status_var, "Fehler beim Laden")
            print(f"Kalender Fehler: {e}")

        # Schedule UI update on main thread
        try:
            self.root.after(0, self._build_calendar)
        except:
            pass