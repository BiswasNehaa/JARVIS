import asyncio
import os
import re
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import av  # comes with faster-whisper; decodes edge-tts's mp3 output
import edge_tts
import numpy as np
import sounddevice as sd

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
_CLAUSE_BREAK = re.compile(r"(?<=[,;:\u2014])\s*|\s+(?=\u2014)")
FIRST_CHUNK_MAX_CHARS = 80  # synthesis time grows with length, so keep the very first chunk short
FIRST_CHUNK_MIN_CHARS = 15


def _split_for_speech(text: str) -> list[str]:
    """Sentences, with a long opening sentence split at its first natural pause (comma, dash,
    semicolon) so playback can start on a short clause while the rest synthesizes."""
    chunks = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if chunks and len(chunks[0]) > FIRST_CHUNK_MAX_CHARS:
        for match in _CLAUSE_BREAK.finditer(chunks[0]):
            if FIRST_CHUNK_MIN_CHARS <= match.start() <= FIRST_CHUNK_MAX_CHARS:
                head, tail = chunks[0][:match.start()].strip(), chunks[0][match.end():].strip()
                if tail:
                    chunks[0:1] = [head, tail]
                break
    return chunks


def _synthesize_to_file(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    asyncio.run(_synthesize(text, path))
    return path


PLAYBACK_RATE = 24000  # edge-tts's native rate
PLAYBACK_BLOCK = 1200  # 50ms: how quickly interrupt() takes effect

_interrupt = threading.Event()


def interrupt() -> None:
    """Cut off whatever JARVIS is saying right now (e.g. you said "stop")."""
    _interrupt.set()


def _decode(path: str) -> np.ndarray:
    with av.open(path) as container:
        resampler = av.AudioResampler(format="flt", layout="mono", rate=PLAYBACK_RATE)
        chunks = [
            out.to_ndarray().reshape(-1)
            for frame in container.decode(audio=0)
            for out in resampler.resample(frame)
        ]
    return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)


def _play(audio: np.ndarray) -> bool:
    """Play in small blocks so an interrupt stops it within ~50ms (playsound couldn't be stopped).
    Returns False if interrupted."""
    with sd.OutputStream(samplerate=PLAYBACK_RATE, channels=1, dtype="float32") as stream:
        for start in range(0, len(audio), PLAYBACK_BLOCK):
            if _interrupt.is_set():
                return False
            stream.write(audio[start:start + PLAYBACK_BLOCK].reshape(-1, 1))
    return True


def speak(text: str) -> dict:
    """Speak `text`, starting playback after the first sentence (or opening clause) is synthesized rather than the whole
    reply; the next sentence is synthesized in the background while the current one plays.

    Returns {"first_audio": seconds until playback started, "interrupted": bool} for main.py."""
    start = time.perf_counter()
    sentences = _split_for_speech(_clean_for_speech(text))
    timing = {"first_audio": 0.0, "interrupted": False}
    _interrupt.clear()
    if not sentences:
        return timing

    with ThreadPoolExecutor(max_workers=1) as synth:
        pending = synth.submit(_synthesize_to_file, sentences[0])
        for index in range(len(sentences)):
            path = pending.result()
            if index + 1 < len(sentences) and not _interrupt.is_set():
                pending = synth.submit(_synthesize_to_file, sentences[index + 1])
            try:
                if _interrupt.is_set():
                    timing["interrupted"] = True
                    break
                audio = _decode(path)
                with _playback_lock:
                    if index == 0:
                        timing["first_audio"] = time.perf_counter() - start
                    if not _play(audio):
                        timing["interrupted"] = True
                        break
            finally:
                os.remove(path)
    if timing["interrupted"]:
        # The next sentence may have been synthesized already and never played
        try:
            os.remove(pending.result())
        except (OSError, Exception):  # noqa: BLE001 - already removed, or synthesis failed
            pass
    return timing
