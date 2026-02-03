#!/bin/bash
# Startet das Dashboard

cd "$(dirname "$0")"

# Aktiviere venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual Environment nicht gefunden!"
    exit 1
fi

# Starte Hauptanwendung
python src/main.py

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
