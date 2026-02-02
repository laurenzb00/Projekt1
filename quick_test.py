#!/usr/bin/env python3
"""
Quick Performance Test
======================
Testet SQLite vs CSV Performance ohne GUI
"""

import time
import os

print("="*80)
print("🔬 PERFORMANCE TEST - SQLite vs CSV")
print("="*80)

# Test 1: CSV Import
print("\n📄 Test 1: CSV Lesen (alte Methode)")
start = time.time()

fronius_path = "FroniusDaten.csv"
if os.path.exists(fronius_path):
    # Simuliere das aktuelle Verhalten
    with open(fronius_path, 'rb') as f:
        f.seek(0, 2)  # Gehe ans Ende
        size_mb = f.tell() / 1024 / 1024
        f.seek(max(0, f.tell() - 65536), 0)  # Lies letzte 64KB
        chunk = f.read()
    
    csv_time = time.time() - start
    print(f"   ✓ CSV gelesen ({size_mb:.1f} MB) in {csv_time:.3f}s")
else:
    print(f"   ⚠️ {fronius_path} nicht gefunden")
    csv_time = 0

# Test 2: SQLite
print("\n💾 Test 2: SQLite Zugriff")
start = time.time()

try:
    from datastore import DataStore
    
    store = DataStore()
    
    # Check DB
    cursor = store.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM fronius")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("   📊 Importiere CSV zu SQLite...")
        import_start = time.time()
        store.import_fronius_csv(fronius_path)
        import_time = time.time() - import_start
        print(f"   ✓ Import in {import_time:.1f}s")
    
    # Test Queries
    query_start = time.time()
    
    last = store.get_last_fronius_record()
    hourly = store.get_hourly_averages(24)
    daily = store.get_daily_totals(7)
    
    query_time = time.time() - query_start
    
    db_size_mb = os.path.getsize(store.db_path) / 1024 / 1024
    
    print(f"   ✓ Queries (last + 24h + 7d) in {query_time:.3f}s")
    print(f"   💾 DB Size: {db_size_mb:.1f} MB")
    
    store.close()
    
    sqlite_time = time.time() - start
    print(f"   ✓ Total SQLite Zeit: {sqlite_time:.3f}s")
    
except Exception as e:
    print(f"   ❌ SQLite Error: {e}")
    sqlite_time = 0

# Vergleich
if csv_time > 0 and sqlite_time > 0:
    print("\n" + "="*80)
    print("📊 ERGEBNIS")
    print("="*80)
    print(f"CSV Zugriff:      {csv_time:.3f}s")
    print(f"SQLite Queries:   {query_time:.3f}s")
    print(f"Speedup:          {csv_time/query_time:.0f}x schneller ⚡")
    print("="*80)

print("\n✅ Test abgeschlossen")
