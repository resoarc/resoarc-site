@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js 20 or newer is required. Please install Node.js and try again.
  pause
  exit /b 1
)
if not exist "dist\index.html" (
  echo ResoArc Sheet build is missing. Please use the full QA package.
  pause
  exit /b 1
)
start "ResoArc Sheet - offline" /min cmd /k "node serve.mjs"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5174/"
endlocal