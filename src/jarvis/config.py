import os
import sys

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

WAKE_WORD = "jarvis"
COMMAND_RECORD_SECONDS = 5
WHISPER_MODEL_SIZE = "base.en"


def require_keys() -> None:
    missing = [
        name
        for name, value in [
            ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
            ("PICOVOICE_ACCESS_KEY", PICOVOICE_ACCESS_KEY),
        ]
        if not value
    ]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your API keys.")
        sys.exit(1)
