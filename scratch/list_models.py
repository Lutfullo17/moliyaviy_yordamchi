import google.generativeai as genai
import sys
import os
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.conf import settings
django.setup()

genai.configure(api_key=settings.GEMINI_API_KEY)

try:
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model: {m.name}, Methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
