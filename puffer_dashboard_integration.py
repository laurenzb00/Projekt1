"""
PUFFERSPEICHER DASHBOARD INTEGRATIONEN
======================================

Verschiedene Wege, die Pufferdaten in der UI zu nutzen
"""

import json
import os
import csv
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

class PufferDataProvider:
    """Provider für Pufferspeicher-Daten aus JSON"""
    
    def __init__(self, json_path="Pufferspeicher.json"):
        self.json_path = json_path
    
    def get_current_state(self) -> Optional[Dict]:
        """Gibt den aktuellen Pufferstatus zurück"""
        if not os.path.exists(self.json_path):
            return None
        
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data[-1] if data else None
        except:
            return None
    
    def get_stratification_quality(self) -> Optional[float]:
        """
        Berechnet Schichtungsqualität (0-1)
        1 = perfekte Schichtung, 0 = keine Schichtung
        """
        state = self.get_current_state()
        if not state or not all(k in state for k in ['Oben', 'Mitte', 'Unten']):
            return None
        
        try:
            top = float(state['Oben'])
            mid = float(state['Mitte'])
            bottom = float(state['Unten'])
            
            # Ideal: top > mid > bottom
            ideal_diff = (top - mid) + (mid - bottom)
            max_diff = 60  # Max erwarteter Unterschied
            
            quality = max(0, min(1, ideal_diff / max_diff))
            return quality
        except:
            return None
    
    def get_charge_level(self) -> Optional[float]:
        """
        Gibt Ladezustand als 0-100% zurück
        Basierend auf Durchschnittstemp vs. min/max
        """
        state = self.get_current_state()
        if not state:
            return None
        
        try:
            temps = [
                float(state.get('Oben', 0)),
                float(state.get('Mitte', 0)),
                float(state.get('Unten', 0))
            ]
            temps = [t for t in temps if t > 0]
            if not temps:
                return None
            
            avg = sum(temps) / len(temps)
            
            # Annahme: 20°C = 0%, 80°C = 100%
            charge = max(0, min(100, (avg - 20) * 100 / 60))
            return charge
        except:
            return None
    
    def get_thermal_capacity_used(self) -> Optional[float]:
        """
        Berechnet die genutzte Wärmekapazität basierend auf
        Oberflächentemperatur minus Rückkehrtemperatur
        """
        # Benötigt Zusatzdaten - vereinfachte Version
        state = self.get_current_state()
        if not state:
            return None
        
        try:
            top = float(state.get('Oben', 0))
            bottom = float(state.get('Unten', 0))
            
            # Der Unterschied zeigt, wie viel des Speichers "aktiv" ist
            return max(0, top - bottom)
        except:
            return None
    
    def get_trend(self, minutes=30) -> Dict[str, str]:
        """
        Berechnet den Trend der letzten N Minuten
        """
        if not os.path.exists(self.json_path):
            return {"trend": "KEINE_DATEN"}
        
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if len(data) < 2:
                return {"trend": "UNBEKANNT"}
            
            cutoff = datetime.now() - timedelta(minutes=minutes)
            
            # Finde Einträge im Zeitfenster
            temps_alt = []
            temps_neu = []
            
            for entry in data:
                try:
                    ts = datetime.fromisoformat(entry['Zeitstempel'])
                    temp = float(entry.get('Mitte', 0))
                    
                    if ts < cutoff:
                        temps_alt.append(temp)
                    else:
                        temps_neu.append(temp)
                except:
                    pass
            
            if not temps_alt or not temps_neu:
                return {"trend": "UNBEKANNT"}
            
            avg_alt = sum(temps_alt) / len(temps_alt)
            avg_neu = sum(temps_neu) / len(temps_neu)
            diff = avg_neu - avg_alt
            
            if diff > 2:
                return {"trend": "LÄDT 📈", "diff": f"+{diff:.1f}°C"}
            elif diff < -2:
                return {"trend": "ENTLÄDT 📉", "diff": f"{diff:.1f}°C"}
            else:
                return {"trend": "STABIL ➡️", "diff": f"{diff:.1f}°C"}
        except:
            return {"trend": "FEHLER"}


