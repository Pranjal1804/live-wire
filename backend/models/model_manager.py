import os
import asyncio
import numpy as np
from typing import Optional

class WhisperTranscriber:
    def __init__(self, model_size: str = "base.en"):
        from faster_whisper import WhisperModel
        print(f"Loading Whisper {model_size}...")
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            num_workers=2,
        )
        self.model_size = model_size
        self.initial_prompt = (
            "This is a customer service call. "
            "Common phrases: account, subscription, cancel, refund, billing, "
            "support, upgrade, discount, complaint, issue, resolve."
        )
        print(f"Whisper {model_size} ready")
    
    def transcribe(self, audio: np.ndarray) -> str:
        try:
            segments, info = self.model.transcribe(
                audio,
                beam_size=5,
                language="en",
                initial_prompt=self.initial_prompt,
                vad_filter=True,
                vad_parameters={
                    "min_silence_duration_ms": 300,
                    "speech_pad_ms": 200,
                },
                condition_on_previous_text=True,
                temperature=0.0,
            )
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip()
        except Exception as e:
            print(f"Whisper error: {e}")
            return ""

class EmotionDetector:
    def __init__(self):
        try:
            from transformers import pipeline as hf_pipeline
            print("Loading emotion detection model...")
            self.pipeline = hf_pipeline(
                "audio-classification",
                model="superb/wav2vec2-base-superb-er",
                device=-1,
            )
            self._loaded = True
            print("Emotion model ready")
        except Exception as e:
            print(f"Emotion model failed to load: {e}")
            self._loaded = False
    
    def predict(self, audio: np.ndarray) -> dict:
        if not self._loaded:
            return self._sentiment_fallback(audio)
        try:
            results = self.pipeline({"array": audio, "sampling_rate": 16000})
            top = results[0]
            all_scores = {r["label"]: r["score"] for r in results}
            return {
                "label": top["label"].lower(),
                "score": top["score"],
                "all_scores": all_scores,
                "is_negative": top["label"].lower() in ["angry", "disgusted", "fearful", "sad"],
                "risk_level": self._compute_risk(all_scores)
            }
        except Exception as e:
            return self._sentiment_fallback(audio)
    
    def _compute_risk(self, scores: dict) -> float:
        negative_emotions = ["angry", "disgusted", "fearful", "sad"]
        risk = sum(scores.get(e, 0) for e in negative_emotions)
        return min(risk, 1.0)
    
    def _sentiment_fallback(self, audio: np.ndarray) -> dict:
        rms = float(np.sqrt(np.mean(audio**2)))
        if rms > 0.1:
            return {"label": "angry", "score": 0.6, "all_scores": {}, 
                   "is_negative": True, "risk_level": 0.6}
        else:
            return {"label": "neutral", "score": 0.8, "all_scores": {},
                   "is_negative": False, "risk_level": 0.1}

class ModelManager:
    _transcriber: Optional[WhisperTranscriber] = None
    _emotion_model: Optional[EmotionDetector] = None
    _initialized = False
    
    @classmethod
    async def initialize(cls):
        loop = asyncio.get_event_loop()
        whisper_model = os.environ.get("WHISPER_MODEL", "base.en")
        cls._transcriber = await loop.run_in_executor(
            None, WhisperTranscriber, whisper_model
        )
        cls._emotion_model = await loop.run_in_executor(
            None, EmotionDetector
        )
        cls._initialized = True
    
    @classmethod
    async def get_transcriber(cls) -> WhisperTranscriber:
        if not cls._initialized:
            await cls.initialize()
        return cls._transcriber
    
    @classmethod
    async def get_emotion_model(cls) -> EmotionDetector:
        if not cls._initialized:
            await cls.initialize()
        return cls._emotion_model
