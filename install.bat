@echo off
echo Installing Logitech Battery Monitor dependencies...
pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo ERROR: pip install failed. Make sure Python is installed and on PATH.
    pause
    exit /b 1
)
echo.
echo Installation complete. Run start.bat to launch the monitor.
pause
