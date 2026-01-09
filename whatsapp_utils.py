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

# --- ROBUST MODEL LIST ---
MODEL_LIST = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-preview-09-2025",
    "gemini-2.5-flash-lite-preview-09-2025",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

SYSTEM_PROMPT = """You are 'Pathsetu', an AI Career GPS.
RULES:
1. Reply in the same language (English/Hindi/Marathi/Telugu).
2. Keep answers SHORT (max 50 words) for WhatsApp.
3. Be realistic and practical.
4. If asked for a Roadmap, generate Mermaid.js code."""

# --- FALLBACK ENGINE ---
async def generate_with_fallback(history, user_prompt):
    """Tries models one by one until success"""
    last_error = None
    
    for model_name in MODEL_LIST:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT
            )
            chat_session = model.start_chat(history=history)
            response = await chat_session.send_message_async(user_prompt)
            return response
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

# --- GRAPHICS ENGINE ---
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
            # Audio handling requires Media download URL (Advanced)
            # For MVP, we treat it as text request prompt
            user_prompt = "User sent an audio. Reply: 'I heard you, but I can only read text on WhatsApp right now.'"
            user_display = "[Audio Message]"
        
        else:
            return 

        # 3. GENERATE (With Fallback)
        try:
            response = await generate_with_fallback(past_history, user_prompt)
            ai_text = response.text
        except Exception as e:
            send_whatsapp_message(sender_id, "⚠️ Brain Overload: Please wait 1 minute.")
            logging.error(f"All Models Failed: {e}")
            return

        # 4. SAVE TO DB
        await add_history(sender_id, user_display, ai_text)

        # 5. CHECK VISUALS
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

        # 6. REPLY
        send_whatsapp_message(sender_id, ai_text)

    except Exception as e:
        logging.error(f"WhatsApp Logic Error: {e}")
