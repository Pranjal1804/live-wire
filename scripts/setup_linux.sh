#!/bin/bash
# ────────────────────────────────────────────────────────────
# MAESTRO  --  System Setup for Linux
# Run: bash scripts/setup_linux.sh
# ────────────────────────────────────────────────────────────

set -e

# ── Colors (muted, readable) ────────────────────────────────
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
WHITE='\033[97m'
GREEN='\033[38;5;108m'   # sage
RED='\033[38;5;167m'     # muted coral
AMBER='\033[38;5;179m'   # warm amber
BLUE='\033[38;5;110m'    # steel blue
GRAY='\033[38;5;243m'    # neutral gray

# ── Drawing helpers ──────────────────────────────────────────
hr()      { printf "${GRAY}  %s${RESET}\n" "$(printf '%.0s─' {1..52})"; }
header()  { printf "\n${WHITE}${BOLD}  %s${RESET}\n" "$1"; hr; }
step()    { printf "${BLUE}  [%s/%s]${RESET} ${WHITE}%s${RESET}" "$1" "$2" "$3"; }
ok()      { printf " ${GREEN}done${RESET}\n"; }
skip()    { printf " ${AMBER}skipped${RESET}\n"; }
fail()    { printf " ${RED}failed${RESET}\n"; }
info()    { printf "${GRAY}       %s${RESET}\n" "$1"; }
note()    { printf "${AMBER}  -->  %s${RESET}\n" "$1"; }

TOTAL_STEPS=7

# ── Banner ───────────────────────────────────────────────────
clear 2>/dev/null || true
printf "\n"
printf "${GRAY}  ┌──────────────────────────────────────────────────┐${RESET}\n"
printf "${GRAY}  │${RESET}  ${WHITE}${BOLD}MAESTRO${RESET}  ${DIM}System Setup${RESET}                            ${GRAY}│${RESET}\n"
printf "${GRAY}  │${RESET}  ${DIM}Real-time AI sales coaching platform${RESET}              ${GRAY}│${RESET}\n"
printf "${GRAY}  └──────────────────────────────────────────────────┘${RESET}\n"
printf "\n"

# ── Detect package manager ───────────────────────────────────
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

distro_label() {
    case "$1" in
        pacman) echo "Arch / EndeavourOS / Manjaro" ;;
        apt)    echo "Debian / Ubuntu / Mint" ;;
        dnf)    echo "Fedora / RHEL / Rocky" ;;
        zypper) echo "openSUSE" ;;
        emerge) echo "Gentoo" ;;
        xbps)   echo "Void Linux" ;;
        nix)    echo "NixOS" ;;
        *)      echo "Unknown" ;;
    esac
}

PKG_MGR=$(detect_pkg_manager)
DISTRO=$(distro_label "$PKG_MGR")

printf "${GRAY}  System${RESET}     $(uname -sr)\n"
printf "${GRAY}  Package${RESET}    ${WHITE}${PKG_MGR}${RESET}  ${DIM}(${DISTRO})${RESET}\n"
printf "\n"

if [ "$PKG_MGR" = "unknown" ]; then
    printf "${RED}  Could not detect a supported package manager.${RESET}\n"
    printf "${DIM}  Supported: pacman, apt, dnf, zypper${RESET}\n\n"
    exit 1
fi

# ── Package installer ────────────────────────────────────────
install_packages() {
    case "$PKG_MGR" in
        pacman)
            sudo pacman -Syu --noconfirm > /dev/null 2>&1
            sudo pacman -S --needed --noconfirm "$@" > /dev/null 2>&1
            ;;
        apt)
            sudo apt-get update -qq > /dev/null 2>&1
            sudo apt-get install -y -qq "$@" > /dev/null 2>&1
            ;;
        dnf)
            sudo dnf install -y -q "$@" > /dev/null 2>&1
            ;;
        zypper)
            sudo zypper install -y "$@" > /dev/null 2>&1
            ;;
        *)
            printf "${RED}Unsupported: ${PKG_MGR}${RESET}\n"
            printf "Install manually: $@\n"
            return 1
            ;;
    esac
}

# ═════════════════════════════════════════════════════════════
header "Installing"

# ── 1. Audio System ──────────────────────────────────────────
step 1 $TOTAL_STEPS "Audio system"

if systemctl --user is-active --quiet pipewire 2>/dev/null; then
    info "PipeWire active"
    case "$PKG_MGR" in
        pacman) install_packages pipewire-pulse pipewire-alsa pavucontrol ;;
        apt)    install_packages pipewire-pulse pavucontrol ;;
        dnf)    install_packages pipewire-pulseaudio pavucontrol ;;
        *)      true ;;
    esac
    ok
