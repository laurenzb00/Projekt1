"""
Synchronisiere CSV-Dateien vom Raspberry Pi zum lokalen PC
"""
import paramiko
import os
from datetime import datetime

# Raspberry Pi Konfiguration
PI_HOST = "192.168.1.200"
PI_USER = "laurenz"
PI_PASSWORD = "laurenz"
PI_PATH = "/home/laurenz/projekt1/Projekt1/"

# Lokaler Pfad
LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))

# Dateien zum Synchronisieren
FILES_TO_SYNC = [
    "FroniusDaten.csv",
    "Heizungstemperaturen.csv",
    "ErtragHistory.csv",
]


def sync_files():
    """Synchronisiere Dateien vom Pi zum PC."""
    try:
        print(f"Verbinde zu {PI_HOST}...")
        
        # SSH-Verbindung aufbauen
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(PI_HOST, username=PI_USER, password=PI_PASSWORD)
        
        # SFTP-Session öffnen
        sftp = ssh.open_sftp()
        
        print(f"✓ Verbunden\n")
        
        # Dateien herunterladen
        for filename in FILES_TO_SYNC:
            remote_file = os.path.join(PI_PATH, filename).replace("\\", "/")
            local_file = os.path.join(LOCAL_PATH, filename)
            
            try:
                print(f"Lade {filename}...", end=" ")
                sftp.get(remote_file, local_file)
                
                # Dateigröße anzeigen
                size = os.path.getsize(local_file)
                size_mb = size / (1024 * 1024)
                print(f"✓ ({size_mb:.2f} MB)")
                
            except FileNotFoundError:
                print(f"✗ Datei nicht gefunden auf Pi")
            except Exception as e:
                print(f"✗ Fehler: {e}")
        
        # Verbindung schließen
        sftp.close()
        ssh.close()
        
        print(f"\n✓ Synchronisation abgeschlossen ({datetime.now().strftime('%H:%M:%S')})")
        return True
        
    except Exception as e:
        print(f"✗ Fehler bei Verbindung: {e}")
        return False


if __name__ == "__main__":
    sync_files()
