import numpy as np
from faster_whisper import WhisperModel

from . import config

_model = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(pcm_samples: list[int]) -> str:
    audio = np.array(pcm_samples, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _ = _get_model().transcribe(audio, language="en")
    return " ".join(segment.text.strip() for segment in segments).strip()
