import os
import sys

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

COMMAND_RECORD_SECONDS = 5
WHISPER_MODEL_SIZE = "base.en"


def require_keys() -> None:
    if not GROQ_API_KEY:
        print("Missing required environment variable: GROQ_API_KEY")
        print("Copy .env.example to .env and fill in your API key.")
        sys.exit(1)
