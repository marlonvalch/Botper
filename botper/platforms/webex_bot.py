
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from webexteamssdk import WebexTeamsAPI
from fastapi import FastAPI, Request
from core.base_bot import BaseBot
from core.tasks import TaskManager
from core.meetings import MeetingManager
from core.webex_meetings import WebexMeetingsSDK
from utils.helpers import format_task_card
from dotenv import load_dotenv

load_dotenv()

WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN")

class WebexBot(BaseBot):
	def __init__(self):
		self.api = WebexTeamsAPI(access_token=WEBEX_BOT_TOKEN)
		self.meetings_sdk = WebexMeetingsSDK(access_token=WEBEX_BOT_TOKEN)
		self.access_token = WEBEX_BOT_TOKEN
		self.task_manager = TaskManager()
		self.meeting_manager = MeetingManager()
		self.app = FastAPI()
		self.processed_messages = set()  # Track processed message IDs to avoid duplicates
		self.pending_meetings = {}  # Track ongoing meeting creation sessions
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
					elif action_data.get('action') == 'schedule_meeting':
						self.handle_meeting_form_submission(room_id, person_id, action_data)
					elif action_data.get('action') == 'cancel_meeting':
						self.cancel_meeting_creation(room_id, person_id)
						
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
					elif text == "meetings":
						self.handle_meeting_command("list", room_id)
					elif text.startswith("delete"):
						task_id = msg.text[7:].strip()
						self.handle_task_command("delete", room_id, {"task_id": task_id})
					elif text.startswith("schedule meeting") or text.startswith("meeting"):
						meeting_title = msg.text.replace("schedule meeting", "").replace("meeting", "").strip()
						if meeting_title:
							self.start_meeting_creation(room_id, person_id, meeting_title, person_email)
						else:
							self.send_message(room_id, "Please provide a meeting title. Example: 'schedule meeting Team Standup'")
					elif text.startswith("instant meeting"):
						meeting_title = msg.text.replace("instant meeting", "").strip()
						if meeting_title:
							self.create_instant_meeting(room_id, person_email, meeting_title)
						else:
							self.send_message(room_id, "Please provide a meeting title. Example: 'instant meeting Quick Sync'")
					elif text == "my meetings":
						self.list_user_meetings(room_id, person_email)
				except Exception as e:
					print(f"Error processing message {message_id}: {e}")
					return {"status": "error", "message": f"Could not process message: {e}"}
				
			return {"status": "ok"}

	def send_greeting(self, room_id):
		print(f"Sending greeting to room: {room_id}")
		greeting = "Hello! This is Botper! I will help you set up your tasks and schedule your Webex meetings!"
		menu = "🎯 COMMANDS:\n\n📋 Tasks:\n- task <description>\n- list\n- delete <task id>\n\n🎬 Meetings:\n- schedule meeting <title> (interactive form)\n- instant meeting <title> (starts now)\n- meetings (bot's database)\n- my meetings (your Webex meetings)\n\n💡 Examples:\n- 'schedule meeting Team Standup'\n- 'instant meeting Quick Sync'\n- 'my meetings'"
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

	def handle_meeting_command(self, command, room_id, data=None):
		if command == "list":
			meetings = self.meeting_manager.list_meetings()
			if meetings:
				meeting_list = "Scheduled Meetings:\n"
				for i, meeting in enumerate(meetings, 1):
					status = "SCHEDULED" if meeting.get("status") == "scheduled" else "COMPLETED"
					date_str = meeting.get('date', 'No date set')
					time_str = meeting.get('time', 'No time set')
					timezone_str = meeting.get('timezone', 'No timezone')
					
					# Handle both old format (space_url) and new format (meeting_url)
					meeting_url = meeting.get('webex_meeting_url') or meeting.get('webex_space_url', '')
					meeting_id = meeting.get('webex_meeting_id', '')
					meeting_password = meeting.get('webex_meeting_password', '')
					
					meeting_list += f"{i}. {status} - {meeting['title']}\n"
					meeting_list += f"   Date: {date_str}\n"
					meeting_list += f"   Time: {time_str} ({timezone_str})\n"
					
					# Show host information if available
					host_email = meeting.get('host_email', '')
					if host_email:
						meeting_list += f"   Host: {host_email}\n"
					
					if meeting_url and meeting_url != "Could not create Webex space" and meeting_url != "Could not create Webex meeting":
						if meeting_id and not meeting_id.startswith('space_'):
							# Real Webex meeting
							meeting_list += f"   JOIN MEETING: {meeting_url}\n"
							if meeting_password:
								meeting_list += f"   Password: {meeting_password}\n"
							meeting_list += f"   Meeting ID: {meeting_id}\n"
						else:
							# Webex space
							meeting_list += f"   Webex Space: {meeting_url}\n"
					else:
						meeting_list += f"   Create meeting at: https://webex.com/\n"
					meeting_list += "\n"
				self.send_message(room_id, meeting_list)
			else:
				self.send_message(room_id, "No meetings scheduled yet.\n\nUse 'schedule meeting <title>' to create one!")

	def start_meeting_creation(self, room_id, person_id, title, person_email):
		"""Start the interactive meeting creation process"""
		session_key = f"{room_id}_{person_id}"
		self.pending_meetings[session_key] = {
			"title": title,
			"step": "details",
			"room_id": room_id,
			"person_id": person_id,
			"host_email": person_email
		}
		
		self.show_meeting_form(room_id, title)

	def show_meeting_form(self, room_id, title):
		"""Show the meeting scheduling form"""
		import datetime
		today = datetime.date.today()
		
		meeting_form = {
			"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
			"type": "AdaptiveCard",
			"version": "1.3",
			"body": [
				{
					"type": "TextBlock",
					"text": "Schedule Webex Meeting",
					"weight": "Bolder",
					"size": "Large",
					"horizontalAlignment": "Center"
				},
				{
					"type": "TextBlock",
					"text": f"Meeting: {title}",
					"weight": "Bolder",
					"color": "Accent"
				},
				{
					"type": "TextBlock",
					"text": "Date (MM/DD/YYYY):",
					"weight": "Bolder"
				},
				{
					"type": "Input.Date",
					"id": "meeting_date",
					"value": today.strftime('%Y-%m-%d')
				},
				{
					"type": "TextBlock",
					"text": "Time:",
					"weight": "Bolder"
				},
				{
					"type": "Input.ChoiceSet",
					"id": "meeting_time",
					"style": "compact",
					"value": "09:00",
					"choices": [
						{"title": "12:00 AM", "value": "00:00"},
						{"title": "12:30 AM", "value": "00:30"},
						{"title": "01:00 AM", "value": "01:00"},
						{"title": "01:30 AM", "value": "01:30"},
						{"title": "02:00 AM", "value": "02:00"},
						{"title": "02:30 AM", "value": "02:30"},
						{"title": "03:00 AM", "value": "03:00"},
						{"title": "03:30 AM", "value": "03:30"},
						{"title": "04:00 AM", "value": "04:00"},
						{"title": "04:30 AM", "value": "04:30"},
						{"title": "05:00 AM", "value": "05:00"},
						{"title": "05:30 AM", "value": "05:30"},
						{"title": "06:00 AM", "value": "06:00"},
						{"title": "06:30 AM", "value": "06:30"},
						{"title": "07:00 AM", "value": "07:00"},
						{"title": "07:30 AM", "value": "07:30"},
						{"title": "08:00 AM", "value": "08:00"},
						{"title": "08:30 AM", "value": "08:30"},
						{"title": "09:00 AM", "value": "09:00"},
						{"title": "09:30 AM", "value": "09:30"},
						{"title": "10:00 AM", "value": "10:00"},
						{"title": "10:30 AM", "value": "10:30"},
						{"title": "11:00 AM", "value": "11:00"},
						{"title": "11:30 AM", "value": "11:30"},
						{"title": "12:00 PM", "value": "12:00"},
						{"title": "12:30 PM", "value": "12:30"},
						{"title": "01:00 PM", "value": "13:00"},
						{"title": "01:30 PM", "value": "13:30"},
						{"title": "02:00 PM", "value": "14:00"},
						{"title": "02:30 PM", "value": "14:30"},
						{"title": "03:00 PM", "value": "15:00"},
						{"title": "03:30 PM", "value": "15:30"},
						{"title": "04:00 PM", "value": "16:00"},
						{"title": "04:30 PM", "value": "16:30"},
						{"title": "05:00 PM", "value": "17:00"},
						{"title": "05:30 PM", "value": "17:30"},
						{"title": "06:00 PM", "value": "18:00"},
						{"title": "06:30 PM", "value": "18:30"},
						{"title": "07:00 PM", "value": "19:00"},
						{"title": "07:30 PM", "value": "19:30"},
						{"title": "08:00 PM", "value": "20:00"},
						{"title": "08:30 PM", "value": "20:30"},
						{"title": "09:00 PM", "value": "21:00"},
						{"title": "09:30 PM", "value": "21:30"},
						{"title": "10:00 PM", "value": "22:00"},
						{"title": "10:30 PM", "value": "22:30"},
						{"title": "11:00 PM", "value": "23:00"},
						{"title": "11:30 PM", "value": "23:30"}
					]
				},
				{
					"type": "TextBlock",
					"text": "Timezone:",
					"weight": "Bolder"
				},
				{
					"type": "Input.ChoiceSet",
					"id": "timezone",
					"style": "compact",
					"value": "UTC+00:00",
					"choices": [
						{"title": "GMT-12:00, Dateline (Eniwetok)", "value": "UTC-12:00"},
						{"title": "GMT-11:00, Samoa (Samoa)", "value": "UTC-11:00"},
						{"title": "GMT-10:00, Hawaii (Honolulu)", "value": "UTC-10:00"},
						{"title": "GMT-09:00, Alaska (Anchorage)", "value": "UTC-09:00"},
						{"title": "GMT-08:00, Pacific (San Jose)", "value": "UTC-08:00"},
						{"title": "GMT-07:00, Mountain (Arizona)", "value": "UTC-07:00"},
						{"title": "GMT-07:00, Mountain (Denver)", "value": "UTC-07:00"},
						{"title": "GMT-06:00, Central (Chicago)", "value": "UTC-06:00"},
						{"title": "GMT-06:00, Mexico (Mexico City, Tegucigalpa)", "value": "UTC-06:00"},
						{"title": "GMT-06:00, Central (Regina)", "value": "UTC-06:00"},
						{"title": "GMT-05:00, S. America Pacific (Bogota)", "value": "UTC-05:00"},
						{"title": "GMT-05:00, Eastern (New York)", "value": "UTC-05:00"},
						{"title": "GMT-05:00, Eastern (Indiana)", "value": "UTC-05:00"},
						{"title": "GMT-04:00, Atlantic (Halifax)", "value": "UTC-04:00"},
						{"title": "GMT-04:00, S. America Western (Caracas)", "value": "UTC-04:00"},
						{"title": "GMT-03:30, Newfoundland (Newfoundland)", "value": "UTC-03:30"},
						{"title": "GMT-03:00, S. America Eastern (Brasilia)", "value": "UTC-03:00"},
						{"title": "GMT-03:00, S. America Eastern (Buenos Aires)", "value": "UTC-03:00"},
						{"title": "GMT-02:00, Mid-Atlantic (Mid-Atlantic)", "value": "UTC-02:00"},
						{"title": "GMT-01:00, Azores (Azores)", "value": "UTC-01:00"},
						{"title": "GMT+00:00, Greenwich (Casablanca)", "value": "UTC+00:00"},
						{"title": "GMT+00:00, GMT (London)", "value": "UTC+00:00"},
						{"title": "GMT+01:00, Europe (Amsterdam)", "value": "UTC+01:00"},
						{"title": "GMT+01:00, Europe (Paris)", "value": "UTC+01:00"},
						{"title": "GMT+01:00, Europe (Prague)", "value": "UTC+01:00"},
						{"title": "GMT+01:00, Europe (Berlin)", "value": "UTC+01:00"},
						{"title": "GMT+02:00, Greece (Athens)", "value": "UTC+02:00"},
						{"title": "GMT+02:00, Eastern Europe (Bucharest)", "value": "UTC+02:00"},
						{"title": "GMT+02:00, Egypt (Cairo)", "value": "UTC+02:00"},
						{"title": "GMT+02:00, South Africa (Pretoria)", "value": "UTC+02:00"},
						{"title": "GMT+02:00, Northern Europe (Helsinki)", "value": "UTC+02:00"},
						{"title": "GMT+02:00, Israel (Tel Aviv)", "value": "UTC+02:00"},
						{"title": "GMT+03:00, Saudi Arabia (Baghdad)", "value": "UTC+03:00"},
						{"title": "GMT+03:00, Russian (Moscow)", "value": "UTC+03:00"},
						{"title": "GMT+03:00, Nairobi (Nairobi)", "value": "UTC+03:00"},
						{"title": "GMT+03:00, Iran (Tehran)", "value": "UTC+03:00"},
						{"title": "GMT+04:00, Arabian (Abu Dhabi, Muscat)", "value": "UTC+04:00"},
						{"title": "GMT+04:00, Baku (Baku)", "value": "UTC+04:00"},
						{"title": "GMT+04:00, Afghanistan (Kabul)", "value": "UTC+04:00"},
						{"title": "GMT+05:00, West Asia (Ekaterinburg)", "value": "UTC+05:00"},
						{"title": "GMT+05:00, West Asia (Islamabad)", "value": "UTC+05:00"},
						{"title": "GMT+05:30, India (Bombay)", "value": "UTC+05:30"},
						{"title": "GMT+06:00, Columbo (Columbo)", "value": "UTC+06:00"},
						{"title": "GMT+06:00, Central Asia (Almaty)", "value": "UTC+06:00"},
						{"title": "GMT+07:00, Bangkok (Bangkok)", "value": "UTC+07:00"},
						{"title": "GMT+08:00, China (Beijing)", "value": "UTC+08:00"},
						{"title": "GMT+08:00, Australia Western (Perth)", "value": "UTC+08:00"},
						{"title": "GMT+08:00, Singapore (Singapore)", "value": "UTC+08:00"},
						{"title": "GMT+08:00, Taipei (Hong Kong)", "value": "UTC+08:00"},
						{"title": "GMT+09:00, Tokyo (Tokyo)", "value": "UTC+09:00"},
						{"title": "GMT+09:00, Korea (Seoul)", "value": "UTC+09:00"},
						{"title": "GMT+09:30, Yakutsk (Yakutsk)", "value": "UTC+09:30"},
						{"title": "GMT+09:30, Australia Central (Adelaide)", "value": "UTC+09:30"},
						{"title": "GMT+09:30, Australia Central (Darwin)", "value": "UTC+09:30"},
						{"title": "GMT+10:00, Australia Eastern (Brisbane)", "value": "UTC+10:00"},
						{"title": "GMT+10:00, Australia Eastern (Sydney)", "value": "UTC+10:00"},
						{"title": "GMT+10:00, West Pacific (Guam)", "value": "UTC+10:00"},
						{"title": "GMT+10:00, Tasmania (Hobart)", "value": "UTC+10:00"},
						{"title": "GMT+10:00, Vladivostok (Vladivostok)", "value": "UTC+10:00"},
						{"title": "GMT+11:00, Central Pacific (Solomon Is)", "value": "UTC+11:00"},
						{"title": "GMT+12:00, New Zealand (Wellington)", "value": "UTC+12:00"},
						{"title": "GMT+12:00, Fiji (Fiji)", "value": "UTC+12:00"}
					]
				},
				{
					"type": "TextBlock",
					"text": "Participants (email addresses, comma-separated):",
					"weight": "Bolder"
				},
				{
					"type": "Input.Text",
					"id": "participants",
					"placeholder": "user1@company.com, user2@company.com",
					"isMultiline": True
				}
			],
			"actions": [
				{
					"type": "Action.Submit",
					"title": "Schedule Meeting",
					"data": {
						"action": "schedule_meeting",
						"meeting_title": title
					}
				},
				{
					"type": "Action.Submit",
					"title": "Cancel",
					"data": {
						"action": "cancel_meeting"
					}
				}
			]
		}
		
		self.send_message(room_id, "Please fill in the meeting details:", card=meeting_form)

	def handle_meeting_form_submission(self, room_id, person_id, form_data):
		"""Handle the submitted meeting form"""
		session_key = f"{room_id}_{person_id}"
		
		if session_key not in self.pending_meetings:
			self.send_message(room_id, "ERROR: Meeting session not found. Please start again.")
			return
		
		# Get host email from session data
		host_email = self.pending_meetings[session_key].get('host_email', 'user@company.com')
		
		try:
			# Extract form data
			title = form_data.get('meeting_title', '')
			date_raw = form_data.get('meeting_date', '').strip()
			time = form_data.get('meeting_time', '').strip()
			timezone = form_data.get('timezone', 'UTC')
			participants_str = form_data.get('participants', '').strip()
			
			# Convert date from YYYY-MM-DD (Input.Date format) to MM/DD/YYYY for display
			from datetime import datetime
			date_display = date_raw  # Keep original for processing
			try:
				if date_raw and '-' in date_raw:
					# Convert YYYY-MM-DD to MM/DD/YYYY for display
					date_obj = datetime.strptime(date_raw, "%Y-%m-%d")
					date_display = date_obj.strftime("%m/%d/%Y")
			except:
				date_display = date_raw
			
			# Validate required fields
			if not all([title, date_raw, time]):
				self.send_message(room_id, "ERROR: Please fill in all required fields (date and time).")
				return
			
			# Parse participants
			participants = []
			if participants_str:
				participants = [email.strip() for email in participants_str.split(',') if email.strip()]
			
			# Create actual Webex video meeting
			meeting_url = None
			meeting_id = None
			meeting_password = None
			
			# Create Webex video meeting using enhanced SDK
			start_time, end_time = self.meetings_sdk.format_datetime(date_raw, time, timezone)
			
			meeting_result = self.meetings_sdk.create_meeting(
				title=title,
				start_time=start_time,
				end_time=end_time,
				host_email=host_email,
				participants=participants,
				timezone="UTC",
				enable_recording=False
			)
			
			if meeting_result["success"]:
				meeting_url = meeting_result["webLink"]
				meeting_id = meeting_result["meetingId"]
				meeting_password = meeting_result["password"]
			else:
				meeting_url = None
				meeting_id = None
				meeting_password = None
				print(f"Meeting creation failed: {meeting_result['error']}")
			
			# Only save meeting if it was created successfully
			if meeting_url and meeting_id:
				# Create meeting object for successful meetings only
				meeting = {
					"title": f"Webex Meeting: {title}",
					"date": date_display,
					"time": time,
					"timezone": timezone,
					"participants": participants,
					"host_email": host_email,
					"status": "scheduled",
					"webex_meeting_url": meeting_url,
					"webex_meeting_id": meeting_id,
					"webex_meeting_password": meeting_password,
					"platform": "webex"
				}
				
				# Save to database
				result = self.meeting_manager.create_meeting(meeting)
				
				# Also create as a task
				task = {
					"title": f"Webex Meeting: {title}",
					"completed": False,
					"type": "meeting",
					"webex_meeting_url": meeting_url,
					"date": date_display,
					"time": time
				}
				self.task_manager.create_task(task)
			
			# Clean up session
			del self.pending_meetings[session_key]
			
			# Send comprehensive confirmation based on meeting creation result
			if meeting_url and meeting_id:
				# SUCCESS - Real Webex meeting created
				confirmation = f"✅ WEBEX VIDEO MEETING CREATED SUCCESSFULLY!\n\n"
				confirmation += f"📅 Title: {title}\n"
				confirmation += f"📆 Date: {date_display}\n"
				confirmation += f"⏰ Time: {time} ({timezone})\n\n"
				confirmation += f"🎬 JOIN WEBEX VIDEO MEETING:\n"
				confirmation += f"🔗 {meeting_url}\n\n"
				if meeting_password:
					confirmation += f"🔐 Meeting Password: {meeting_password}\n\n"
				confirmation += f"🆔 Meeting ID: {meeting_id}\n\n"
				confirmation += f"👤 Meeting Host: {host_email}\n\n"
				confirmation += f"🎯 Full Video Conference Features:\n"
				confirmation += "• HD Video and Audio\n"
				confirmation += "• Screen Sharing & Annotation\n" 
				confirmation += "• Meeting Recording\n"
				confirmation += "• Interactive Chat\n"
				confirmation += "• Participant Controls\n\n"
			else:
				# FAILURE - Could not create meeting
				confirmation = f"❌ FAILED TO CREATE WEBEX VIDEO MEETING\n\n"
				confirmation += f"📅 Requested: {title}\n"
				confirmation += f"📆 Date: {date_display}\n" 
				confirmation += f"⏰ Time: {time} ({timezone})\n\n"
				confirmation += "🚫 Meeting Creation Failed - Possible Issues:\n"
				confirmation += "• Bot lacks Webex Meetings API permissions\n"
				confirmation += "• Host email not authorized for meetings\n"
				confirmation += "• API rate limits or quota exceeded\n"
				confirmation += "• Invalid meeting parameters\n\n"
				confirmation += "🛠️ MANUAL ALTERNATIVE REQUIRED:\n"
				confirmation += "1. Visit: https://webex.com/\n"
				confirmation += "2. Click 'Schedule a Meeting'\n"
				confirmation += f"3. Title: {title}\n"
				confirmation += f"4. Date/Time: {date_display} at {time} ({timezone})\n"
				if participants:
					confirmation += f"5. Invite: {', '.join(participants)}\n"
				confirmation += "\n⚠️ NO MEETING WAS CREATED AUTOMATICALLY\n"
			
			# Add participants info and task status
			if participants:
				confirmation += f"👥 Invited Participants: {', '.join(participants)}\n\n"
			
			if meeting_url and meeting_id:
				confirmation += f"✅ Meeting saved to your tasks list."
			else:
				confirmation += f"❌ No meeting created - manual setup required."
			
			self.send_message(room_id, confirmation)
			
		except Exception as e:
			self.send_message(room_id, f"ERROR: Failed to schedule meeting: {e}")
			# Clean up session on error
			if session_key in self.pending_meetings:
				del self.pending_meetings[session_key]

	def cancel_meeting_creation(self, room_id, person_id):
		"""Cancel the meeting creation process"""
		session_key = f"{room_id}_{person_id}"
		if session_key in self.pending_meetings:
			del self.pending_meetings[session_key]
		self.send_message(room_id, "Meeting scheduling cancelled.")

	def create_instant_meeting(self, room_id, host_email, title):
		"""Create an instant meeting that starts now"""
		result = self.meetings_sdk.create_instant_meeting(
			title=title,
			host_email=host_email
		)
		
		if result["success"]:
			confirmation = f"🚀 INSTANT WEBEX MEETING CREATED!\n\n"
			confirmation += f"📅 Title: {title}\n"
			confirmation += f"👤 Host: {host_email}\n"
			confirmation += f"⚡ Status: LIVE NOW (1 hour duration)\n\n"
			confirmation += f"🎬 JOIN MEETING IMMEDIATELY:\n"
			confirmation += f"🔗 {result['webLink']}\n\n"
			if result.get('password'):
				confirmation += f"🔐 Password: {result['password']}\n\n"
			confirmation += f"🆔 Meeting ID: {result['meetingId']}\n\n"
			confirmation += "⏰ Meeting is active for 1 hour from now!"
		else:
			# Check if this is a permission error
			if result.get("error") == "PERMISSION_ERROR":
				confirmation = result.get("message", "Permission error occurred")
			else:
				# Try creating a meeting space as fallback
				try:
					fallback_space = self.api.rooms.create(title=f"📞 {title} - Meeting Room")
					confirmation = f"❌ **Meeting API Unavailable** (Missing Permissions)\n\n"
					confirmation += f"✅ **CREATED MEETING SPACE INSTEAD:**\n\n"
					confirmation += f"📅 Title: {title}\n"
					confirmation += f"🏠 Space: {fallback_space.title}\n"
					confirmation += f"🔗 Join: [Open Meeting Space](https://teams.webex.com/space/{fallback_space.id})\n\n"
					confirmation += f"💡 **To enable video meetings:**\n"
					confirmation += f"1. Go to developer.webex.com\n"
					confirmation += f"2. Add meeting scopes to your bot\n"
					confirmation += f"3. Regenerate your bot token"
				except Exception as e:
					confirmation = f"❌ **MEETING CREATION FAILED**\n\n"
					confirmation += f"Error: {result.get('error', 'Unknown error')}\n\n"
					confirmation += f"🔧 **TO FIX BOT PERMISSIONS:**\n"
					confirmation += f"1. Go to [developer.webex.com](https://developer.webex.com)\n" 
					confirmation += f"2. Edit your bot → **Scopes**\n"
					confirmation += f"3. Add: `meeting:schedules_write` & `meeting:schedules_read`\n"
					confirmation += f"4. **Regenerate** your bot token\n"
					confirmation += f"5. Update your `.env` file"
		
		self.send_message(room_id, confirmation)

	def list_user_meetings(self, room_id, host_email):
		"""List meetings for a specific user"""
		result = self.meetings_sdk.list_meetings(host_email=host_email, max_meetings=10)
		
		if result["success"] and result["meetings"]:
			meeting_list = f"📅 YOUR WEBEX MEETINGS ({host_email}):\n\n"
			
			for i, meeting in enumerate(result["meetings"], 1):
				title = meeting.get('title', 'Untitled Meeting')
				start_time = meeting.get('start', '')
				meeting_id = meeting.get('id', '')
				web_link = meeting.get('webLink', '')
				
				# Format the start time nicely
				if start_time:
					try:
						from datetime import datetime
						dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
						formatted_time = dt.strftime('%m/%d/%Y at %I:%M %p UTC')
					except:
						formatted_time = start_time
				else:
					formatted_time = 'No time set'
				
				meeting_list += f"{i}. {title}\n"
				meeting_list += f"   📆 {formatted_time}\n"
				meeting_list += f"   🔗 {web_link}\n"
				meeting_list += f"   🆔 ID: {meeting_id}\n\n"
				
		elif result["success"]:
			meeting_list = f"📅 No meetings found for {host_email}\n\n"
			meeting_list += "Use 'schedule meeting <title>' to create one!"
		else:
			meeting_list = f"❌ Error retrieving meetings: {result.get('error', 'Unknown error')}"
		
		self.send_message(room_id, meeting_list)
