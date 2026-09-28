@echo off
rem Double-click once on a new laptop to install everything (after installing Python and Node.js).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
pause
