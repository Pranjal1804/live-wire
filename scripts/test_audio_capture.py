#!/usr/bin/env python3
"""
MAESTRO -- Audio Capture Test Script
Run: python scripts/test_audio_capture.py
Tests that audio capture is working before starting the full system.
"""

import sounddevice as sd
import numpy as np
import sys
import time
import os

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


def banner():
    print()
    print(f"{GRAY}  ┌──────────────────────────────────────────────────┐{RESET}")
    print(f"{GRAY}  │{RESET}  {WHITE}{BOLD}MAESTRO{RESET}  {DIM}Audio Diagnostic{RESET}                         {GRAY}│{RESET}")
    print(f"{GRAY}  │{RESET}  {DIM}Verify capture devices and audio levels{RESET}           {GRAY}│{RESET}")
    print(f"{GRAY}  └──────────────────────────────────────────────────┘{RESET}")
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

def list_audio_devices():
    header("Audio devices")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        marker = "  "
        if "monitor" in dev["name"].lower() or "maestro" in dev["name"].lower():
            marker = f"{GREEN}>>{RESET}"
        if dev["max_input_channels"] > 0:
            print(f"  {marker} {GRAY}[{i}]{RESET} {DIM}IN{RESET}   {dev['name']}  {DIM}(ch: {dev['max_input_channels']}){RESET}")
        if dev["max_output_channels"] > 0:
            print(f"  {marker} {GRAY}[{i}]{RESET} {DIM}OUT{RESET}  {dev['name']}  {DIM}(ch: {dev['max_output_channels']}){RESET}")
    print(HR)
    info(f"{GREEN}>>{RESET} = virtual/monitor source (preferred for capture)")


def find_best_capture_device():
    """Find the best device for capturing meeting audio."""
    devices = sd.query_devices()

    # Priority order: virtual sink first, then monitor, then system defaults
    priority_keywords = [
        "maestro_virtual_capture",
        "maestro",
        "monitor",
        "pipewire",
        "pulse",
    ]

    for keyword in priority_keywords:
        for i, dev in enumerate(devices):
            if keyword in dev["name"].lower() and dev["max_input_channels"] > 0:
                return i, dev["name"]

    return None, "default"


def test_audio_levels(device_index=None, device_name="default", duration=5):
    """Test that audio is being captured with actual levels."""
    header("Level test")
    info(f"Device: {WHITE}{device_name}{RESET}")
    info(f"Duration: {duration} seconds")
    print()
    note("Play something in your meeting or browser now")
    print()

    devices = sd.query_devices()
    device_info = (
        devices[device_index]
        if device_index is not None
        else sd.query_devices(kind="input")
    )
    sample_rate = int(device_info["default_samplerate"])
    chunk_size = int(sample_rate * 0.1)

    levels = []

    def audio_callback(indata, frames, time_info, status):
        rms = np.sqrt(np.mean(indata ** 2))
        levels.append(rms)
        bar_len = int(rms * 500)
        bar = "+" * min(bar_len, 40)
        sys.stdout.write(
            f"\r{GRAY}       [{bar:<40}] {rms:.4f}{RESET}"
        )
        sys.stdout.flush()

    try:
        kwargs = {
            "samplerate": sample_rate,
            "channels": min(device_info["max_input_channels"], 1),
            "dtype": np.float32,
            "blocksize": chunk_size,
            "callback": audio_callback,
        }
        if device_index is not None:
            kwargs["device"] = device_index

        with sd.InputStream(**kwargs):
            time.sleep(duration)

        print()
        print()
        avg_level = np.mean(levels) if levels else 0
        max_level = np.max(levels) if levels else 0

        info(f"Average level: {avg_level:.4f}")
        info(f"Peak level:    {max_level:.4f}")

        if max_level > 0.001:
            print()
            note(f"{GREEN}Audio capture is working{RESET}")
            return True
        else:
            print()
            note(f"{RED}No audio detected. Check your audio routing.{RESET}")
            info("Try running: bash scripts/setup_audio.sh")
            info("Try: pavucontrol to route meeting app to virtual sink")
            return False

    except Exception as e:
        print()
        note(f"{RED}Error: {e}{RESET}")
        info("Make sure PulseAudio/PipeWire is running")
        info("Try: systemctl --user restart pipewire")
        return False


def test_whisper_transcription():
    """Quick test that Whisper can transcribe captured audio."""
    header("Whisper transcription test")
    try:
        from faster_whisper import WhisperModel
        import scipy.signal

        info("Loading tiny model for test (fastest)...")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")

        device_info = sd.query_devices(kind="input")
        native_rate = int(device_info["default_samplerate"])
        target_rate = 16000
        duration = 3

        print()
        note(f"Speak now ({duration} seconds): 'Testing one two three'")
        info(f"Recording at {native_rate}Hz...")
        print()

        audio_data = sd.rec(
            int(duration * native_rate),
            samplerate=native_rate,
            channels=1,
            dtype=np.float32,
        )
        sd.wait()

        audio_flat = audio_data.flatten()

        if native_rate != target_rate:
            info(f"Resampling {len(audio_flat)} samples from {native_rate}Hz to {target_rate}Hz...")
            num_samples = int(len(audio_flat) * target_rate / native_rate)
            audio_flat = scipy.signal.resample(audio_flat, num_samples)

        segments, _ = model.transcribe(audio_flat, beam_size=5)

        text = " ".join([seg.text for seg in segments])
        info(f"Transcribed: '{text}'")

        if text.strip():
            note(f"{GREEN}Whisper transcription working{RESET}")
            return True
        else:
            note(f"{AMBER}No speech detected (try speaking louder){RESET}")
            return False

    except ImportError:
        note(f"{AMBER}faster-whisper or scipy not installed. Run setup script first.{RESET}")
        return False
    except Exception as e:
        note(f"{RED}Whisper error: {e}{RESET}")
        return False


def main():
    banner()

    # Step 1: List all devices
    step(1, 4, "Enumerate audio devices")
    ok()
    list_audio_devices()

    # Step 2: Find best device
    step(2, 4, "Select capture device")
    device_index, device_name = find_best_capture_device()
    ok(f"[{device_index}] {device_name}")

    # Step 3: Save device to config
    step(3, 4, "Save device config")
    config_path = "config/audio_device.txt"
    os.makedirs("config", exist_ok=True)
    with open(config_path, "w") as f:
        f.write(f"{device_index or 'default'}\n{device_name}")
    ok(config_path)

    # Step 4: Test audio levels
    step(4, 4, "Audio level test")
    print()
    input(f"{GRAY}       Press ENTER to start (5 seconds)...{RESET}")
    success = test_audio_levels(device_index, device_name)

    # Optional: Whisper test
    if success:
        print()
        choice = input(f"{GRAY}       Test Whisper transcription? (y/N): {RESET}").strip().lower()
        if choice == "y":
            test_whisper_transcription()

    # Done
    print()
    print(f"{GRAY}  ┌──────────────────────────────────────────────────┐{RESET}")
    print(f"{GRAY}  │{RESET}  {GREEN}{BOLD}Diagnostic complete{RESET}                               {GRAY}│{RESET}")
    print(f"{GRAY}  └──────────────────────────────────────────────────┘{RESET}")
    print()
    header("Next")
    info("cd backend && source venv/bin/activate &&")
    info("uvicorn main:app --reload --port 8000")
    print()


if __name__ == "__main__":
    main()
