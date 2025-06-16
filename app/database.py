from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["loop"]

store_status_col = db["store_status"]
business_hours_col = db["business_hours"]
store_timezones_col = db["store_timezones"]