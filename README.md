# Botper

A multiplatform bot for Webex, Microsoft Teams, and Zoom, supporting task and meeting management with adaptive cards and MongoDB.

## Features
- Webex, Teams, and Zoom bot support (runs any/all platforms based on .env config)
- Task management with checkboxes, strikethrough, and CRUD via adaptive/chatbot cards
- Meeting scheduling (Webex, Teams, Zoom) as tasks
- MongoDB backend for tasks and meetings
- FastAPI + Uvicorn for webhook endpoints

## Prerequisites
- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (for fast dependency management)
- MongoDB instance (local or remote)

## Setup

1. **Clone the repo**

2. **Create and activate a virtual environment**

   ```powershell
   uv venv .venv

   
   .\.venv\Scripts\Activate.ps1

   
   ```

3. **Install dependencies**

   ```powershell
   uv pip install -r botper/requirements.txt
   ```

4. **Configure environment variables**

   Copy `.env` to the root and fill in your credentials:

   ```
   cp botper/.env .env
   # Edit .env and set your tokens, MongoDB info, etc.
   ```

5. **Start MongoDB**

   Ensure your MongoDB instance is running and accessible as configured in `.env`.

6. **Run the app**

   ```powershell
   python botper/main.py
   ```

   The app will start webhook servers for each platform that is ready/configured.

7. **Expose endpoints (for local dev)**

   Use [ngrok](https://ngrok.com/) or similar to expose your FastAPI endpoints to the internet for Webex/Teams/Zoom webhooks.

## 👤 User Interaction Flow

### **Starting the Bot**
```powershell
python botper/main.py
```

The startup will:
- Check platform configurations (Webex/Teams/Zoom)
- Start ngrok tunnel automatically 
- Display webhook setup instructions

### **Basic Bot Usage (No OAuth Required)**

**In any Webex space where the bot is added:**

1. **Get started:**
   ```
   User: "hello"
   Bot: Hello! This is Botper! I will help you manage your tasks and meetings.
   
   🎯 COMMANDS:
   📋 Tasks:
   - task <description>
   - list
   - delete <task id>
   
   📞 Meetings:
   - meeting <title> - Schedule a meeting
   ```

2. **Create tasks:**
   ```
   User: "task Prepare presentation for Monday"
   Bot: "OK: Task created: Prepare presentation for Monday"
   [Shows updated task list with interactive buttons]
   ```

3. **Manage tasks:**
   ```
   User: "list"
   Bot: [Shows adaptive card with checkboxes, modify/delete buttons]
   ```

### **Enhanced Usage (With OAuth Integration)**

**Setup OAuth (one-time):**
1. Visit `http://localhost:8001` (or ngrok URL)
2. Click "🚀 Connect to Webex"
3. Authorize the integration

**Now meetings are automatic:**
```
User: "meeting Team Standup" 
Bot: "✅ Meeting Created Successfully!

📞 Team Standup
🔗 Link: https://cisco.webex.com/meet/pr123456789
⏰ Starts: 15:00 UTC

🤖 Automatically added to your tasks!"
```

### **Key Benefits**
- **Simple Commands**: Just type in Webex chat
- **Real Meetings**: Creates actual Webex video calls
- **Auto Tasks**: Meetings become trackable tasks automatically
- **Interactive**: Click buttons instead of typing commands
- **Persistent**: Tasks saved in MongoDB

## Webhook Endpoints
- Webex: `POST /webex/webhook` (default port 8001)
- Teams: `POST /teams/webhook` (default port 8002)  
- Zoom: `POST /zoom/webhook` (default port 8003)

## Notes
- Meeting links are real, functional Webex video calls created via official API
- OAuth integration enables automatic meeting creation with user permissions
- For production, configure proper webhook URLs and security
