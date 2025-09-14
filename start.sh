#!/bin/bash
cd "$(dirname "$0")"

# venv anlegen, falls sie nicht existiert
if [ ! -d "venv" ]; then
    echo "🔧 Erstelle virtuelles Environment..."
    python3 -m venv venv
fi

# Pakete installieren
echo "📦 Installiere/prüfe Abhängigkeiten..."
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt

# Programm starten
echo "🚀 Starte Programm..."
exec ./venv/bin/python main.py
