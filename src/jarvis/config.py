import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
USER_NAME = os.getenv("USER_NAME", "Neha")
TTS_VOICE = os.getenv("TTS_VOICE", "en-CA-LiamNeural")
TTS_RATE = os.getenv("TTS_RATE", "+0%")  # e.g. "+8%" for a faster, less flat pace
TTS_PITCH = os.getenv("TTS_PITCH", "+0Hz")  # e.g. "+15Hz" for a warmer, less monotone pitch

MAX_COMMAND_SECONDS = 25  # hard cap, in case you never go quiet
SILENCE_HANG_MS = 2000  # stop recording after this much quiet, once you've started speaking
SILENCE_RMS_THRESHOLD = 300  # int16 amplitude below this counts as "quiet" — tune if it cuts you off early
WHISPER_MODEL_SIZE = "base.en"

AUDIO_LEVEL_REFERENCE = 3000  # int16 mean-abs amplitude mapped to "full" HUD waveform reactivity — tune by ear

VOICEPRINTS_PATH = Path(os.getenv("VOICEPRINTS_PATH", "data/voiceprints/speakers.json"))
SPEAKER_MATCH_THRESHOLD = float(os.getenv("SPEAKER_MATCH_THRESHOLD", "0.78"))  # cosine similarity cutoff for "known voice" — tune by ear
STOP_PHRASES = (  # said mid-command, ends the turn immediately instead of going to the brain
    "stop session",
    "end session",
    "jarvis stop",
    "stop listening",
)


def require_keys() -> None:
    if not GROQ_API_KEY:
        print("Missing required environment variable: GROQ_API_KEY")
        print("Copy .env.example to .env and fill in your API key.")
        sys.exit(1)
