
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class MongoDB:
	def __init__(self):
		hosts = os.getenv('MONGO_HOSTS').split(',')
		username = os.getenv('MONGO_USERNAME')
		password = os.getenv('MONGO_PASSWORD')
		port = os.getenv('MONGO_PORT')
		dbname = os.getenv('MONGO_DATABASE')
		if username and password:
			uri = f"mongodb://{username}:{password}@{','.join([f'{h}:{port}' for h in hosts])}/{dbname}?authSource=admin"
		else:
			uri = f"mongodb://{','.join([f'{h}:{port}' for h in hosts])}/{dbname}"
		self.client = MongoClient(uri)
		self.db = self.client[dbname]
		self.tasks_col = self.db['tasks']
		self.meetings_col = self.db['meetings']

	def get_tasks_collection(self):
		return self.tasks_col

	def get_meetings_collection(self):
		return self.meetings_col
