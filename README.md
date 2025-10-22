# Botper

A multiplatform bot for Webex, Microsoft Teams, and Zoom, supporting task and meeting management with adaptive cards and MongoDB.
Ready to run on a container with the Docker file in the project 
Ready to start a CI/CD process with Jenkins file in the project

## Features
- Webex, Teams, and Zoom bot support (runs any/all platforms based on .env config)
- Task management with checkboxes, strikethrough, and CRUD via adaptive/chatbot cards
- Meeting scheduling (Webex, Teams, Zoom) as tasks
- MongoDB backend for tasks and meetings
- FastAPI + Uvicorn for webhook endpoints
- App can be run on a container with the current docker.

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
   .\.venv\Scripts\Activate.ps1
   python botper/main.py
   ```

   The app will start webhook servers for each platform that is ready/configured.

7. **Expose endpoints (for local dev)**

   Ngrok tunnel:(ngrok is a tunneling tool. It gives  local machine a temporary, public HTTPS URL that forwards traffic to a port on localhost (e.g., http://127.0.0.1:8000). That lets cloud services (like Webex or Microsoft Teams) send webhooks to this app  running only on the user device.)

   Use [ngrok](https://ngrok.com/) or similar to expose  FastAPI endpoints to the internet for Webex/Teams/Zoom webhooks.

## Running in a Container

1. Build the Docker image:

```sh
docker build -t botper-app .
```

2. Run the container:

```sh
docker run -p 8000:8000 --env WEBEX_BOT_TOKEN=Botper_token_here
```

## Jenkins Pipeline

- The included `Jenkinsfile` will:
  - Build the Docker image
  - Optionally run tests (edit as needed)
  - Optionally push to a Docker registry (set `REGISTRY` env var)

To use:
1. Set up a Jenkins job with this repo.
2. Make sure Jenkins has Docker and Python installed.
3. Configure any secrets (like `WEBEX_BOT_TOKEN`) as needed.

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
   User: "hello" or "help"
   
   Bot: Hello! This is Botper! I will help you manage your tasks and meetings.
   
   🎯 COMMANDS:
   📋 Tasks:
   - task <description> : create tasks 
   - list : list tasks
    - Meetings:  Schedule Meetings
    
   -From the card
   -✅ Complete Task
   -  Delete Task
   -✏️ Edit Task
   - Schedule meeting button
   -Create note button
   -Edit note button
  
   
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



## Webhook Endpoints
- Webex: `POST /webex/webhook` (default port 8001)
- Teams: `POST /teams/webhook` (default port 8002)  
- Zoom: `POST /zoom/webhook` (default port 8003)

## Notes
-  Functional Webex video calls created via official API
- ⚠️Microsoft Teams meeting and Zoom meeting bots are in maintentance
