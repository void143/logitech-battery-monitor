$ErrorActionPreference = "Stop"

$root        = Split-Path $PSScriptRoot -Parent
$installerDir = $PSScriptRoot
$distDir     = Join-Path $root "dist"
$wix         = Join-Path $env:USERPROFILE ".dotnet\tools\wix.exe"

# Read version from monitor.py
$versionLine = Select-String -Path (Join-Path $root "monitor.py") -Pattern 'APP_VERSION\s*=\s*"(.+)"'
$appVersion  = $versionLine.Matches[0].Groups[1].Value
$msiName     = "LogitechBatteryMonitor-$appVersion-x64.msi"
$msiPath     = Join-Path $distDir $msiName

Write-Host "Version : $appVersion"
Write-Host "Output  : $msiPath"

# Ensure dist dir exists
New-Item -ItemType Directory -Force $distDir | Out-Null

# Set env var for WiX preprocessor $(env.APP_VERSION)
$env:APP_VERSION = $appVersion

# Build (run from installer dir so .wix extension cache is found)
Push-Location $installerDir
try {
    $extList = & $wix extension list 2>$null
    if (-not ($extList -match "WixToolset\.UI")) {
        Write-Host "Installing WiX UI extension..."
        & $wix extension add WixToolset.UI.wixext/6.0.2
    }
    & $wix build "package.wxs" -o $msiPath -ext WixToolset.UI.wixext
    if ($LASTEXITCODE -ne 0) { throw "WiX build failed (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "MSI ready: $msiPath"
Write-Host "Size     : $([math]::Round((Get-Item $msiPath).Length / 1MB, 1)) MB"
