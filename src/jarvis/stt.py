import threading

import numpy as np
from faster_whisper import WhisperModel

from . import config

_model = None
_model_lock = threading.Lock()  # main.py warms the model up on a background thread at startup


def _get_model() -> WhisperModel:
    global _model
    with _model_lock:
        if _model is None:
            _model = WhisperModel(config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


# Whisper normally drops fillers, so "tell me, um..." comes back as a finished "Tell me?". A prompt
# written with fillers nudges it to keep them, which is what lets main.py tell a pause to think apart
# from the end of a sentence.
FILLER_PROMPT = "Umm, let me think, like, hmm... Okay, so, uh, here's what I'm, like, thinking."


CONTEXT_PROMPT_CHARS = 400  # Whisper only reads ~224 tokens of prompt; keep the most recent part


def conversation_prompt(history: list[dict], speaker_name: str) -> str:
    """The last few lines of the conversation, written like a transcript. Whisper treats its prompt
    as "the text just before this audio", so words already said (a library, a name, a place) are
    spelled and heard correctly when they come up again instead of turning into sound-alikes."""
    lines = [
        f"{speaker_name if turn['role'] == 'user' else 'JARVIS'}: {turn['content']}"
        for turn in history
        if turn.get("role") in ("user", "assistant") and turn.get("content")
    ]
    if config.STT_HINTS:
        lines.insert(0, config.STT_HINTS)
    return " ".join(lines)[-CONTEXT_PROMPT_CHARS:]


def transcribe(pcm_samples: list[int], keep_fillers: bool = False, context: str = "") -> str:
    audio = np.array(pcm_samples, dtype=np.int16).astype(np.float32) / 32768.0
    # Greedy decoding (beam_size=1) is roughly 2x faster than the default beam of 5 with no audible
    # accuracy loss on short spoken commands; vad_filter skips silent stretches instead of decoding them.
    segments, _ = _get_model().transcribe(
        audio,
        language="en",
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=" ".join(p for p in (context, FILLER_PROMPT if keep_fillers else "") if p) or None,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
