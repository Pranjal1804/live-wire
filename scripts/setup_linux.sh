#!/bin/bash
# ============================================================
# MAESTRO -- Full System Setup for Linux (any distribution)
# Run: bash scripts/setup_linux.sh
# ============================================================

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  MAESTRO Setup -- Linux             ${NC}"
echo -e "${GREEN}=====================================${NC}"

# ── Detect package manager ──────────────────────────────────
detect_pkg_manager() {
    if command -v pacman &> /dev/null; then
        echo "pacman"
    elif command -v apt-get &> /dev/null; then
        echo "apt"
    elif command -v dnf &> /dev/null; then
        echo "dnf"
    elif command -v zypper &> /dev/null; then
        echo "zypper"
    elif command -v emerge &> /dev/null; then
        echo "emerge"
    elif command -v xbps-install &> /dev/null; then
        echo "xbps"
    elif command -v nix-env &> /dev/null; then
        echo "nix"
    else
        echo "unknown"
    fi
}

PKG_MGR=$(detect_pkg_manager)
echo -e "Detected package manager: ${YELLOW}${PKG_MGR}${NC}"

install_packages() {
    case "$PKG_MGR" in
        pacman)
            sudo pacman -Syu --noconfirm
            sudo pacman -S --needed --noconfirm "$@"
            ;;
        apt)
            sudo apt-get update
            sudo apt-get install -y "$@"
            ;;
        dnf)
            sudo dnf install -y "$@"
            ;;
        zypper)
            sudo zypper install -y "$@"
            ;;
        *)
            echo -e "${RED}Unsupported package manager: ${PKG_MGR}${NC}"
            echo "Please install these packages manually: $@"
            return 1
            ;;
    esac
}

# ── 1. Audio System ─────────────────────────────────────────
echo -e "\n${YELLOW}[1/7] Checking audio system...${NC}"
if systemctl --user is-active --quiet pipewire 2>/dev/null; then
    echo -e "${GREEN}PipeWire is active${NC}"
    case "$PKG_MGR" in
        pacman) install_packages pipewire-pulse pipewire-alsa pavucontrol ;;
        apt)    install_packages pipewire-pulse pavucontrol ;;
        dnf)    install_packages pipewire-pulseaudio pavucontrol ;;
        *)      echo "Ensure PipeWire PulseAudio compatibility layer is installed" ;;
    esac
elif systemctl --user is-active --quiet pulseaudio 2>/dev/null; then
    echo -e "${GREEN}PulseAudio is active${NC}"
    case "$PKG_MGR" in
        pacman) install_packages pulseaudio pulseaudio-alsa pavucontrol ;;
        apt)    install_packages pulseaudio pavucontrol ;;
        dnf)    install_packages pulseaudio pavucontrol ;;
        *)      echo "Ensure PulseAudio is installed" ;;
    esac
else
    echo -e "${YELLOW}No audio daemon detected. Installing PipeWire...${NC}"
    case "$PKG_MGR" in
        pacman) install_packages pipewire pipewire-pulse pipewire-alsa pavucontrol ;;
        apt)    install_packages pipewire pipewire-pulse pavucontrol ;;
        dnf)    install_packages pipewire pipewire-pulseaudio pavucontrol ;;
        *)      echo "Please install PipeWire or PulseAudio manually" ;;
    esac
fi

