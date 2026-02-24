@echo off
:: Nova Voice Assistant — Silent Launcher
:: Starts Nova in system tray mode without a console window.
:: Double-click this file or add it to Windows Startup folder.

set "VENV=%~dp0..\.venv-1\Scripts\pythonw.exe"
set "SCRIPT=%~dp0tray_app.py"

if exist "%VENV%" (
    start "" "%VENV%" "%SCRIPT%"
) else (
    :: Fallback: use system pythonw
    start "" pythonw "%SCRIPT%"
)
