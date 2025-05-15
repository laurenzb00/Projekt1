import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.dates as mdates
from matplotlib.dates import AutoDateLocator
from matplotlib.ticker import MaxNLocator

WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Funktion zum Filtern der Daten der letzten 48 Stunden
def filter_data_last_48_hours(csv_file):
    try:
        daten = pd.read_csv(csv_file, parse_dates=["Zeitstempel"])
        jetzt = pd.Timestamp.now()
        daten = daten[daten["Zeitstempel"] >= (daten["Zeitstempel"].max() - pd.Timedelta(hours=48))]
        return daten
    except Exception as e:
        print(f"Fehler beim Filtern der Daten: {e}")
        return None

# Funktion zum Erstellen der Fronius-Grafik
def update_fronius_graphics():
    daten = filter_data_last_48_hours(os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv"))
    if daten is None or daten.empty:
        print("Keine Daten für Fronius verfügbar.")
        return

    try:
        daten["Zeitstempel"] = daten["Zeitstempel"].dt.floor("5min")  # Runden auf 5-Minuten-Intervalle
        daten = daten.groupby("Zeitstempel").mean().reset_index()

        pv_leistung = daten["PV-Leistung (kW)"] * 1000
        hausverbrauch = daten["Hausverbrauch (kW)"] * 1000
        batterieladestand = daten["Batterieladestand (%)"]

        fig, ax1 = plt.subplots(figsize=(12, 6), dpi=100)
        ax1.plot(daten["Zeitstempel"], hausverbrauch, label="Hausverbrauch (W)", color="#3498DB", linewidth=2)
        ax1.plot(daten["Zeitstempel"], pv_leistung, label="PV-Leistung (W)", color="#F1C40F", linewidth=2)
        ax1.set_xlabel("Zeit", fontsize=12, color="#333333")
        ax1.set_ylabel("Leistung (W)", fontsize=12, color="#333333")
        ax1.tick_params(axis="y", labelcolor="#333333")
        ax1.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.xticks(rotation=45, fontsize=10, color="#333333")
        plt.yticks(fontsize=10, color="#333333")

        ax2 = ax1.twinx()
        ax2.plot(daten["Zeitstempel"], batterieladestand, label="Batterieladestand (%)", color="#9B59B6", linewidth=2, linestyle="--")
        ax2.set_ylabel("Batterieladestand (%)", fontsize=12, color="#333333")
        ax2.tick_params(axis="y", labelcolor="#333333")
        plt.yticks(fontsize=10, color="#333333")

        fig.suptitle("Fronius GEN24 Leistungsdaten (Letzte 48 Stunden)", fontsize=16, fontweight="bold", color="#333333")
        ax1.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)

        ax1_lines, ax1_labels = ax1.get_legend_handles_labels()
        ax2_lines, ax2_labels = ax2.get_legend_handles_labels()
        ax1.legend(ax1_lines + ax2_lines, ax1_labels + ax2_labels, loc="upper left", fontsize=10, frameon=True, shadow=False, facecolor="white", edgecolor="gray")

        last_update = pd.Timestamp.now().strftime("%d.%m.%Y %H:%M:%S")
        plt.text(0.99, 0.01, f"Letzte Aktualisierung: {last_update}", fontsize=8, color="gray",
                 ha="right", va="bottom", transform=plt.gcf().transFigure)

        plt.tight_layout()
        grafik_pfad = os.path.join(WORKING_DIRECTORY, "FroniusDaten.png")
        plt.savefig(grafik_pfad, dpi=100)
        plt.close()
        print(f"Fronius-Grafik aktualisiert ({last_update}).")
    except Exception as e:
        print(f"Fehler beim Erstellen der Fronius-Grafik: {e}")

# Funktion zum Erstellen der Heizungstemperatur-Grafik
def update_bmk_graphics():
    daten = filter_data_last_48_hours(os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv"))
    if daten is None or daten.empty:
        print("Keine Daten für Heizungstemperaturen verfügbar.")
        return

    try:
        daten["Zeitstempel"] = daten["Zeitstempel"].dt.floor("5min")  # Runden auf 5-Minuten-Intervalle
        daten = daten.groupby("Zeitstempel").mean().reset_index()

        fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
        ax.plot(daten["Zeitstempel"], daten["Kesseltemperatur"], label="Kesseltemperatur (°C)", color="#FF5733", linewidth=2)
        ax.plot(daten["Zeitstempel"], daten["Außentemperatur"], label="Außentemperatur (°C)", color="#3498DB", linewidth=2)
        ax.set_title("Heizungstemperaturen (Letzte 48 Stunden)", fontsize=16, fontweight="bold", color="#333333")
        ax.set_xlabel("Zeit", fontsize=12, color="#333333")
        ax.set_ylabel("Temperatur (°C)", fontsize=12, color="#333333")
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
        plt.xticks(rotation=45, fontsize=10, color="#333333")
        plt.yticks(fontsize=10, color="#333333")
        ax.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)
        ax.legend(fontsize=10, loc="upper left", frameon=True, shadow=False, facecolor="white", edgecolor="gray")

        last_update = pd.Timestamp.now().strftime("%d.%m.%Y %H:%M:%S")
        plt.text(0.99, 0.01, f"Letzte Aktualisierung: {last_update}", fontsize=8, color="gray",
                 ha="right", va="bottom", transform=plt.gcf().transFigure)

        plt.tight_layout()
        grafik_pfad = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.png")
        plt.savefig(grafik_pfad, dpi=100)
        plt.close()
        print(f"Heizungstemperaturen-Grafik aktualisiert ({last_update}).")
    except Exception as e:
        print(f"Fehler beim Erstellen der Heizungstemperaturen-Grafik: {e}")

