# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY botper/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Set environment variables (optional)
# Webex bot
#  You can REPLACE THIS WITH YOUR ACTUAL BOT TOKEN FROM https://developer.webex.com/
ENV WEBEX_BOT_TOKEN=NGRhZjlmYjktZjJmOS00ZmJjLWE4YTUtYzIwOTU2ZTc2OWJiYTVlYTA0Y2EtNDlh_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f

# Webex Integration 
ENV WEBEX_CLIENT_ID=C4fa44b2e29bb7f7040b977a150645cac64dbd708b7b91be64bf478af76e2190f
ENV WEBEX_CLIENT_SECRET=7200d6fdc7a23c146a6a4dbb4913d8acb1e329e55e0ce5df2d78de8fa3717aeb
ENV WEBEX_REDIRECT_URI=http://localhost:8000/auth/webex/callback

# Microsoft Teams Bot Configuration
ENV TEAMS_BOT_ID=your_teams_bot_app_id_here
ENV TEAMS_BOT_PASSWORD=your_teams_bot_app_password_here

# Optional: For advanced Teams features (Graph API)
ENV TEAMS_TENANT_ID=your_azure_tenant_id_here
ENV TEAMS_CLIENT_ID=your_azure_app_client_id_here
ENV TEAMS_CLIENT_SECRET=your_azure_app_client_secret_here

# ngrok configuration
ENV NGROK_AUTH_TOKEN=33kKvcOEOXV1js7kqYpl1bKZF26_zrpMBT1PaQGtshetcFs1

ENV MONGO_USERNAME=
ENV MONGO_PASSWORD=
ENV MONGO_HOSTS=localhost
ENV MONGO_DATABASE=botper
ENV MONGO_PORT=27017

# Run the FastAPI app with Uvicorn
CMD ["python", "run_all.py"]
