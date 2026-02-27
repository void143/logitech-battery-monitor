@echo off
setlocal EnableDelayedExpansion

:: ---------------------------------------------------------------------------
:: Logitech Battery Monitor — MSI build script
:: Requires: Python 3.10+, .NET SDK 6+
:: Produces:  dist\LogitechBatteryMonitor-<version>-x64.msi
:: ---------------------------------------------------------------------------

cd /d "%~dp0.."
set ROOT=%CD%
set INSTALLER_DIR=%ROOT%\installer
set DIST_DIR=%ROOT%\dist

:: Read version from monitor.py
for /f "tokens=3 delims= " %%v in ('findstr /r "^APP_VERSION" "%ROOT%\monitor.py"') do (
    set APP_VERSION=%%v
    set APP_VERSION=!APP_VERSION:"=!
)
echo Version: %APP_VERSION%
set MSI_NAME=LogitechBatteryMonitor-%APP_VERSION%-x64.msi

:: ---------------------------------------------------------------------------
:: Step 1 — Install build tools
:: ---------------------------------------------------------------------------
echo.
echo [1/5] Checking build tools...
pip show pyinstaller >nul 2>&1 || (
    echo Installing PyInstaller...
    pip install pyinstaller
)

dotnet tool list -g 2>nul | findstr "wix" >nul || (
    echo Installing WiX 4 toolset...
    dotnet tool install --global wix
)

:: Refresh PATH so wix.exe is visible in this session
set PATH=%PATH%;%USERPROFILE%\.dotnet\tools

:: ---------------------------------------------------------------------------
:: Step 2 — Generate icon.ico
:: ---------------------------------------------------------------------------
echo.
echo [2/5] Generating icon.ico...
python "%INSTALLER_DIR%\make_icon.py"
if %errorlevel% neq 0 (echo ERROR: Icon generation failed & exit /b 1)

:: ---------------------------------------------------------------------------
:: Step 3 — PyInstaller: bundle app into single exe
:: ---------------------------------------------------------------------------
echo.
echo [3/5] Building standalone executable (PyInstaller)...
pyinstaller "%INSTALLER_DIR%\monitor.spec" --distpath "%DIST_DIR%" --workpath "%ROOT%\build" --noconfirm
if %errorlevel% neq 0 (echo ERROR: PyInstaller failed & exit /b 1)
if not exist "%DIST_DIR%\LogitechBatteryMonitor.exe" (
    echo ERROR: Expected %DIST_DIR%\LogitechBatteryMonitor.exe not found
    exit /b 1
)

:: ---------------------------------------------------------------------------
:: Step 4 — WiX 4: build MSI
:: ---------------------------------------------------------------------------
echo.
echo [4/5] Building MSI (WiX 4)...
set APP_VERSION=%APP_VERSION%
wix build "%INSTALLER_DIR%\package.wxs" -o "%DIST_DIR%\%MSI_NAME%"
if %errorlevel% neq 0 (echo ERROR: WiX build failed & exit /b 1)

:: ---------------------------------------------------------------------------
:: Step 5 — Done
:: ---------------------------------------------------------------------------
echo.
echo [5/5] Done!
echo.
echo Installer: %DIST_DIR%\%MSI_NAME%
echo.
pause
