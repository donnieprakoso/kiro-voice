import numpy as np
import logging
from faster_whisper import WhisperModel
from collections import deque
import threading

logger = logging.getLogger(__name__)

class Transcriber:
    """Handle real-time audio transcription using faster-whisper."""
    
    def __init__(self, model_size="base", device="auto"):
        logger.info(f"Loading Whisper model: {model_size}")
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.sample_rate = 16000
        self.audio_buffer = deque(maxlen=int(self.sample_rate * 5))  # 5 seconds buffer
        self.min_audio_length = int(self.sample_rate * 1)  # 1 second minimum
        self.lock = threading.Lock()
        logger.info("Whisper model loaded")
    
    def add_audio(self, audio_chunk):
        """Add audio chunk to buffer."""
        with self.lock:
            # Flatten and convert to float32
            audio_data = audio_chunk.flatten().astype(np.float32)
            self.audio_buffer.extend(audio_data)
    
    def transcribe(self):
        """Transcribe accumulated audio buffer."""
        with self.lock:
            if len(self.audio_buffer) < self.min_audio_length:
                return ""
            
            # Convert buffer to numpy array
            audio_array = np.array(self.audio_buffer, dtype=np.float32)
            
            # Clear buffer after reading
            self.audio_buffer.clear()
        
        try:
            # Transcribe
            segments, info = self.model.transcribe(
                audio_array,
                language="en",
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Collect all segments
            text = " ".join([segment.text for segment in segments]).strip()
            
            if text:
                logger.debug(f"Transcribed: '{text}'")
            
            return text
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
