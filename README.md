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
   .venv\Scripts\activate
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

## Webhook Endpoints
- Webex: `POST /webex/webhook` (default port 8000)
- Teams: `POST /teams/webhook` (default port 8001)
- Zoom: `POST /zoom/webhook` (default port 8002)

## Notes
- Meeting scheduling and card interactivity require further integration with each platform's SDK and APIs.
- For production, run each bot in a separate process/thread for concurrency.
