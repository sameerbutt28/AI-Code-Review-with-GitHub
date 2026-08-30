@echo off
title AI Code Review Backend
cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  python -m venv venv
  if errorlevel 1 (
    echo Failed to create venv. Install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
  )
  call venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call venv\Scripts\activate.bat
)

if not exist ".env" (
  echo Creating .env from .env.example ...
  copy .env.example .env >nul
  echo.
  echo IMPORTANT: Open backend\.env and set your OPENAI_API_KEY before demos.
  echo.
)

echo Starting AI Code Review backend (demo mode)...
python run.py --demo
pause
