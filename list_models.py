import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load key from .env
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("🔍 Searching for your available free Gemini models...\n")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            # We filter for text generation models
            print(f"⭐ {m.name}")
except Exception as e:
    print(f"❌ Error: {e}")