# Funktion zum Erstellen der Zusammenfassungs-Grafik
def update_summary_graphics():
    try:
        fronius_path = os.path.join(WORKING_DIRECTORY, "FroniusDaten.csv")
        heizung_path = os.path.join(WORKING_DIRECTORY, "Heizungstemperaturen.csv")
        background_image_path = os.path.join(WORKING_DIRECTORY, "icons", "background.png")

        if not os.path.exists(fronius_path) or not os.path.exists(heizung_path):
            print("CSV-Dateien fehlen. Zusammenfassungsgrafik wird nicht aktualisiert.")
            return

        fronius_daten = pd.read_csv(fronius_path)
        heizung_daten = pd.read_csv(heizung_path)

        if fronius_daten.empty or heizung_daten.empty:
            print("CSV-Dateien sind leer. Zusammenfassungsgrafik wird nicht aktualisiert.")
            return

        fronius_daten.columns = fronius_daten.columns.str.strip()
        heizung_daten.columns = heizung_daten.columns.str.strip()

        aktuelle_netz_leistung = fronius_daten["Netz-Leistung (kW)"].iloc[-1]
        aktuelle_batterieladestand = fronius_daten["Batterieladestand (%)"].iloc[-1]
        aktuelle_hausverbrauch = fronius_daten["Hausverbrauch (kW)"].iloc[-1]
        aktuelle_puffer_oben = heizung_daten["Pufferspeicher Oben"].iloc[-1]
        aktuelle_puffer_mitte = heizung_daten["Pufferspeicher Mitte"].iloc[-1]
        aktuelle_puffer_unten = heizung_daten["Pufferspeicher Unten"].iloc[-1]
        aktuelle_kesseltemperatur = heizung_daten["Kesseltemperatur"].iloc[-1]
        aktuelle_aussentemperatur = heizung_daten["Außentemperatur"].iloc[-1]

        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)  # Optimiert für 1024x600

        # Hintergrundbild hinzufügen
        if os.path.exists(background_image_path):
            try:
                if not hasattr(update_summary_graphics, "background_image"):
                    update_summary_graphics.background_image = plt.imread(background_image_path)
                img = update_summary_graphics.background_image
                ax.imshow(img, extent=[0, 1, 0, 1], aspect='auto', zorder=-1)
                print("Hintergrundbild erfolgreich geladen.")
            except Exception as e:
                print(f"Fehler beim Laden des Hintergrundbilds: {e}")
        else:
            print(f"Hintergrundbild nicht gefunden: {background_image_path}")

        ax.axis("off")
        daten = [
            ("Puffertemperatur Oben", f"{aktuelle_puffer_oben:.1f} °C", "temperature.png"),
            ("Puffertemperatur Mitte", f"{aktuelle_puffer_mitte:.1f} °C", "temperature.png"),
            ("Puffertemperatur Unten", f"{aktuelle_puffer_unten:.1f} °C", "temperature.png"),
            ("Kesseltemperatur", f"{aktuelle_kesseltemperatur:.1f} °C", "boiler.png"),
            ("Außentemperatur", f"{aktuelle_aussentemperatur:.1f} °C", "outdoor.png"),
            ("Batterieladestand", f"{aktuelle_batterieladestand:.1f} %", "battery.png"),
            ("Hausverbrauch", f"{aktuelle_hausverbrauch:.1f} kW", "house.png"),
            ("Netz-Leistung", f"{aktuelle_netz_leistung:.1f} kW", "power.png"),
        ]
        icon_zoom = 0.1
        y_pos = 0.9
        for label, value, icon_name in daten:
            icon_path = os.path.join(WORKING_DIRECTORY, "icons", icon_name)
            if os.path.exists(icon_path):
                image = plt.imread(icon_path)
                imagebox = OffsetImage(image, zoom=icon_zoom)
                ab = AnnotationBbox(imagebox, (0.2, y_pos), frameon=False)
                ax.add_artist(ab)
            ax.text(0.3, y_pos, label, fontsize=14, fontweight="bold", ha="left", va="center", color="white")
            ax.text(0.85, y_pos, value, fontsize=14, fontweight="bold", ha="right", va="center", color="white")
            y_pos -= 0.1

        # Zeitstempel hinzufügen (klein unten rechts)
        last_update = pd.Timestamp.now().strftime("%d.%m.%Y %H:%M:%S")
        plt.text(0.99, 0.01, f"Letzte Aktualisierung: {last_update}", fontsize=8, color="white",
                 ha="right", va="bottom", transform=plt.gcf().transFigure)

        grafik_pfad = os.path.join(WORKING_DIRECTORY, "Zusammenfassung.png")
        plt.savefig(grafik_pfad, dpi=100, bbox_inches="tight")  # DPI auf 100 setzen
        plt.close()
        print(f"Zusammenfassungsgrafik aktualisiert ({last_update}).")
    except Exception as e:
        print(f"Fehler beim Aktualisieren der Zusammenfassungsgrafik: {e}")