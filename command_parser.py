import logging

logger = logging.getLogger(__name__)

# Voice command mappings
VOICE_COMMANDS = {
    'period': '.',
    'comma': ',',
    'question mark': '?',
    'exclamation mark': '!',
    'new line': '\n',
    'enter': '__EXECUTE__',
    'delete': '__DELETE__',
    'clear': '__CLEAR__'
}

def parse_transcription(text):
    """
    Parse transcription text for voice commands.
    Returns tuple: (processed_text, should_execute, should_delete, should_clear)
    """
    text = text.strip().lower()
    
    if not text:
        return '', False, False, False
    
    # Check for clear command
    if 'clear' in text:
        text = text.replace('clear', '').strip()
        logger.debug("Clear command detected")
        return text, False, False, True
    
    # Check for delete command
    if 'delete' in text:
        text = text.replace('delete', '').strip()
        logger.debug("Delete command detected")
        return text, False, True, False
    
    # Check for execute command
    if 'enter' in text:
        text = text.replace('enter', '').strip()
        logger.debug(f"Execute command detected. Text: '{text}'")
        return text, True, False, False
    
    # Replace voice commands with actual characters
    processed = text
    for voice_cmd, char in VOICE_COMMANDS.items():
        if voice_cmd in processed:
            processed = processed.replace(voice_cmd, char)
            logger.debug(f"Replaced '{voice_cmd}' with '{char}'")
    
    return processed, False, False, False
