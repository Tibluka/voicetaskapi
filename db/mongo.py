from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client['agacode']

spending_collection = db['spending']
user_collection = db["users"]