import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
from groq import Groq

# Load environment
load_dotenv(override=True)
api_key = os.getenv('GROQ_API_KEY', '')

print('🧪 Testing Groq Vision Models...\n')

client = Groq(api_key=api_key)

# Models to test
test_models = [
    'llama-3.2-11b-vision-preview',
    'llama-3.2-90b-vision-preview',
    'llama-3.2-11b-vision',
    'llama-3.2-90b-vision',
    'llava-v1.5-7b-4096-preview',
]

# Simple test - text only first
for model in test_models:
    try:
        print(f'Testing: {model}')
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say OK"}],
            temperature=0,
            max_tokens=10
        )
        result = response.choices[0].message.content
        print(f'  ✅ SUCCESS: {result}\n')
        break  # Found working model
    except Exception as e:
        error_msg = str(e)
        if 'decommissioned' in error_msg:
            print(f'  ❌ Decommissioned\n')
        elif 'not_found' in error_msg or 'does not exist' in error_msg:
            print(f'  ❌ Not found\n')
        else:
            print(f'  ❌ Error: {error_msg[:100]}\n')

print('\n💡 Checking Groq documentation for current vision models...')
print('Visit: https://console.groq.com/docs/vision')
