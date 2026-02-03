@echo off
REM Startet das Dashboard auf Windows

cd /d "%~dp0"

REM Aktiviere venv
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Virtual Environment nicht gefunden!
    echo Bitte erstelle mit: python -m venv .venv
    pause
    exit /b 1
)

REM Starte Hauptanwendung
python src\main.py
pause