class HeizungDataProvider:
    """Provider für Heizungs-Daten aus CSV"""
    
    def __init__(self, csv_path="Heizungstemperaturen.csv"):
        self.csv_path = csv_path
    
    def get_latest_record(self) -> Optional[Dict]:
        """Gibt den letzten Datensatz"""
        if not os.path.exists(self.csv_path):
            return None
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
                return records[-1] if records else None
        except:
            return None
    
    def get_all_available_fields(self) -> List[str]:
        """Gibt alle verfügbaren Felder zurück"""
        record = self.get_latest_record()
        if not record:
            return []
        
        return list(record.keys())
    
    def get_boiler_efficiency(self) -> Optional[Dict]:
        """
        Berechnet Kesseleffizienz
        (Pufferdurchschnitt vs. Kesseltemperatur)
        """
        try:
            record = self.get_latest_record()
            if not record:
                return None
            
            kessel = float(record.get('Kesseltemperatur', 0))
            puffer_temps = [
                float(record.get('Pufferspeicher Oben', 0)),
                float(record.get('Pufferspeicher Mitte', 0)),
                float(record.get('Pufferspeicher Unten', 0)),
            ]
            puffer_temps = [t for t in puffer_temps if t > 0]
            
            if not puffer_temps or kessel == 0:
                return None
            
            puffer_avg = sum(puffer_temps) / len(puffer_temps)
            efficiency = max(0, min(100, 100 - abs(kessel - puffer_avg) * 5))
            
            return {
                "Kesseltemp": f"{kessel:.1f}°C",
                "Pufferdurchschnitt": f"{puffer_avg:.1f}°C",
                "Effizienz": f"{efficiency:.0f}%"
            }
        except:
            return None
    
    def get_heat_loss_estimate(self) -> Optional[Dict]:
        """
        Schätzt Wärmeverluste basierend auf
        Außentemp vs. Pufferentladung
        """
        if not os.path.exists(self.csv_path):
            return None
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
            
            if len(records) < 2:
                return None
            
            # Letzter vs. Vorheriger Eintrag
            prev = records[-2]
            curr = records[-1]
            
            mitte_prev = float(prev.get('Pufferspeicher Mitte', 0))
            mitte_curr = float(curr.get('Pufferspeicher Mitte', 0))
            außen = float(curr.get('Außentemperatur', 0))
            
            temp_change = mitte_curr - mitte_prev
            
            return {
                "Letzte_Temperaturänderung": f"{temp_change:.1f}°C",
                "Außentemperatur": f"{außen:.1f}°C",
                "Status": "Hohe Verluste" if temp_change < -1 else "Normal"
            }
        except:
            return None


# BEISPIELE für UI-Integration

def beispiel_dashboard_widget():
    """
    Beispiel für ein Dashboard-Widget
    """
    puffer = PufferDataProvider()
    heizung = HeizungDataProvider()
    
    print("=" * 80)
    print("PUFFERSPEICHER DASHBOARD")
    print("=" * 80)
    
    # Aktueller Status
    state = puffer.get_current_state()
    if state:
        print(f"\n🌡️  AKTUELLER STATUS:")
        print(f"  Oben:   {state.get('Oben', '---')}°C")
        print(f"  Mitte:  {state.get('Mitte', '---')}°C")
        print(f"  Unten:  {state.get('Unten', '---')}°C")
        print(f"  Status: {state.get('Status', '---')}")
    
    # Qualität & Ladezustand
    quality = puffer.get_stratification_quality()
    charge = puffer.get_charge_level()
    trend = puffer.get_trend(30)
    
    print(f"\n📊 METRIKEN:")
    if quality is not None:
        print(f"  Schichtungsqualität: {quality*100:.0f}%")
    if charge is not None:
        print(f"  Ladezustand: {charge:.0f}%")
    print(f"  Trend: {trend.get('trend', '?')} {trend.get('diff', '')}")
    
    # Kesseleffizienz
    efficiency = heizung.get_boiler_efficiency()
    if efficiency:
        print(f"\n⚙️  KESSELEFFIZIENZ:")
        for key, val in efficiency.items():
            print(f"  {key}: {val}")
    
    # Wärmeverluste
    losses = heizung.get_heat_loss_estimate()
    if losses:
        print(f"\n🔥 WÄRMEVERLUSTE:")
        for key, val in losses.items():
            print(f"  {key}: {val}")


if __name__ == "__main__":
    beispiel_dashboard_widget()
