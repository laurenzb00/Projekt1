#!/usr/bin/env python3
import os
import urllib.parse as urlparse

def main():
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except Exception as e:
        print("spotipy fehlt. Bitte vorher installieren:  python -m pip install spotipy")
        raise

    # >>> Trage deine Keys ein (oder nutze Umgebungsvariablen) <<<
    CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "8cff12b3245a4e4088d5751360f62705")
    CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "af9ecfa466504d7795416a3f2c66f5c5")
    REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8889/callback")

    SCOPE = "user-read-currently-playing user-modify-playback-state user-read-playback-state"
    CACHE_PATH = os.path.join(os.path.abspath(os.getcwd()), ".cache-spotify")

    oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE_PATH,
        open_browser=False,   # WICHTIG: kein Browser-Autostart
        show_dialog=False,
    )

    # 1) Falls bereits ein Token im Cache liegt: fertig.
    token_info = oauth.get_cached_token()
    if token_info:
        print("✅ Token bereits im Cache. Kein Login nötig.")
        return

    # 2) Login-URL erzeugen und anzeigen
    auth_url = oauth.get_authorize_url()
    print("\n=== Spotify Login ===")
    print("Öffne diese URL im Browser (auf irgendeinem Gerät):\n")
    print(auth_url, "\n")
    print("Logge dich ein und erlaube die Berechtigungen.")
    print("Du wirst danach auf eine URL wie z. B.")
    print(f"   {REDIRECT_URI}?code=...&state=...")
    print("weitergeleitet. Kopiere diese **komplette** URL und füge sie hier ein.\n")

    try:
        redirect_response = input("👉 Eingabe der kompletten Redirect-URL: ").strip()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        return

    # 3) 'code' aus der Redirect-URL extrahieren
    parsed = urlparse.urlparse(redirect_response)
    query = urlparse.parse_qs(parsed.query)
    code = (query.get("code") or [None])[0]
    if not code:
        print("❌ Konnte keinen 'code' Parameter in der URL finden.")
        return

    # 4) Access-Token abholen und im Cache speichern
    token_info = oauth.get_access_token(code, as_dict=True)
    if token_info and token_info.get("access_token"):
        print("✅ Login erfolgreich. Token gespeichert unter:", CACHE_PATH)
        # Test: einmal Spotipy-Client erzeugen
        sp = spotipy.Spotify(auth_manager=oauth)
        me = sp.current_user()
        print(f"Angemeldet als: {me.get('display_name') or me.get('id')}")
    else:
        print("❌ Token konnte nicht ermittelt werden.")

if __name__ == "__main__":
    main()
