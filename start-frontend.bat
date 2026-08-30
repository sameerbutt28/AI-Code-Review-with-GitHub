@echo off
title AI Code Review Frontend
cd /d "%~dp0frontend"

if not exist "node_modules" (
  echo Installing frontend dependencies (first run)...
  call npm install
  if errorlevel 1 (
    echo npm install failed. Install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
  )
)

echo Starting AI Code Review frontend...
echo Open http://localhost:5173 in your browser
call npm run dev
pause
