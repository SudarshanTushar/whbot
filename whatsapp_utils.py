import logging
import requests
import json
import base64
import io
import os
from google import genai
from google.genai import types
from gtts import gTTS
from config import GEMINI_API_KEY, WHATSAPP_TOKEN, PHONE_NUMBER_ID
from db import get_history, add_history, clear_history

# --- NEW AI CLIENT ---
MISSING_KEY_MESSAGE = "GEMINI_API_KEY is missing; AI responses are disabled."
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    logging.error(MISSING_KEY_MESSAGE)

# --- ROBUST MODEL LIST ---
MODEL_LIST = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

SYSTEM_PROMPT = """You are 'Pathsetu', an AI Career GPS.
RULES:
1. Reply in the same language (English/Hindi/Marathi/Telugu).
2. Keep answers SHORT (max 50 words) for WhatsApp.
3. Be realistic and practical.
4. If asked for a Roadmap, generate Mermaid.js code."""

# --- HELPER: HISTORY CONVERTER ---
def format_history_for_new_sdk(db_history, new_user_text):
    """
    Converts old DB format {'role': 'user', 'parts': ['text']} 
    to New SDK format {'role': 'user', 'parts': [{'text': 'text'}]}
    """
    formatted_contents = []
    
    # 1. Add System Instruction first (Best practice in new SDK)
    formatted_contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=SYSTEM_PROMPT)])
    )
    
    # 2. Add Past History
    for entry in db_history:
        role = entry.get("role")
        # Ensure 'model' role is strictly used (some old DBs use 'assistant')
        if role == "model": 
            role = "model"
        else:
            role = "user"
            
        parts_text = entry.get("parts", [])
        if isinstance(parts_text, list):
            # Join list of strings into one string if needed, or take first
            text_content = " ".join(parts_text) if parts_text else ""
        else:
            text_content = str(parts_text)
            
        formatted_contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=text_content)])
        )

    # 3. Add Current User Query
    formatted_contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=new_user_text)])
    )
    
    return formatted_contents


def ensure_client_available(sender_id=None):
    """Ensure the Gemini client is configured; returns True when available, otherwise False (and optionally notifies the sender)."""
    if client:
        return True
    if sender_id:
        send_whatsapp_message(sender_id, MISSING_KEY_MESSAGE)
    return False

# --- FALLBACK ENGINE ---
def generate_with_fallback(formatted_contents):
    """Tries models one by one using the new SDK. Returns the AI text or None if the client is unavailable."""
    if not ensure_client_available():
        return None
    last_error = None
    
    for model_name in MODEL_LIST:
        try:
            # New SDK Generation Call
            response = client.models.generate_content(
                model=model_name,
                contents=formatted_contents,
                config=types.GenerateContentConfig(
                    temperature=0.7
                )
            )
            return response.text
        except Exception as e:
            logging.warning(f"⚠️ Model '{model_name}' failed. Switching... Error: {e}")
            last_error = e
            continue
            
    raise last_error

# --- WHATSAPP API SENDERS ---
def send_whatsapp_message(to_number, text):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=data)

def send_whatsapp_image(to_number, image_url, caption):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "image",
        "image": {"link": image_url, "caption": caption}
    }
    requests.post(url, headers=headers, json=data)

def generate_graph_url(mermaid_code):
    try:
        graph_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
        graph_bytes = graph_code.encode("utf8")
        base64_bytes = base64.urlsafe_b64encode(graph_bytes)
        return f"https://mermaid.ink/img/{base64_bytes.decode('ascii')}"
    except:
        return None

# --- MAIN EVENT PROCESSOR ---
async def process_whatsapp_event(body):
    try:
        entry = body['entry'][0]
        changes = entry['changes'][0]
        value = changes['value']
        
        if 'messages' not in value:
            return

        message = value['messages'][0]
        sender_id = message['from']
        
        # 1. LOAD HISTORY
        past_history = await get_history(sender_id)
        
        user_prompt = ""
        user_display = ""

        # 2. HANDLE INPUT
        msg_type = message['type']
        
        if msg_type == 'text':
            user_prompt = message['text']['body']
            user_display = user_prompt
            
            if user_prompt.lower() in ["/start", "hi", "hello"]:
                await clear_history(sender_id)
                send_whatsapp_message(sender_id, "Namaste! 🙏 Pathsetu here.\nAsk me about careers!")
                return

        elif msg_type == 'audio':
            user_prompt = "User sent audio. Reply: 'I heard you, but reply in text.'"
            user_display = "[Audio Message]"
        
        else:
            return 

        # 3. PREPARE CONTENT (CONVERT TO NEW FORMAT)
        formatted_contents = format_history_for_new_sdk(past_history, user_prompt)

        if not ensure_client_available(sender_id):
            return

        # 4. GENERATE (With Fallback)
        try:
            ai_text = generate_with_fallback(formatted_contents)
            if ai_text is None:
                return
        except Exception as e:
            send_whatsapp_message(sender_id, "⚠️ Traffic Jam: Please wait 1 minute.")
            logging.error(f"All Models Failed: {e}")
            return

        # 5. SAVE TO DB (Keep old simple format for DB storage)
        await add_history(sender_id, user_display, ai_text)

        # 6. CHECK VISUALS
        if "```mermaid" in ai_text:
            try:
                parts = ai_text.split("```mermaid")
                graph_code = parts[1].split("```")[0]
                img_url = generate_graph_url(graph_code)
                if img_url:
                    send_whatsapp_image(sender_id, img_url, "Your Roadmap 📍")
            except:
                pass
            ai_text = ai_text.replace("```mermaid", "").replace("graph TD", "").replace("```", "")

        # 7. REPLY
        send_whatsapp_message(sender_id, ai_text)

    except Exception as e:
        logging.error(f"WhatsApp Logic Error: {e}")
