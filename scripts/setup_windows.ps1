# ============================================================
# MAESTRO -- Full System Setup for Windows
# Run (PowerShell as Admin): powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
# ============================================================

$ErrorActionPreference = "Stop"

function Write-Step($step, $total, $msg) {
    Write-Host "`n[$step/$total] $msg" -ForegroundColor Yellow
}

Write-Host "=====================================" -ForegroundColor Green
Write-Host "  MAESTRO Setup -- Windows            " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# -- 1. Check for winget or choco --------------------------------
Write-Step 1 8 "Checking package manager..."

$useWinget = $false
$useChoco = $false

if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "Found winget" -ForegroundColor Green
    $useWinget = $true
} elseif (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Host "Found chocolatey" -ForegroundColor Green
    $useChoco = $true
} else {
    Write-Host "Neither winget nor chocolatey found." -ForegroundColor Red
    Write-Host "Install winget (comes with App Installer from Microsoft Store)" -ForegroundColor Red
    Write-Host "Or install chocolatey: https://chocolatey.org/install" -ForegroundColor Red
    exit 1
}

# -- 2. Install system dependencies ------------------------------
Write-Step 2 8 "Installing system dependencies..."

function Install-IfMissing($cmd, $wingetId, $chocoId) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "  Installing $cmd..."
        if ($useWinget) {
            winget install --id $wingetId --accept-source-agreements --accept-package-agreements -e
        } elseif ($useChoco) {
            choco install $chocoId -y
        }
    } else {
        Write-Host "  $cmd already installed" -ForegroundColor Green
    }
}

Install-IfMissing "python" "Python.Python.3.12" "python312"
Install-IfMissing "node" "OpenJS.NodeJS.LTS" "nodejs-lts"
Install-IfMissing "git" "Git.Git" "git"
Install-IfMissing "rustc" "Rustlang.Rustup" "rustup.install"

# Refresh PATH after installations
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

# -- 3. Install Rust (if rustup was just installed) ----------------
Write-Step 3 8 "Checking Rust toolchain..."

if (Get-Command rustup -ErrorAction SilentlyContinue) {
    rustup default stable
    rustup update stable
    Write-Host "Rust $(rustc --version)" -ForegroundColor Green
} else {
    Write-Host "rustup not found in PATH. You may need to restart your terminal." -ForegroundColor Yellow
    Write-Host "Then run: rustup default stable" -ForegroundColor Yellow
}

# -- 4. Install pnpm ---------------------------------------------
Write-Step 4 8 "Checking pnpm..."

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Host "  Installing pnpm..."
    npm install -g pnpm
} else {
    Write-Host "  pnpm already installed: $(pnpm --version)" -ForegroundColor Green
}

# -- 5. Install Visual Studio Build Tools (for native deps) --------
Write-Step 5 8 "Checking C++ build tools..."

# Tauri on Windows needs MSVC build tools and WebView2
$vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vsWhere) {
    $vsInstalls = & $vsWhere -latest -property installationPath
    if ($vsInstalls) {
        Write-Host "  Visual Studio Build Tools found" -ForegroundColor Green
    }
} else {
    Write-Host "  Visual Studio Build Tools not detected." -ForegroundColor Yellow
    Write-Host "  Tauri requires MSVC C++ build tools." -ForegroundColor Yellow
    Write-Host "  Install from: https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Yellow
    Write-Host "  Select 'Desktop development with C++' workload." -ForegroundColor Yellow
}

# WebView2 is included in Windows 10 1803+ and Windows 11
Write-Host "  WebView2 (required by Tauri) is included in Windows 10/11" -ForegroundColor Green

# -- 6. Python backend setup --------------------------------------
Write-Step 6 8 "Setting up Python virtual environment..."

Push-Location "$PSScriptRoot\.."

python -m venv backend\venv
& backend\venv\Scripts\Activate.ps1

pip install --upgrade pip

pip install `
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
    "scipy"

deactivate

Write-Host "Python environment ready!" -ForegroundColor Green

# -- 7. Frontend setup --------------------------------------------
Write-Step 7 8 "Setting up frontend (Tauri v2 + React)..."

Push-Location frontend
pnpm install
Pop-Location

# -- 8. Redis (optional) ------------------------------------------
Write-Step 8 8 "Redis setup..."

if (Get-Command redis-server -ErrorAction SilentlyContinue) {
    Write-Host "  Redis already installed" -ForegroundColor Green
} else {
    Write-Host "  Redis is optional on Windows. MAESTRO falls back to JSON file storage." -ForegroundColor Yellow
    Write-Host "  To install Redis: winget install Redis.Redis" -ForegroundColor Yellow
    Write-Host "  Or use Memurai (Redis-compatible for Windows): https://www.memurai.com/" -ForegroundColor Yellow
}

Pop-Location

# -- Done ---------------------------------------------------------
Write-Host "`n=====================================" -ForegroundColor Green
Write-Host "  MAESTRO Setup Complete!              " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. " -NoNewline; Write-Host "powershell scripts\setup_audio_windows.ps1" -ForegroundColor Yellow -NoNewline; Write-Host " -- Configure virtual audio"
Write-Host "  2. " -NoNewline; Write-Host "python scripts\download_models.py" -ForegroundColor Yellow -NoNewline; Write-Host "          -- Download AI models (~400MB)"
Write-Host "  3. " -NoNewline; Write-Host "copy .env.example .env" -ForegroundColor Yellow -NoNewline; Write-Host "                       -- Add your Gemini API key"
Write-Host "  4. " -NoNewline; Write-Host "cd backend && .\venv\Scripts\Activate.ps1 && uvicorn main:app --reload" -ForegroundColor Yellow
Write-Host "  5. " -NoNewline; Write-Host "cd frontend && pnpm tauri dev" -ForegroundColor Yellow -NoNewline; Write-Host "              -- Launch overlay"
Write-Host ""
Write-Host "NOTE: If you just installed Rust or Build Tools, restart your terminal first." -ForegroundColor Red
