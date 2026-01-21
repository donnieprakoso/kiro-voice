import logging
import asyncio
import threading
import numpy as np
from collections import deque
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.model import TranscriptEvent

logger = logging.getLogger(__name__)


class AWSTranscriber:
    """Handle real-time audio transcription using Amazon Transcribe."""

    def __init__(self, region="ap-southeast-1", language_code="en-US"):
        logger.info(f"Initializing Amazon Transcribe (region: {region}, language: {language_code})")
        self.region = region
        self.language_code = language_code
        self.sample_rate = 16000

        self.audio_queue = deque()
        self.output_queue = deque(maxlen=10)
        self.running = False
        self.loop = None
        self.thread = None

        # Silence asyncio debug logs
        logging.getLogger('asyncio').setLevel(logging.WARNING)

        logger.info("Amazon Transcribe initialized")

    async def _stream_audio(self):
        """Stream audio to Amazon Transcribe."""
        client = TranscribeStreamingClient(region=self.region)

        stream = await client.start_stream_transcription(
            language_code=self.language_code,
            media_sample_rate_hz=self.sample_rate,
            media_encoding="pcm",
        )

        async def write_chunks():
            """Write audio chunks from queue to stream."""
            while self.running:
                if self.audio_queue:
                    chunk = self.audio_queue.popleft()
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                else:
                    await asyncio.sleep(0.01)
            await stream.input_stream.end_stream()

        async def read_responses():
            """Read transcription responses from stream."""
            async for event in stream.output_stream:
                if isinstance(event, TranscriptEvent):
                    for result in event.transcript.results:
                        if not result.is_partial:
                            for alt in result.alternatives:
                                text = alt.transcript.strip()
                                if text:
                                    logger.debug(f"Amazon Transcribed: '{text}'")
                                    self.output_queue.append(text)

        await asyncio.gather(write_chunks(), read_responses())

    def _run_stream(self):
        """Run streaming in background thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._stream_audio())
        except Exception as e:
            logger.error(f"Amazon Transcribe error: {e}")
        finally:
            self.loop.close()

    def start(self):
        """Start the transcription stream."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_stream, daemon=True)
        self.thread.start()

        # Wait for stream to be ready
        import time
        time.sleep(1)
        logger.info("Amazon Transcribe stream started")

    def stop(self):
        """Stop the transcription stream."""
        self.running = False
        logger.info("Amazon Transcribe stream stopped")

    def add_audio(self, audio_chunk):
        """Add audio chunk to transcription queue."""
        if not self.running:
            return

        # Convert numpy array to bytes (16-bit PCM)
        audio_data = audio_chunk.flatten().astype(np.float32)
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()

        # Add to queue (non-blocking)
        self.audio_queue.append(audio_bytes)

    def transcribe(self):
        """Get transcribed text from queue."""
        if self.output_queue:
            return self.output_queue.popleft()
        return ""
