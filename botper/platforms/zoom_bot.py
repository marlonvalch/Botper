
import os
from fastapi import FastAPI, Request
from ..core.base_bot import BaseBot
from ..core.tasks import TaskManager
from ..core.meetings import MeetingManager
from ..utils.helpers import format_task_card
from dotenv import load_dotenv

load_dotenv()

class ZoomBot(BaseBot):
	def __init__(self):
		self.task_manager = TaskManager()
		self.meeting_manager = MeetingManager()
		self.app = FastAPI()
		self.setup_routes()

	def setup_routes(self):
		@self.app.post("/zoom/webhook")
		async def webhook(request: Request):
			data = await request.json()
			# Simplified: parse incoming Zoom message
			text = data.get('payload', {}).get('cmd', '').strip().lower()
			to_jid = data.get('payload', {}).get('toJid', '')
			if text == "hello" or text == "hi":
				self.send_greeting(to_jid)
			elif text.startswith("task"):
				task_title = text[5:].strip()
				if task_title:
					self.handle_task_command("create", to_jid, {"title": task_title})
			elif text == "list":
				self.handle_task_command("list", to_jid)
			elif text.startswith("delete"):
				task_id = text[7:].strip()
				self.handle_task_command("delete", to_jid, {"task_id": task_id})
			# Add more command handling as needed
			return {"status": "ok"}

	def send_greeting(self, to_jid):
		greeting = "Hello This is Botper !  Check my menu ,I will help you set up your tasks and schedule your meetings !"
		menu = "Commands:\n- task <task description>\n- list\n- delete <task id>\n- schedule meeting"
		self.send_message(to_jid, f"{greeting}\n{menu}")

	def start(self):
		import uvicorn
		uvicorn.run(self.app, host="0.0.0.0", port=8002)

	def send_message(self, to_jid, message, card=None):
		# Placeholder: Integrate with Zoom SDK to send message/card
		pass

	def handle_task_command(self, command, to_jid, data=None):
		if command == "create":
			task = {"title": data["title"], "completed": False}
			self.task_manager.create_task(task)
			self.send_message(to_jid, f"Task created: {data['title']}")
			self.handle_task_command("list", to_jid)
		elif command == "list":
			tasks = self.task_manager.list_tasks()
			card = format_task_card(tasks, platform="zoom")
			self.send_message(to_jid, "Here are your tasks:", card=card)
		elif command == "delete":
			self.task_manager.delete_task(data["task_id"])
			self.send_message(to_jid, f"Task deleted: {data['task_id']}")
			self.handle_task_command("list", to_jid)

	def handle_meeting_command(self, command, to_jid, data=None):
		# Meeting scheduling logic (prompt for date, users, etc.)
		pass
