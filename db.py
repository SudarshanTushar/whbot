import certifi
import os
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

# Mongo client/collection are initialised lazily only when MONGO_URI is provided.
client = None
collection = None

if MONGO_URI:
    client = AsyncIOMotorClient(
        MONGO_URI,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsCAFile=certifi.where()
    )
    db = client["career_gps_bot"]
    collection = db["user_history"]

async def get_history(user_id):
    """Fetch chat history"""
    if not collection:
        return []
    try:
        doc = await collection.find_one({"user_id": str(user_id)})
        if doc and "history" in doc:
            return doc["history"]
    except Exception as e:
        print(f"DB Read Error: {e}")
    return []

async def add_history(user_id, user_text, model_text):
    """Save message"""
    if not collection:
        return
    try:
        new_entries = [
            {"role": "user", "parts": [user_text]},
            {"role": "model", "parts": [model_text]}
        ]
        await collection.update_one(
            {"user_id": str(user_id)},
            {"$push": {"history": {"$each": new_entries}}},
            upsert=True
        )
    except Exception as e:
        print(f"DB Write Error: {e}")

async def clear_history(user_id):
    """Clear history"""
    if not collection:
        return
    try:
        await collection.delete_one({"user_id": str(user_id)})
    except:
        pass
