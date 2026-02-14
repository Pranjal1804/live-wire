# ────────────────────────────────────────────────────────────
# MAESTRO  --  System Setup for Windows
# Run (Admin): powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
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

$TOTAL = 8

# -- Banner -----------------------------------------------------------

Write-Host ""
Write-Host "  ┌──────────────────────────────────────────────────┐" -ForegroundColor DarkGray
Write-Host -NoNewline "  │" -ForegroundColor DarkGray
Write-Host -NoNewline "  MAESTRO" -ForegroundColor White
Write-Host -NoNewline "  System Setup                            " -ForegroundColor DarkGray
Write-Host "│" -ForegroundColor DarkGray
Write-Host -NoNewline "  │" -ForegroundColor DarkGray
Write-Host -NoNewline "  Real-time AI sales coaching platform     " -ForegroundColor DarkGray
Write-Host "         │" -ForegroundColor DarkGray
Write-Host "  └──────────────────────────────────────────────────┘" -ForegroundColor DarkGray
Write-Host ""

# -- 1. Package manager -----------------------------------------------

Step 1 $TOTAL "Package manager"

$useWinget = $false
$useChoco  = $false

if (Get-Command winget -ErrorAction SilentlyContinue) {
    Ok "winget"
    $useWinget = $true
} elseif (Get-Command choco -ErrorAction SilentlyContinue) {
    Ok "chocolatey"
    $useChoco = $true
} else {
    Fail
    Note "Install winget (App Installer from Microsoft Store)"
    Note "Or install chocolatey: https://chocolatey.org/install"
    exit 1
}

# -- 2. System dependencies -------------------------------------------

Header "Installing"

Step 2 $TOTAL "System dependencies"
Info "python, nodejs, git, rust"

function Install-IfMissing($cmd, $wingetId, $chocoId) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Info "Installing $cmd..."
        if ($useWinget) {
            winget install --id $wingetId --accept-source-agreements --accept-package-agreements -e 2>$null | Out-Null
        } elseif ($useChoco) {
            choco install $chocoId -y 2>$null | Out-Null
        }
    }
}

Install-IfMissing "python" "Python.Python.3.12" "python312"
Install-IfMissing "node"   "OpenJS.NodeJS.LTS"  "nodejs-lts"
Install-IfMissing "git"    "Git.Git"             "git"
Install-IfMissing "rustc"  "Rustlang.Rustup"     "rustup.install"

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
Ok

# -- 3. Rust toolchain ------------------------------------------------

Step 3 $TOTAL "Rust toolchain"

if (Get-Command rustup -ErrorAction SilentlyContinue) {
    rustup default stable 2>$null | Out-Null
    rustup update stable 2>$null | Out-Null
    $rustVer = rustc --version 2>$null
    Ok $rustVer
} else {
    Skip "restart terminal, then: rustup default stable"
}

# -- 4. pnpm ----------------------------------------------------------

Step 4 $TOTAL "pnpm"

if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    $pnpmVer = pnpm --version 2>$null
    Skip "v$pnpmVer"
} else {
    npm install -g pnpm 2>$null | Out-Null
    Ok
}

# -- 5. C++ build tools -----------------------------------------------

Step 5 $TOTAL "C++ build tools"

$vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vsWhere) {
    $vsInstalls = & $vsWhere -latest -property installationPath 2>$null
    if ($vsInstalls) {
        Ok
    } else {
        Skip "install Visual C++ build tools"
    }
} else {
    Skip
    Info "Tauri requires MSVC C++ build tools"
    Info "https://visualstudio.microsoft.com/visual-cpp-build-tools/"
    Info "Select 'Desktop development with C++' workload"
}
Info "WebView2 is included in Windows 10/11"

# -- 6. Python backend ------------------------------------------------

Step 6 $TOTAL "Python environment"

Push-Location "$PSScriptRoot\.."

python -m venv backend\venv 2>$null
& backend\venv\Scripts\Activate.ps1

pip install --upgrade pip -q 2>$null | Out-Null

pip install -q `
    "fastapi>=0.109.0" `
    "uvicorn[standard]>=0.25.0" `
    "websockets>=12.0" `
    "python-dotenv>=1.0.0" `
    "sounddevice>=0.4.6" `
    "torch>=2.9.0" `
    "torchaudio>=2.9.0" `
    "faster-whisper>=0.10.0" `
    "onnxruntime>=1.16.3" `
    "transformers>=4.37.0" `
    "chromadb>=0.4.22" `
    "langchain>=0.1.0" `
    "langchain-google-genai>=0.0.6" `
    "langgraph>=0.0.26" `
    "google-generativeai>=0.3.2" `
    "redis>=5.0.1" `
    "httpx>=0.26.0" `
    "pyyaml>=6.0.1" `
    "silero-vad>=4.0.0" `
    "huggingface-hub>=0.20.3" `
    "sentence-transformers>=2.3.1" `
    "aiofiles>=23.2.1" `
    "python-multipart>=0.0.6" `
    "slack-sdk>=3.26.2" `
    "numpy" `
    "scipy" 2>$null | Out-Null

deactivate
Ok

# -- 7. Frontend -------------------------------------------------------

Step 7 $TOTAL "Frontend packages"

Push-Location frontend
Info "pnpm install"
pnpm install --silent 2>$null | Out-Null
Pop-Location
Ok

# -- 8. Redis (optional) -----------------------------------------------

Step 8 $TOTAL "Redis"

if (Get-Command redis-server -ErrorAction SilentlyContinue) {
    Ok
} else {
    Skip "optional, falls back to JSON file storage"
    Info "To install: winget install Redis.Redis"
}

Pop-Location

# -- Done --------------------------------------------------------------

Write-Host ""
Write-Host "  ┌──────────────────────────────────────────────────┐" -ForegroundColor DarkGray
Write-Host -NoNewline "  │" -ForegroundColor DarkGray
Write-Host -NoNewline "  Setup complete" -ForegroundColor DarkGreen
Write-Host "                                  │" -ForegroundColor DarkGray
Write-Host "  └──────────────────────────────────────────────────┘" -ForegroundColor DarkGray

Header "Next steps"
Write-Host "  1.  " -NoNewline -ForegroundColor White
Write-Host "powershell scripts\setup_audio_windows.ps1" -ForegroundColor DarkGray
Info "Configure virtual audio"
Write-Host "  2.  " -NoNewline -ForegroundColor White
Write-Host "python scripts\download_models.py" -ForegroundColor DarkGray
Info "Download AI models (~400MB)"
Write-Host "  3.  " -NoNewline -ForegroundColor White
Write-Host "copy .env.example .env" -ForegroundColor DarkGray
Info "Add your Gemini API key"
Write-Host "  4.  " -NoNewline -ForegroundColor White
Write-Host "cd backend && .\venv\Scripts\Activate.ps1 &&" -ForegroundColor DarkGray
Write-Host "      uvicorn main:app --reload --port 8000" -ForegroundColor DarkGray
Info "Start the backend"
Write-Host "  5.  " -NoNewline -ForegroundColor White
Write-Host "cd frontend && pnpm tauri dev" -ForegroundColor DarkGray
Info "Launch the overlay"
Write-Host ""

Note "If you just installed Rust or Build Tools, restart your terminal first."
Write-Host ""