elif systemctl --user is-active --quiet pulseaudio 2>/dev/null; then
    info "PulseAudio active"
    case "$PKG_MGR" in
        pacman) install_packages pulseaudio pulseaudio-alsa pavucontrol ;;
        apt)    install_packages pulseaudio pavucontrol ;;
        dnf)    install_packages pulseaudio pavucontrol ;;
        *)      true ;;
    esac
    ok
else
    info "No audio daemon detected, installing PipeWire"
    case "$PKG_MGR" in
        pacman) install_packages pipewire pipewire-pulse pipewire-alsa pavucontrol ;;
        apt)    install_packages pipewire pipewire-pulse pavucontrol ;;
        dnf)    install_packages pipewire pipewire-pulseaudio pavucontrol ;;
        *)      true ;;
    esac
    ok
fi

# ── 2. Core System Dependencies ─────────────────────────────
step 2 $TOTAL_STEPS "System dependencies"
info "python, nodejs, npm, git, ffmpeg, redis ..."

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
        info "Install manually: python3, pip, nodejs, npm, git, ffmpeg, redis"
        ;;
esac
ok

# ── 3. Tauri System Dependencies ────────────────────────────
step 3 $TOTAL_STEPS "Tauri dependencies"

case "$PKG_MGR" in
    pacman)
        install_packages webkit2gtk-4.1 libappindicator-gtk3 librsvg patchelf openssl
        ok
        ;;
    apt|dnf)
        info "Included in step 2"
        skip
        ;;
    *)
        info "Install manually: webkit2gtk-4.1, libappindicator, librsvg"
        skip
        ;;
esac

# ── 4. Rust ──────────────────────────────────────────────────
step 4 $TOTAL_STEPS "Rust toolchain"

if command -v rustc &> /dev/null; then
    info "$(rustc --version)"
    skip
else
    info "Installing via rustup"
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y > /dev/null 2>&1
    source "$HOME/.cargo/env"
    ok
fi

# ── 5. pnpm ─────────────────────────────────────────────────
step 5 $TOTAL_STEPS "pnpm"

if command -v pnpm &> /dev/null; then
    info "v$(pnpm --version)"
    skip
else
    info "Installing via npm"
    npm install -g pnpm > /dev/null 2>&1
    ok
fi

# ── 6. Python Backend ───────────────────────────────────────
step 6 $TOTAL_STEPS "Python environment"
cd "$(dirname "$0")/.."

info "Creating venv + installing requirements"
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install --upgrade pip -q > /dev/null 2>&1
pip install -r backend/requirements.txt -q > /dev/null 2>&1
deactivate
ok

# ── 7. Frontend Dependencies ────────────────────────────────
step 7 $TOTAL_STEPS "Frontend packages"

info "pnpm install"
cd frontend
pnpm install --silent > /dev/null 2>&1
cd ..
ok

# ═════════════════════════════════════════════════════════════
header "Post-install"

# ── Audio Permissions ────────────────────────────────────────
printf "${GRAY}  Audio groups${RESET}"
sudo usermod -a -G audio "$USER" 2>/dev/null || true
sudo usermod -a -G pulse "$USER" 2>/dev/null || true
sudo usermod -a -G pulse-access "$USER" 2>/dev/null || true
printf " ${GREEN}done${RESET}\n"

# ── Redis ────────────────────────────────────────────────────
printf "${GRAY}  Redis service${RESET}"
sudo systemctl enable redis 2>/dev/null || sudo systemctl enable redis-server 2>/dev/null || true
sudo systemctl start redis 2>/dev/null || sudo systemctl start redis-server 2>/dev/null || true
printf " ${GREEN}done${RESET}\n"

# ═════════════════════════════════════════════════════════════
printf "\n"
printf "${GRAY}  ┌──────────────────────────────────────────────────┐${RESET}\n"
printf "${GRAY}  │${RESET}  ${GREEN}${BOLD}Setup complete${RESET}                                    ${GRAY}│${RESET}\n"
printf "${GRAY}  └──────────────────────────────────────────────────┘${RESET}\n"
printf "\n"

header "Next steps"
printf "${WHITE}  1.${RESET}  ${DIM}bash${RESET} scripts/setup_audio.sh\n"
info "Configure audio loopback"
printf "${WHITE}  2.${RESET}  ${DIM}python3${RESET} scripts/download_models.py\n"
info "Download AI models (~400MB)"
printf "${WHITE}  3.${RESET}  ${DIM}cp${RESET} .env.example .env\n"
info "Add your Gemini API key"
printf "${WHITE}  4.${RESET}  ${DIM}cd backend && source venv/bin/activate &&${RESET}\n"
printf "      ${DIM}uvicorn main:app --reload --port 8000${RESET}\n"
info "Start the backend"
printf "${WHITE}  5.${RESET}  ${DIM}cd frontend && pnpm tauri dev${RESET}\n"
info "Launch the overlay"
printf "\n"
note "Log out and back in for audio group changes to take effect."
printf "\n"
