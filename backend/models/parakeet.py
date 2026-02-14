"""
Parakeet-TDT transcription engine.

Uses nvidia/parakeet-tdt-0.6b-v3 via NVIDIA NeMo for local GPU inference
on an RTX 4060 (8GB VRAM). The model produces word-level timestamps and
native punctuation without a separate punctuation model.

If NeMo/Parakeet is not installed, falls back to Faster-Whisper so the
backend remains functional during development.
"""

import asyncio
import base64
import struct
import time
from typing import Optional

import numpy as np

# ── Model singleton ──

_model = None
_model_lock = asyncio.Lock()
_backend = None  # "parakeet" or "whisper"


async def get_model():
    """Load the transcription model once. Thread-safe via asyncio lock."""
    global _model, _backend
    async with _model_lock:
        if _model is not None:
            return _model

        loop = asyncio.get_event_loop()
        _model = await loop.run_in_executor(None, _load_model)
        return _model


def _load_model():
    """Try Parakeet first, fall back to Faster-Whisper."""
    global _backend

    # Attempt 1: NVIDIA Parakeet-TDT via NeMo
    try:
        import nemo.collections.asr as nemo_asr

        print("Loading nvidia/parakeet-tdt-0.6b-v3 on GPU...")
        model = nemo_asr.models.ASRModel.from_pretrained(
            model_name="nvidia/parakeet-tdt-0.6b-v3"
        )
        # Move to GPU -- RTX 4060 has 8GB VRAM, this model is ~600MB
        model = model.cuda()
        model.eval()
        _backend = "parakeet"
        print("Parakeet-TDT loaded on GPU")
        return model
    except ImportError:
        print("NeMo not installed, falling back to Faster-Whisper")
    except Exception as e:
        print(f"Parakeet load failed ({e}), falling back to Faster-Whisper")

    # Attempt 2: Faster-Whisper (existing setup)
    try:
        from faster_whisper import WhisperModel

        print("Loading Faster-Whisper base.en on CPU...")
        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        _backend = "whisper"
        print("Faster-Whisper ready (CPU fallback)")
        return model
    except Exception as e:
        print(f"Whisper fallback also failed: {e}")
        _backend = None
        return None


def decode_audio_chunk(audio_b64: str) -> np.ndarray:
    """
    Decode a base64-encoded 16-bit PCM (16 kHz mono) chunk into a float32
    numpy array normalized to [-1.0, 1.0].
    """
    raw_bytes = base64.b64decode(audio_b64)
    # 16-bit signed little-endian PCM
    sample_count = len(raw_bytes) // 2
    samples = struct.unpack(f"<{sample_count}h", raw_bytes)
    audio = np.array(samples, dtype=np.float32) / 32768.0
    return audio


async def transcribe(audio: np.ndarray, source: str = "unknown") -> dict:
    """
    Transcribe a float32 audio array (16 kHz mono).

    Returns:
        {
            "text": "full transcript",
            "words": [{"word": "hello", "start": 0.1, "end": 0.5}, ...],
            "source": "mic" | "loopback",
            "duration_secs": 2.5,
            "latency_ms": 180,
            "backend": "parakeet" | "whisper"
        }
    """
    model = await get_model()
    if model is None:
        return {
            "text": "",
            "words": [],
            "source": source,
            "duration_secs": len(audio) / 16000.0,
            "latency_ms": 0,
            "backend": "none",
            "error": "No transcription model available",
        }

    loop = asyncio.get_event_loop()
    t0 = time.perf_counter()
    result = await loop.run_in_executor(None, _run_inference, model, audio)
    latency_ms = (time.perf_counter() - t0) * 1000

    result["source"] = source
    result["duration_secs"] = len(audio) / 16000.0
    result["latency_ms"] = round(latency_ms, 1)
    result["backend"] = _backend
    return result


def _run_inference(model, audio: np.ndarray) -> dict:
    """Run transcription synchronously (called in executor thread)."""
    if _backend == "parakeet":
        return _run_parakeet(model, audio)
    elif _backend == "whisper":
        return _run_whisper(model, audio)
    return {"text": "", "words": []}


def _run_parakeet(model, audio: np.ndarray) -> dict:
    """
    Run Parakeet-TDT inference.

    Parakeet-TDT is a Token-and-Duration Transducer that predicts both
    tokens and their durations natively, giving us word-level timestamps
    without a separate alignment step.
    """
    import torch

    with torch.no_grad():
        # NeMo ASR models accept a list of file paths or numpy arrays.
        # For in-memory audio, we use transcribe() with audio tensors.
        # The timestamps=True flag enables word-level timing output.
        output = model.transcribe(
            [audio],
            batch_size=1,
            timestamps=True,
            verbose=False,
        )

    # NeMo returns a list of Hypothesis objects
    if not output or len(output) == 0:
        return {"text": "", "words": []}

    # Extract text and word timestamps from the hypothesis
    # NeMo output structure varies by version -- handle both formats
    hypothesis = output[0] if isinstance(output, list) else output

    # Handle the case where output is a tuple (text_list, _)
    if isinstance(output, tuple):
        texts = output[0]
        text = texts[0] if texts else ""
    elif isinstance(hypothesis, str):
        text = hypothesis
    elif hasattr(hypothesis, "text"):
        text = hypothesis.text
    else:
        text = str(hypothesis)

    words = []

    # Try to extract word-level timestamps
    # Parakeet-TDT with timestamps=True provides these in the hypothesis
    if isinstance(output, tuple) and len(output) > 1 and output[1] is not None:
        timestamp_output = output[1]
        if isinstance(timestamp_output, list) and len(timestamp_output) > 0:
            segment_timestamps = timestamp_output[0]
            if isinstance(segment_timestamps, list):
                for seg in segment_timestamps:
                    if hasattr(seg, "word") or isinstance(seg, dict):
                        word_data = seg if isinstance(seg, dict) else vars(seg)
                        words.append({
                            "word": word_data.get("word", word_data.get("char", "")),
                            "start": round(word_data.get("start", word_data.get("start_offset", 0)), 3),
                            "end": round(word_data.get("end", word_data.get("end_offset", 0)), 3),
                        })

    # If the model did not provide timestamps in the expected format,
    # fall back to segment-level output
    if not words and hasattr(hypothesis, "timestep") and hypothesis.timestep:
        for ts in hypothesis.timestep.get("word", []):
            words.append({
                "word": ts.get("word", ""),
                "start": round(ts.get("start_offset", 0), 3),
                "end": round(ts.get("end_offset", 0), 3),
            })

    return {"text": text.strip(), "words": words}


def _run_whisper(model, audio: np.ndarray) -> dict:
    """Fallback: Faster-Whisper with word timestamps."""
    segments, _info = model.transcribe(
        audio,
        beam_size=5,
        language="en",
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300, "speech_pad_ms": 200},
        word_timestamps=True,
        condition_on_previous_text=True,
        temperature=0.0,
    )

    text_parts = []
    words = []
    for seg in segments:
        text_parts.append(seg.text.strip())
        if seg.words:
            for w in seg.words:
                words.append({
                    "word": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                })

    return {"text": " ".join(text_parts).strip(), "words": words}
