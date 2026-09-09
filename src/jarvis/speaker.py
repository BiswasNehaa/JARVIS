import json

import numpy as np
from resemblyzer import VoiceEncoder

from . import config

_encoder: VoiceEncoder | None = None


def _get_encoder() -> VoiceEncoder:
    global _encoder
    if _encoder is None:
        _encoder = VoiceEncoder()
    return _encoder


def embed(samples: list[int]) -> np.ndarray:
    """Turn a recorded utterance into a 256-dim voice embedding."""
    wav = np.array(samples, dtype=np.float32) / 32768.0
    return _get_encoder().embed_utterance(wav)


def _load_profiles() -> dict[str, list[float]]:
    if not config.VOICEPRINTS_PATH.exists():
        return {}
    return json.loads(config.VOICEPRINTS_PATH.read_text())


def _save_profiles(profiles: dict[str, list[float]]) -> None:
    config.VOICEPRINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.VOICEPRINTS_PATH.write_text(json.dumps(profiles, indent=2))


def identify(embedding: np.ndarray) -> str | None:
    """Return the enrolled speaker whose voiceprint best matches, or None if no one clears the threshold."""
    profiles = _load_profiles()

    best_name, best_score = None, -1.0
    for name, vector in profiles.items():
        score = float(np.dot(embedding, vector))
        if score > best_score:
            best_name, best_score = name, score

    if best_name is not None and best_score >= config.SPEAKER_MATCH_THRESHOLD:
        return best_name
    return None


def enroll(name: str, embeddings: list[np.ndarray]) -> None:
    """Average one or more sample embeddings into a single voiceprint and save it under `name`."""
    averaged = np.mean(embeddings, axis=0)
    averaged /= np.linalg.norm(averaged)

    profiles = _load_profiles()
    profiles[name] = averaged.tolist()
    _save_profiles(profiles)
