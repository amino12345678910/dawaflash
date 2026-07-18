import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
import google.generativeai as genai

# Load environment
load_dotenv(override=True)
api_key = os.getenv('GEMINI_API_KEY', '')

print('🔍 Listing available Gemini models...\n')

try:
    genai.configure(api_key=api_key, transport="rest")

    models = genai.list_models()

    vision_models = []
    text_models = []

    for model in models:
        # Check if supports vision (image input)
        supports_vision = 'generateContent' in model.supported_generation_methods

        if supports_vision and 'vision' in model.name.lower():
            vision_models.append(model.name)
        elif supports_vision:
            text_models.append(model.name)

    print('📸 VISION MODELS:')
    if vision_models:
        for m in vision_models:
            print(f'  ✓ {m}')
    else:
        print('  (No explicit vision models, but some text models support images)')

    print('\n📝 TEXT/MULTI-MODAL MODELS (may support images):')
    for m in text_models[:15]:
        print(f'  • {m}')

except Exception as e:
    print(f'❌ Error: {e}')
