# Botper Integration Setup Guide

## Overview
This guide shows you how to set up the Webex Integration + Bot collaboration in Botper. The integration allows users to create meetings via OAuth, while the bot automatically detects and creates tasks for those meetings.

## Architecture
```
User → OAuth Integration → Webex API (Create Meeting) → Webhook → Bot → Task Creation
```

## Step 1: Create Webex Integration

1. **Go to**: https://developer.webex.com/my-apps/new/integration

2. **Fill out the integration details**:
   - **Integration Name**: `Botper Integration` (or your choice)
   - **Icon**: Upload your app icon
   - **Description**: `Personal task and meeting management bot`
   - **Redirect URI**: `http://localhost:8000/auth/webex/callback` (for local dev)
   - **Scopes**: Select these permissions:
     - ✅ `spark:messages_read` - Read messages  
     - ✅ `spark:messages_write` - Send messages
     - ✅ `spark:rooms_read` - Read room information
     - ✅ `spark:people_read` - Read user information
     - ✅ `meeting:schedules_write` - Create meetings
     - ✅ `meeting:schedules_read` - Read meeting schedules

3. **Save and copy credentials**:
   - **Client ID** 
   - **Client Secret**
   - **Redirect URI**

## Step 2: Environment Variables

Create a `.env` file in your `botper` directory with these variables:

```bash
# Existing Bot Configuration
WEBEX_BOT_TOKEN=your_existing_bot_token

# New Integration OAuth Credentials  
WEBEX_CLIENT_ID=your_integration_client_id
WEBEX_CLIENT_SECRET=your_integration_client_secret
WEBEX_REDIRECT_URI=http://localhost:8000/auth/webex/callback

# Optional: For production deployment
# WEBEX_REDIRECT_URI=https://yourdomain.com/auth/webex/callback
```

## Step 3: Setup Webhooks for Integration

The integration needs webhooks to notify your bot when meetings are created.

**Important**: Your bot webhook URL must be accessible from the internet for the integration to work. For local development, you can use:

- **ngrok**: `ngrok http 8000` then use the ngrok URL
- **localtunnel**: `npx localtunnel --port 8000`

Your webhook URL should be: `https://your-tunnel-url.com/webex/webhook`

## Step 4: How It Works

### Basic Flow:
1. **User Authorization**: User visits `http://localhost:8000` → Clicks "Connect to Webex" → Authorizes
2. **Meeting Creation**: User types `meeting Team Standup` in Webex → Bot creates meeting via OAuth
3. **Webhook Trigger**: Webex sends webhook to bot about new meeting
4. **Task Creation**: Bot automatically creates task with meeting link

### Commands Available:

#### Without OAuth (Traditional Bot):
- `task [description]` - Create task
- `list` - Show tasks  
- `delete [task_id]` - Delete task
- `meeting [title]` - Redirect to manual meeting creation

#### With OAuth (Enhanced):
- `meeting [title]` - **Automatically creates meeting + task!**
- All the above commands still work

## Step 5: Testing the Integration

### 1. Start Your Bot
```bash
cd botper
python main.py
```

### 2. Set Up OAuth
1. Visit: `http://localhost:8000`
2. Click "🚀 Connect to Webex"  
3. Authorize the integration
4. Test creating a meeting on the success page

### 3. Test Via Chat
1. Go to a Webex space where your bot is present
2. Type: `meeting Team Standup`
3. If authorized: Meeting created automatically + task created
4. If not authorized: Redirected to manual creation + authorization offer

## Step 6: Production Deployment

For production:

### Update Environment Variables:
```bash
WEBEX_REDIRECT_URI=https://yourdomain.com/auth/webex/callback
```

### Update Integration Settings:
- Go back to https://developer.webex.com/my-apps
- Edit your integration
- Update **Redirect URI** to your production domain

### Security Considerations:
- Store user tokens in a proper database (not in-memory)
- Implement token refresh logic for long-term usage
- Use HTTPS for all OAuth flows
- Validate webhook signatures (optional but recommended)

## Troubleshooting

### Common Issues:

1. **"OAuth credentials not configured"**
   - Check your `.env` file has `WEBEX_CLIENT_ID` and `WEBEX_CLIENT_SECRET`
   - Restart your bot after adding environment variables

2. **"Token exchange failed"**
   - Verify your `WEBEX_REDIRECT_URI` matches exactly in both `.env` and integration settings
   - Check that your Client ID and Secret are correct

3. **"Bot doesn't receive webhooks"**
   - Ensure your webhook URL is publicly accessible
   - Use ngrok or similar for local development
   - Check that webhook is registered for "meetings" resource

4. **"Meeting created but no task appears"**
   - Check console logs for webhook data
   - Verify webhook URL is accessible
   - Ensure bot is in the same spaces as the user

### Debug Mode:
Your bot logs important information to console. Watch for:
```
Meeting webhook received: meeting_123 for host: user@example.com
OAuth successful for user: John Doe (john@example.com)  
Meeting created successfully: https://cisco.webex.com/meet/...
```

## Benefits of This Setup

### For Users:
- **Seamless**: One command creates meeting + task
- **Automatic**: No manual task creation needed
- **Flexible**: Works with or without OAuth

### For Developers:
- **Backward Compatible**: Existing bot functionality preserved
- **Extensible**: Easy to add more OAuth-powered features  
- **Scalable**: Token storage can be moved to database

## Next Steps

Consider extending this integration with:
- **Calendar Integration**: Sync with Google Calendar/Outlook
- **Recurring Meetings**: Support for meeting series
- **Meeting Templates**: Predefined meeting configurations
- **Advanced Permissions**: Role-based meeting creation