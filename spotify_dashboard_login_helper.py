import os
import tkinter as tk
from tkinter import ttk


def build_login_popup(parent, oauth, on_token):
    win = tk.Toplevel(parent)
    win.title("Spotify Login")
    win.geometry("700x280")
    win.configure(bg="#1E1E1E")
    win.grab_set()

    url = oauth.get_authorize_url()

    tk.Label(win, text="Spotify Login", fg="white", bg="#1E1E1E", font=("Arial", 16, "bold")).pack(pady=(12, 6))
    tk.Label(win, text="URL öffnen, anmelden und Code einfügen:", fg="#A0A0A0", bg="#1E1E1E").pack()

    url_entry = tk.Entry(win, font=("Arial", 9))
    url_entry.pack(fill="x", padx=16, pady=(8, 4))
    url_entry.insert(0, url)

    code_var = tk.StringVar()
    tk.Entry(win, textvariable=code_var, font=("Arial", 12)).pack(fill="x", padx=16, pady=(6, 8))

    def submit():
        code = code_var.get().strip()
        if not code:
            return
        try:
            token_info = oauth.get_access_token(code, as_dict=True)
            if token_info and token_info.get("access_token"):
                on_token()
                win.destroy()
        except Exception:
            pass

    ttk.Button(win, text="Code einreichen", command=submit).pack(pady=6)
    return win
