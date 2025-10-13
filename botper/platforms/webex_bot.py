import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from webexteamssdk import WebexTeamsAPI
from fastapi import FastAPI, Request
from core.base_bot import BaseBot
from core.tasks import TaskManager
from utils.helpers import format_task_card
from dotenv import load_dotenv

load_dotenv()

WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN")

class WebexBot(BaseBot):
	def __init__(self):
		self.api = WebexTeamsAPI(access_token=WEBEX_BOT_TOKEN)
		self.access_token = WEBEX_BOT_TOKEN
		self.task_manager = TaskManager()
		self.app = FastAPI()
		self.processed_messages = set()  # Track processed message IDs to avoid duplicates
		self.pending_meeting_tasks = {}  # Track meeting title for linking task
		self.setup_routes()

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
					elif action_data.get('action') == 'save_meeting_link':
						meeting_title = action_data.get('meeting_title', '')
						meeting_link = action_data.get('meeting_link', '').strip()
						self.handle_meeting_link_save(room_id, person_id, meeting_title, meeting_link)
						
				except Exception as e:
					print(f"Error processing action {action_id}: {e}")
					return {"status": "error", "message": f"Could not process action: {e}"}
				
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
					return {"status": "error", "message": "Could not verify bot identity"}
				
				try:
					msg = self.api.messages.get(message_id)
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
							self.redirect_to_webex_meeting(room_id, person_id, meeting_title)
						else:
							self.send_message(room_id, "Please provide a meeting title. Example: 'schedule meeting Team Standup'")
				except Exception as e:
					print(f"Error processing message {message_id}: {e}")
					return {"status": "error", "message": f"Could not process message: {e}"}
				
			return {"status": "ok"}

	def send_greeting(self, room_id):
		print(f"Sending greeting to room: {room_id}")
		greeting = "Hello! This is Botper! I will help you set up your tasks and schedule your Webex meetings!"
		menu = "🎯 COMMANDS:\n\n📋 Tasks:\n- task <description>\n- list\n- delete <task id>\n\n🎬 Meetings:\n- schedule meeting <title> (redirects to Webex scheduler)\n\n💡 Examples:\n- 'schedule meeting Team Standup'\n- 'task Prepare presentation for meeting'"
		self.send_message(room_id, f"{greeting}\n\n{menu}")

	def start(self, port=8000):
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
		"""Redirect user to Webex native scheduler and collect meeting link"""
		# Store the meeting title for later linking
		session_key = f"{room_id}_{person_id}"
		self.pending_meeting_tasks[session_key] = meeting_title
		
		# Create simple card for meeting link collection
		meeting_card = {
			"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
			"type": "AdaptiveCard",
			"version": "1.3",
			"body": [
				{
					"type": "TextBlock",
					"text": "🎬 Schedule Webex Meeting",
					"weight": "Bolder",
					"size": "Large",
					"horizontalAlignment": "Center"
				},
				{
					"type": "TextBlock",
					"text": f"Meeting: {meeting_title}",
					"weight": "Bolder",
					"color": "Accent"
				},
				{
					"type": "TextBlock",
					"text": "Follow these steps:",
					"weight": "Bolder"
				},
				{
					"type": "TextBlock",
					"text": "1. **Open Webex app** on your device\n2. Go to **'Meetings'** (below 'Messaging')\n3. Click **'Schedule a meeting'**\n4. Set your meeting details\n5. **Copy the meeting link** after creating\n6. **Paste the link below** and click 'Save'",
					"wrap": True
				},
				{
					"type": "TextBlock",
					"text": "Meeting Link:",
					"weight": "Bolder"
				},
				{
					"type": "Input.Text",
					"id": "meeting_link",
					"placeholder": "Paste your Webex meeting link here...",
					"isMultiline": False
				}
			],
			"actions": [
				{
					"type": "Action.Submit",
					"title": "💾 Save Meeting & Link",
					"data": {
						"action": "save_meeting_link",
						"meeting_title": meeting_title
					}
				}
			]
		}
		
		self.send_message(room_id, f"Let's schedule your '{meeting_title}' meeting using Webex's native scheduler:", card=meeting_card)

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