import pandas as pd
from datetime import datetime, timedelta

df = pd.read_csv('FroniusDaten.csv', parse_dates=['Zeitstempel'])
df['Date'] = df['Zeitstempel'].dt.date

print("=" * 60)
print("FRONIUS DATEN ANALYSE")
print("=" * 60)

print(f"\n✓ Gesamtzeilen: {len(df):,}")
print(f"✓ Eindeutige Tage: {df['Date'].nunique()}")
print(f"✓ Zeitraum: {df['Zeitstempel'].min()} bis {df['Zeitstempel'].max()}")

# Tage mit Daten
days_with_data = sorted(df['Date'].unique())
print(f"\n✓ Tage mit Messwerten: {len(days_with_data)}")

# Finde Lücken
print("\n→ Größte Lücken zwischen Tagen:")
gaps = []
for i in range(len(days_with_data) - 1):
    gap_days = (days_with_data[i+1] - days_with_data[i]).days
    if gap_days > 1:
        gaps.append((days_with_data[i], days_with_data[i+1], gap_days))

gaps.sort(key=lambda x: x[2], reverse=True)
for start, end, gap in gaps[:10]:
    print(f"  {start} → {end}: {gap} Tage Lücke")

# Prüfe PV-Leistung
print(f"\n→ PV-Leistung Statistik:")
print(f"  Min: {df['PV-Leistung (kW)'].min():.3f} kW")
print(f"  Max: {df['PV-Leistung (kW)'].max():.3f} kW")
print(f"  Mean: {df['PV-Leistung (kW)'].mean():.3f} kW")

# Wie viele Einträge pro Tag (durchschnitt)
entries_per_day = len(df) / len(days_with_data)
print(f"\n✓ Durchschnitt Einträge pro Tag mit Daten: {entries_per_day:.0f}")

# Prüfe Januar-Februar 2026 (letzter Monat)
jan_df = df[df['Zeitstempel'] > datetime(2026, 1, 1)]
print(f"\n→ Januar 2026 Daten:")
print(f"  Einträge: {len(jan_df):,}")
print(f"  Tage mit Messwerten: {jan_df['Date'].nunique()}")
print(f"  Tage im Januar: {31}")
print(f"  Tage ohne Messwerte: {31 - jan_df['Date'].nunique()}")
