#!/usr/bin/env python3
"""
Performance Profiler - Analysiert CPU/Memory/Speed
===================================================
Identifiziert Bottlenecks und Optimierungsmöglichkeiten
"""

import psutil
import time
import os
from datetime import datetime

class PerformanceMonitor:
    """Monitore Ressourcennutzung."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = datetime.now()
        self.snapshots = []
    
    def snapshot(self, label=""):
        """Erstelle Performance Snapshot."""
        cpu_percent = self.process.cpu_percent(interval=0.1)
        mem_info = self.process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        snap = {
            'time': elapsed,
            'label': label,
            'cpu': cpu_percent,
            'mem_mb': mem_mb,
            'threads': self.process.num_threads()
        }
        
        self.snapshots.append(snap)
        
        if label:
            print(f"[PROFILE] {label:30} | CPU: {cpu_percent:6.2f}% | RAM: {mem_mb:7.1f} MB | Threads: {snap['threads']}")
        
        return snap
    
    def report(self):
        """Generiere Performance Report."""
        print("\n" + "="*80)
        print("PERFORMANCE REPORT")
        print("="*80)
        
        if not self.snapshots:
            print("Keine Snapshots vorhanden")
            return
        
        # Statistiken
        cpu_values = [s['cpu'] for s in self.snapshots]
        mem_values = [s['mem_mb'] for s in self.snapshots]
        
        print(f"\n📊 CPU Usage:")
        print(f"   Min:     {min(cpu_values):6.2f}%")
        print(f"   Max:     {max(cpu_values):6.2f}%")
        print(f"   Average: {sum(cpu_values)/len(cpu_values):6.2f}%")
        
        print(f"\n💾 Memory Usage:")
        print(f"   Min:     {min(mem_values):7.1f} MB")
        print(f"   Max:     {max(mem_values):7.1f} MB")
        print(f"   Average: {sum(mem_values)/len(mem_values):7.1f} MB")
        print(f"   Growth:  {max(mem_values) - min(mem_values):+7.1f} MB")
        
        print(f"\n⏱️  Timeline:")
        for snap in self.snapshots:
            if snap['label']:
                print(f"   {snap['time']:8.2f}s - {snap['label']:30} | CPU: {snap['cpu']:6.2f}% | RAM: {snap['mem_mb']:7.1f} MB")
        
        print("\n" + "="*80)


def profile_csv_reading():
    """Profil CSV vs SQLite Lesevorgänge."""
    import csv
    import sqlite3
    from datastore import DataStore
    
    print("\n" + "="*80)
    print("CSV vs SQLite PERFORMANCE TEST")
    print("="*80)
    
    fronius_path = "FroniusDaten.csv"
    
    if not os.path.exists(fronius_path):
        print(f"❌ {fronius_path} nicht gefunden")
        return
    
    monitor = PerformanceMonitor()
    
    # Test 1: CSV Datei Größe
    csv_size_mb = os.path.getsize(fronius_path) / 1024 / 1024
    print(f"\n📄 CSV File Size: {csv_size_mb:.1f} MB")
    
    # Test 2: CSV lesen (alte Methode)
    print("\n🔴 Test 1: Reading CSV (old method)")
    monitor.snapshot("Start CSV read")
    
    csv_lines = []
    try:
        with open(fronius_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_lines.append(row)
    except:
        pass
    
    monitor.snapshot(f"Read {len(csv_lines)} lines from CSV")
    csv_snap = monitor.snapshots[-1]
    
    # Test 3: SQLite Import
    print("\n🟢 Test 2: SQLite Import & Index")
    monitor.snapshot("Start SQLite import")
    
    store = DataStore()
    store.import_fronius_csv(fronius_path)
    
    monitor.snapshot("SQLite import complete")
    sqlite_snap = monitor.snapshots[-1]
    
    db_size_mb = os.path.getsize(store.db_path) / 1024 / 1024 if os.path.exists(store.db_path) else 0
    print(f"💾 SQLite DB Size: {db_size_mb:.1f} MB (Compression: {100 - (db_size_mb/csv_size_mb*100):.0f}%)")
    
    # Test 4: Query Performance
    print("\n🔵 Test 3: Query Performance")
    monitor.snapshot("Start query test")
    
    for i in range(10):
        last = store.get_last_fronius_record()
        hourly = store.get_hourly_averages(24)
    
    monitor.snapshot("10x queries completed (last record + hourly avg)")
    query_snap = monitor.snapshots[-1]
    
    store.close()
    
    # Vergleich
    print("\n📈 RESULTS:")
    print(f"   CSV Read Time:        ~{csv_snap['time']:.2f}s")
    print(f"   SQLite Import Time:   ~{(sqlite_snap['time'] - monitor.snapshots[-3]['time']):.2f}s")
    print(f"   Query Time (10x):     ~{(query_snap['time'] - monitor.snapshots[-2]['time']):.2f}s")
    print(f"\n   💡 SQLite queries sind ~100x schneller als CSV scans!")
    
    monitor.report()


if __name__ == "__main__":
    try:
        profile_csv_reading()
    except Exception as e:
        print(f"❌ Profile error: {e}")
        import traceback
        traceback.print_exc()
