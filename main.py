#!/usr/bin/env python3
import argparse
import logging
import sys
import time
import threading
from collections import deque
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

from audio_handler import select_audio_device, AudioCapture
from tmux_controller import select_tmux_pane, send_to_tmux
from transcriber import Transcriber
from transcriber_aws import AWSTranscriber
from command_parser import parse_transcription

console = Console()

class VoiceToKiro:
    """Main application class."""

    def __init__(self, remote_mode=False, debug_log=None, use_aws=False):
        self.remote_mode = remote_mode
        self.debug_log = debug_log
        self.use_aws = use_aws
        self.setup_logging()

        self.buffer = ""
        self.is_listening = False
        self.is_muted = False
        self.running = True

        self.audio_device = None
        self.tmux_pane = None
        self.audio_capture = None
        self.transcriber = None

        self.lock = threading.Lock()

    def setup_logging(self):
        """Setup logging configuration."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        if self.debug_log:
            handler = logging.FileHandler(self.debug_log)
            level = logging.DEBUG
        else:
            handler = logging.StreamHandler(sys.stderr)
            level = logging.INFO

        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(handler)
        root_logger.setLevel(level)

    def setup(self):
        """Setup audio device and tmux pane."""
        try:
            # Select audio device (skip in remote mode)
            if not self.remote_mode:
                self.audio_device = select_audio_device()
            else:
                self.audio_device = {'name': 'stdin (remote)', 'index': None}
                console.print("[yellow]Remote mode: Reading audio from stdin[/yellow]")

            # Select tmux pane
            self.tmux_pane = select_tmux_pane()

            # Initialize transcriber
            if self.use_aws:
                console.print("\n[yellow]Initializing Amazon Transcribe...[/yellow]")
                self.transcriber = AWSTranscriber()
                self.transcriber.start()
            else:
                console.print("\n[yellow]Loading Whisper model...[/yellow]")
                self.transcriber = Transcriber(model_size="large-v3")

            # Initialize audio capture
            self.audio_capture = AudioCapture(
                device_index=self.audio_device['index'] if not self.remote_mode else None,
                sample_rate=16000,
                callback=self.on_audio_chunk,
                stdin_mode=self.remote_mode
            )

            return True
        except Exception as e:
            console.print(f"[red]Setup failed: {e}[/red]")
            return False

    def on_audio_chunk(self, audio_data):
        """Callback for audio chunks."""
        if not self.is_muted and self.transcriber:
            self.transcriber.add_audio(audio_data)

    def process_transcription(self):
        """Process transcription in background thread."""
        while self.running:
            if not self.is_muted and self.transcriber:
                text = self.transcriber.transcribe()
                if text:
                    processed_text, should_execute, should_delete, should_clear = parse_transcription(text)

                    with self.lock:
                        # Handle clear command
                        if should_clear:
                            self.buffer = ""
                            continue
                        
                        # Handle delete command
                        if should_delete:
                            words = self.buffer.split()
                            if words:
                                words.pop()
                                self.buffer = " ".join(words)
                            continue
                        
                        # Add processed text to buffer
                        if processed_text:
                            self.buffer += " " + processed_text
                            self.buffer = self.buffer.strip()

                        # Execute if needed
                        if should_execute:
                            if self.buffer:
                                send_to_tmux(self.buffer, self.tmux_pane)
                                self.buffer = ""

            time.sleep(0.5)

    def generate_display(self):
        """Generate the TUI display."""
        with self.lock:
            status_text = "Listening 🎤" if not self.is_muted else "Muted 🔇"
            status_style = "green" if not self.is_muted else "yellow"
            device_name = self.audio_device['name'] if self.audio_device else "None"

            # Main panel content
            content = Text()
            content.append("Status: ", style="bold")
            content.append(status_text + "\n", style=status_style)
            content.append(f"Device: {device_name}\n")
            content.append(f"Target: {self.tmux_pane}\n\n")
            content.append("─" * 40 + "\n")
            content.append("Buffer:\n", style="bold cyan")
            content.append("> ")
            if self.buffer:
                content.append(self.buffer + "\n\n")
            else:
                content.append("(empty)\n\n", style="dim")
            content.append("─" * 40 + "\n")
            content.append("Commands: ", style="bold yellow")
            content.append("/mute /exit\n")
            content.append("Voice: ", style="bold yellow")
            content.append("period, comma, question mark,\n       exclamation mark, new line, enter,\n       delete, clear\n")

            return Panel(content, title="Voice-to-Kiro", border_style="blue")

    def handle_command(self, cmd):
        """Handle user commands."""
        cmd = cmd.strip().lower()

        if cmd == "/exit":
            self.running = False
            return True
        elif cmd == "/mute":
            self.is_muted = not self.is_muted
            if self.is_muted:
                self.audio_capture.pause()
            else:
                self.audio_capture.resume()
            return False

        return False

    def run(self):
        """Run the main application loop."""
        if not self.setup():
            return

        # Start audio capture
        self.audio_capture.start()
        self.is_listening = True

        # Start transcription thread
        transcription_thread = threading.Thread(target=self.process_transcription, daemon=True)
        transcription_thread.start()

        console.print("\n[green]Voice-to-Kiro started![/green]")
        console.print("Type commands or let it listen...\n")

        try:
            with Live(self.generate_display(), refresh_per_second=2, console=console) as live:
                while self.running:
                    live.update(self.generate_display())
                    time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources."""
        self.running = False
        if self.audio_capture:
            self.audio_capture.stop()
        if self.transcriber and self.use_aws:
            self.transcriber.stop()
        console.print("\n[yellow]Shutting down...[/yellow]")

def main():
    parser = argparse.ArgumentParser(description="Voice-to-Kiro CLI")
    parser.add_argument('--remote', action='store_true', help='Remote mode: read audio from stdin')
    parser.add_argument('--debug-log', type=str, help='Write debug logs to file (e.g., ./app.log)')
    parser.add_argument('--aws', action='store_true', help='Use Amazon Transcribe instead of local Whisper')
    args = parser.parse_args()

    app = VoiceToKiro(remote_mode=args.remote, debug_log=args.debug_log, use_aws=args.aws)
    app.run()

if __name__ == "__main__":
    main()
