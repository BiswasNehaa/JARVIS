import asyncio
import os
import tempfile

import edge_tts
from playsound import playsound

# Free Microsoft neural voice with a warm, confident tone. Swap freely —
# run `edge-tts --list-voices` to browse alternatives.
VOICE = "en-US-GuyNeural"


async def _synthesize(text: str, path: str) -> None:
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(path)


def speak(text: str) -> None:
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        asyncio.run(_synthesize(text, path))
        playsound(path)
    finally:
        os.remove(path)
