fr#!/usr/bin/env python3
"""
MAESTRO — Audio Capture Test Script
Run: python scripts/test_audio_capture.py
Tests that audio capture is working before starting the full system.
"""

import sounddevice as sd
import numpy as np
import sys
import time

def list_audio_devices():
    print("\n🎵 Available Audio Devices:")
    print("=" * 60)
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        marker = "  "
        if "monitor" in dev['name'].lower() or "maestro" in dev['name'].lower():
            marker = "⭐"  # Highlight virtual sinks
        if dev['max_input_channels'] > 0:
            print(f"{marker} [{i}] INPUT:  {dev['name']} (ch: {dev['max_input_channels']})")
        if dev['max_output_channels'] > 0:
            print(f"{marker} [{i}] OUTPUT: {dev['name']} (ch: {dev['max_output_channels']})")
    print("=" * 60)
    print("⭐ = Virtual/monitor source (preferred for meeting capture)")

def find_best_capture_device():
    """Find the best device for capturing meeting audio."""
    devices = sd.query_devices()
    
    # Priority order for EndeavourOS
    # The device name is "Maestro_Virtual_Capture"
    priority_keywords = [
        "maestro_virtual_capture",  # Specific name from setup_audio.sh
        "maestro",                  # Any maestro device
        "monitor",                  # Any monitor source (captures output)
        "pipewire",                 # Use pipewire directly if available
        "pulse",                    # PulseAudio bridge
    ]
    
    for keyword in priority_keywords:
        for i, dev in enumerate(devices):
            if keyword in dev['name'].lower() and dev['max_input_channels'] > 0:
                return i, dev['name']
    
    # Fall back to default input
    return None, "default"

def test_audio_levels(device_index=None, device_name="default", duration=5):
    """Test that audio is being captured with actual levels."""
    print(f"\n🎤 Testing audio capture from: {device_name}")
    print(f"   Duration: {duration} seconds")
    print(f"   → PLAY SOMETHING IN YOUR MEETING OR BROWSER NOW ←")
    print("   Monitoring audio levels...")
    
    devices = sd.query_devices()
    device_info = devices[device_index] if device_index is not None else sd.query_devices(kind='input')
    sample_rate = int(device_info['default_samplerate'])
    chunk_size = int(sample_rate * 0.1)  # 100ms chunks
    
    levels = []
    
    def audio_callback(indata, frames, time_info, status):
        if status:
            pass # Suppress overflow messages for the clean UI
        rms = np.sqrt(np.mean(indata**2))
        levels.append(rms)
        bar_len = int(rms * 500)
        bar = "█" * min(bar_len, 50)
        sys.stdout.write(f"\r   Level: [{bar:<50}] {rms:.4f}")
        sys.stdout.flush()
    
    try:
        kwargs = {
            "samplerate": sample_rate,
            "channels": min(device_info['max_input_channels'], 1),
            "dtype": np.float32,
            "blocksize": chunk_size,
            "callback": audio_callback,
        }
        if device_index is not None:
            kwargs["device"] = device_index
            
        with sd.InputStream(**kwargs):
            time.sleep(duration)
        
        print("\n")
        avg_level = np.mean(levels) if levels else 0
        max_level = np.max(levels) if levels else 0
        
        print(f"   Average level: {avg_level:.4f}")
        print(f"   Peak level:    {max_level:.4f}")
        
        if max_level > 0.001:
            print("   ✅ Audio capture is WORKING!")
            return True
        else:
            print("   ❌ No audio detected. Check your audio routing.")
            print("   → Try running: bash scripts/setup_audio.sh")
            print("   → Try: pavucontrol to route meeting app to virtual sink")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("   → Make sure PulseAudio/PipeWire is running")
        print("   → Try: systemctl --user restart pipewire")
        return False

def test_whisper_transcription():
    """Quick test that Whisper can transcribe captured audio."""
    print("\n🧠 Testing Whisper transcription...")
    try:
        from faster_whisper import WhisperModel
        import scipy.signal
        print("   Loading tiny model for test (fastest)...")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        
        # Get default sample rate
        device_info = sd.query_devices(kind='input')
        native_rate = int(device_info['default_samplerate'])
        target_rate = 16000
        duration = 3
        
        # Record 3 seconds
        print(f"   → SPEAK NOW ({duration} seconds): 'Testing one two three' ←")
        print(f"   (Recording at {native_rate}Hz...)")
        
        audio_data = sd.rec(
            int(duration * native_rate), 
            samplerate=native_rate, 
            channels=1, 
            dtype=np.float32
        )
        sd.wait()
        
        audio_flat = audio_data.flatten()
        
        # Resample if needed
        if native_rate != target_rate:
            print(f"   (Resampling {len(audio_flat)} samples from {native_rate}Hz to {target_rate}Hz...)")
            num_samples = int(len(audio_flat) * target_rate / native_rate)
            audio_flat = scipy.signal.resample(audio_flat, num_samples)
            
        segments, info = model.transcribe(audio_flat, beam_size=5)
        
        text = " ".join([seg.text for seg in segments])
        print(f"   Transcribed: '{text}'")
        
        if text.strip():
            print("   ✅ Whisper transcription WORKING!")
            return True
        else:
            print("   ⚠️  No speech detected (try speaking louder)")
            return False
            
    except ImportError:
        print("   ⚠️  faster-whisper (or scipy) not installed yet. Run setup script first.")
        return False
    except Exception as e:
        print(f"   ❌ Whisper error: {e}")
        return False

def main():
    print("=" * 60)
    print("  MAESTRO — Audio System Diagnostic")
    print("=" * 60)
    
    # Step 1: List all devices
    list_audio_devices()
    
    # Step 2: Find best device
    device_index, device_name = find_best_capture_device()
    print(f"\n🎯 Best capture device found: [{device_index}] {device_name}")
    
    # Step 3: Save device to config
    config_path = "config/audio_device.txt"
    import os
    os.makedirs("config", exist_ok=True)
    with open(config_path, "w") as f:
        f.write(f"{device_index or 'default'}\n{device_name}")
    print(f"   Device saved to {config_path}")
    
    # Step 4: Test audio levels
    input("\nPress ENTER to start audio level test (5 seconds)...")
    success = test_audio_levels(device_index, device_name)
    
    # Step 5: Test Whisper
    if success:
        test_choice = input("\nTest Whisper transcription? (y/N): ").strip().lower()
        if test_choice == 'y':
            test_whisper_transcription()
    
    print("\n" + "=" * 60)
    print("  Diagnostic complete!")
    print("  If audio works → Run: cd backend && uvicorn main:app --reload")
    print("=" * 60)

if __name__ == "__main__":
    main()
