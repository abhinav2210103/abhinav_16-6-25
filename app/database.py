# app/database.py

from pymongo import MongoClient

# Connect to local MongoDB and 'loop' database
client = MongoClient("mongodb://localhost:27017/")
db = client["loop"]

# Access collections
store_status_col = db["store_status"]
business_hours_col = db["business_hours"]
store_timezones_col = db["store_timezones"]