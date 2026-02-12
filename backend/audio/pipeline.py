import asyncio
import numpy as np
from typing import TYPE_CHECKING
from audio.capture import AudioCapture
from audio.vad import get_vad

if TYPE_CHECKING:
    from agents.orchestrator import MaestroAgent

SAMPLE_RATE = 16000

class AudioPipeline:
    def __init__(self, agent: "MaestroAgent", session_id: str):
        self.agent = agent
        self.session_id = session_id
        self.capture = AudioCapture(callback=self.on_audio_chunk)
        self.vad = None
        self._running = False
        self._transcript_context = []
        self._emotion_history = []
        
    async def start(self):
        print(f"Starting audio pipeline for session {self.session_id}")
        self.vad = await get_vad()
        
        from models.model_manager import ModelManager
        self.transcriber = await ModelManager.get_transcriber()
        self.emotion_model = await ModelManager.get_emotion_model()
        
        self._running = True
        await self.capture.start()
    
    async def stop(self):
        self._running = False
        self.capture.stop()
    
    async def on_audio_chunk(self, audio: np.ndarray):
        if not self._running:
            return
        
        speech_ratio = self.vad.get_speech_ratio(audio)
        if speech_ratio < 0.2:
            return
        
        try:
            transcript_task = asyncio.create_task(self._transcribe(audio))
            emotion_task = asyncio.create_task(self._detect_emotion(audio))
            
            transcript, emotion = await asyncio.gather(
                transcript_task,
                emotion_task,
                return_exceptions=True
            )
            
        except Exception as e:
            print(f"Pipeline error: {e}")
            return
        
        if isinstance(transcript, Exception):
            print(f"Transcription failed: {transcript}")
            transcript = None
        if isinstance(emotion, Exception):
            print(f"Emotion detection failed: {emotion}")
            emotion = {"label": "neutral", "score": 0.5}
        
        if transcript and transcript.strip():
            self._transcript_context.append(transcript)
            self._emotion_history.append(emotion)
            
            if len(self._transcript_context) > 15:
                self._transcript_context.pop(0)
                self._emotion_history.pop(0)
            
            await self.agent.perceive({
                "transcript": transcript,
                "emotion": emotion,
                "speech_ratio": speech_ratio,
                "context": self._transcript_context[-5:],
                "emotion_trend": self._emotion_history[-5:],
            })
    
    async def _transcribe(self, audio: np.ndarray) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.transcriber.transcribe, audio)
    
    async def _detect_emotion(self, audio: np.ndarray) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.emotion_model.predict, audio)
