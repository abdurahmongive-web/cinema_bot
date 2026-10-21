import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Model to use: gemini-2.5-flash is fast, smart and has 1500 free requests per day
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
