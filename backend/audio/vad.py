import os
import numpy as np
import torch
from typing import Optional
import asyncio

VAD_THRESHOLD = float(os.environ.get("VAD_THRESHOLD", "0.5"))
SAMPLE_RATE = 16000

class VoiceActivityDetector:
    def __init__(self):
        self.model = None
        self.get_speech_timestamps = None
        self._loaded = False
        
    async def load(self):
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_sync)
        except Exception as e:
            print(f"Silero VAD load failed: {e}. Using fallback.")
    
    def _load_sync(self):
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True
        )
        (self.get_speech_timestamps, _, _, _, _) = utils
        self.model.eval()
        self._loaded = True
        print("Silero VAD loaded")
    
    def is_speech(self, audio: np.ndarray) -> bool:
        if not self._loaded:
            return self._energy_based_vad(audio)
        
        try:
            audio_tensor = torch.FloatTensor(audio)
            with torch.no_grad():
                speech_prob = self.model(audio_tensor, SAMPLE_RATE).item()
            return speech_prob > VAD_THRESHOLD
        except Exception:
            return self._energy_based_vad(audio)
    
    def _energy_based_vad(self, audio: np.ndarray) -> bool:
        rms = np.sqrt(np.mean(audio**2))
        return rms > 0.005
    
    def get_speech_ratio(self, audio: np.ndarray) -> float:
        if not self._loaded:
            rms = np.sqrt(np.mean(audio**2))
            return min(rms * 100, 1.0)
        
        try:
            audio_tensor = torch.FloatTensor(audio)
            with torch.no_grad():
                speech_prob = self.model(audio_tensor, SAMPLE_RATE).item()
            return speech_prob
        except Exception:
            return 0.5

_vad_instance: Optional[VoiceActivityDetector] = None

async def get_vad() -> VoiceActivityDetector:
    global _vad_instance
    if _vad_instance is None:
        _vad_instance = VoiceActivityDetector()
        await _vad_instance.load()
    return _vad_instance
