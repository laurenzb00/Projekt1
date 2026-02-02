"""
Synchronisiere FroniusDaten.csv vom Raspberry Pi mit telnetlib
"""
import socket
import os

PI_HOST = "192.168.1.200"
PI_USER = "laurenz"
PI_PASSWORD = "laurenz"
PI_PATH = "/home/laurenz/projekt1/Projekt1/FroniusDaten.csv"
LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))

# Nutze SCP über subprocess
import subprocess

try:
    remote_file = f"{PI_USER}@{PI_HOST}:{PI_PATH}"
    local_file = os.path.join(LOCAL_PATH, "FroniusDaten.csv")
    
    print(f"Verbinde zu {PI_HOST}...")
    print(f"Lade FroniusDaten.csv herunter (8.7 MiB)...\n")
    
    # Nutze plink (PuTTY) oder SSH über subprocess
    import sys
    
    cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        f"{PI_USER}@{PI_HOST}:{PI_PATH}",
        local_file
    ]
    
    # Mit Passwort
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode == 0:
        size = os.path.getsize(local_file) / (1024 * 1024)
        print(f"\n✓ FroniusDaten.csv erfolgreich heruntergeladen ({size:.2f} MiB)")
    else:
        print(f"\n✗ Fehler beim Download")
        
except Exception as e:
    print(f"✗ Fehler: {e}")
