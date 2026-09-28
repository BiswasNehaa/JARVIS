import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "low")  # gpt-oss only: low | medium | high — low is much faster
USER_NAME = os.getenv("USER_NAME", "Neha")
TTS_VOICE = os.getenv("TTS_VOICE", "en-CA-LiamNeural")
TTS_RATE = os.getenv("TTS_RATE", "+0%")  # e.g. "+8%" for a faster, less flat pace
TTS_PITCH = os.getenv("TTS_PITCH", "+0Hz")  # e.g. "+15Hz" for a warmer, less monotone pitch

MAX_COMMAND_SECONDS = 25  # hard cap, in case you never go quiet (roomy, since pauses to think are allowed)
NO_SPEECH_TIMEOUT_SECONDS = 6  # give up if you never start talking after the wake word
# After JARVIS answers it keeps listening this long for a follow-up, no "Hey Jarvis" needed;
# silence for this long ends the conversation. Set to 0 to require the wake word every time.
FOLLOW_UP_SECONDS = float(os.getenv("FOLLOW_UP_SECONDS", "8"))
SILENCE_HANG_MS = int(os.getenv("SILENCE_HANG_MS", "1200"))  # after this much quiet, stop IF what you said sounds like a finished sentence
MAX_SILENCE_HANG_MS = int(os.getenv("MAX_SILENCE_HANG_MS", "3500"))  # stop after this much quiet no matter what (a pause to think mid-sentence fits under it)
SILENCE_RMS_THRESHOLD = 300  # minimum int16 amplitude for speech; raised automatically in noisy rooms (audio.SpeechDetector)
# webrtcvad (installed via webrtcvad-wheels) must also hear a voice, so steady fan/hum noise can't
# keep a recording open until MAX_COMMAND_SECONDS. 0-3, higher = stricter.
VAD_AGGRESSIVENESS = int(os.getenv("VAD_AGGRESSIVENESS", "2"))
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base.en")

AUDIO_LEVEL_REFERENCE = 3000  # int16 mean-abs amplitude mapped to "full" HUD waveform reactivity — tune by ear

VOICEPRINTS_PATH = Path(os.getenv("VOICEPRINTS_PATH", "data/voiceprints/speakers.json"))
SPEAKER_MATCH_THRESHOLD = float(os.getenv("SPEAKER_MATCH_THRESHOLD", "0.75"))  # cosine similarity cutoff for "known voice" — Neha's live turns scored 0.77-0.91 (2026-09-28)
SPEAKER_STICKY_THRESHOLD = float(os.getenv("SPEAKER_STICKY_THRESHOLD", "0.65"))  # near-miss cutoff: at or above this, stay with the last speaker instead of re-asking
SPEAKER_MAX_SAMPLES = 30  # voice samples kept per speaker (oldest dropped first) — more samples, steadier voiceprint
STOP_PHRASES = (  # said mid-command, ends the turn immediately instead of going to the brain
    "stop session",
    "end session",
    "jarvis stop",
    "stop listening",
)

ALLOWED_APPS = {  # Phase 5 skills — name JARVIS can call -> Windows executable (resolved via PATH)
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "file explorer": "explorer.exe",
    "wordpad": "write.exe",
}


def require_keys() -> None:
    if not GROQ_API_KEY:
        print("Missing required environment variable: GROQ_API_KEY")
        print("Copy .env.example to .env and fill in your API key.")
        sys.exit(1)
