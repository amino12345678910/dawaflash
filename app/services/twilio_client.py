import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER", "+14155238886")

def send_whatsapp_message(to_number: str, body_text: str):
    """Sends a WhatsApp message using Twilio REST API to bypass the 15s timeout."""
    print(f"📡 [ASYNC] Sending WhatsApp message to {to_number}...")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    # Ensure phone numbers have the whatsapp prefix for Twilio sandbox/prod
    to_prefix = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number
    from_prefix = f"whatsapp:{TWILIO_NUMBER}" if not TWILIO_NUMBER.startswith("whatsapp:") else TWILIO_NUMBER

    data = {
        "From": from_prefix,
        "To": to_prefix,
        "Body": body_text
    }
    
    try:
        response = requests.post(url, data=data, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        if response.status_code in [200, 201]:
            print("✅ [ASYNC] Message successfully dispatched via Twilio REST API!")
        else:
            print(f"❌ [ASYNC] Twilio API Error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"💥 [ASYNC] Failed to send REST message: {str(e)}")
