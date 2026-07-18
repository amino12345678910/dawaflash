import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
import google.generativeai as genai

# Load environment
load_dotenv(override=True)
api_key = os.getenv('GEMINI_API_KEY', '')

print(f'Testing Gemini 2.0 Flash')
print(f'API Key: {api_key[:20]}...' if api_key else 'MISSING')

try:
    genai.configure(api_key=api_key, transport="rest")

    # Test with Gemini 2.0 Flash
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    response = model.generate_content(
        "Say hello in 3 words",
        generation_config={"temperature": 0}
    )

    result = response.text
    print(f'\n[Gemini 2.0 Test] SUCCESS: {result}')
    print(f'[Model] gemini-2.0-flash-exp')
    print(f'\n✓ Gemini 2.0 API is working!')

except Exception as e:
    print(f'\n[Gemini Test] FAILED: {e}')
    print('\nTrying fallback to gemini-1.5-flash...')

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say hello in 3 words")
        result = response.text
        print(f'[Gemini 1.5 Test] SUCCESS: {result}')
        print('NOTE: Use gemini-1.5-flash instead of 2.0')
    except Exception as e2:
        print(f'[Gemini 1.5 Test] ALSO FAILED: {e2}')
        print('\nCheck your GEMINI_API_KEY in .env file')
        print('Get one at: https://aistudio.google.com/apikey')
