# ────────────────────────────────────────────────────────────
# MAESTRO  --  Virtual Audio Setup for Windows
# Run: powershell -ExecutionPolicy Bypass -File scripts\setup_audio_windows.ps1
# ────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

# -- Helpers ----------------------------------------------------------

function Hr {
    Write-Host "  ────────────────────────────────────────────────────" -ForegroundColor DarkGray
}

function Header($title) {
    Write-Host ""
    Write-Host "  $title" -ForegroundColor White
    Hr
}

function Step($n, $total, $msg) {
    Write-Host "  " -NoNewline
    Write-Host "[$n/$total]" -ForegroundColor DarkCyan -NoNewline
    Write-Host " $msg" -ForegroundColor White -NoNewline
}

function Ok($detail) {
    Write-Host " done" -ForegroundColor DarkGreen -NoNewline
    if ($detail) { Write-Host "  $detail" -ForegroundColor DarkGray } else { Write-Host "" }
}

function Skip($detail) {
    Write-Host " skipped" -ForegroundColor DarkYellow -NoNewline
    if ($detail) { Write-Host "  $detail" -ForegroundColor DarkGray } else { Write-Host "" }
}

function Fail($detail) {
    Write-Host " failed" -ForegroundColor DarkRed -NoNewline
    if ($detail) { Write-Host "  $detail" -ForegroundColor DarkGray } else { Write-Host "" }
}

function Info($msg) {
    Write-Host "       $msg" -ForegroundColor DarkGray
}

function Note($msg) {
    Write-Host "  -->  $msg" -ForegroundColor DarkYellow
}

# -- Banner -----------------------------------------------------------

Write-Host ""
Write-Host "  ┌──────────────────────────────────────────────────┐" -ForegroundColor DarkGray
Write-Host -NoNewline "  │" -ForegroundColor DarkGray
Write-Host -NoNewline "  MAESTRO" -ForegroundColor White
Write-Host -NoNewline "  Audio Setup (Windows)                   " -ForegroundColor DarkGray
Write-Host "│" -ForegroundColor DarkGray
Write-Host -NoNewline "  │" -ForegroundColor DarkGray
Write-Host -NoNewline "  Virtual audio routing for meeting capture" -ForegroundColor DarkGray
Write-Host "        │" -ForegroundColor DarkGray
Write-Host "  └──────────────────────────────────────────────────┘" -ForegroundColor DarkGray
Write-Host ""

# -- 1. Detect virtual audio cable ------------------------------------

Step 1 4 "Detect virtual audio cable"

$vbCableFound = $false
$audioDevices = Get-CimInstance Win32_SoundDevice | Select-Object -ExpandProperty Name

foreach ($dev in $audioDevices) {
    if ($dev -match "VB-Audio|CABLE|Virtual") {
        $vbCableFound = $true
    }
}

if ($vbCableFound) {
    Ok
    foreach ($dev in $audioDevices) {
        if ($dev -match "VB-Audio|CABLE|Virtual") {
            Info $dev
        }
    }
} else {
    Fail "no virtual audio cable detected"
    Write-Host ""
    Note "MAESTRO needs a virtual audio device to capture meeting audio."
    Note "Install one of the following (free):"
    Write-Host ""

    Header "Option A -- VB-Cable (recommended)"
    Info "1. Download from: https://vb-audio.com/Cable/"
    Info "2. Run VBCABLE_Setup_x64.exe as Administrator"
    Info "3. Reboot your PC"
    Info "4. Re-run this script"

    Header "Option B -- Virtual Audio Cable (VAC)"
    Info "Download from: https://vac.muzychenko.net/en/"

    Write-Host ""
    $install = Read-Host "       Open the VB-Cable download page? (y/N)"
    if ($install -eq 'y' -or $install -eq 'Y') {
        Start-Process "https://vb-audio.com/Cable/"
    }

    Write-Host ""
    Note "After installing a virtual audio cable, re-run this script."
    exit 0
}

# -- 2. List audio devices --------------------------------------------

Step 2 4 "Enumerate audio devices"
Ok

Header "Audio devices"
$devices = Get-CimInstance Win32_SoundDevice
$index = 0
foreach ($dev in $devices) {
    $marker = "  "
    if ($dev.Name -match "VB-Audio|CABLE|Virtual|Monitor") {
        $marker = ">>"
    }
    Write-Host "  $marker " -NoNewline -ForegroundColor DarkGreen
    Write-Host "[$index]" -NoNewline -ForegroundColor DarkGray
    Write-Host " $($dev.Name)" -NoNewline
    Write-Host "  ($($dev.Status))" -ForegroundColor DarkGray
    $index++
}
Write-Host ""
Info ">> = virtual audio device (use for meeting capture)"

# -- 3. Save config ---------------------------------------------------

Step 3 4 "Save device config"

$configDir = Join-Path $PSScriptRoot "..\config"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

$configFile = Join-Path $configDir "audio_device.txt"

$cableDevice = $audioDevices | Where-Object { $_ -match "CABLE" } | Select-Object -First 1
if ($cableDevice) {
    Set-Content -Path $configFile -Value "default`n$cableDevice"
    Ok $cableDevice
} else {
    Set-Content -Path $configFile -Value "default`ndefault"
    Skip "using default device"
}

# -- 4. Verify --------------------------------------------------------

Step 4 4 "Verify"
Ok

# -- Routing instructions ---------------------------------------------

Header "How to route meeting audio"

Write-Host "  A.  " -NoNewline -ForegroundColor White
Write-Host "Open Windows Sound Settings" -ForegroundColor DarkGray
Info "Right-click speaker icon in taskbar"
Info "Set meeting app output to 'CABLE Input (VB-Audio Virtual Cable)'"
Write-Host ""

Write-Host "  B.  " -NoNewline -ForegroundColor White
Write-Host "Per-app routing" -ForegroundColor DarkGray
Info "Zoom:        Settings > Audio > Speaker > CABLE Input"
Info "Teams:       Settings > Devices > Speaker > CABLE Input"
Info "Google Meet: Settings (gear) > Audio > Speaker > CABLE Input"
Write-Host ""

Write-Host "  C.  " -NoNewline -ForegroundColor White
Write-Host "To still hear audio yourself" -ForegroundColor DarkGray
Info "Open VB-Cable Control Panel and enable 'Listen to this device'"
Info "Or use VoiceMeeter (free) for advanced routing"
Write-Host ""

Note "Test it: python scripts\test_audio_capture.py"
Write-Host ""
