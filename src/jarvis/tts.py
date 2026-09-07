import asyncio
import os
import re
import tempfile

import edge_tts
from playsound import playsound

from . import config

# Set TTS_VOICE in .env to change this without touching code.
# Browse options at https://speech.microsoft.com/portal/voicegallery

_EMOJI_PATTERN = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+")
_MARKDOWN_CHARS = re.compile(r"[*_#`]")


def _clean_for_speech(text: str) -> str:
    text = _EMOJI_PATTERN.sub("", text)
    text = _MARKDOWN_CHARS.sub("", text)
    return text.strip()


async def _synthesize(text: str, path: str) -> None:
    communicate = edge_tts.Communicate(text, config.TTS_VOICE, rate=config.TTS_RATE, pitch=config.TTS_PITCH)
    await communicate.save(path)


def speak(text: str) -> None:
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        asyncio.run(_synthesize(_clean_for_speech(text), path))
        playsound(path)
    finally:
        os.remove(path)
