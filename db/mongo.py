from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client['VoiceTask']

spending_collection = db['spending']
user_collection = db["users"]
password_resets = db["password_resets"]
profile_config_collection = db["profile_config"]