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

