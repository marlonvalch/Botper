import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from webexteamssdk import WebexTeamsAPI
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from core.base_bot import BaseBot
from core.tasks import TaskManager
from utils.helpers import format_task_card
from oauth_handler import WebexOAuthHandler
from dotenv import load_dotenv

load_dotenv()

WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN")

class WebexBot(BaseBot):
	def __init__(self):
		self.api = WebexTeamsAPI(access_token=WEBEX_BOT_TOKEN)
		self.access_token = WEBEX_BOT_TOKEN
		self.task_manager = TaskManager()
		self.app = FastAPI()
		self.oauth_handler = WebexOAuthHandler()
		self.user_tokens = {}  # Store user OAuth tokens (in production, use a database)
		self.processed_messages = set()  # Track processed message IDs to avoid duplicates
		self.pending_meeting_tasks = {}  # Track meeting title for linking task
		self.processed_events = set()  # Track processed calendar events
		self.setup_routes()
		# Calendar monitoring disabled - bot token doesn't have meeting API access

	def setup_routes(self):
		@self.app.post("/webex/webhook")
		async def webhook(request: Request):
			data = await request.json()
			
			# Extract unique identifier for deduplication
			event_id = data.get('data', {}).get('id', '')
			if event_id in self.processed_messages:
				print(f"Skipping duplicate event: {event_id}")
				return {"status": "ok", "message": "duplicate event"}
			
			# Add to processed messages (keep last 100 to prevent memory leak)
			self.processed_messages.add(event_id)
			if len(self.processed_messages) > 100:
				self.processed_messages.pop()
			
			print(f"Webhook received: {data}")  # Debug logging
			
			# Handle Adaptive Card submissions (button clicks)
			if data.get('resource') == 'attachmentActions' and data.get('event') == 'created':
				action_id = data['data']['id']
				room_id = data['data']['roomId']
				person_id = data['data']['personId']
				
				# Get bot's own person ID to avoid responding to own actions
				try:
					bot_person = self.api.people.me()
					if person_id == bot_person.id:
						print("Ignoring action from bot itself")
						return {"status": "ok"}
				except Exception as e:
					print(f"Error getting bot info: {e}")
					return {"status": "error", "message": "Could not verify bot identity"}
				
				try:
					# Get the action data
					action = self.api.attachment_actions.get(action_id)
					action_data = action.inputs
					print(f"Processing action: {action_data}")
					
					if action_data.get('action') == 'delete':
						task_id = action_data.get('task_id')
						self.handle_task_command("delete", room_id, {"task_id": task_id})
					elif action_data.get('action') == 'modify':
						task_id = action_data.get('task_id')
						# Get current task details for the modify form
						tasks = self.task_manager.list_tasks()
						current_task = next((task for task in tasks if str(task["_id"]) == task_id), None)
						if current_task:
							self.handle_modify_task(room_id, task_id, current_task["title"])
						else:
							self.send_message(room_id, "ERROR: Task not found!")
					elif action_data.get('action') == 'update':
						task_id = action_data.get('task_id')
						new_title = action_data.get('new_title', '').strip()
						self.handle_update_task(room_id, task_id, new_title)
					elif action_data.get('action') == 'cancel':
						self.send_message(room_id, "Modification cancelled.")
						self.handle_task_command("list", room_id)
						
				except Exception as e:
					print(f"Error processing action {action_id}: {e}")
					return {"status": "error", "message": f"Could not process action: {e}"}
			
			# Handle meeting webhooks (automatic task creation)
			elif data.get('resource') == 'meetings' and data.get('event') == 'created':
				try:
					meeting_data = data.get('data', {})
					meeting_id = meeting_data.get('id', '')
					host_email = meeting_data.get('hostEmail', '')
					
					print(f"Meeting webhook received: {meeting_id} for host: {host_email}")
					
					# Process the meeting webhook
					self.handle_meeting_webhook(meeting_data)
					
				except Exception as e:
					print(f"Error processing meeting webhook: {e}")
					return {"status": "error", "message": f"Could not process meeting webhook: {e}"}
				
			# Handle regular messages
			elif data.get('resource') == 'messages' and data.get('event') == 'created':
				message_id = data['data']['id']
				room_id = data['data']['roomId']
				person_id = data['data']['personId']
				person_email = data['data'].get('personEmail', 'user@company.com')
				
				# Get bot's own person ID to avoid responding to own messages
				try:
					bot_person = self.api.people.me()
					if person_id == bot_person.id:
						print("Ignoring message from bot itself")
						return {"status": "ok"}
				except Exception as e:
					print(f"Error getting bot info: {e}")
					# Continue processing even if bot verification fails
				
				try:
					# Add retry logic for message retrieval
					import time
					max_retries = 3
					retry_delay = 1
					
					for attempt in range(max_retries):
						try:
							msg = self.api.messages.get(message_id)
							break
						except Exception as retry_e:
							if attempt == max_retries - 1:
								# Last attempt failed
								if "404" in str(retry_e) or "Not Found" in str(retry_e):
									print(f"Message {message_id} not found - likely from inaccessible room or deleted. Skipping.")
									return {"status": "ok", "message": "message not accessible"}
								else:
									raise retry_e
							else:
								print(f"Retry {attempt + 1} for message {message_id}: {retry_e}")
								time.sleep(retry_delay)
								retry_delay *= 2  # Exponential backoff
					
					# Check if message has text content
					if not hasattr(msg, 'text') or not msg.text:
						print(f"Message {message_id} has no text content - likely a file or card")
						return {"status": "ok", "message": "no text content"}
					
					text = msg.text.strip().lower()
					print(f"Processing message: '{text}' from person: {person_id}")
					
					if text == "hello" or text == "hi":
						self.send_greeting(room_id)
					elif text.startswith("task"):
						task_title = msg.text[5:].strip()
						if task_title:
							self.handle_task_command("create", room_id, {"title": task_title})
					elif text == "list":
						self.handle_task_command("list", room_id)
					elif text.startswith("delete"):
						task_id = msg.text[7:].strip()
						self.handle_task_command("delete", room_id, {"task_id": task_id})
					elif text.startswith("schedule meeting") or text.startswith("meeting"):
						meeting_title = msg.text.replace("schedule meeting", "").replace("meeting", "").strip()
						if meeting_title:
							# Try to create meeting via OAuth first, then fallback to redirect
							self.handle_meeting_request(room_id, person_id, person_email, meeting_title)
						else:
							self.send_message(room_id, "Please provide a meeting title. Example: 'schedule meeting Team Standup'")

				except Exception as e:
					error_msg = str(e)
					if "404" in error_msg or "Not Found" in error_msg:
						print(f"Message {message_id} not found - bot may not have access to this room")
						return {"status": "ok", "message": "message not accessible"}
					elif "403" in error_msg or "Forbidden" in error_msg:
						print(f"Access denied for message {message_id} - insufficient permissions")
						return {"status": "ok", "message": "access denied"}
					else:
						print(f"Error processing message {message_id}: {e}")
						return {"status": "error", "message": f"Could not process message: {e}"}
				
			# Handle meeting creation events
			elif data.get('resource') == 'meetings' and data.get('event') == 'created':
				meeting_id = data['data']['id']
				meeting_title = data['data']['title']
				meeting_link = data['data']['webLink']
				host_email = data['data']['hostEmail']
				
				print(f"New meeting created: {meeting_title} (ID: {meeting_id})")
				
				# Optionally, create a task for the meeting
				task = {
					"title": f"📞 {meeting_title}",
					"completed": False,
					"type": "meeting",
					"meeting_link": meeting_link,
					"platform": "webex"
				}
				self.task_manager.create_task(task)
				
				# Notify the user (or the room) about the new meeting
				self.send_message(room_id, f"✅ New meeting scheduled: **{meeting_title}**\n🔗 Link: {meeting_link}")
				
			return {"status": "ok"}

		# OAuth Integration Routes
		@self.app.get("/auth/webex")
		async def start_oauth(state: str = None):
			"""Initiate OAuth flow - redirect user to Webex authorization"""
			try:
				auth_url = self.oauth_handler.get_authorization_url(state)
				return RedirectResponse(url=auth_url)
			except Exception as e:
				return HTMLResponse(f"<h1>Error</h1><p>Failed to start OAuth flow: {e}</p>", status_code=500)

		@self.app.get("/auth/webex/callback")
		async def oauth_callback(code: str = None, state: str = None, error: str = None):
			"""Handle OAuth callback from Webex"""
			if error:
				return HTMLResponse(f"<h1>Authorization Error</h1><p>{error}</p>", status_code=400)
			
			if not code:
				return HTMLResponse("<h1>Error</h1><p>No authorization code received</p>", status_code=400)
			
			try:
				# Exchange code for tokens
				token_data = self.oauth_handler.exchange_code_for_token(code)
				
				# Get user info
				user_info = self.oauth_handler.get_user_info(token_data['access_token'])
				
				# Store user tokens (in production, use a proper database)
				user_id = user_info['id']
				self.user_tokens[user_id] = {
					'access_token': token_data['access_token'],
					'refresh_token': token_data['refresh_token'],
					'expires_in': token_data['expires_in'],
					'user_info': user_info
				}
				
				print(f"OAuth successful for user: {user_info.get('displayName')} ({user_info.get('emails', ['unknown'])[0]})")
				
				# Success page with meeting creation option
				return HTMLResponse(f"""
				<html>
					<head><title>Botper - Authorization Successful</title></head>
					<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
						<h1 style="color: #00BCF2;">✅ Authorization Successful!</h1>
						<p>Welcome, <strong>{user_info.get('displayName', 'User')}</strong>!</p>
						<p>Botper is now connected to your Webex account.</p>
						
						<div style="margin: 30px 0;">
							<h2>🎯 Test Meeting Creation</h2>
							<p>Create a test meeting to see the bot integration:</p>
							<form action="/create-meeting" method="post" style="display: inline-block;">
								<input type="hidden" name="user_id" value="{user_id}">
								<input type="text" name="title" placeholder="Meeting Title" value="Botper Test Meeting" style="padding: 10px; margin: 5px; width: 200px;">
								<br>
								<button type="submit" style="padding: 10px 20px; background-color: #00BCF2; color: white; border: none; border-radius: 5px; margin: 10px;">
									🚀 Create Test Meeting
								</button>
							</form>
						</div>
						
						<p style="color: #666; font-size: 14px;">
							Your bot will automatically detect when meetings are created and add them as tasks!
						</p>
						<p><a href="https://teams.webex.com" style="color: #00BCF2;">Return to Webex</a></p>
					</body>
				</html>
				""")
				
			except Exception as e:
				print(f"OAuth callback error: {e}")
				return HTMLResponse(f"<h1>Error</h1><p>Failed to complete authorization: {e}</p>", status_code=500)

		@self.app.get("/")
		async def home():
			"""Home page with integration setup instructions"""
			return HTMLResponse(f"""
			<html>
				<head><title>Botper - Webex Integration</title></head>
				<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
					<h1 style="color: #00BCF2;">🤖 Botper - Webex Integration</h1>
					<p>Your personal task and meeting management bot for Webex</p>
					
					<div style="margin: 30px 0;">
						<h2>🔗 Connect Your Account</h2>
						<p>Authorize Botper to create meetings on your behalf:</p>
						<a href="/auth/webex" style="
							display: inline-block; 
							padding: 15px 30px; 
							background-color: #00BCF2; 
							color: white; 
							text-decoration: none; 
							border-radius: 5px; 
							font-weight: bold;
							margin: 10px;
						">🚀 Connect to Webex</a>
					</div>
					
					<div style="margin: 30px 0; text-align: left; max-width: 600px; margin: 30px auto;">
						<h3>🔄 How It Works:</h3>
						<ol>
							<li><strong>Authorize:</strong> Click "Connect to Webex" above</li>
							<li><strong>Create:</strong> Integration creates meetings with your permissions</li>
							<li><strong>Detect:</strong> Bot automatically detects new meetings via webhooks</li>
							<li><strong>Task:</strong> Bot creates tasks with meeting links automatically</li>
						</ol>
						
						<h3>✨ What Botper Can Do:</h3>
						<ul>
							<li>📋 <strong>Task Management:</strong> Create, list, modify, and delete tasks</li>
							<li>📞 <strong>Meeting Integration:</strong> Automatic task creation for scheduled meetings</li>
							<li>� <strong>OAuth Integration:</strong> Create meetings directly via authorization</li>
							<li>⚡ <strong>Interactive Cards:</strong> Use buttons to manage tasks efficiently</li>
						</ul>
						
						<h3>🎯 Bot Commands:</h3>
						<ul>
							<li><code>task [description]</code> - Create a new task</li>
							<li><code>list</code> - Show all tasks</li>
							<li><code>delete [task_id]</code> - Remove a task</li>
							<li><code>meeting [title]</code> - Schedule a Webex meeting</li>
						</ul>
					</div>
				</body>
			</html>
			""")

		@self.app.post("/create-meeting")
		async def create_meeting(request: Request):
			"""Create a meeting using user's OAuth token"""
			form_data = await request.form()
			user_id = form_data.get('user_id')
			title = form_data.get('title', 'Botper Test Meeting')
			
			if not user_id or user_id not in self.user_tokens:
				return HTMLResponse("<h1>Error</h1><p>User not authorized. Please authorize first.</p>", status_code=400)
			
			try:
				# Get user's access token
				access_token = self.user_tokens[user_id]['access_token']
				
				# Calculate meeting time (1 hour from now)
				from datetime import datetime, timedelta
				import pytz
				
				now = datetime.now(pytz.UTC)
				start_time = now + timedelta(minutes=5)  # Start in 5 minutes
				end_time = start_time + timedelta(hours=1)  # 1 hour duration
				
				meeting_details = {
					'title': title,
					'start': start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
					'end': end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
					'timezone': 'UTC',
					'enabledAutoRecordMeeting': False,
					'allowAnyUserToBeCoHost': False
				}
				
				# Create meeting using user's OAuth token
				meeting = self.oauth_handler.create_meeting(access_token, meeting_details)
				
				print(f"Meeting created successfully: {meeting.get('webLink', 'No link')}")
				
				# Create task with meeting link automatically
				meeting_link = meeting.get('webLink', 'No link available')
				task = {
					"title": f"📞 {title}",
					"completed": False,
					"type": "meeting",
					"meeting_link": meeting_link,
					"platform": "webex",
					"start_time": start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
				}
				
				try:
					task_result = self.task_manager.create_task(task)
					print(f"✅ Task created automatically for meeting: {title}")
				except Exception as task_error:
					print(f"❌ Failed to create task for meeting: {task_error}")
				
				# Return success page
				return HTMLResponse(f"""
				<html>
					<head><title>Meeting Created Successfully</title></head>
					<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
						<h1 style="color: #00BCF2;">🎉 Meeting Created Successfully!</h1>
						<div style="background-color: #f0f8ff; padding: 20px; border-radius: 10px; margin: 20px 0;">
							<h2>📞 {meeting.get('title', 'Meeting')}</h2>
							<p><strong>Meeting ID:</strong> {meeting.get('meetingNumber', 'N/A')}</p>
							<p><strong>Start Time:</strong> {start_time.strftime('%Y-%m-%d %H:%M UTC')}</p>
							<p><strong>Join Link:</strong> <a href="{meeting.get('webLink', '#')}" target="_blank">{meeting.get('webLink', 'No link available')}</a></p>
						</div>
						
						<div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0;">
							<h3>🤖 What Happens Next:</h3>
							<p>Your bot will automatically receive a webhook about this meeting and create a task for it!</p>
							<p>Check your Webex spaces where the bot is present to see the automatic task creation.</p>
						</div>
						
						<p>
							<a href="/" style="color: #00BCF2;">← Back to Home</a> | 
							<a href="{meeting.get('webLink', '#')}" target="_blank" style="color: #00BCF2;">Join Meeting →</a>
						</p>
					</body>
				</html>
				""")
				
			except Exception as e:
				print(f"Error creating meeting: {e}")
				return HTMLResponse(f"""
				<html>
					<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
						<h1 style="color: red;">❌ Meeting Creation Failed</h1>
						<p>Error: {str(e)}</p>
						<p><a href="/" style="color: #00BCF2;">← Back to Home</a></p>
					</body>
				</html>
				""", status_code=500)

	def send_greeting(self, room_id):
		print(f"Sending greeting to room: {room_id}")
		greeting = "Hello! This is Botper! I will help you manage your tasks and meetings."
		menu = "🎯 COMMANDS:\n\n📋 Tasks:\n- task <description>\n- list\n- delete <task id>\n\n📞 Meetings:\n- meeting <title> - Schedule a meeting\n\n💡 Examples:\n- 'task Prepare presentation for meeting'\n- 'meeting Team Standup'"
		self.send_message(room_id, f"{greeting}\n\n{menu}")

	def start(self, port=8000):
		self.current_port = port  # Store current port for OAuth URL generation
		import uvicorn
		uvicorn.run(self.app, host="0.0.0.0", port=port)
		
	def start_on_port(self, port):
		self.start(port=port)

	def send_message(self, room_id, message, card=None):
		try:
			print(f"Sending message to room {room_id}: {message}")
			if card:
				result = self.api.messages.create(roomId=room_id, text=message, attachments=[{"contentType": "application/vnd.microsoft.card.adaptive", "content": card}])
			else:
				result = self.api.messages.create(roomId=room_id, text=message)
			print(f"Message sent successfully: {result.id}")
		except Exception as e:
			print(f"Error sending message: {e}")

	def handle_task_command(self, command, room_id, data=None):
		if command == "create":
			task = {"title": data["title"], "completed": False}
			result = self.task_manager.create_task(task)
			self.send_message(room_id, f"OK: Task created: {data['title']}")
			self.handle_task_command("list", room_id)
		elif command == "list":
			tasks = self.task_manager.list_tasks()
			card = format_task_card(tasks, platform="webex")
			self.send_message(room_id, "Here are your tasks:", card=card)
		elif command == "delete":
			try:
				self.task_manager.delete_task(data["task_id"])
				self.send_message(room_id, "OK: Task deleted successfully!")
				self.handle_task_command("list", room_id)
			except Exception as e:
				self.send_message(room_id, f"ERROR: Error deleting task: {e}")

	def handle_meeting_command(self, command, room_id, data=None):
		"""Handle meeting-related commands (schedule, list, etc.)."""
		if command == "schedule":
			meeting_title = data.get("title", "New Meeting") if data else "New Meeting"
			self.redirect_to_webex_meeting(room_id, data.get("person_id") if data else None, meeting_title)
		elif command == "list":
			# List existing meeting tasks
			tasks = self.task_manager.list_tasks()
			meeting_tasks = [task for task in tasks if task.get("type") == "meeting"]
			if meeting_tasks:
				card = format_task_card(meeting_tasks, platform="webex")
				self.send_message(room_id, "Here are your scheduled meetings:", card=card)
			else:
				self.send_message(room_id, "No meetings scheduled yet. Create a meeting in Webex and I'll automatically detect it!")
		else:
			self.send_message(room_id, "Available meeting commands: schedule, list")

	def handle_meeting_request(self, room_id, person_id, person_email, meeting_title):
		"""Handle meeting creation request - try OAuth first, fallback to redirect"""
		# First, check if user has authorized OAuth
		user_token = None
		for user_id, token_data in self.user_tokens.items():
			if token_data.get('user_info', {}).get('emails', [None])[0] == person_email:
				user_token = token_data
				break
		
		if user_token:
			# User has OAuth token - create meeting directly
			try:
				from datetime import datetime, timedelta
				import pytz
				
				now = datetime.now(pytz.UTC)
				start_time = now + timedelta(minutes=5)  # Start in 5 minutes
				end_time = start_time + timedelta(hours=1)  # 1 hour duration
				
				meeting_details = {
					'title': meeting_title,
					'start': start_time.isoformat(),
					'end': end_time.isoformat(),
					'timezone': 'UTC',
					'enabledAutoRecordMeeting': False,
					'allowAnyUserToBeCoHost': False
				}
				
				# Create meeting using user's OAuth token
				meeting = self.oauth_handler.create_meeting(user_token['access_token'], meeting_details)
				
				# Create task with meeting link automatically
				meeting_link = meeting.get('webLink', 'No link available')
				task = {
					"title": f"📞 {meeting_title}",
					"completed": False,
					"type": "meeting",
					"meeting_link": meeting_link,
					"platform": "webex",
					"start_time": start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
				}
				
				try:
					task_result = self.task_manager.create_task(task)
					print(f"✅ Task created automatically for meeting: {meeting_title}")
				except Exception as task_error:
					print(f"❌ Failed to create task for meeting: {task_error}")
				
				self.send_message(room_id, f"✅ **Meeting Created Successfully!**\n\n📞 **{meeting_title}**\n🔗 **Link:** {meeting_link}\n⏰ **Starts:** {start_time.strftime('%H:%M UTC')}\n\n🤖 Task created automatically! Use 'list' to see it.")
				
			except Exception as e:
				print(f"OAuth meeting creation failed: {e}")
				self.send_message(room_id, f"❌ Failed to create meeting via OAuth: {e}\n\nFalling back to manual method...")
				self.redirect_to_webex_meeting(room_id, person_id, meeting_title)
		else:
			# No OAuth token - offer authorization or use redirect method
			port = getattr(self, 'current_port', 8001)  # Use current port or default to 8001
			self.send_message(room_id, f"🔐 **Enhanced Meeting Creation Available!**\n\nFor automatic meeting creation, authorize Botper:\n👉 Visit: http://localhost:{port}/auth/webex\n\n⏭️ Meanwhile, I'll redirect you to create the meeting manually...")
			self.redirect_to_webex_meeting(room_id, person_id, meeting_title)

	def handle_modify_task(self, room_id, task_id, current_title):
		"""Handle modify task action - create an input form"""
		try:
			# Create an Adaptive Card for task modification
			modify_card = {
				"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
				"type": "AdaptiveCard",
				"version": "1.3",
				"body": [
					{
						"type": "TextBlock",
						"text": "Modify Task",
						"weight": "Bolder",
						"size": "Large",
						"horizontalAlignment": "Center"
					},
					{
						"type": "TextBlock",
						"text": "Current title:",
						"weight": "Bolder"
					},
					{
						"type": "TextBlock",
						"text": current_title,
						"color": "Attention",
						"isSubtle": True
					},
					{
						"type": "Input.Text",
						"id": "new_title",
						"placeholder": "Enter new task title...",
						"value": current_title
					}
				],
				"actions": [
					{
						"type": "Action.Submit",
						"title": "Save Changes",
						"data": {
							"action": "update",
							"task_id": task_id
						}
					},
					{
						"type": "Action.Submit", 
						"title": "Cancel",
						"data": {
							"action": "cancel"
						}
					}
				]
			}
			
			self.send_message(room_id, "Please modify your task:", card=modify_card)
			
		except Exception as e:
			self.send_message(room_id, f"ERROR: Error creating modify form: {e}")

	def handle_update_task(self, room_id, task_id, new_title):
		"""Handle the actual task update"""
		try:
			if not new_title or not new_title.strip():
				self.send_message(room_id, "ERROR: Task title cannot be empty!")
				return
				
			update_result = self.task_manager.update_task(task_id, {"title": new_title.strip()})
			if update_result.modified_count > 0:
				self.send_message(room_id, f"OK: Task updated successfully!")
				self.handle_task_command("list", room_id)
			else:
				self.send_message(room_id, "ERROR: Task not found or no changes made.")
				
		except Exception as e:
			self.send_message(room_id, f"ERROR: Error updating task: {e}")

	def redirect_to_webex_meeting(self, room_id, person_id, meeting_title):
		"""Redirect user to Webex native scheduler with automatic detection"""
		# Get person email for meeting matching
		try:
			person = self.api.people.get(person_id)
			person_email = person.emails[0] if person.emails else "unknown@example.com"
		except:
			person_email = "unknown@example.com"
		
		# Store the meeting request for automatic matching
		session_key = f"{person_email}_{meeting_title.lower().strip()}"
		self.pending_meeting_tasks[session_key] = {
			"title": meeting_title,
			"room_id": room_id,
			"person_id": person_id,
			"person_email": person_email,
			"timestamp": __import__('time').time()
		}
		
		# Try to create the meeting automatically using Webex API
		try:
			# Create meeting using Webex Meetings API
			import requests
			from datetime import datetime, timedelta
			
			# Get access token from environment
			access_token = os.getenv('WEBEX_ACCESS_TOKEN')
			
			# Set meeting for 1 hour from now as default
			start_time = datetime.now() + timedelta(hours=1)
			
			meeting_data = {
				"title": meeting_title,
				"start": start_time.isoformat() + "Z",
				"end": (start_time + timedelta(hours=1)).isoformat() + "Z",
				"timezone": "UTC",
				"enabledAutoRecordMeeting": False,
				"allowAnyUserToBeCoHost": False
			}
			
			headers = {
				"Authorization": f"Bearer {access_token}",
				"Content-Type": "application/json"
			}
			
			# Create meeting via API
			response = requests.post(
				"https://webexapis.com/v1/meetings",
				json=meeting_data,
				headers=headers
			)
			
			if response.status_code == 200:
				meeting_info = response.json()
				meeting_link = meeting_info.get("webLink", "")
				
				if meeting_link:
					# Create task with the meeting link
					task = {
						"title": f"📞 {meeting_title}",
						"completed": False,
						"type": "meeting", 
						"meeting_link": meeting_link,
						"platform": "webex"
					}
					
					self.task_manager.create_task(task)
					
					# Send success message with meeting details
					success_card = {
						"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
						"type": "AdaptiveCard",
						"version": "1.3",
						"body": [
							{
								"type": "TextBlock",
								"text": "✅ Meeting Created Successfully!",
								"weight": "Bolder",
								"size": "Large",
								"color": "Good"
							},
							{
								"type": "TextBlock",
								"text": f"📞 {meeting_title}",
								"weight": "Bolder"
							},
							{
								"type": "TextBlock",
								"text": f"🕐 {start_time.strftime('%m/%d/%Y at %I:%M %p')}",
								"isSubtle": True
							},
							{
								"type": "TextBlock",
								"text": f"🔗 [Join Meeting]({meeting_link})",
								"wrap": True
							}
						]
					}
					
					self.send_message(room_id, f"✅ **Meeting created and task added automatically!**", card=success_card)
					return
			
		except Exception as e:
			print(f"Error creating meeting automatically: {e}")
		
		# Fallback: If automatic creation fails, show manual instructions
		fallback_card = {
			"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
			"type": "AdaptiveCard",
			"version": "1.3",
			"body": [
				{
					"type": "TextBlock",
					"text": "🎬 Schedule Meeting Manually",
					"weight": "Bolder",
					"size": "Large"
				},
				{
					"type": "TextBlock",
					"text": f"Meeting: {meeting_title}",
					"weight": "Bolder",
					"color": "Accent"
				},
				{
					"type": "TextBlock",
					"text": "⚠️ Automatic creation temporarily unavailable. Please schedule manually in Webex app.",
					"wrap": True,
					"color": "Warning"
				}
			]
		}
		
		self.send_message(room_id, f"🎬 **Please schedule '{meeting_title}' manually**", card=fallback_card)

	def handle_meeting_link_save(self, room_id, person_id, meeting_title, meeting_link):
		"""Save the meeting as a task with the provided link"""
		session_key = f"{room_id}_{person_id}"
		
		try:
			# Validate meeting link
			if not meeting_link or not ("webex.com" in meeting_link or "meet" in meeting_link):
				self.send_message(room_id, "❌ Please provide a valid Webex meeting link.")
				return
			
			# Create task with meeting link
			task = {
				"title": f"📞 {meeting_title}",
				"completed": False,
				"type": "meeting",
				"meeting_link": meeting_link,
				"platform": "webex"
			}
			
			result = self.task_manager.create_task(task)
			
			# Clean up session
			if session_key in self.pending_meeting_tasks:
				del self.pending_meeting_tasks[session_key]
			
			# Send confirmation
			confirmation = f"✅ **MEETING TASK CREATED SUCCESSFULLY!**\n\n"
			confirmation += f"📅 **Meeting:** {meeting_title}\n"
			confirmation += f"🔗 **Link:** {meeting_link}\n\n"
			confirmation += f"💾 **Saved to tasks** - Use 'list' to see all your tasks\n\n"
			confirmation += f"🎯 **Your meeting is ready!** Participants can join using the link above."
			
			self.send_message(room_id, confirmation)
			
			# Show updated task list
			self.handle_task_command("list", room_id)
			
		except Exception as e:
			self.send_message(room_id, f"❌ Error saving meeting: {e}")
			if session_key in self.pending_meeting_tasks:
				del self.pending_meeting_tasks[session_key]

	def handle_meeting_webhook(self, meeting_data):
		"""Handle automatic meeting detection from webhook"""
		try:
			# Extract meeting details from webhook data
			meeting_id = meeting_data.get('id', '')
			meeting_title = meeting_data.get('title', 'Unnamed Meeting')
			host_email = meeting_data.get('hostEmail', '')
			web_link = meeting_data.get('webLink', '')
			start_time = meeting_data.get('start', '')
			
			print(f"Processing meeting webhook - Title: '{meeting_title}', Host: {host_email}")
			
			# Look for matching pending meeting requests
			matching_request = None
			session_key_to_remove = None
			
			# Clean up old pending requests (older than 1 hour)
			current_time = __import__('time').time()
			keys_to_remove = []
			for key, request in self.pending_meeting_tasks.items():
				if isinstance(request, dict) and current_time - request.get('timestamp', 0) > 3600:
					keys_to_remove.append(key)
			
			for key in keys_to_remove:
				del self.pending_meeting_tasks[key]
			
			# Find matching request by host email and title similarity
			for session_key, request in self.pending_meeting_tasks.items():
				if not isinstance(request, dict):
					continue
					
				if (request.get('person_email', '').lower() == host_email.lower() and 
					self._titles_match(request.get('title', ''), meeting_title)):
					matching_request = request
					session_key_to_remove = session_key
					break
			
			if matching_request:
				# Create automatic task for matched meeting
				self._create_automatic_meeting_task(matching_request, meeting_data)
				
				# Clean up the pending request
				if session_key_to_remove:
					del self.pending_meeting_tasks[session_key_to_remove]
			else:
				print(f"No matching request found for meeting: '{meeting_title}' by {host_email}")
				
		except Exception as e:
			print(f"Error handling meeting webhook: {e}")

	def _titles_match(self, requested_title, actual_title):
		"""Check if meeting titles match (fuzzy matching)"""
		if not requested_title or not actual_title:
			return False
		
		# Normalize titles for comparison
		req_norm = requested_title.lower().strip()
		act_norm = actual_title.lower().strip()
		
		# Exact match
		if req_norm == act_norm:
			return True
		
		# Check if requested title is contained in actual title
		if req_norm in act_norm or act_norm in req_norm:
			return True
		
		# Check for word overlap (at least 2 common words)
		req_words = set(req_norm.split())
		act_words = set(act_norm.split())
		common_words = req_words.intersection(act_words)
		
		return len(common_words) >= min(2, len(req_words), len(act_words))

	def _create_automatic_meeting_task(self, request, meeting_data):
		"""Create a task automatically from webhook data"""
		try:
			meeting_title = request['title']
			room_id = request['room_id']
			web_link = meeting_data.get('webLink', 'No link available')
			start_time = meeting_data.get('start', '')
			
			# Create task with meeting details
			task = {
				"title": f"📞 {meeting_title}",
				"completed": False,
				"type": "meeting",
				"meeting_link": web_link,
				"platform": "webex",
				"start_time": start_time
			}
			
			result = self.task_manager.create_task(task)
			
			# Send automatic confirmation
			confirmation = f"🎉 **MEETING AUTOMATICALLY DETECTED!**\n\n"
			confirmation += f"📅 **Meeting:** {meeting_title}\n"
			confirmation += f"🔗 **Link:** {web_link}\n"
			if start_time:
				try:
					from datetime import datetime
					dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
					formatted_time = dt.strftime('%m/%d/%Y at %I:%M %p UTC')
					confirmation += f"⏰ **Time:** {formatted_time}\n"
				except:
					pass
			confirmation += f"\n✅ **Automatically added to your tasks!**\n"
			confirmation += f"💡 Use 'list' to see all your tasks."
			
			self.send_message(room_id, confirmation)
			
			# Show updated task list
			self.handle_task_command("list", room_id)
			
			print(f"✅ Automatically created task for meeting: {meeting_title}")
			
		except Exception as e:
			print(f"Error creating automatic meeting task: {e}")
			# Send error message to user
			try:
				self.send_message(request['room_id'], f"❌ Meeting detected but failed to create task: {e}")
			except:
				pass

	def start_calendar_monitoring(self):
		"""Start monitoring calendar events for Webex meetings - DISABLED"""
		# NOTE: Calendar monitoring disabled because bot tokens don't have meeting API scopes
		# This feature requires user OAuth tokens with meeting:schedules_read scope
		print("📝 Calendar monitoring disabled - requires OAuth user tokens")
		return
		
		# Original code kept for reference but disabled:
		# import threading
		# import time
		# 
		# def calendar_monitor():
		# 	print("🗓️ Starting Webex calendar monitoring...")
		# 	while True:
		# 		try:
		# 			self.check_calendar_events()
		# 			time.sleep(30)  # Check every 30 seconds
		# 		except Exception as e:
		# 			print(f"❌ Calendar monitoring error: {e}")
		# 			time.sleep(60)  # Wait longer on error
		
		# Start monitoring in background thread
		# monitor_thread = threading.Thread(target=calendar_monitor, daemon=True)
		# monitor_thread.start()

	# def check_calendar_events(self):
	# 	"""Check calendar for new Webex meetings and create tasks"""
	# 	import requests
	# 	from datetime import datetime, timedelta
	# 	
	# 	try:
	# 		print("🔍 Checking for calendar events...")
	# 		
	# 		# Get events from Webex Events API
	# 		headers = {
	# 			"Authorization": f"Bearer {self.access_token}",
	# 			"Content-Type": "application/json"
	# 		}
	# 		
	# 		# Get meetings for the next 7 days
	# 		from_date = datetime.now().isoformat() + "Z" 
	# 		to_date = (datetime.now() + timedelta(days=7)).isoformat() + "Z"
	# 		
	# 		print(f"📅 Searching meetings from {from_date} to {to_date}")
	# 		
	# 		# Try Webex Meetings API (most likely to work)
	# 		meetings_url = f"https://webexapis.com/v1/meetings"
	# 		params = {
	# 			"from": from_date,
	# 			"to": to_date,
	# 			"max": 100
	# 		}
	# 		
	# 		print(f"🌐 Calling: {meetings_url}")
	# 		response = requests.get(meetings_url, headers=headers, params=params)
	# 		print(f"📡 Response status: {response.status_code}")
	# 		
	# 		if response.status_code == 200:
	# 			meetings_data = response.json()
	# 			meetings = meetings_data.get('items', [])
	# 			print(f"📋 Found {len(meetings)} meetings")
	# 			
	# 			for meeting in meetings:
	# 				print(f"🎯 Processing meeting: {meeting.get('title', 'No title')}")
	# 				self.process_meeting_event(meeting)
	# 		else:
	# 			print(f"❌ Meetings API failed with status {response.status_code}")
	# 			print(f"📄 Response: {response.text[:200]}...")
	# 			
	# 			# Try alternative: Get user's own meetings
	# 			alt_url = "https://webexapis.com/v1/meetings"
	# 			alt_response = requests.get(alt_url, headers=headers)
	# 			print(f"🔄 Alternative API status: {alt_response.status_code}")
	# 			
	# 			if alt_response.status_code == 200:
	# 				alt_data = alt_response.json()
	# 				alt_meetings = alt_data.get('items', [])
	# 				print(f"📋 Alternative found {len(alt_meetings)} meetings")
	# 				
	# 				for meeting in alt_meetings:
	# 					self.process_meeting_event(meeting)
	# 			
	# 	except Exception as e:
	# 		print(f"❌ Error checking calendar events: {e}")
	# 		import traceback
	# 		print(f"🔍 Full error: {traceback.format_exc()}")

	# def process_calendar_event(self, event):
	# 	"""Process a calendar event and create task if it's a Webex meeting"""
	# 	try:
	# 		event_id = event.get('id')
	# 		event_title = event.get('title', 'Webex Meeting')
	# 		event_start = event.get('start')
	# 		web_link = event.get('webLink')
	# 		
	# 		# Check if we've already processed this event
	# 		if event_id in self.processed_events:
	# 			return
	# 		
	# 		# Only process if it has a Webex link
	# 		if web_link and 'webex.com' in web_link:
	# 			# Mark as processed
	# 			self.processed_events.add(event_id)
	# 			
	# 			# Create task
	# 			task = {
	# 				"title": f"Scheduled meeting ({event_title})",
	# 				"completed": False,
	# 				"type": "meeting",
	# 				"meeting_link": web_link,
	# 				"platform": "webex",
	# 				"meeting_time": event_start
	# 			}
	# 			
	# 			result = self.task_manager.create_task(task)
	# 			print(f"✅ Auto-created task from calendar: {event_title}")
	# 			
	# 	except Exception as e:
	# 		print(f"❌ Error processing calendar event: {e}")

	# def process_meeting_event(self, meeting):
	# 	"""Process a meeting event from meetings API"""
	# 	try:
	# 		meeting_id = meeting.get('id')
	# 		meeting_title = meeting.get('title', 'Webex Meeting')
	# 		meeting_start = meeting.get('start')
	# 		web_link = meeting.get('webLink')
	# 		
	# 		print(f"🔍 Processing meeting ID: {meeting_id}")
	# 		print(f"📝 Title: {meeting_title}")
	# 		print(f"🔗 Link: {web_link}")
	# 		print(f"⏰ Start: {meeting_start}")
	# 		
	# 		# Check if we've already processed this meeting
	# 		if meeting_id in self.processed_events:
	# 			print(f"⏭️ Already processed meeting: {meeting_id}")
	# 			return
	# 		
	# 		# Mark as processed
	# 		self.processed_events.add(meeting_id)
	# 		print(f"✅ Marked as processed: {meeting_id}")
	# 		
	# 		# Create task
	# 		task = {
	# 			"title": f"Scheduled meeting ({meeting_title})",
	# 			"completed": False,
	# 			"type": "meeting",
	# 			"meeting_link": web_link,
	# 			"platform": "webex",
	# 			"meeting_time": meeting_start
	# 		}
	# 		
	# 		print(f"📋 Creating task: {task['title']}")
	# 		result = self.task_manager.create_task(task)
	# 		print(f"🎉 Auto-created task from meeting API: {meeting_title}")
	# 		
	# 	except Exception as e:
	# 		print(f"❌ Error processing meeting: {e}")
	# 		import traceback
	# 		print(f"🔍 Full error: {traceback.format_exc()}")