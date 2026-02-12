#!/usr/bin/env python3
"""
MAESTRO — AI Model Downloader
Downloads and caches all required AI models.
Run: python scripts/download_models.py
"""

import os
import sys
import time

def download_whisper():
    print("\n[1/3] Downloading Faster-Whisper (base.en model ~145MB)...")
    print("      This is the real-time transcription engine.")
    try:
        from faster_whisper import WhisperModel
        # This triggers automatic download
        print("      Downloading... (may take a minute)")
        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        print("      ✅ Whisper base.en ready!")
        
        # Also download tiny for ultra-fast mode
        print("      Also downloading tiny model for <200ms mode...")
        model_tiny = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        print("      ✅ Whisper tiny.en ready!")
        return True
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return False

def download_emotion_model():
    print("\n[2/3] Downloading Emotion Detection model...")
    print("      Using SpeechBrain emotion model (~80MB)")
    try:
        from transformers import pipeline
        # Using a lighter emotion model for real-time use
        print("      Downloading superb/wav2vec2-base-superb-er...")
        emotion_pipeline = pipeline(
            "audio-classification",
            model="superb/wav2vec2-base-superb-er",
            device=-1  # CPU
        )
        print("      ✅ Emotion model ready!")
        return True
    except Exception as e:
        print(f"      ⚠️  Could not download emotion model: {e}")
        print("      Using fallback: sentiment from transcript text")
        return False

def download_vad_model():
    print("\n[3/3] Downloading Silero VAD (Voice Activity Detection ~2MB)...")
    try:
        import torch
        print("      Downloading silero-vad...")
        model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True
        )
        # Save locally
        os.makedirs("backend/models/cached", exist_ok=True)
        torch.save(model.state_dict(), "backend/models/cached/silero_vad.pt")
        print("      ✅ VAD model ready!")
        return True
    except Exception as e:
        print(f"      ⚠️  VAD download error: {e}")
        print("      Falling back to energy-based VAD")
        return False

def setup_embedding_model():
    print("\n[+] Setting up embedding model for knowledge base RAG...")
    try:
        from sentence_transformers import SentenceTransformer
        print("     Downloading all-MiniLM-L6-v2 (~90MB)...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("     ✅ Embedding model ready!")
        return True
    except Exception as e:
        print(f"     ⚠️  Embedding model error: {e}")
        return False

def create_env_file():
    """Create .env.example if not exists."""
    env_path = ".env.example"
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write("""# MAESTRO Environment Configuration
# Copy this to .env and fill in your values

# ── Required ──────────────────────────────────────────────────
# Get free key at: https://aistudio.google.com/
GEMINI_API_KEY=your_gemini_api_key_here

# ── Optional ──────────────────────────────────────────────────
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
        print("✅ Created .env.example")

if __name__ == "__main__":
    print("=" * 55)
    print("  MAESTRO — Model Download & Setup")
    print("=" * 55)
    print("  Estimated download: ~400MB total")
    print("  This only runs once. Models are cached.")
    
    create_env_file()
    
    results = {
        "whisper": download_whisper(),
        "emotion": download_emotion_model(),
        "vad": download_vad_model(),
        "embeddings": setup_embedding_model(),
    }
    
    print("\n" + "=" * 55)
    print("  Download Summary:")
    for name, success in results.items():
        status = "✅" if success else "⚠️ "
        print(f"  {status} {name}")
    
    print("\n  Next: cp .env.example .env")
    print("  Then: cd backend && uvicorn main:app --reload")
    print("=" * 55)
