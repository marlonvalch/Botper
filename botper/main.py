
import os
import sys
import socket
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Load .env from project root
env_path = current_dir.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Smart startup functionality
def find_available_port(start_port=8001, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    return None

def kill_processes_on_port(port):
    """Kill any processes using the specified port (Windows)"""
    try:
        # Use netstat to find processes using the port
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        pids = []
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.append(pid)
        
        killed = 0
        for pid in pids:
            try:
                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                print(f"Killed process PID {pid} using port {port}")
                killed += 1
            except Exception:
                pass
        
        if killed > 0:
            time.sleep(2)  # Give processes time to clean up
            return True
        return False
        
    except Exception:
        return False

def check_port_available(port):
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
            return True
    except OSError:
        return False

def start_ngrok_if_available(port):
    """Start ngrok tunnel if available"""
    ngrok_path = current_dir.parent / 'ngrok.exe'
    
    if not ngrok_path.exists():
        print(f"WARNING: ngrok.exe not found at {ngrok_path}")
        print("Download from: https://ngrok.com/download")
        print("Place ngrok.exe in the project root directory")
        print(f"\nBot is running on: http://localhost:{port}")
        print("You can manually start ngrok with: ngrok http " + str(port))
        return None
    
    try:
        print(f"Starting ngrok tunnel on port {port}...")
        
        ngrok_process = subprocess.Popen([
            str(ngrok_path), 
            'http', 
            str(port)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        time.sleep(3)  # Give ngrok time to start
        
        if ngrok_process.poll() is None:
            print("OK: ngrok tunnel started!")
            print(f"Check ngrok dashboard: http://127.0.0.1:4040")
            print(f"Webhook URL format: https://your-ngrok-url.ngrok.io/webex/webhook")
            return ngrok_process
        else:
            # Get error output
            stdout, stderr = ngrok_process.communicate()
            
            # Check if it's the "already online" error
            if "already online" in stderr:
                print("WARNING: ngrok tunnel already running")
                print("This is fine - your existing ngrok tunnel is active")
                print("Check ngrok dashboard: http://127.0.0.1:4040")
                print("Your webhook should already be configured")
                return None  # Don't return process since we don't own it
            else:
                print("ERROR: ngrok failed to start")
                if stderr:
                    # Only show first line of error for cleaner output
                    error_line = stderr.split('\n')[0]
                    print(f"Error: {error_line}")
                return None
            
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        return None

def is_webex_ready():
    token = os.getenv('WEBEX_BOT_TOKEN')
    return bool(token and token.strip())

def is_teams_ready():
    bot_id = os.getenv('TEAMS_BOT_ID')
    bot_password = os.getenv('TEAMS_BOT_PASSWORD')
    return bool(bot_id and bot_id != 'your_teams_bot_app_id_here' and 
                bot_password and bot_password != 'your_teams_bot_app_password_here')

def is_zoom_ready():
    # For now, return False since Zoom requires more setup
    return False

def start_bot_with_smart_port():
    """Start bot with intelligent port management"""
    print("BOTPER SMART STARTUP")
    print("=" * 50)
    
    # Check .env file
    if not env_path.exists():
        print("ERROR: .env file not found!")
        print(f"Expected location: {env_path}")
        return 1
    
    print("OK: Configuration loaded")
    
    # Check platforms
    webex_ready = is_webex_ready()
    teams_ready = is_teams_ready()
    zoom_ready = is_zoom_ready()
    
    print(f"\nPlatform Status:")
    print(f"  Webex: {'READY' if webex_ready else 'NOT CONFIGURED'}")
    print(f"  Teams: {'READY' if teams_ready else 'NOT CONFIGURED'}")
    print(f"  Zoom:  {'READY' if zoom_ready else 'NOT CONFIGURED'}")
    
    # Initialize bots
    bots = []
    if webex_ready:
        try:
            from platforms.webex_bot import WebexBot
            bot = WebexBot()
            bots.append(('Webex', bot))
            print("OK: Webex bot initialized")
        except Exception as e:
            print(f"ERROR: Error initializing Webex bot: {e}")
    
    if teams_ready:
        try:
            from platforms.teams_bot import TeamsBot
            bot = TeamsBot()
            bots.append(('Teams', bot))
            print("OK: Teams bot initialized")
        except Exception as e:
            print(f"ERROR: Error initializing Teams bot: {e}")
    
    if zoom_ready:
        try:
            from platforms.zoom_bot import ZoomBot
            bot = ZoomBot()
            bots.append(('Zoom', bot))
            print("OK: Zoom bot initialized")
        except Exception as e:
            print(f"ERROR: Error initializing Zoom bot: {e}")

    if not bots:
        print("\nERROR: No platform bots are ready!")
        print("\nTo configure:")
        print("  - Webex: Set WEBEX_BOT_TOKEN in .env")
        print("  - Teams: Set TEAMS_BOT_ID and TEAMS_BOT_PASSWORD in .env")
        print("  - Zoom: Configure Zoom credentials")
        return 1

    # Smart port management
    preferred_port = int(os.getenv('BOTPER_PORT', 8001))
    
    print(f"\nChecking port {preferred_port}...")
    
    if not check_port_available(preferred_port):
        print(f"WARNING: Port {preferred_port} is in use")
        print("Attempting to free the port...")
        
        if kill_processes_on_port(preferred_port):
            time.sleep(2)
            if check_port_available(preferred_port):
                print(f"OK: Port {preferred_port} is now available")
                port = preferred_port
            else:
                print(f"ERROR: Port {preferred_port} still in use, finding alternative...")
                port = find_available_port(preferred_port + 1)
        else:
            print("Finding alternative port...")
            port = find_available_port(preferred_port + 1)
    else:
        print(f"OK: Port {preferred_port} is available")
        port = preferred_port
    
    if port is None:
        print("ERROR: No available ports found in range 8001-8010!")
        return 1
    
    print(f"\nUsing port {port}")
    
    # Start ngrok first (non-blocking)
    ngrok_process = None
    if '--no-ngrok' not in sys.argv:
        ngrok_process = start_ngrok_if_available(port)
    
    # Start bot
    name, bot = bots[0]  # Start first available bot
    print(f"\nStarting {name} bot...")
    print(f"Webhook endpoint: http://localhost:{port}/{name.lower()}/webhook")
    
    if ngrok_process:
        print("\nComplete setup ready!")
        print("Next steps:")
        print("   1. Check ngrok dashboard: http://127.0.0.1:4040")
        print("   2. Copy your ngrok URL")
        print("   3. Configure webhook in Webex: https://developer.webex.com/my-apps")
        print("   4. Set webhook URL to: https://your-ngrok-url.ngrok.io/webex/webhook")
    else:
        print(f"\nBot running on: http://localhost:{port}")
        print("To expose publicly, run: ngrok http " + str(port))
    
    print(f"\nPress Ctrl+C to stop")
    
    try:
        # Start the bot
        bot.start(port=port)
    except KeyboardInterrupt:
        print(f"\nStopping {name} bot...")
        if ngrok_process:
            try:
                ngrok_process.terminate()
                ngrok_process.wait(timeout=5)
                print("OK: ngrok stopped")
            except:
                ngrok_process.kill()
                print("OK: ngrok force stopped")
        print("OK: Shutdown complete")
    except Exception as e:
        print(f"ERROR: {e}")
        if ngrok_process:
            ngrok_process.terminate()
        return 1
    
    return 0

def main():
    """Main entry point with argument handling"""
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Botper - Multi-platform Bot")
            print("Usage: python main.py [options]")
            print("\nOptions:")
            print("  --no-ngrok    Start bot without ngrok tunnel")
            print("  --port PORT   Use specific port (default: 8001)")
            print("  -h, --help    Show this help")
            return 0
        elif sys.argv[1] == '--port' and len(sys.argv) > 2:
            os.environ['BOTPER_PORT'] = sys.argv[2]
    
    return start_bot_with_smart_port()

if __name__ == "__main__":
    main()
