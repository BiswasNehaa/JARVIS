import os
import sys

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

MAX_COMMAND_SECONDS = 8  # hard cap, in case you never go quiet
SILENCE_HANG_MS = 1200  # stop recording after this much quiet, once you've started speaking
SILENCE_RMS_THRESHOLD = 300  # int16 amplitude below this counts as "quiet" — tune if it cuts you off early
WHISPER_MODEL_SIZE = "base.en"


def require_keys() -> None:
    if not GROQ_API_KEY:
        print("Missing required environment variable: GROQ_API_KEY")
        print("Copy .env.example to .env and fill in your API key.")
        sys.exit(1)
