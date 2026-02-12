# ============================================================
# MAESTRO -- Virtual Audio Setup for Windows
# This configures virtual audio routing for meeting capture.
# Run: powershell -ExecutionPolicy Bypass -File scripts\setup_audio_windows.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Green
Write-Host "  MAESTRO -- Audio Setup (Windows)    " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# -- Check for VB-Cable -------------------------------------------
Write-Host "`nChecking for virtual audio cable..." -ForegroundColor Yellow

$vbCableFound = $false
$audioDevices = Get-CimInstance Win32_SoundDevice | Select-Object -ExpandProperty Name

foreach ($dev in $audioDevices) {
    if ($dev -match "VB-Audio|CABLE|Virtual") {
        Write-Host "  Found virtual audio device: $dev" -ForegroundColor Green
        $vbCableFound = $true
    }
}

if (-not $vbCableFound) {
    Write-Host ""
    Write-Host "  No virtual audio cable detected." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  MAESTRO needs a virtual audio device to capture meeting audio." -ForegroundColor Yellow
    Write-Host "  Install one of the following (free):" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  OPTION A -- VB-Cable (Recommended):" -ForegroundColor Cyan
    Write-Host "    1. Download from: https://vb-audio.com/Cable/" -ForegroundColor White
    Write-Host "    2. Run VBCABLE_Setup_x64.exe as Administrator" -ForegroundColor White
    Write-Host "    3. Reboot your PC" -ForegroundColor White
    Write-Host "    4. Re-run this script" -ForegroundColor White
    Write-Host ""
    Write-Host "  OPTION B -- Virtual Audio Cable (VAC):" -ForegroundColor Cyan
    Write-Host "    Download from: https://vac.muzychenko.net/en/" -ForegroundColor White
    Write-Host ""

    $install = Read-Host "Would you like to open the VB-Cable download page? (y/N)"
    if ($install -eq 'y' -or $install -eq 'Y') {
        Start-Process "https://vb-audio.com/Cable/"
    }

    Write-Host ""
    Write-Host "After installing a virtual audio cable, re-run this script." -ForegroundColor Yellow
    exit 0
}

# -- List audio devices -------------------------------------------
Write-Host "`nAll audio devices:" -ForegroundColor Yellow
$devices = Get-CimInstance Win32_SoundDevice
$index = 0
foreach ($dev in $devices) {
    $marker = "  "
    if ($dev.Name -match "VB-Audio|CABLE|Virtual|Monitor") {
        $marker = "* "
    }
    Write-Host "  $marker[$index] $($dev.Name) ($($dev.Status))"
    $index++
}
Write-Host "  * = Virtual audio device (use for meeting capture)" -ForegroundColor Cyan

# -- Save config ---------------------------------------------------
Write-Host "`nSaving audio device config..." -ForegroundColor Yellow

$configDir = Join-Path $PSScriptRoot "..\config"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

$configFile = Join-Path $configDir "audio_device.txt"

# Try to find the CABLE output/monitor
$cableDevice = $audioDevices | Where-Object { $_ -match "CABLE" } | Select-Object -First 1
if ($cableDevice) {
    Set-Content -Path $configFile -Value "default`n$cableDevice"
    Write-Host "  Saved device: $cableDevice" -ForegroundColor Green
} else {
    Set-Content -Path $configFile -Value "default`ndefault"
    Write-Host "  Using default device" -ForegroundColor Yellow
}

# -- Instructions --------------------------------------------------
Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  HOW TO ROUTE YOUR MEETING AUDIO    " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "1. Open Windows Sound Settings (right-click speaker icon in taskbar)" -ForegroundColor White
Write-Host "2. Set your meeting app's output to 'CABLE Input (VB-Audio Virtual Cable)'" -ForegroundColor White
Write-Host ""
Write-Host "   For Zoom:" -ForegroundColor Cyan
Write-Host "     Settings -> Audio -> Speaker -> CABLE Input" -ForegroundColor White
Write-Host ""
Write-Host "   For Teams:" -ForegroundColor Cyan
Write-Host "     Settings -> Devices -> Speaker -> CABLE Input" -ForegroundColor White
Write-Host ""
Write-Host "   For Google Meet:" -ForegroundColor Cyan
Write-Host "     Settings (gear icon) -> Audio -> Speaker -> CABLE Input" -ForegroundColor White
Write-Host ""
Write-Host "3. To still hear audio yourself:" -ForegroundColor Yellow
Write-Host "   Open VB-Cable Control Panel and enable 'Listen to this device'" -ForegroundColor White
Write-Host "   Or use VoiceMeeter (free) for advanced routing" -ForegroundColor White
Write-Host ""
Write-Host "Test it:" -ForegroundColor Yellow
Write-Host "  python scripts\test_audio_capture.py" -ForegroundColor Cyan
