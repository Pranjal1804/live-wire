#!/bin/bash
# ────────────────────────────────────────────────────────────
# MAESTRO  --  Audio Virtual Sink Setup (PulseAudio/PipeWire)
# Run: bash scripts/setup_audio.sh
# ────────────────────────────────────────────────────────────

set -e

# ── Colors (muted, matching setup_linux.sh) ─────────────────
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
WHITE='\033[97m'
GREEN='\033[38;5;108m'
RED='\033[38;5;167m'
AMBER='\033[38;5;179m'
BLUE='\033[38;5;110m'
GRAY='\033[38;5;243m'

hr()     { printf "${GRAY}  %s${RESET}\n" "$(printf '%.0s─' {1..52})"; }
header() { printf "\n${WHITE}${BOLD}  %s${RESET}\n" "$1"; hr; }
info()   { printf "${GRAY}       %s${RESET}\n" "$1"; }
note()   { printf "${AMBER}  -->  %s${RESET}\n" "$1"; }

# ── Banner ───────────────────────────────────────────────────
printf "\n"
printf "${GRAY}  ┌──────────────────────────────────────────────────┐${RESET}\n"
printf "${GRAY}  │${RESET}  ${WHITE}${BOLD}MAESTRO${RESET}  ${DIM}Audio Sink Setup${RESET}                         ${GRAY}│${RESET}\n"
printf "${GRAY}  │${RESET}  ${DIM}Virtual audio routing for meeting capture${RESET}         ${GRAY}│${RESET}\n"
printf "${GRAY}  └──────────────────────────────────────────────────┘${RESET}\n"
printf "\n"

# ── Detect audio system ──────────────────────────────────────
printf "${BLUE}  [1/4]${RESET} ${WHITE}Detect audio system${RESET}"

if systemctl --user is-active --quiet pipewire 2>/dev/null; then
    AUDIO_SYSTEM="pipewire"
    printf " ${GREEN}PipeWire${RESET}\n"
elif systemctl --user is-active --quiet pulseaudio 2>/dev/null; then
    AUDIO_SYSTEM="pulseaudio"
    printf " ${AMBER}PulseAudio${RESET}\n"
else
    AUDIO_SYSTEM="unknown"
    printf " ${RED}not found${RESET}\n"
    note "Neither PipeWire nor PulseAudio detected."
    note "Install PipeWire or PulseAudio and try again."
    exit 1
fi

# ── Create Virtual Null Sink ─────────────────────────────────
printf "${BLUE}  [2/4]${RESET} ${WHITE}Create virtual sink${RESET}"

pactl load-module module-null-sink \
    sink_name=maestro_capture \
    sink_properties=device.description="Maestro_Virtual_Capture" > /dev/null 2>&1 || true

pactl load-module module-loopback \
    source=maestro_capture.monitor \
    sink="$(pactl get-default-sink)" > /dev/null 2>&1 || true

printf " ${GREEN}done${RESET}\n"
info "Sink: maestro_capture"
info "Loopback: routed to default output"

# ── Make persistent ──────────────────────────────────────────
printf "${BLUE}  [3/4]${RESET} ${WHITE}Persist across reboots${RESET}"

PULSE_CONF="$HOME/.config/pulse/default.pa"
mkdir -p "$HOME/.config/pulse"

if ! grep -q "maestro_capture" "$PULSE_CONF" 2>/dev/null; then
    cat >> "$PULSE_CONF" << 'EOF'

# MAESTRO Virtual Capture Sink
.nofail
load-module module-null-sink sink_name=maestro_capture sink_properties=device.description="Maestro_Virtual_Capture"
load-module module-loopback source=maestro_capture.monitor
.fail
EOF
    printf " ${GREEN}done${RESET}\n"
else
    printf " ${AMBER}already configured${RESET}\n"
fi

# ── Verify ───────────────────────────────────────────────────
printf "${BLUE}  [4/4]${RESET} ${WHITE}Verify sink${RESET}"

if pactl list sources short 2>/dev/null | grep -q "maestro_capture"; then
    printf " ${GREEN}ready${RESET}\n"
else
    printf " ${RED}not found${RESET}\n"
    note "Try rebooting and running this script again."
fi

# ── Available sources ────────────────────────────────────────
header "Audio sources"
pactl list sources short 2>/dev/null | while read -r line; do
    printf "${GRAY}       %s${RESET}\n" "$line"
done

printf "\n"
note "Use source: maestro_capture.monitor"

# ── Routing instructions ────────────────────────────────────
header "How to route meeting audio"

printf "${WHITE}  A.${RESET}  ${DIM}GUI (recommended)${RESET}\n"
info "1. Open pavucontrol"
info "2. Go to Playback tab"
info "3. Set your meeting app output to Maestro_Virtual_Capture"
info "4. Audio passes through via loopback"

printf "\n"
printf "${WHITE}  B.${RESET}  ${DIM}Command line${RESET}\n"
info "pactl list sink-inputs short"
info "pactl move-sink-input <N> maestro_capture"

printf "\n"
printf "${WHITE}  C.${RESET}  ${DIM}System monitor (captures all audio)${RESET}\n"
info "Use source: \$(pactl get-default-source).monitor"

printf "\n"
note "Test it: python3 scripts/test_audio_capture.py"
printf "\n"
