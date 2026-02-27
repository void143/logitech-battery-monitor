@echo off
REM Start the Logitech Battery Monitor without a console window.
REM Uses pythonw.exe so no terminal appears.
set SCRIPT=%~dp0monitor.py
set PYW=

REM Try to find pythonw.exe next to the python.exe on PATH
for /f "delims=" %%i in ('where python 2^>nul') do (
    if not defined PYW (
        set "PYW=%%~dpi\pythonw.exe"
    )
)

if not defined PYW (
    echo Could not locate pythonw.exe. Starting with python instead.
    start "" python "%SCRIPT%"
) else (
    if exist "%PYW%" (
        start "" "%PYW%" "%SCRIPT%"
    ) else (
        echo pythonw.exe not found at %PYW%, falling back to python.
        start "" python "%SCRIPT%"
    )
)
