import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
from groq import Groq

# Load environment
load_dotenv(override=True)
api_key = os.getenv('GROQ_API_KEY', '')

print('🔍 Fetching available Groq models...\n')

try:
    client = Groq(api_key=api_key)
    models = client.models.list()

    vision_models = []
    text_models = []

    for model in models.data:
        model_id = model.id
        if 'vision' in model_id.lower() or 'llava' in model_id.lower():
            vision_models.append(model_id)
        else:
            text_models.append(model_id)

    print('📸 VISION MODELS (support images):')
    if vision_models:
        for m in vision_models:
            print(f'  ✓ {m}')
    else:
        print('  (checking all models for vision capabilities...)')
        # Try common vision model names
        common_vision = [
            'llama-3.2-11b-vision',
            'llama-3.2-90b-vision',
            'llama-vision-free',
            'llava-v1.5-7b-4096-preview',
            'llava-1.6-7b-preview'
        ]
        for m in common_vision:
            print(f'  ? {m} (might work)')

    print('\n📝 TEXT MODELS:')
    for m in text_models[:10]:  # Show first 10
        print(f'  - {m}')

    print(f'\n💡 Total models available: {len(models.data)}')

except Exception as e:
    print(f'❌ Error: {e}')
