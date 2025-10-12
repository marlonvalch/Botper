# Botper - Complete Meeting Scheduler

## How to Run

### Single Command Startup
```bash
python botper/main.py
```

That's it! The main.py now includes smart startup with automatic port conflict resolution and ngrok integration.

## What It Does

1. **Smart Port Management**
   - Automatically detects if port 8001 is in use
   - Kills conflicting processes automatically
   - Falls back to alternative ports (8002, 8003, etc.) if needed

2. **Automatic ngrok Integration**
   - Starts ngrok tunnel automatically (ngrok.exe found in project root)
   - Handles existing ngrok tunnels gracefully
   - Shows webhook URL format for easy configuration
   - Provides ngrok dashboard access at http://127.0.0.1:4040

3. **Video Meeting Scheduling**
   - Creates actual Webex video conferences with join URLs
   - Full meeting scheduler with interactive forms
   - Prompts for date, time, timezone, and participants
   - Real video meetings with audio, screen sharing, recording
   - Generates secure meeting URLs and passwords
   - All meetings tagged with "Webex Meeting:" prefix

4. **Platform Detection**
   - Checks which platforms are configured (.env file)
   - Only starts available/configured bots
   - Clear status messages for each platform

## Alternative Ways to Run

### Option 1: Direct (Recommended)
```bash
python botper/main.py
```

### Option 2: Legacy Script
```bash
python run_all.py
```
(This just calls main.py internally)

### Option 3: Module Mode
```bash
python -m botper.main
```

## Command Line Options

```bash
# Start without ngrok
python botper/main.py --no-ngrok

# Use specific port
python botper/main.py --port 8002

# Show help
python botper/main.py --help
```

## Bot Commands

### Task Management
- `task <description>` - Create a new task
- `list` - Show all tasks
- `delete <task id>` - Delete a task

### Meeting Scheduling
- `schedule meeting <title>` - Start interactive meeting scheduler
- `meetings` - List all scheduled meetings

### Example Interaction
```
User: schedule meeting Team Standup
Bot: [Shows interactive form with dropdown selections for:]
     - Date (Calendar picker - displays as MM/DD/YYYY format like 10/12/2025)
     - Time (12:00 AM to 11:30 PM in 30-min intervals)
     - Timezone (62 worldwide timezones from GMT-12:00 to GMT+12:00)
     - Participants (comma-separated emails)

Bot: Webex Video Meeting Scheduled Successfully!

     Title: Team Standup
     Date: 10/15/2025
     Time: 14:30 (UTC-05:00)

     JOIN MEETING:
     https://cisco.webex.com/meet/pr12345678901
     
     Meeting Password: SecurePass123
     Meeting ID: 123456789012345

     This is a full Webex video conference with:
     - Video and audio capabilities
     - Screen sharing
     - Recording options
     - Chat features
     - Participant management

     Invited Participants: user1@company.com, user2@company.com
     This meeting has been added to your tasks list.
```

### Enhanced Features

#### Comprehensive Timezone Support (62 Zones)
- **Americas**: GMT-12:00 (Dateline) to GMT-05:00 (Eastern)
- **Europe/Africa**: GMT-01:00 (Azores) to GMT+03:00 (Moscow)  
- **Asia/Pacific**: GMT+03:00 (Tehran) to GMT+12:00 (New Zealand)
- **Special**: Half-hour zones like GMT+05:30 (India), GMT-03:30 (Newfoundland)

#### Time Selection Dropdown
- **Format**: 12-hour AM/PM display with 24-hour values
- **Range**: 12:00 AM (00:00) to 11:30 PM (23:30)
- **Intervals**: 30-minute increments throughout the day
- **Default**: 09:00 AM for business hours convenience

### 🏢 **Real Webex Integration**

#### Automatic Webex Space Creation
- **Dedicated Spaces**: Creates a Webex space for each meeting
- **Participant Management**: Automatically adds participants to the space
- **Immediate Access**: Space ready for pre-meeting collaboration
- **Persistent**: Space remains available after the meeting

#### Meeting Options
1. **Webex Space Method**: Use the created space and click "Meet" button
2. **Formal Scheduling**: Follow provided instructions to create official meetings at webex.com
3. **Instant Meeting**: Start ad-hoc meetings directly from the space

#### Clear Instructions
- **No Confusion**: Bot explains the difference between spaces and meetings
- **Multiple Paths**: Provides options for different meeting needs
- **Professional URLs**: Real Webex space links, not placeholder URLs

## Sample Startup Output

```
BOTPER SMART STARTUP
==================================================
OK: Configuration loaded

Platform Status:
  Webex: READY
  Teams: NOT CONFIGURED
  Zoom:  NOT CONFIGURED
OK: Webex bot initialized

Checking port 8001...
OK: Port 8001 is available

Using port 8001
Starting ngrok tunnel on port 8001...
WARNING: ngrok tunnel already running
This is fine - your existing ngrok tunnel is active
Check ngrok dashboard: http://127.0.0.1:4040
Your webhook should already be configured

Starting Webex bot...
Webhook endpoint: http://localhost:8001/webex/webhook

Press Ctrl+C to stop
```

## Benefits

- ✓ **Single file startup** - Everything in main.py
- ✓ **No Unicode issues** - Plain text output only
- ✓ **Automatic port management** - No more manual process killing
- ✓ **Integrated ngrok** - Automatic tunnel creation
- ✓ **Clean shutdown** - Ctrl+C stops everything
- ✓ **Minimal dependencies** - Uses built-in Python tools
- ✓ **Clear error messages** - Easy troubleshooting

## Files Simplified

- ✓ Removed: start_botper.py, cleanup.py, PORT_CONFLICT_SOLUTION.md
- ✓ Enhanced: botper/main.py (now includes all smart features)
- ✓ Updated: run_all.py (simple wrapper)
- ✓ Cleaned: No Unicode characters, minimal dependencies

## Configuration for Video Meetings

To create actual Webex video conferences, you need to configure:

### 1. Environment Variables (.env file)
```
WEBEX_BOT_TOKEN=your_bot_token_here
```

### 2. Dynamic Meeting Host
- **Automatic Host**: The person scheduling the meeting becomes the host
- **Direct Email Use**: Uses email directly from Webex webhook data  
- **No API Calls**: Simple and efficient implementation

### 3. Required Permissions
Your Webex bot needs these scopes:
- `spark:rooms_read`
- `spark:rooms_write`  
- `spark:memberships_read`
- `spark:memberships_write`
- `meeting:schedules_write` (for video meetings)
- `meeting:schedules_read`

### 4. Meeting API Access
- Video meetings require Webex Meetings API access
- Creates actual video conferences with the scheduler as host
- Simplified error handling for better reliability

Copy `.env.example` to `.env` and configure your credentials.

## Troubleshooting

- **Port conflicts**: Automatically resolved
- **Missing ngrok**: Bot still works, manual ngrok instructions provided
- **Platform not ready**: Clear configuration instructions shown
- **Process stuck**: Automatic cleanup on startup