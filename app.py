import os
import asyncio
from flask import Flask, request, jsonify
from config import VERIFY_TOKEN
from whatsapp_utils import process_whatsapp_event

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Pathsetu WhatsApp Bot is Running!", 200

# --- WEBHOOK VERIFICATION (Required by Meta) ---
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Forbidden", 403
    return "ignored", 200

# --- MESSAGE RECEIVER ---
@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json()
    
    # Run the async logic in the background
    # Note: In production, use Celery or a proper async queue
    if body:
        asyncio.run(process_whatsapp_event(body))
    
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
