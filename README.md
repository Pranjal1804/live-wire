#  MAESTRO — Agentic Sales Co-Pilot
### Complete Build Guide for EndeavourOS

---

##  FEASIBILITY NOTES (READ BEFORE STARTING)

###  What Works Great on Linux
- PulseAudio/PipeWire monitor sources (native VB-Cable replacement)
- Faster-Whisper transcription (excellent on CPU)
- Emotion detection from audio
- Electron transparent overlay (works on X11; Wayland needs `--ozone-platform=x11`)
- Gemini API (free tier: 15 requests/min)

### Real-World Caveats
| Feature | Reality |
|---------|---------|
| Transcription latency | 800ms–2s CPU, ~200ms with GPU |
| "Capturing actual words" | Works BUT Zoom/Teams compress audio. Use monitor source for best quality |
| Emotion accuracy | ~70% on clean audio, ~50% on compressed meeting audio |
| Wayland overlay | Requires `--ozone-platform=x11` flag or use X11 session |

### The Word Capture Problem (Your Main Concern)
The real issue isn't VB-Cable — it's **audio quality from meetings**.

**Why meeting audio is hard:**
1. Zoom/Teams use Opus codec @ 20kHz (slightly degrades Whisper)
2. Background noise + multiple speakers confuse VAD
3. Echo cancellation mutates audio waveforms

**Our solutions in this code:**
- `initial_prompt` in Whisper seeds domain vocabulary (huge accuracy boost)
- 300ms chunk overlap prevents words being cut at boundaries
- Built-in Whisper VAD + Silero VAD double-filters silence
- `condition_on_previous_text=True` maintains context between chunks

---

## STEP-BY-STEP BUILD GUIDE

---

### STEP 0: Prerequisites Check

```bash
# Check your OS
uname -a
# Should show: EndeavourOS / Arch Linux

# Check audio system
systemctl --user status pipewire
# EndeavourOS uses PipeWire by default

# Check Python version (need 3.10+)
python --version

# Check Node version (need 18+)  
node --version
```

---

### STEP 1: Clone / Set Up Project

```bash
# If you downloaded the zip:
cd ~/
mkdir maestro && cd maestro
# (copy all the project files here)

# OR if using git:
git init
# then copy files in
```

---

### STEP 2: Run System Setup

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run full system setup (installs all system packages)
bash scripts/setup_endeavouros.sh
```

This installs: Python, Node.js, Redis, ffmpeg, portaudio, pipewire-pulse, yay

** LOG OUT AND BACK IN after this step** (audio group permissions)

---

### STEP 3: Set Up Virtual Audio Sink

```bash
# Creates the "VB-Cable equivalent" on Linux
bash scripts/setup_audio.sh
```

Then open pavucontrol:
```bash
pavucontrol &
```

In pavucontrol:
1. **Playback tab** → Find Zoom/Teams/Meet
2. Click the output device dropdown → select **"Maestro_Virtual_Capture"**
3. You'll still hear audio via the loopback module

---

### STEP 4: Configure Environment

```bash
# Create your .env file
cp .env.example .env

# Edit it
nano .env
```

Fill in:
```
GEMINI_API_KEY=your_key_here  ← Get free at https://aistudio.google.com/apikey
```

---

### STEP 5: Set Up Python Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Go back to project root
cd ..
```

---

### STEP 6: Download AI Models (~400MB, one time)

```bash
# Make sure venv is active
source backend/venv/bin/activate

# Download all models
python scripts/download_models.py
```

This downloads:
- Whisper base.en + tiny.en (~300MB)
- wav2vec2 emotion model (~80MB)
- Silero VAD (~2MB)
- MiniLM embeddings (~90MB)

---

### STEP 7: Test Audio Capture

```bash
# IMPORTANT: Test before running the full system
python scripts/test_audio_capture.py
```

Start Zoom/Teams/Meet, join a test call, and check levels.
If you see audio levels → everything is working!

---

### STEP 8: Set Up Frontend

```bash
cd frontend

# Install Node packages
npm install

# Go back
cd ..
```

---

### STEP 9: Run MAESTRO

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

You should see:
```
 MAESTRO Agent starting up...
 Models warm and ready
INFO: Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 — Frontend Overlay:**
```bash
cd frontend
npm run electron
```

The HUD overlay will appear on the right side of your screen.

---

### STEP 10: Using MAESTRO

1. Start your Zoom/Teams/Meet call
2. Route audio through virtual sink (pavucontrol)
3. Click **▶ START MONITORING** in the HUD
4. Talk — transcripts and coaching will appear in real-time!

---

## TROUBLESHOOTING

### "No audio detected"
```bash
# Check PipeWire is running
systemctl --user status pipewire

# Restart PipeWire
systemctl --user restart pipewire

# List audio sources
pactl list sources short

# Test direct capture
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### "Overlay not transparent" (Wayland)
```bash
# Run Electron with X11 backend
cd frontend
ELECTRON_OZONE_PLATFORM_HINT=x11 npm run electron

# OR add to ~/.bashrc:
export ELECTRON_OZONE_PLATFORM_HINT=x11
```

### "Whisper too slow"
Change in `.env`:
```
WHISPER_MODEL=tiny.en    # 3x faster, slightly less accurate
```

### "Gemini API errors"
```bash
# Test your key
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"hello"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=YOUR_KEY"
```

### "Redis connection failed"
```bash
sudo systemctl start redis
redis-cli ping   # Should return: PONG
```

### "Emotion model download fails"
The system falls back to energy-based detection automatically.
Models download to `~/.cache/huggingface/hub/`

---

## ADD YOUR KNOWLEDGE BASE

```bash
# While backend is running, add documents via API:
curl -X POST http://localhost:8000/api/kb/add \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Return Policy",
    "content": "Your return policy text here...",
    "category": "policy"
  }'
```

---

## UPGRADE PATH

### GPU Acceleration (if you have NVIDIA)
```bash
# In model_manager.py, change:
device="cpu"   →   device="cuda"
compute_type="int8"   →   compute_type="float16"

# Install CUDA torch:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Better Transcription
- Switch to `small.en` model for noisy environments
- Add speaker diarization with `pyannote-audio`

---

## FILE REFERENCE

```
maestro/
├── scripts/setup_endeavouros.sh   ← Run first (system deps)
├── scripts/setup_audio.sh         ← Run second (virtual sink)
├── scripts/download_models.py     ← Run third (AI models)
├── scripts/test_audio_capture.py  ← Test audio works
├── backend/main.py                ← FastAPI server entry point
├── backend/agents/orchestrator.py ← The agent brain 
├── backend/audio/pipeline.py      ← Audio → AI pipeline
├── backend/models/model_manager.py← Whisper + emotion models
├── backend/tools/kb_search.py     ← RAG knowledge base
├── frontend/src/main.ts           ← Electron window
├── frontend/src/components/HUD.tsx← Main overlay UI 
├── frontend/src/stores/callStore.ts← App state
└── config/agent_config.yaml       ← Tune agent behavior
```
