import os
import html
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Mocking the Twilio REST Client API w/ print logs
class MockMessages:
    def create(self, **kwargs):
        body = kwargs.get('body', '')
        to = kwargs.get('to', '')
        # Print with ascii fallback representation for standard terminal compatibility
        safe_body = body.encode('ascii', errors='replace').decode('ascii')
        print(f"📡 [MOCK TWILIO SMS SENT] To: {to} | Body: {safe_body}")
        return None

class MockClient:
    def __init__(self, *args, **kwargs):
        self.messages = MockMessages()

# Mocking the Gemini document verification engine to always return valid
import app.main
app.main.twilio_client = MockClient()
app.main.analyze_onboarding_document = lambda step, data: {"valid": True}

# Also mock standard requests.get to return fake image data
import requests
class MockResponse:
    status_code = 200
    content = b"fake_image_bytes"
requests.get = lambda *args, **kwargs: MockResponse()

from app.database.db import init_db, get_user_state
from app.main import whatsapp_webhook
from fastapi import BackgroundTasks

def run_bg_tasks(bg_tasks):
    """Executes scheduled background tasks in a synchronous test environment."""
    for task in bg_tasks.tasks:
        task.func(*task.args, **task.kwargs)
    bg_tasks.tasks.clear()

def test_onboarding_flow():
    print("[TEST] Initializing clean database...")
    init_db()
    
    phone_number = "+21650123456"
    from_arg = f"whatsapp:{phone_number}"
    bg_tasks = BackgroundTasks()
    
    print("\n--- Onboarding Initial State Check ---")
    state = get_user_state(phone_number)
    print(f"Initial state (Expected 'NEED_CIN'): {state}")
    
    print("\n--- STEP 1: User sends text message w/o image ---")
    response_1 = whatsapp_webhook(bg_tasks, from_arg, "Hello", 0, None)
    resp_text_1 = response_1.body.decode('utf-8')
    print(f"Immediate webhook reply: {resp_text_1.encode('ascii', errors='replace').decode('ascii')}")
    run_bg_tasks(bg_tasks)
    state = get_user_state(phone_number)
    print(f"State after STEP 1 (Expected 'NEED_CIN'): {state}")
    
    print("\n--- STEP 2: User uploads CIN image ---")
    response_2 = whatsapp_webhook(bg_tasks, from_arg, "", 1, "https://example.com/cin.jpg")
    resp_text_2 = response_2.body.decode('utf-8')
    print(f"Immediate webhook reply: {resp_text_2.encode('ascii', errors='replace').decode('ascii')}")
    
    print("⏳ Executing visual verification background task...")
    run_bg_tasks(bg_tasks)
    state = get_user_state(phone_number)
    print(f"State after STEP 2 (Expected 'NEED_FACE'): {state}")
    
    print("\n--- STEP 2.5: User sends text message w/o image in NEED_FACE ---")
    response_2_5 = whatsapp_webhook(bg_tasks, from_arg, "Status?", 0, None)
    resp_text_2_5 = response_2_5.body.decode('utf-8')
    print(f"Immediate webhook reply: {resp_text_2_5.encode('ascii', errors='replace').decode('ascii')}")
    run_bg_tasks(bg_tasks)
    state = get_user_state(phone_number)
    print(f"State after STEP 2.5 (Expected 'NEED_FACE'): {state}")
    
    print("\n--- STEP 3: User uploads Face image ---")
    response_3 = whatsapp_webhook(bg_tasks, from_arg, "", 1, "https://example.com/face.jpg")
    resp_text_3 = response_3.body.decode('utf-8')
    print(f"Immediate webhook reply: {resp_text_3.encode('ascii', errors='replace').decode('ascii')}")
    
    print("⏳ Executing face verification background task...")
    run_bg_tasks(bg_tasks)
    state = get_user_state(phone_number)
    print(f"State after STEP 3 (Expected 'NEED_CARNET'): {state}")
    
    print("\n--- STEP 3.5: User sends text message w/o image in NEED_CARNET ---")
    response_3_5 = whatsapp_webhook(bg_tasks, from_arg, "Status?", 0, None)
    resp_text_3_5 = response_3_5.body.decode('utf-8')
    print(f"Immediate webhook reply: {resp_text_3_5.encode('ascii', errors='replace').decode('ascii')}")
    run_bg_tasks(bg_tasks)
    state = get_user_state(phone_number)
    print(f"State after STEP 3.5 (Expected 'NEED_CARNET'): {state}")

    print("\n--- STEP 4: User uploads Carnet Vert image ---")
    response_4 = whatsapp_webhook(bg_tasks, from_arg, "", 1, "https://example.com/carnet.jpg")
    resp_text_4 = response_4.body.decode('utf-8')
    print(f"Immediate webhook reply: {resp_text_4.encode('ascii', errors='replace').decode('ascii')}")
    
    print("⏳ Executing carnet verification background task...")
    run_bg_tasks(bg_tasks)
    state = get_user_state(phone_number)
    print(f"State after STEP 4 (Expected 'VERIFIED'): {state}")

    print("\n--- STEP 5: VERIFIED user sends message w/o image ---")
    response_5 = whatsapp_webhook(bg_tasks, from_arg, "Hello", 0, None)
    resp_text_5 = response_5.body.decode('utf-8')
    print(f"Bot reply: {resp_text_5.encode('ascii', errors='replace').decode('ascii')}")

if __name__ == "__main__":
    test_onboarding_flow()
