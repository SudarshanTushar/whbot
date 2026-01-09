import logging
import requests
import json
import base64
import io
import google.generativeai as genai
from gtts import gTTS
from config import GEMINI_API_KEY, WHATSAPP_TOKEN, PHONE_NUMBER_ID
from db import get_history, add_history, clear_history

# --- AI CONFIGURATION ---
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are 'Pathsetu', an AI Career GPS.
RULES:
1. Reply in the same language (English/Hindi/Marathi/Telugu).
2. Keep answers SHORT (WhatsApp users hate long texts).
3. Be realistic and practical.
4. If asked for a Roadmap, generate Mermaid.js code."""

# Using the Fallback Logic (Simplified for brevity)
model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)

# --- WHATSAPP API HELPERS ---
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

# --- GRAPHICS ENGINE ---
def generate_graph_url(mermaid_code):
    try:
        graph_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
        graph_bytes = graph_code.encode("utf8")
        base64_bytes = base64.urlsafe_b64encode(graph_bytes)
        return f"https://mermaid.ink/img/{base64_bytes.decode('ascii')}"
    except:
        return None

# --- MAIN LOGIC ---
async def process_whatsapp_event(body):
    """Handles incoming WhatsApp messages"""
    try:
        entry = body['entry'][0]
        changes = entry['changes'][0]
        value = changes['value']
        
        if 'messages' not in value:
            return # Not a message (maybe a status update)

        message = value['messages'][0]
        sender_id = message['from'] # This is the Phone Number
        
        # 1. LOAD HISTORY (Using Phone Number as User ID)
        past_history = await get_history(sender_id)
        chat_session = model.start_chat(history=past_history)
        
        user_prompt = ""
        user_display = ""

        # 2. DETERMINE INPUT TYPE
        msg_type = message['type']
        
        if msg_type == 'text':
            user_prompt = message['text']['body']
            user_display = user_prompt
            
            # Handle /start command logic manually
            if user_prompt.lower() == "/start" or user_prompt.lower() == "hi":
                await clear_history(sender_id)
                send_whatsapp_message(sender_id, "Namaste! 🙏 I am Pathsetu for WhatsApp.\nAsk me about careers!")
                return

        elif msg_type == 'audio':
            # Handling Voice in WhatsApp is complex (requires downloading media URL)
            # For this MVP, we will treat it as a placeholder or need extra code to download
            user_prompt = "User sent an audio file. Please reply: 'I received your audio.'"
            user_display = "[Audio Message]"
        
        else:
            return # Unsupported type

        # 3. AI GENERATION
        response = await chat_session.send_message_async(user_prompt)
        ai_text = response.text
        
        # 4. SAVE TO DB
        await add_history(sender_id, user_display, ai_text)

        # 5. CHECK VISUALS
        if "```mermaid" in ai_text:
            parts = ai_text.split("```mermaid")
            graph_code = parts[1].split("```")[0]
            img_url = generate_graph_url(graph_code)
            if img_url:
                send_whatsapp_image(sender_id, img_url, "Your Roadmap 📍")
            ai_text = ai_text.replace("```mermaid", "").replace("graph TD", "").replace("```", "")

        # 6. SEND REPLY
        send_whatsapp_message(sender_id, ai_text)

    except Exception as e:
        logging.error(f"WhatsApp Error: {e}")
