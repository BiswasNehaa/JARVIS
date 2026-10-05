"""How something was said, not just what: loudness, pitch movement and pace, compared with how this
speaker usually sounds. Sarcasm and mood often live here ("great, just great" said flat and quiet),
and the transcript alone loses them. The result is a few plain words the brain reads alongside the
transcript; deciding what they mean is left to the model."""

import numpy as np

from .audio import SAMPLE_RATE

# Baselines adapt as she talks; a feature only gets described once there's something to compare to.
MIN_TURNS_FOR_BASELINE = 3
BASELINE_WEIGHT = 0.2  # how fast "usual" follows recent turns
NOTABLE = 0.35  # relative change from usual worth mentioning (35%)

_baselines: dict[str, dict[str, float]] = {}  # speaker -> feature -> running average
_turns: dict[str, int] = {}


def _features(samples: list[int], words: int) -> dict[str, float] | None:
    import librosa  # imported here: slow to load, and only needed once there's speech

    audio = np.array(samples, dtype=np.float32) / 32768.0
    rms = librosa.feature.rms(y=audio)[0]
    voiced = rms > max(rms.max() * 0.1, 1e-4)
    seconds = voiced.sum() * 512 / SAMPLE_RATE
    if seconds < 0.8:
        return None
    f0 = librosa.yin(audio, fmin=75, fmax=400, sr=SAMPLE_RATE)
    f0 = f0[: len(voiced)][voiced[: len(f0)]]
    if len(f0) < 5:
        return None
    return {
        "loudness": float(rms[voiced].mean()),
        "pitch": float(np.median(f0)),
        "pitch_range": float(np.percentile(f0, 90) - np.percentile(f0, 10)),  # low = flat, monotone
        "pace": words / seconds,
    }


DESCRIPTIONS = {  # feature -> (word when higher than usual, word when lower)
    "loudness": ("louder", "quieter"),
    "pitch": ("higher-pitched", "lower-pitched"),
    "pitch_range": ("more animated", "flatter, more monotone"),
    "pace": ("faster", "slower"),
}


def describe(samples: list[int], text: str, speaker: str) -> str:
    """e.g. "quieter, flatter, more monotone and slower than usual", or "" when nothing stands out."""
    try:
        features = _features(samples, len(text.split()))
    except Exception:  # noqa: BLE001 - tone is a nice-to-have, never worth failing a turn over
        return ""
    if not features:
        return ""

    baseline = _baselines.setdefault(speaker, {})
    turns = _turns[speaker] = _turns.get(speaker, 0) + 1
    notes = []
    for name, value in features.items():
        usual = baseline.get(name)
        if usual and turns > MIN_TURNS_FOR_BASELINE:
            change = (value - usual) / usual
            if abs(change) >= NOTABLE:
                notes.append(DESCRIPTIONS[name][0 if change > 0 else 1])
        baseline[name] = value if usual is None else usual + BASELINE_WEIGHT * (value - usual)
    if not notes:
        return ""
    return (", ".join(notes[:-1]) + " and " + notes[-1] if len(notes) > 1 else notes[0]) + " than usual"


def warm_up() -> None:
    """Loading librosa and compiling its pitch tracker takes ~9s the first time; do it at startup."""
    tone = np.sin(2 * np.pi * 200 * np.arange(SAMPLE_RATE * 2) / SAMPLE_RATE) * 8000
    _features(tone.astype(np.int16).tolist(), 4)
