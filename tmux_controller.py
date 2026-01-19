import subprocess
import logging

logger = logging.getLogger(__name__)

def list_tmux_panes():
    """List all tmux panes with their details."""
    try:
        result = subprocess.run(
            ['tmux', 'list-panes', '-a', '-F', 
             '#{session_name}:#{window_index}.#{pane_index}|#{pane_current_command}|#{pane_title}'],
            capture_output=True,
            text=True,
            check=True
        )
        
        panes = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 2:
                    panes.append({
                        'target': parts[0],
                        'command': parts[1],
                        'title': parts[2] if len(parts) > 2 else ''
                    })
        
        return panes
    except subprocess.CalledProcessError:
        raise RuntimeError("tmux is not running or not installed")
    except FileNotFoundError:
        raise RuntimeError("tmux is not installed")

def select_tmux_pane():
    """Prompt user to select a tmux pane."""
    panes = list_tmux_panes()
    
    if not panes:
        raise RuntimeError("No tmux panes found")
    
    print("\n=== Available Tmux Panes ===")
    for i, pane in enumerate(panes):
        print(f"{i + 1}. {pane['target']} - {pane['command']} ({pane['title']})")
    
    while True:
        try:
            choice = int(input("\nSelect pane number: ")) - 1
            if 0 <= choice < len(panes):
                selected = panes[choice]
                logger.info(f"Selected tmux pane: {selected['target']}")
                return selected['target']
            print("Invalid selection. Try again.")
        except (ValueError, KeyboardInterrupt):
            print("Invalid input. Try again.")

def send_to_tmux(text, target_pane):
    """Send text to specified tmux pane and execute."""
    try:
        # Send the text
        subprocess.run(
            ['tmux', 'send-keys', '-t', target_pane, '-l', text],
            check=True
        )
        # Send Enter key
        subprocess.run(
            ['tmux', 'send-keys', '-t', target_pane, 'Enter'],
            check=True
        )
        logger.info(f"Sent to tmux pane {target_pane}: {text[:50]}...")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to send to tmux: {e}")
        return False
