#!/usr/bin/env python3
"""
MAESTRO -- AI Model Downloader
Downloads and caches all required AI models.
Run: python scripts/download_models.py
"""

import os
import sys

# -- Colors (muted, matching setup_linux.sh) -------------------------
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
WHITE  = "\033[97m"
GREEN  = "\033[38;5;108m"
RED    = "\033[38;5;167m"
AMBER  = "\033[38;5;179m"
BLUE   = "\033[38;5;110m"
GRAY   = "\033[38;5;243m"

HR = f"{GRAY}  {'─' * 52}{RESET}"

TOTAL_STEPS = 4


def banner():
    print()
    print(f"{GRAY}  ┌──────────────────────────────────────────────────┐{RESET}")
    print(f"{GRAY}  │{RESET}  {WHITE}{BOLD}MAESTRO{RESET}  {DIM}Model Download{RESET}                           {GRAY}│{RESET}")
    print(f"{GRAY}  │{RESET}  {DIM}Download and cache required AI models (~400MB){RESET}    {GRAY}│{RESET}")
    print(f"{GRAY}  └──────────────────────────────────────────────────┘{RESET}")
    print()
    info("This only runs once. Models are cached locally.")
    print()


def header(title):
    print(f"\n{WHITE}{BOLD}  {title}{RESET}")
    print(HR)


def step(n, total, msg):
    sys.stdout.write(f"{BLUE}  [{n}/{total}]{RESET} {WHITE}{msg}{RESET}")
    sys.stdout.flush()


def ok(detail=""):
    suffix = f"  {DIM}{detail}{RESET}" if detail else ""
    print(f" {GREEN}done{RESET}{suffix}")


def skip(detail=""):
    suffix = f"  {DIM}{detail}{RESET}" if detail else ""
    print(f" {AMBER}skipped{RESET}{suffix}")


def fail(detail=""):
    suffix = f"  {DIM}{detail}{RESET}" if detail else ""
    print(f" {RED}failed{RESET}{suffix}")


def info(msg):
    print(f"{GRAY}       {msg}{RESET}")


def note(msg):
    print(f"{AMBER}  -->  {msg}{RESET}")


# --------------------------------------------------------------------

def download_whisper():
    step(1, TOTAL_STEPS, "Faster-Whisper")
    info("base.en (~145MB) + tiny.en -- real-time transcription")
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        model_tiny = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        ok("base.en + tiny.en")
        return True
    except Exception as e:
        fail(str(e))
        return False


def download_emotion_model():
    step(2, TOTAL_STEPS, "Emotion detection")
    info("wav2vec2-base-superb-er (~80MB)")
    try:
        from transformers import pipeline

        emotion_pipeline = pipeline(
            "audio-classification",
            model="superb/wav2vec2-base-superb-er",
            device=-1,
        )
        ok()
        return True
    except Exception as e:
        skip(f"fallback to text sentiment -- {e}")
        return False


def download_vad_model():
    step(3, TOTAL_STEPS, "Silero VAD")
    info("Voice activity detection (~2MB)")
    try:
        import torch

        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )
        os.makedirs("backend/models/cached", exist_ok=True)
        torch.save(model.state_dict(), "backend/models/cached/silero_vad.pt")
        ok()
        return True
    except Exception as e:
        skip(f"fallback to energy-based VAD -- {e}")
        return False


def setup_embedding_model():
    step(4, TOTAL_STEPS, "Embedding model")
    info("all-MiniLM-L6-v2 (~90MB) -- knowledge base RAG")
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        ok()
        return True
    except Exception as e:
        fail(str(e))
        return False


def create_env_file():
    """Create .env.example if it does not exist."""
    env_path = ".env.example"
    if os.path.exists(env_path):
        return
    with open(env_path, "w") as f:
        f.write("""# MAESTRO Environment Configuration
# Copy this to .env and fill in your values

# -- Required ---------------------------------------------------------
# Get free key at: https://aistudio.google.com/
GEMINI_API_KEY=your_gemini_api_key_here

# -- Optional ---------------------------------------------------------
# Redis (defaults to local)
REDIS_URL=redis://localhost:6379

# Slack escalation bot token (optional)
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_CHANNEL=#sales-escalations

# Audio device (auto-detected if empty)
AUDIO_DEVICE_NAME=maestro_capture.monitor

# Model settings
WHISPER_MODEL=base.en       # tiny.en / base.en / small.en
EMOTION_MODEL=superb/wav2vec2-base-superb-er
CHUNK_DURATION_MS=2000      # Audio chunk size in ms
VAD_THRESHOLD=0.5           # Voice detection threshold (0-1)

# Agent settings
GEMINI_MODEL=gemini-1.5-flash
MAX_TOKENS=1024
TEMPERATURE=0.3
""")
    info("Created .env.example")


# --------------------------------------------------------------------

def main():
    banner()
    create_env_file()

    header("Downloading")

    results = {}
    results["whisper"]    = download_whisper()
    results["emotion"]    = download_emotion_model()
    results["vad"]        = download_vad_model()
    results["embeddings"] = setup_embedding_model()

    # Summary
    header("Summary")
    for name, success in results.items():
        status = f"{GREEN}ok{RESET}" if success else f"{AMBER}fallback{RESET}"
        print(f"  {GRAY}  {status}  {WHITE}{name}{RESET}")

    # Done
    print()
    print(f"{GRAY}  ┌──────────────────────────────────────────────────┐{RESET}")
    print(f"{GRAY}  │{RESET}  {GREEN}{BOLD}Download complete{RESET}                                 {GRAY}│{RESET}")
    print(f"{GRAY}  └──────────────────────────────────────────────────┘{RESET}")
    print()
    header("Next")
    info("cp .env.example .env")
    info("cd backend && source venv/bin/activate &&")
    info("uvicorn main:app --reload --port 8000")
    print()


if __name__ == "__main__":
    main()
