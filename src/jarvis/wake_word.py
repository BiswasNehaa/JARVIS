import re
from collections import deque

import numpy as np
from openwakeword.model import Model

from . import config, stt

WAKE_MODEL_NAME = "hey_jarvis"
THRESHOLD = 0.5

# "Hello Jarvis" and "Hi Jarvis" often don't clear THRESHOLD: the model was trained on "Hey Jarvis"
# in mostly American voices. Indian-English "Hello Jarvis" (edge-tts Neerja/Prabhat, with mic-like
# noise added) peaked at 0.12-0.43, so the old 0.15 cutoff for a Whisper second opinion missed many
# tries outright. Anything above NEAR_MISS_THRESHOLD now gets that check; ordinary speech can also
# score 0.02-0.28 now and then, which costs a ~0.7s Whisper pass but never wakes JARVIS by itself.
NEAR_MISS_THRESHOLD = config.WAKE_NEAR_MISS_THRESHOLD
NEAR_MISS_WAIT_FRAMES = 8  # ~0.6s after the score last rose above the cutoff, so all of "Jarvis" is in
BUFFER_FRAMES = 36  # ~2.9s of audio kept for the Whisper check: a slow "Hello... Jarvis" fits
# Whisper's spellings of "Jarvis" in an Indian accent include "Jervis", "Jarvi", "Jaarvis", "Jarwis".
_JARVIS = r"(jarvis|jervis|jarvi|jaarvis|jarwis|jarvees)"
WAKE_PHRASE = re.compile(rf"\b(hey|hi|hello|helo|hallo|hiya|ok|okay)\b[\s,.!]*{_JARVIS}\b", re.IGNORECASE)
# "Bye Jarvis" quits JARVIS entirely (Whisper often writes it "By Jarvis"). The wake-word model keys
# on "Jarvis", so it can fire on this too.
GOODBYE_PHRASE = re.compile(rf"\b(bye|by|buy|goodbye|good bye)\b[\s,.!]*{_JARVIS}\b", re.IGNORECASE)

_recent_frames: deque[np.ndarray] = deque(maxlen=BUFFER_FRAMES)
_near_miss_frames_left = 0
_near_miss_peak = 0.0


def create_model() -> Model:
    """openWakeWord ships a pretrained "Hey Jarvis" model — free, offline, no key needed.

    First run requires a one-time model download; see README setup step 3.
    """
    return Model(wakeword_models=[WAKE_MODEL_NAME], inference_framework="onnx")


def _whisper_confirms(peak: float) -> bool:
    text = stt.transcribe(np.concatenate(list(_recent_frames)).tolist())
    confirmed = bool(WAKE_PHRASE.search(text) or GOODBYE_PHRASE.search(text))
    if confirmed or "jar" in text.lower() or "jer" in text.lower():
        # Shows how close a missed try came, for tuning WAKE_NEAR_MISS_THRESHOLD
        print(f"(wake check: score {peak:.2f}, heard {text!r}{'' if confirmed else ' - not a wake phrase'})")
    return confirmed


def is_goodbye(text: str) -> bool:
    return bool(GOODBYE_PHRASE.search(text))


def recent_audio() -> list[int]:
    """The last ~2.9s of audio, which ends with the wake phrase just detected."""
    return np.concatenate(list(_recent_frames)).tolist() if _recent_frames else []


def said_goodbye(audio: list[int]) -> bool:
    """Right after a detection: was it actually "Bye Jarvis"? audio: recent_audio() at detection."""
    return bool(audio) and is_goodbye(stt.transcribe(audio))


def detected(model: Model, frame: np.ndarray) -> bool:
    """True on "Hey Jarvis", "Hello Jarvis" or "Hi Jarvis"."""
    global _near_miss_frames_left, _near_miss_peak
    _recent_frames.append(frame)
    score = model.predict(frame)[WAKE_MODEL_NAME]
    if score >= THRESHOLD:
        _near_miss_frames_left, _near_miss_peak = 0, 0.0
        return True

    if score >= NEAR_MISS_THRESHOLD:
        # Restart the wait while the score is still up: it can cross the cutoff on "Hel-" and only
        # peak on "-vis", and checking too early would cut "Jarvis" off the end of the clip.
        _near_miss_frames_left = NEAR_MISS_WAIT_FRAMES
        _near_miss_peak = max(_near_miss_peak, score)
        return False
    if _near_miss_frames_left == 0:
        return False

    _near_miss_frames_left -= 1
    if _near_miss_frames_left > 0:
        return False
    peak, _near_miss_peak = _near_miss_peak, 0.0
    # The audio isn't cleared after a miss: "Hello" alone can score above the cutoff and get checked
    # before "Jarvis" is said, and the next check (on "Jarvis") needs "Hello" still in the clip.
    # Nothing re-checks the same audio in a loop, since a check only follows a new above-cutoff score.
    return _whisper_confirms(peak)


def reset(model: Model) -> None:
    """Clear the model's rolling audio buffer after a conversation so leftover scores from before
    can't fire a phantom wake-up."""
    global _near_miss_frames_left, _near_miss_peak
    _recent_frames.clear()
    _near_miss_frames_left, _near_miss_peak = 0, 0.0
    if hasattr(model, "reset"):
        model.reset()
