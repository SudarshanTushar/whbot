import os
from dotenv import load_dotenv

load_dotenv()

# --- GEMINI & DB (Same as before) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

# --- WHATSAPP CONFIGURATION ---
# Get these from developers.facebook.com -> WhatsApp -> API Setup
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN") 
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID") 
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_secret_token") # You define this
