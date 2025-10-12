
from .database import MongoDB

class MeetingManager:
	def __init__(self):
		self.db = MongoDB().get_meetings_collection()

	def create_meeting(self, meeting):
		return self.db.insert_one(meeting)

	def list_meetings(self, filter_query=None):
		if filter_query is None:
			filter_query = {}
		return list(self.db.find(filter_query))

	def update_meeting(self, meeting_id, update_fields):
		from bson import ObjectId
		return self.db.update_one({'_id': ObjectId(meeting_id)}, {'$set': update_fields})

	def delete_meeting(self, meeting_id):
		from bson import ObjectId
		return self.db.delete_one({'_id': ObjectId(meeting_id)})
