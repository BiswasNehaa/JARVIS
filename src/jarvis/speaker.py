import json

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

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
    # preprocess_wav trims silence and normalizes volume — without it, embeddings drift with
    # how much trailing silence _record_command happened to capture, causing inconsistent matches
    # turn to turn for the same speaker.
    wav = preprocess_wav(wav)
    return _get_encoder().embed_utterance(wav)


def _load_profiles() -> dict[str, list[list[float]]]:
    """Each speaker maps to a list of sample embeddings. Older files stored one averaged vector per
    speaker — that's read back as a single-sample list so existing enrollments keep working."""
    if not config.VOICEPRINTS_PATH.exists():
        return {}
    raw = json.loads(config.VOICEPRINTS_PATH.read_text())
    return {
        name: [value] if value and not isinstance(value[0], list) else value
        for name, value in raw.items()
    }


def _save_profiles(profiles: dict[str, list[list[float]]]) -> None:
    config.VOICEPRINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.VOICEPRINTS_PATH.write_text(json.dumps(profiles, indent=2))


def _voiceprint(samples: list[list[float]]) -> np.ndarray:
    centroid = np.mean(samples, axis=0)
    return centroid / np.linalg.norm(centroid)


def best_match(embedding: np.ndarray) -> tuple[str | None, float]:
    """Return the closest enrolled speaker and their cosine similarity, whether or not it clears
    the threshold — the caller decides, so near misses can be logged and weighed."""
    best_name, best_score = None, -1.0
    for name, samples in _load_profiles().items():
        score = float(np.dot(embedding, _voiceprint(samples)))
        if score > best_score:
            best_name, best_score = name, score
    return best_name, best_score


def identify(embedding: np.ndarray) -> str | None:
    """Return the enrolled speaker whose voiceprint best matches, or None if no one clears the threshold."""
    name, score = best_match(embedding)
    if name is not None and score >= config.SPEAKER_MATCH_THRESHOLD:
        return name
    return None


def enroll(name: str, embeddings: list[np.ndarray]) -> None:
    """Add sample embeddings to `name`'s voiceprint, creating it if needed. Adds rather than
    replaces: re-enrolling after a missed match used to overwrite a speaker's whole voiceprint
    with two fresh clips, throwing away everything learned so far and making the next miss likelier."""
    profiles = _load_profiles()
    samples = profiles.get(name, []) + [(e / np.linalg.norm(e)).tolist() for e in embeddings]
    profiles[name] = samples[-config.SPEAKER_MAX_SAMPLES:]
    _save_profiles(profiles)
