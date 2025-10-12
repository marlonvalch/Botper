
import os
from fastapi import FastAPI, Request
from ..core.base_bot import BaseBot
from ..core.tasks import TaskManager
from ..core.meetings import MeetingManager
from ..utils.helpers import format_task_card
from dotenv import load_dotenv

load_dotenv()

TEAMS_BOT_ID = os.getenv("TEAMS_BOT_ID")
TEAMS_BOT_PASSWORD = os.getenv("TEAMS_BOT_PASSWORD")

class TeamsBot(BaseBot):
	def __init__(self):
		self.task_manager = TaskManager()
		self.meeting_manager = MeetingManager()
		self.app = FastAPI()
		self.setup_routes()

	def setup_routes(self):
		@self.app.post("/teams/webhook")
		async def webhook(request: Request):
			data = await request.json()
			# Simplified: parse incoming Teams message
			text = data.get('text', '').strip().lower()
			conversation_id = data.get('conversation', {}).get('id', '')
			if text == "hello" or text == "hi":
				self.send_greeting(conversation_id)
			elif text.startswith("task"):
				task_title = data.get('text', '')[5:].strip()
				if task_title:
					self.handle_task_command("create", conversation_id, {"title": task_title})
			elif text == "list":
				self.handle_task_command("list", conversation_id)
			elif text.startswith("delete"):
				task_id = data.get('text', '')[7:].strip()
				self.handle_task_command("delete", conversation_id, {"task_id": task_id})
			# Add more command handling as needed
			return {"status": "ok"}

	def send_greeting(self, conversation_id):
		greeting = "Hello This is Botper !  Check my menu ,I will help you set up your tasks and schedule your meetings !"
		menu = "Commands:\n- task <task description>\n- list\n- delete <task id>\n- schedule meeting"
		self.send_message(conversation_id, f"{greeting}\n{menu}")

	def start(self):
		import uvicorn
		uvicorn.run(self.app, host="0.0.0.0", port=8001)

	def send_message(self, conversation_id, message, card=None):
		# Placeholder: Integrate with Teams SDK to send message/card
		pass

	def handle_task_command(self, command, conversation_id, data=None):
		if command == "create":
			task = {"title": data["title"], "completed": False}
			self.task_manager.create_task(task)
			self.send_message(conversation_id, f"Task created: {data['title']}")
			self.handle_task_command("list", conversation_id)
		elif command == "list":
			tasks = self.task_manager.list_tasks()
			card = format_task_card(tasks, platform="teams")
			self.send_message(conversation_id, "Here are your tasks:", card=card)
		elif command == "delete":
			self.task_manager.delete_task(data["task_id"])
			self.send_message(conversation_id, f"Task deleted: {data['task_id']}")
			self.handle_task_command("list", conversation_id)

	def handle_meeting_command(self, command, conversation_id, data=None):
		# Meeting scheduling logic (prompt for date, users, etc.)
		pass
