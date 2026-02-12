#!/bin/bash
# ============================================================
# MAESTRO — Full System Setup for EndeavourOS (Arch-based)
# Run: bash scripts/setup_endeavouros.sh
# ============================================================

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  MAESTRO Setup — EndeavourOS        ${NC}"
echo -e "${GREEN}=====================================${NC}"

# ── 1. System Update ─────────────────────────────────────────
echo -e "\n${YELLOW}[1/8] Updating system...${NC}"
sudo pacman -Syu --noconfirm

# ── 2. Audio System Check (EndeavourOS uses PipeWire) ────────
echo -e "\n${YELLOW}[2/8] Checking audio system...${NC}"
if systemctl --user is-active --quiet pipewire; then
    echo -e "${GREEN}PipeWire is active (EndeavourOS default — perfect!)${NC}"
    echo "PipeWire is compatible with PulseAudio API via pipewire-pulse"
    
    # Install PipeWire packages and PipeWire-compatible volume control
    sudo pacman -S --noconfirm pipewire-pulse pipewire-alsa pipewire-jack pavucontrol || true
else
    echo -e "${YELLOW}PipeWire not active, installing PulseAudio...${NC}"
    sudo pacman -S --noconfirm pulseaudio pulseaudio-alsa pavucontrol
    systemctl --user enable pulseaudio
    systemctl --user start pulseaudio
fi

# ── 3. Core System Dependencies ──────────────────────────────
echo -e "\n${YELLOW}[3/8] Installing system dependencies...${NC}"
sudo pacman -S --noconfirm \
    python \
    python-pip \
    python-virtualenv \
    python-numpy \
    python-scipy \
    nodejs \
    npm \
    git \
    curl \
    wget \
    redis \
    ffmpeg \
    portaudio \
    base-devel \
    cmake \
    pkg-config \
    gcc-fortran \
    openblas \
    lapack

# ── 4. AUR Helper (yay) for additional packages ───────────────
echo -e "\n${YELLOW}[4/8] Checking for yay (AUR helper)...${NC}"
if ! command -v yay &> /dev/null; then
    echo "Installing yay..."
    cd /tmp
    git clone https://aur.archlinux.org/yay.git
    cd yay
    makepkg -si --noconfirm
    cd -
else
    echo -e "${GREEN}yay already installed${NC}"
fi

# ── 5. Python Backend Dependencies ───────────────────────────
echo -e "\n${YELLOW}[5/8] Setting up Python virtual environment...${NC}"
cd "$(dirname "$0")/.."

# Create venv with system-site-packages to use system numpy/scipy
python -m venv --system-site-packages backend/venv
source backend/venv/bin/activate

pip install --upgrade pip

# Install packages (numpy and scipy come from system packages)
pip install \
    fastapi>=0.109.0 \
    "uvicorn[standard]>=0.25.0" \
    websockets>=12.0 \
    python-dotenv>=1.0.0 \
    sounddevice>=0.4.6 \
    torch>=2.9.0 \
    torchaudio>=2.9.0 \
    faster-whisper>=0.10.0 \
    onnxruntime>=1.16.3 \
    transformers>=4.37.0 \
    chromadb>=0.4.22 \
    langchain>=0.1.0 \
    langchain-google-genai>=0.0.6 \
    langgraph>=0.0.26 \
    google-generativeai>=0.3.2 \
    redis>=5.0.1 \
    httpx>=0.26.0 \
    pyyaml>=6.0.1 \
    silero-vad>=4.0.0 \
    huggingface-hub>=0.20.3 \
    sentence-transformers>=2.3.1 \
    aiofiles>=23.2.1 \
    python-multipart>=0.0.6 \
    slack-sdk>=3.26.2

deactivate

echo -e "${GREEN}Python environment ready!${NC}"

# ── 6. Tauri + React Frontend ──────────────────────────────────
echo -e "\n${YELLOW}[6/8] Setting up frontend (Tauri v2 + React)...${NC}"

# Tauri system dependencies (WebKitGTK, etc.)
sudo pacman -S --noconfirm \
    webkit2gtk-4.1 \
    libappindicator-gtk3 \
    librsvg \
    patchelf \
    openssl

# Install Rust if not present
if ! command -v rustc &> /dev/null; then
    echo "Installing Rust via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    echo -e "${GREEN}Rust already installed: $(rustc --version)${NC}"
fi

# Install pnpm if not present
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
else
    echo -e "${GREEN}pnpm already installed: $(pnpm --version)${NC}"
fi

cd frontend
pnpm install
cd ..

# ── 7. Redis Setup ────────────────────────────────────────────
echo -e "\n${YELLOW}[7/8] Configuring Redis...${NC}"
sudo systemctl enable redis
sudo systemctl start redis
echo -e "${GREEN}Redis running on localhost:6379${NC}"

# ── 8. Permissions for Audio ─────────────────────────────────
echo -e "\n${YELLOW}[8/8] Setting audio permissions...${NC}"
sudo usermod -a -G audio "$USER"
sudo usermod -a -G pulse "$USER" 2>/dev/null || true
sudo usermod -a -G pulse-access "$USER" 2>/dev/null || true

# ── Done ──────────────────────────────────────────────────────
echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}  MAESTRO Setup Complete!                   ${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. ${YELLOW}bash scripts/setup_audio.sh${NC}     — Configure virtual audio sink"
echo -e "  2. ${YELLOW}python scripts/download_models.py${NC} — Download AI models (~2GB)"
echo -e "  3. ${YELLOW}cp .env.example .env${NC}             — Add your Gemini API key"
echo -e "  4. ${YELLOW}cd backend && source venv/bin/activate && uvicorn main:app --reload${NC}"
echo -e "  5. ${YELLOW}cd frontend && pnpm tauri dev${NC}    — Launch overlay"
echo ""
echo -e "${RED}IMPORTANT: Log out and back in for audio group changes to take effect!${NC}"
