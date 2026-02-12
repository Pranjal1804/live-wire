import asyncio
import os
import numpy as np
import sounddevice as sd
from typing import AsyncGenerator, Optional, Callable
import subprocess
import scipy.signal

TARGET_RATE = 16000
CHUNK_DURATION = 2.0
CHUNK_SAMPLES = int(TARGET_RATE * CHUNK_DURATION)
OVERLAP_SAMPLES = int(TARGET_RATE * 0.3)

class AudioCapture:
    def __init__(self, callback: Callable):
        self.callback = callback
        self.device_index = self._find_capture_device()
        self.stream: Optional[sd.InputStream] = None
        self.is_running = False
        self._buffer = np.array([], dtype=np.float32)
        self.device_sample_rate = TARGET_RATE
        
    def _find_capture_device(self) -> Optional[int]:
        config_path = "../config/audio_device.txt"
        if os.path.exists(config_path):
            with open(config_path) as f:
                lines = f.readlines()
                if lines and lines[0].strip() != "default":
                    try:
                        return int(lines[0].strip())
                    except ValueError:
                        pass
        
        devices = sd.query_devices()
        search_order = [
            "maestro_capture.monitor",
            "maestro_capture",
            ".monitor",
            "pulse",
        ]
        
        for keyword in search_order:
            for i, dev in enumerate(devices):
                name = dev['name'].lower()
                if keyword in name and dev['max_input_channels'] > 0:
                    print(f"Auto-selected audio device: [{i}] {dev['name']}")
                    return i
        
        print("No virtual monitor found. Using default microphone.")
        return None

    def get_monitor_source_name(self) -> str:
        try:
            result = subprocess.run(
                ["pactl", "get-default-sink"],
                capture_output=True, text=True
            )
            sink_name = result.stdout.strip()
            return f"{sink_name}.monitor"
        except Exception:
            return "default"

    async def start(self):
        self.is_running = True
        self.loop = asyncio.get_event_loop()
        
        try:
            try:
                self._init_stream(TARGET_RATE)
                self.device_sample_rate = TARGET_RATE
                print(f"Audio capture started at {TARGET_RATE}Hz")
            except Exception as e:
                print(f"Target rate failed ({e}). Trying device default...")
                device_info = sd.query_devices(self.device_index, 'input')
                native_rate = int(device_info['default_samplerate'])
                self._init_stream(native_rate)
                self.device_sample_rate = native_rate
                print(f"Audio capture started at {native_rate}Hz")

        except Exception as e:
            print(f"Audio capture failed: {e}")
            return

        self.stream.start()
        while self.is_running:
            await asyncio.sleep(0.1)
            
        if self.stream:
            self.stream.stop()
            self.stream.close()

    def _init_stream(self, rate: int):
        def audio_callback(indata, frames, time_info, status):
            if status and "InputOverflow" not in str(status):
                print(f"Audio status: {status}")
            self._process_chunk(indata)

        stream_kwargs = {
            "samplerate": rate,
            "channels": 1,
            "dtype": np.float32,
            "blocksize": int(rate * 0.1),
            "callback": audio_callback,
        }
        if self.device_index is not None:
            stream_kwargs["device"] = self.device_index
            
        self.stream = sd.InputStream(**stream_kwargs)

    def _process_chunk(self, indata: np.ndarray):
        audio_chunk = indata[:, 0].copy()
        if self.device_sample_rate != TARGET_RATE:
            num_samples = int(len(audio_chunk) * TARGET_RATE / self.device_sample_rate)
            audio_chunk = scipy.signal.resample(audio_chunk, num_samples)

        self._buffer = np.concatenate([self._buffer, audio_chunk])
        while len(self._buffer) >= CHUNK_SAMPLES:
            chunk = self._buffer[:CHUNK_SAMPLES]
            self._buffer = self._buffer[CHUNK_SAMPLES - OVERLAP_SAMPLES:]
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self.callback(chunk), self.loop)

    def stop(self):
        self.is_running = False
        if self.stream:
            self.stream.stop()
