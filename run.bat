@echo off
rem Double-click to start Marksheet at http://localhost:8000 (close this window to stop).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
pause
