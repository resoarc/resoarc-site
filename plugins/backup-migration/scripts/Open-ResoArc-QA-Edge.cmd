@echo off
setlocal
cd /d "%~dp0.."
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is required to start the dedicated QA Edge.
  pause
  exit /b 1
)
node scripts\qa-edge.mjs start
if errorlevel 1 pause
