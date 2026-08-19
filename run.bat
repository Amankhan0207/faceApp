@echo off
REM Windows launcher
cd /d "%~dp0"

if not exist ".venv" (
  echo Setting up for the first time. This downloads a few hundred MB.
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  
  REM Get Python version
  for /f "tokens=2 delims= " %%I in ('python --version 2^>^&1') do set PY_VER=%%I
  
  echo Detected Python version: %PY_VER%
  
  if "%PY_VER:~0,4%"=="3.13" (
    echo Installing precompiled insightface wheel for Python 3.13...
    .venv\Scripts\pip install https://github.com/Gourieff/Assets/raw/main/Insightface/insightface-0.7.3-cp313-cp313-win_amd64.whl
  ) else if "%PY_VER:~0,4%"=="3.12" (
    echo Installing precompiled insightface wheel for Python 3.12...
    .venv\Scripts\pip install https://github.com/Gourieff/Assets/raw/main/Insightface/insightface-0.7.3-cp312-cp312-win_amd64.whl
  ) else if "%PY_VER:~0,4%"=="3.11" (
    echo Installing precompiled insightface wheel for Python 3.11...
    .venv\Scripts\pip install https://github.com/Gourieff/Assets/raw/main/Insightface/insightface-0.7.3-cp311-cp311-win_amd64.whl
  ) else if "%PY_VER:~0,4%"=="3.10" (
    echo Installing precompiled insightface wheel for Python 3.10...
    .venv\Scripts\pip install https://github.com/Gourieff/Assets/raw/main/Insightface/insightface-0.7.3-cp310-cp310-win_amd64.whl
  )
  
  .venv\Scripts\pip install -r requirements.txt
)

.venv\Scripts\python app.py
