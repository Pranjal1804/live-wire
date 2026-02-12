#!/bin/bash
# ============================================================
# MAESTRO — Audio Virtual Sink Setup (PulseAudio/PipeWire)
# This replaces VB-Cable for Linux!
# Run: bash scripts/setup_audio.sh
# ============================================================

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  MAESTRO — Audio Sink Setup         ${NC}"
echo -e "${GREEN}=====================================${NC}"

# ── Detect audio system ───────────────────────────────────────
if systemctl --user is-active --quiet pipewire; then
    AUDIO_SYSTEM="pipewire"
    echo -e "${GREEN}Detected: PipeWire (EndeavourOS default)${NC}"
else
    AUDIO_SYSTEM="pulseaudio"
    echo -e "${YELLOW}Detected: PulseAudio${NC}"
fi

# ── Create Virtual Null Sink ──────────────────────────────────
echo -e "\n${YELLOW}Creating virtual audio loopback sink...${NC}"

# Load null sink module (this is the "VB-Cable" equivalent on Linux)
pactl load-module module-null-sink \
    sink_name=maestro_capture \
    sink_properties=device.description="Maestro_Virtual_Capture" 2>/dev/null || \
    echo "Sink may already exist, continuing..."

# Load loopback so we can still hear audio while capturing
pactl load-module module-loopback \
    source=maestro_capture.monitor \
    sink=$(pactl get-default-sink) 2>/dev/null || true

echo -e "${GREEN}Virtual sink 'maestro_capture' created!${NC}"

# ── Make it persistent across reboots ────────────────────────
echo -e "\n${YELLOW}Making audio config persistent...${NC}"
PULSE_CONF="$HOME/.config/pulse/default.pa"
mkdir -p "$HOME/.config/pulse"

# Check if already added
if ! grep -q "maestro_capture" "$PULSE_CONF" 2>/dev/null; then
    cat >> "$PULSE_CONF" << 'EOF'

# ── MAESTRO Virtual Capture Sink ──────────────────────────────
.nofail
load-module module-null-sink sink_name=maestro_capture sink_properties=device.description="Maestro_Virtual_Capture"
load-module module-loopback source=maestro_capture.monitor
.fail
EOF
    echo -e "${GREEN}Added to PulseAudio config${NC}"
fi

# ── Show available sources ────────────────────────────────────
echo -e "\n${CYAN}Available audio sources (use in Python capture):${NC}"
pactl list sources short

echo ""
echo -e "${YELLOW}SOURCE TO USE IN maestro: 'maestro_capture.monitor'${NC}"

# ── Test source exists ────────────────────────────────────────
if pactl list sources short | grep -q "maestro_capture"; then
    echo -e "${GREEN}✓ Virtual sink is ready!${NC}"
else
    echo -e "${RED}Virtual sink not found. Try rebooting and running again.${NC}"
fi

# ── Instructions ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  HOW TO ROUTE YOUR MEETING AUDIO          ${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "OPTION A — GUI (Recommended for first-time):"
echo -e "  1. Open ${YELLOW}pavucontrol${NC}"
echo -e "  2. Go to 'Playback' tab"
echo -e "  3. Find Zoom/Teams/Meet → Change output to 'Maestro_Virtual_Capture'"
echo -e "  4. You'll still hear audio via the loopback module"
echo ""
echo -e "OPTION B — Command line:"
echo -e "  ${CYAN}# Find your meeting app's sink input number:${NC}"
echo -e "  pactl list sink-inputs short"
echo -e "  ${CYAN}# Move it to maestro sink (replace N with the number):${NC}"
echo -e "  pactl move-sink-input N maestro_capture"
echo ""
echo -e "OPTION C — Capture system monitor (easiest, no routing needed):"
echo -e "  Use source: ${YELLOW}\$(pactl get-default-source)${NC} with '.monitor' suffix"
echo -e "  This captures ALL system audio (meeting + your mic)"
echo ""
echo -e "${YELLOW}Run test: python scripts/test_audio_capture.py${NC}"
