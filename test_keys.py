import requests

# --- YOUR KEYS ---
# Go to Meta Dashboard -> API Setup to get the NEW 24-hour token
TOKEN = "EAFqTMdAImGsBQbfrDtNOBmaOIrRN9bSOnZC0QoU6LoaNwcEtQ5LfCWRxcG6DMBmZA9lKxpZAdlLXxaJbtU4Bf65FRZBmHPGSNAbuYYofZCmkyUqgNtvzgwcmWTzZCAmbZCE6WJ30uV4VxbGZA5LqaZATS5BgCXukpiffoJnrp1yu6ETlUHaxi4FhdzFlwsn6JIsY5R0q7wr1tNlLAQkr5n0ZBWBYwqZCBvgoAvqF1ZC4datqkODmZC1dZAiuXgXvKM9RkEqggESbGmpH6MYcPlx9X6kNcWcvUb" 

# Use the Phone Number ID you found (921609999371179)
PHONE_ID = "921609994371179" 

# Your personal phone number (e.g., 919876543210) - MUST BE in the 'To' list on Meta
MY_NUMBER = "+15551761508" 

# --- THE TEST ---
url = f"https://graph.facebook.com/v17.0/921609994371179/messages"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}
data = {
    "messaging_product": "whatsapp",
    "to": MY_NUMBER,
    "type": "text",
    "text": {"body": "TEST: Your keys are working!"}
}

print("Sending test message...")
response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    print("\n✅ SUCCESS! Your Keys are correct.")
    print("The problem is inside your Heroku Code.")
else:
    print(f"\n❌ FAILED. Meta rejected your keys.")
    print(f"Error Code: {response.status_code}")
    print(f"Reason: {response.json()}")
