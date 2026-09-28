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


def transcribe(pcm_samples: list[int]) -> str:
    audio = np.array(pcm_samples, dtype=np.int16).astype(np.float32) / 32768.0
    # Greedy decoding (beam_size=1) is roughly 2x faster than the default beam of 5 with no audible
    # accuracy loss on short spoken commands; vad_filter skips silent stretches instead of decoding them.
    segments, _ = _get_model().transcribe(
        audio,
        language="en",
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