# ── 2. Core System Dependencies ─────────────────────────────
echo -e "\n${YELLOW}[2/7] Installing system dependencies...${NC}"
case "$PKG_MGR" in
    pacman)
        install_packages \
            python python-pip python-virtualenv \
            nodejs npm git curl wget redis ffmpeg \
            portaudio alsa-lib base-devel cmake pkg-config
        ;;
    apt)
        install_packages \
            python3 python3-pip python3-venv \
            nodejs npm git curl wget redis-server ffmpeg \
            portaudio19-dev libasound2-dev build-essential cmake pkg-config \
            libssl-dev libwebkit2gtk-4.1-dev libappindicator3-dev \
            librsvg2-dev patchelf
        ;;
    dnf)
        install_packages \
            python3 python3-pip python3-virtualenv \
            nodejs npm git curl wget redis ffmpeg \
            portaudio-devel alsa-lib-devel cmake pkg-config gcc gcc-c++ \
            openssl-devel webkit2gtk4.1-devel libappindicator-gtk3-devel \
            librsvg2-devel patchelf
        ;;
    *)
        echo -e "${RED}Install these manually:${NC}"
        echo "  python3, pip, venv, nodejs, npm, git, ffmpeg, redis"
        echo "  portaudio, alsa-lib (dev headers), cmake, pkg-config"
        echo "  webkit2gtk-4.1 (dev), libappindicator (dev), openssl (dev)"
        ;;
esac

# ── 3. Tauri System Dependencies ────────────────────────────
echo -e "\n${YELLOW}[3/7] Checking Tauri system dependencies...${NC}"
case "$PKG_MGR" in
    pacman)
        install_packages webkit2gtk-4.1 libappindicator-gtk3 librsvg patchelf openssl
        ;;
    apt)
        # Already installed above with the apt block
        echo -e "${GREEN}Tauri deps included in step 2${NC}"
        ;;
    dnf)
        echo -e "${GREEN}Tauri deps included in step 2${NC}"
        ;;
    *)
        echo "Ensure webkit2gtk-4.1, libappindicator, librsvg are installed"
        ;;
esac

# ── 4. Rust ─────────────────────────────────────────────────
echo -e "\n${YELLOW}[4/7] Checking Rust...${NC}"
if ! command -v rustc &> /dev/null; then
    echo "Installing Rust via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    echo -e "${GREEN}Rust already installed: $(rustc --version)${NC}"
fi

# ── 5. pnpm ─────────────────────────────────────────────────
echo -e "\n${YELLOW}[5/7] Checking pnpm...${NC}"
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
else
    echo -e "${GREEN}pnpm already installed: $(pnpm --version)${NC}"
fi

# ── 6. Python Backend ───────────────────────────────────────
echo -e "\n${YELLOW}[6/7] Setting up Python virtual environment...${NC}"
cd "$(dirname "$0")/.."

python3 -m venv backend/venv
source backend/venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
deactivate

echo -e "${GREEN}Python environment ready${NC}"

# ── 7. Frontend Dependencies ────────────────────────────────
echo -e "\n${YELLOW}[7/7] Installing frontend dependencies...${NC}"
cd frontend
pnpm install
cd ..

# ── Audio Permissions ───────────────────────────────────────
echo -e "\nSetting audio permissions..."
sudo usermod -a -G audio "$USER" 2>/dev/null || true
sudo usermod -a -G pulse "$USER" 2>/dev/null || true
sudo usermod -a -G pulse-access "$USER" 2>/dev/null || true

# ── Redis ───────────────────────────────────────────────────
echo "Starting Redis..."
sudo systemctl enable redis 2>/dev/null || sudo systemctl enable redis-server 2>/dev/null || true
sudo systemctl start redis 2>/dev/null || sudo systemctl start redis-server 2>/dev/null || true

# ── Done ────────────────────────────────────────────────────
echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}  MAESTRO Setup Complete                    ${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. ${YELLOW}bash scripts/setup_audio.sh${NC}              -- Configure audio loopback"
echo -e "  2. ${YELLOW}python3 scripts/download_models.py${NC}       -- Download AI models"
echo -e "  3. ${YELLOW}cp .env.example .env${NC}                     -- Add your Gemini API key"
echo -e "  4. ${YELLOW}cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000${NC}"
echo -e "  5. ${YELLOW}cd frontend && pnpm tauri dev${NC}            -- Launch overlay"
echo ""
echo -e "${RED}Log out and back in for audio group changes to take effect.${NC}"
