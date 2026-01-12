@echo off
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Nie znaleziono srodowiska wirtualnego w folderze 'venv'.
    echo Sprawdz, czy folder nazywa sie 'venv' czy '.venv' i edytuj ten plik.
    pause
    exit /b
)

echo Uruchamianie serwera Uvicorn...
echo.

uvicorn main:app --reload

pause