"""
ANALYSE-TOOL für Pufferspeicher und Heizungsdaten
==================================================

Zeigt verfügbare Daten und Nutzungsmöglichkeiten auf
"""

import os
import csv
import json
from datetime import datetime, timedelta
import statistics

class HeizungAnalyse:
    """Analysiert alle extrahierten Heizungs- und Pufferdaten"""
    
    def __init__(self, csv_path="Heizungstemperaturen.csv", json_path="Pufferspeicher.json"):
        self.csv_path = csv_path
        self.json_path = json_path
        self.heizung_daten = []
        self.puffer_daten = []
        self._lade_daten()
    
    def _lade_daten(self):
        """Lädt Daten aus CSV und JSON"""
        self._lade_csv()
        self._lade_json()
    
    def _lade_csv(self):
        """Lädt Heizungsdaten aus CSV"""
        if not os.path.exists(self.csv_path):
            print(f"⚠️  CSV-Datei nicht gefunden: {self.csv_path}")
            return
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.heizung_daten = list(reader)
            print(f"✓ {len(self.heizung_daten)} Heizung-Datensätze geladen")
        except Exception as e:
            print(f"✗ Fehler beim Laden der CSV: {e}")
    
    def _lade_json(self):
        """Lädt Pufferdaten aus JSON"""
        if not os.path.exists(self.json_path):
            print(f"⚠️  JSON-Datei nicht gefunden: {self.json_path}")
            return
        
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.puffer_daten = json.load(f)
            print(f"✓ {len(self.puffer_daten)} Puffer-Datensätze geladen")
        except Exception as e:
            print(f"✗ Fehler beim Laden der JSON: {e}")
    
    def zeige_verfügbare_spalten(self):
        """Zeigt alle verfügbaren Datenfelder"""
        if not self.heizung_daten:
            print("Keine Heizungsdaten vorhanden")
            return
        
        print("\n📊 VERFÜGBARE HEIZUNG-SPALTEN:")
        print("=" * 80)
        spalten = list(self.heizung_daten[0].keys())
        for idx, spalte in enumerate(spalten, 1):
            print(f"  {idx:2}. {spalte}")
        
        print(f"\n✓ Insgesamt {len(spalten)} Datenfelder verfügbar")
    
    def zeige_puffer_struktur(self):
        """Zeigt die Struktur der Pufferdaten"""
        if not self.puffer_daten:
            print("Keine Pufferdaten vorhanden")
            return
        
        print("\n🔥 PUFFERSPEICHER-STRUKTUR:")
        print("=" * 80)
        print(json.dumps(self.puffer_daten[-1], indent=2, ensure_ascii=False))
    
    def berechne_statistiken(self):
        """Berechnet Statistiken über die Pufferdaten"""
        if not self.puffer_daten:
            print("Keine Pufferdaten vorhanden")
            return
        
        print("\n📈 PUFFERSPEICHER-STATISTIKEN:")
        print("=" * 80)
        
        temps_oben = []
        temps_mitte = []
        temps_unten = []
        
        for eintrag in self.puffer_daten:
            try:
                if eintrag.get('Oben'):
                    temps_oben.append(float(eintrag['Oben']))
                if eintrag.get('Mitte'):
                    temps_mitte.append(float(eintrag['Mitte']))
                if eintrag.get('Unten'):
                    temps_unten.append(float(eintrag['Unten']))
            except:
                pass
        
        def zeige_stats(name, temps):
            if temps:
                print(f"\n{name}:")
                print(f"  Min:       {min(temps):6.1f} °C")
                print(f"  Max:       {max(temps):6.1f} °C")
                print(f"  Mittel:    {statistics.mean(temps):6.1f} °C")
                print(f"  Median:    {statistics.median(temps):6.1f} °C")
                if len(temps) > 1:
                    print(f"  Std.Abw.:  {statistics.stdev(temps):6.1f} °C")
        
        zeige_stats("🔴 OBEN", temps_oben)
        zeige_stats("🟡 MITTE", temps_mitte)
        zeige_stats("🔵 UNTEN", temps_unten)
    
    def zeige_zeitliche_entwicklung(self, stunden=24):
        """Zeigt die zeitliche Entwicklung der letzten N Stunden"""
        if not self.puffer_daten:
            print("Keine Pufferdaten vorhanden")
            return
        
        cutoff = datetime.now() - timedelta(hours=stunden)
        relevante_daten = []
        
        for eintrag in self.puffer_daten:
            try:
                ts = datetime.fromisoformat(eintrag['Zeitstempel'])
                if ts >= cutoff:
                    relevante_daten.append(eintrag)
            except:
                pass
        
        print(f"\n⏱️  ENTWICKLUNG (letzte {stunden} Stunden):")
        print("=" * 80)
        print(f"Zeitstempel          │ Oben  │ Mitte │ Unten │ Status")
        print("─" * 80)
        
        for eintrag in relevante_daten[-20:]:  # Zeige letzte 20
            zeit = eintrag.get('Zeitstempel', '---')[:16]
            oben = f"{float(eintrag.get('Oben', 0)):5.1f}" if eintrag.get('Oben') else "  ---"
            mitte = f"{float(eintrag.get('Mitte', 0)):5.1f}" if eintrag.get('Mitte') else "  ---"
            unten = f"{float(eintrag.get('Unten', 0)):5.1f}" if eintrag.get('Unten') else "  ---"
            status = eintrag.get('Status', '?')
            print(f"{zeit} │ {oben} │ {mitte} │ {unten} │ {status}")
    
    def generiere_bericht(self):
        """Generiert einen kompletten Analysebericht"""
        print("\n" + "=" * 80)
        print("🏠 HEIZUNGS- & PUFFERSPEICHER ANALYSE BERICHT")
        print("=" * 80)
        print(f"Erstellt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.zeige_verfügbare_spalten()
        print()
        self.zeige_puffer_struktur()
        print()
        self.berechne_statistiken()
        print()
        self.zeige_zeitliche_entwicklung(24)
        
        print("\n" + "=" * 80)
        print("💡 MÖGLICHE WEITERVERWENDUNGEN:")
        print("=" * 80)
        print("""
1. ⚡ ENERGIEEFFIZIENZ:
   - Pufferstratifikation überwachen (Qualität der Schichtung)
   - Lade-/Entlade-Zyklen analysieren
   - Vergleich Kesseltemperatur vs. Pufferdurchschnitt

2. 🌡️  PROGNOSEN:
   - Abkühlraten berechnen
   - Bereitschaft für nächste Heizphase vorhersagen
   - Außentemperatur-Abhängigkeiten analysieren

3. 📊 OPTIMIERUNGEN:
   - Kesselzündvorgänge reduzieren
   - Puffergröße vs. tatsächliche Nutzung bewerten
   - Wärmeverluste berechnen

4. 🎯 WARTUNG:
   - Thermostate überprüfen (sollten Stratifikation zeigen)
   - Zirkulation kontrollieren
   - Wartungsalarm bei Anomalien

5. 🏘️  GEBÄUDEVERHALTEN:
   - Wärmebedarf pro Außentemperatur
   - Solaranlage-Integration (wenn vorhanden)
   - Vergleich mit Nachbarsystemen
        """)


if __name__ == "__main__":
    analyse = HeizungAnalyse()
    analyse.generiere_bericht()
