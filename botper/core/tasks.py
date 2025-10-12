
from .database import MongoDB

class TaskManager:
	def __init__(self):
		self.db = MongoDB().get_tasks_collection()

	def create_task(self, task):
		return self.db.insert_one(task)

	def list_tasks(self, filter_query=None):
		if filter_query is None:
			filter_query = {}
		return list(self.db.find(filter_query))

	def update_task(self, task_id, update_fields):
		from bson import ObjectId
		return self.db.update_one({'_id': ObjectId(task_id)}, {'$set': update_fields})

	def delete_task(self, task_id):
		from bson import ObjectId
		return self.db.delete_one({'_id': ObjectId(task_id)})
