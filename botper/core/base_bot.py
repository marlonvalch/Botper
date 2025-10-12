
from abc import ABC, abstractmethod

class BaseBot(ABC):
	@abstractmethod
	def start(self):
		"""Start the bot (webhook server, polling, etc.)"""
		pass

	@abstractmethod
	def send_message(self, user_id, message, card=None):
		"""Send a message (optionally with a card) to a user or room."""
		pass

	@abstractmethod
	def handle_task_command(self, command, user_id, data=None):
		"""Handle task-related commands (create, list, update, delete)."""
		pass

	@abstractmethod
	def handle_meeting_command(self, command, user_id, data=None):
		"""Handle meeting-related commands (schedule, list, etc.)."""
		pass
