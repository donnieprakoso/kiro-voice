[![Badge](https://d2v7cx6vtbimce.cloudfront.net/badge.v2?type=code&style=for-the-badge&logoStyle=gray&url=https%3A%2F%2Fgithub.com%2Fdonnieprakoso%2Fkiro-voice)](https://kiro.dev?trk=716f0d36-cc87-416b-9c6a-44880d969921&sc_channel=el)

# Kiro Voice
~~(or Voice-to-Kiro as it was the initial name but I'm too lazy to change the var in the application)~~
This small project is a voice-driven interaction with Kiro-CLI through real-time audio transcription. I'm currently using this to converse with Kiro over tmux. There are 2 available engines: 1) Faster Whisper (locally processed but it's not that accurate enough) and surprisingly accurate and way faster 2) Amazon Transcribe streaming. I'm using Amazon Transcribe streaming at the moment.

## Features

- Real-time speech-to-text using faster-whisper (local, private)
- Voice commands for punctuation and execution
- Tmux integration for command delivery
- Live TUI with Rich
- Debug logging

## Requirements

- Python 3.8+
- tmux
- macOS (or Linux with audio support)
- AWS credentials (for Amazon Transcribe streaming)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Local Mode (Default)

1. Start tmux and run Kiro-CLI in a pane
2. Run the voice application:

```bash
python main.py
```

3. Select your audio input device
4. Select the tmux pane running Kiro-CLI
5. Start speaking!

### Remote Mode (Work in progress to send my audio over SSH. Still deciding to use socket, compression and using `sox` or `ffmpeg`)

This is WIP on how I think it should be. 

Run the application on a remote server and stream audio from your local machine.

**On Remote Server:**
```bash
# SSH into remote server
ssh user@remote

# Start tmux with Kiro-CLI in a pane
# Then run in another pane or terminal:
python main.py --remote
```

**On Local Machine:**
Stream audio using sox or ffmpeg:

```bash
# Using sox (recommended)
sox -d -t raw -r 16000 -e signed -b 16 -c 1 - | ssh user@remote 'cd /path/to/kiro-audio && python main.py --remote'

# Using ffmpeg
ffmpeg -f avfoundation -i ":0" -ar 16000 -ac 1 -f s16le - | ssh user@remote 'cd /path/to/kiro-audio && python main.py --remote'
```

**Install sox on macOS:**
```bash
brew install sox
```

### Voice Commands

- `period` → `.`
- `comma` → `,`
- `question mark` → `?`
- `exclamation mark` → `!`
- `new line` → `\n`
- `command enter` → Execute command (send to Kiro-CLI)

### Control Commands

- `/mute` - Toggle listening on/off
- `/exit` - Quit application
- `/debug` - Toggle debug logs

### Debug Mode

```bash
python main.py --debug
```

## Example

Say: "list all s3 buckets in us-east-1 command enter"

Result: Sends "list all s3 buckets in us-east-1" to Kiro-CLI and executes.

## Architecture

- `main.py` - Main application and TUI
- `audio_handler.py` - Audio device selection and capture
- `transcriber.py` - Whisper transcription
- `tmux_controller.py` - Tmux integration
- `command_parser.py` - Voice command parsing
