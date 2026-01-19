import sounddevice as sd
import logging
import sys
import numpy as np

logger = logging.getLogger(__name__)

def list_audio_devices():
    """List all available audio input devices."""
    devices = sd.query_devices()
    input_devices = []
    
    for idx, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            input_devices.append({
                'index': idx,
                'name': device['name'],
                'channels': device['max_input_channels'],
                'sample_rate': device['default_samplerate']
            })
    
    return input_devices

def select_audio_device():
    """Prompt user to select an audio input device."""
    devices = list_audio_devices()
    
    if not devices:
        raise RuntimeError("No audio input devices found")
    
    print("\n=== Available Audio Input Devices ===")
    for i, device in enumerate(devices):
        print(f"{i + 1}. {device['name']} ({device['channels']} channels, {device['sample_rate']} Hz)")
    
    while True:
        try:
            choice = int(input("\nSelect device number: ")) - 1
            if 0 <= choice < len(devices):
                selected = devices[choice]
                logger.info(f"Selected audio device: {selected['name']}")
                return selected
            print("Invalid selection. Try again.")
        except (ValueError, KeyboardInterrupt):
            print("Invalid input. Try again.")

class AudioCapture:
    """Handle audio capture from selected device or stdin."""
    
    def __init__(self, device_index=None, sample_rate=16000, callback=None, stdin_mode=False):
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.callback = callback
        self.stdin_mode = stdin_mode
        self.stream = None
        self.is_active = False
        self.stdin_thread = None
    
    def start(self):
        """Start audio capture."""
        if self.stdin_mode:
            self._start_stdin_capture()
        else:
            self._start_device_capture()
    
    def _start_device_capture(self):
        """Start capture from audio device."""
        if self.stream is not None:
            return
        
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio callback status: {status}")
            if self.callback and self.is_active:
                self.callback(indata.copy())
        
        self.stream = sd.InputStream(
            device=self.device_index,
            channels=1,
            samplerate=self.sample_rate,
            callback=audio_callback
        )
        self.stream.start()
        self.is_active = True
        logger.info("Audio capture started from device")
    
    def _start_stdin_capture(self):
        """Start capture from stdin (for remote mode)."""
        import threading
        
        def read_stdin():
            logger.info("Reading audio from stdin...")
            chunk_size = 1024  # samples per chunk
            bytes_per_sample = 2  # 16-bit audio
            
            while self.is_active:
                try:
                    # Read raw audio data from stdin
                    data = sys.stdin.buffer.read(chunk_size * bytes_per_sample)
                    if not data:
                        break
                    
                    # Convert bytes to numpy array
                    audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    audio_array = audio_array.reshape(-1, 1)
                    
                    if self.callback:
                        self.callback(audio_array)
                except Exception as e:
                    logger.error(f"Error reading from stdin: {e}")
                    break
            
            logger.info("Stdin capture ended")
        
        self.is_active = True
        self.stdin_thread = threading.Thread(target=read_stdin, daemon=True)
        self.stdin_thread.start()
        logger.info("Audio capture started from stdin")
    
    def stop(self):
        """Stop audio capture."""
        self.is_active = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        if self.stdin_thread:
            self.stdin_thread.join(timeout=2)
        
        logger.info("Audio capture stopped")
    
    def pause(self):
        """Pause audio processing without stopping stream."""
        self.is_active = False
        logger.info("Audio capture paused")
    
    def resume(self):
        """Resume audio processing."""
        self.is_active = True
        logger.info("Audio capture resumed")
