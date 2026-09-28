import asyncio
import os
import re
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import edge_tts
from playsound import playsound

from . import config

# Set TTS_VOICE in .env to change this without touching code.
# Browse options at https://speech.microsoft.com/portal/voicegallery

_EMOJI_PATTERN = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+")
_MARKDOWN_CHARS = re.compile(r"[*_#`]")
_playback_lock = threading.Lock()  # timers fire on their own thread; keep playback from overlapping


def _clean_for_speech(text: str) -> str:
    text = _EMOJI_PATTERN.sub("", text)
    text = _MARKDOWN_CHARS.sub("", text)
    return text.strip()


async def _synthesize(text: str, path: str) -> None:
    communicate = edge_tts.Communicate(text, config.TTS_VOICE, rate=config.TTS_RATE, pitch=config.TTS_PITCH)
    await communicate.save(path)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _synthesize_to_file(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    asyncio.run(_synthesize(text, path))
    return path


def speak(text: str) -> dict:
    """Speak `text`, starting playback after the first sentence is synthesized rather than the whole
    reply; the next sentence is synthesized in the background while the current one plays.

    Returns {"first_audio": seconds until playback started} for main.py's timing log."""
    start = time.perf_counter()
    sentences = [s for s in _SENTENCE_SPLIT.split(_clean_for_speech(text)) if s.strip()]
    timing = {"first_audio": 0.0}
    if not sentences:
        return timing

    with ThreadPoolExecutor(max_workers=1) as synth:
        pending = synth.submit(_synthesize_to_file, sentences[0])
        for index in range(len(sentences)):
            path = pending.result()
            if index + 1 < len(sentences):
                pending = synth.submit(_synthesize_to_file, sentences[index + 1])
            try:
                with _playback_lock:
                    if index == 0:
                        timing["first_audio"] = time.perf_counter() - start
                    playsound(path)
            finally:
                os.remove(path)
    return timing
