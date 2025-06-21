from pymongo import MongoClient

client = MongoClient("mongodb+srv://sarveshatawane03:y2flIDD1EmOaU5de@cluster0.sssmr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["vendor_db"]
vendor_collection = db["vendors"]
