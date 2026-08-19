@echo off
REM Windows launcher
cd /d "%~dp0"

if not exist ".venv" (
  echo Setting up for the first time. This downloads a few hundred MB.
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt
)

.venv\Scripts\python app.py
