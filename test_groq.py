import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
from groq import Groq

# Load environment
load_dotenv(override=True)
api_key = os.getenv('GROQ_API_KEY', '')

print(f'Testing Groq API')
print(f'API Key: {api_key[:20]}...' if api_key else 'MISSING')

try:
    client = Groq(api_key=api_key)

    # Test text completion
    response = client.chat.completions.create(
        model="llama-3.2-11b-vision-preview",
        messages=[
            {"role": "user", "content": "Say hello in 3 words"}
        ],
        temperature=0,
        max_tokens=20
    )

    result = response.choices[0].message.content
    print(f'\n[Groq Test] SUCCESS: {result}')
    print(f'[Model] llama-3.2-11b-vision-preview')
    print(f'\nGroq API is working! ✓')

except Exception as e:
    print(f'\n[Groq Test] FAILED: {e}')
    print('\nMake sure you have a valid GROQ_API_KEY in .env file')
    print('Get one at: https://console.groq.com/keys')
