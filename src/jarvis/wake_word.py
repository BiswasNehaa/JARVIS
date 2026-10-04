import re
from collections import deque

import numpy as np
from openwakeword.model import Model

from . import stt

WAKE_MODEL_NAME = "hey_jarvis"
THRESHOLD = 0.5

# "Hello Jarvis" and "Hi Jarvis" usually clear THRESHOLD on their own (the model mostly keys on
# "Jarvis"), but in testing an Indian-English "Hi Jarvis" peaked at only ~0.38. Scores in this
# near-miss band get a second opinion from Whisper; unrelated speech scores ~0.00, so this rarely runs.
NEAR_MISS_THRESHOLD = 0.15
NEAR_MISS_WAIT_FRAMES = 6  # ~0.5s: let the score finish peaking before falling back to Whisper
BUFFER_FRAMES = 30  # ~2.4s of audio kept for the Whisper check
WAKE_PHRASE = re.compile(r"\b(hey|hi|hello|hiya|ok|okay)\b[\s,.!]*(jarvis|jervis|jarvi)\b", re.IGNORECASE)
# "Bye Jarvis" quits JARVIS entirely (Whisper often writes it "By Jarvis"). The wake-word model keys
# on "Jarvis", so it can fire on this too.
GOODBYE_PHRASE = re.compile(r"\b(bye|by|buy|goodbye|good bye)\b[\s,.!]*(jarvis|jervis|jarvi)\b", re.IGNORECASE)

_recent_frames: deque[np.ndarray] = deque(maxlen=BUFFER_FRAMES)
_near_miss_frames_left = 0


def create_model() -> Model:
    """openWakeWord ships a pretrained "Hey Jarvis" model — free, offline, no key needed.

    First run requires a one-time model download; see README setup step 3.
    """
    return Model(wakeword_models=[WAKE_MODEL_NAME], inference_framework="onnx")


def _whisper_confirms() -> bool:
    text = stt.transcribe(np.concatenate(list(_recent_frames)).tolist())
    return bool(WAKE_PHRASE.search(text) or GOODBYE_PHRASE.search(text))


def is_goodbye(text: str) -> bool:
    return bool(GOODBYE_PHRASE.search(text))


def recent_audio() -> list[int]:
    """The last ~2.4s of audio, which ends with the wake phrase just detected."""
    return np.concatenate(list(_recent_frames)).tolist() if _recent_frames else []


def said_goodbye() -> bool:
    """Right after a detection: was it actually "Bye Jarvis"? Checks the last ~2.4s of audio."""
    if not _recent_frames:
        return False
    return is_goodbye(stt.transcribe(np.concatenate(list(_recent_frames)).tolist()))


def detected(model: Model, frame: np.ndarray) -> bool:
    """True on "Hey Jarvis", "Hello Jarvis" or "Hi Jarvis"."""
    global _near_miss_frames_left
    _recent_frames.append(frame)
    score = model.predict(frame)[WAKE_MODEL_NAME]
    if score >= THRESHOLD:
        _near_miss_frames_left = 0
        return True

    if _near_miss_frames_left == 0:
        if score >= NEAR_MISS_THRESHOLD:
            _near_miss_frames_left = NEAR_MISS_WAIT_FRAMES
        return False

    _near_miss_frames_left -= 1
    if _near_miss_frames_left > 0:
        return False
    if _whisper_confirms():
        return True
    _recent_frames.clear()  # don't re-check the same audio
    return False


def reset(model: Model) -> None:
    """Clear the model's rolling audio buffer after a conversation so leftover scores from before
    can't fire a phantom wake-up."""
    global _near_miss_frames_left
    _recent_frames.clear()
    _near_miss_frames_left = 0
    if hasattr(model, "reset"):
        model.reset()
