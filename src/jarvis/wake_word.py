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
# tries outright. Anything above NEAR_MISS_THRESHOLD now gets that check. "Jarvis" mid-sentence
# ("What's up Jarvis", "Good morning Jarvis") often scores only 0.02-0.06, so the cutoff is low and most
# sentences said nearby get one ~0.7s Whisper pass; that never wakes JARVIS unless "Jarvis" is in it.
# Test clips (Indian + US voices, noise): 67/72 such phrases woke it at 0.02, 64 at 0.04, 59 at 0.06.
NEAR_MISS_THRESHOLD = config.WAKE_NEAR_MISS_THRESHOLD
# After a score above the cutoff, the check waits for the end of the sentence: QUIET_FRAMES of quiet
# (~0.25s), or MAX_WAIT_FRAMES (~1.1s) if the room never goes quiet. A fixed 0.6s wait checked "Good
# morning..." and "Can you hear me..." before "Jarvis" had been said, and then nothing re-checked.
QUIET_FRAMES = 3
MAX_WAIT_FRAMES = 14
NOISE_FRAMES = 60  # ~5s of recent frame levels, to tell quiet from talking in this room
QUIET_OVER_NOISE = 2.0  # a frame quieter than this many times the room's noise counts as a pause
BUFFER_FRAMES = 36  # ~2.9s of audio kept for the Whisper check: a slow "Hello... Jarvis" fits
# Whisper's spellings of "Jarvis" in an Indian accent include "Jervis", "Jarvi", "Jaarvis", "Jarwis",
# "Jarvy", "Jarbith", "Jarveth", "Jarvick": anything starting jarv/jarb/jerv/jarw. No common English
# word does, and this is only ever checked right after the wake-word model's score went up.
_JARVIS = r"(j[ae]a?r[vbw]\w*)"
JARVIS_WORD = re.compile(rf"\b{_JARVIS}", re.IGNORECASE)
# "Jarvis" anywhere in what was said wakes JARVIS ("What's up Jarvis", "Jarvis, are you there?",
# "Can you hear me Jarvis?"), unless it's clearly being talked about rather than to: "my Jarvis is
# broken", "a project called Jarvis". The pretrained model can't tell these apart (both score up to
# 1.0), so the words decide. "Your" isn't in the list: Whisper writes an Indian-accent "Yo Jarvis"
# as "Your Jarvis".
_TALKED_ABOUT = re.compile(
    r"\b(my|his|her|our|their|the|a|an|this|that|called|named|about|of|with|from|and|or|like|love|hate|use|using|build|built|building|made|making)[\s,]*$", re.IGNORECASE
)
# The strict form: a greeting right before "Jarvis". Used while JARVIS is speaking, so a mishearing of
# its own voice can't count as being called.
GREETING_PHRASE = re.compile(rf"\b(hey|hi|hello|helo|hallo|hiya|ok|okay)\b[\s,.!]*{_JARVIS}", re.IGNORECASE)
# "Bye Jarvis" quits JARVIS entirely (Whisper often writes it "By Jarvis"). The wake-word model keys
# on "Jarvis", so it can fire on this too.
GOODBYE_PHRASE = re.compile(rf"\b(bye|by|buy|goodbye|good bye)\b[\s,.!]*{_JARVIS}", re.IGNORECASE)


def is_wake_phrase(text: str, anywhere: bool = True) -> bool:
    """True when JARVIS is being called by name in text (see _TALKED_ABOUT for what doesn't count)."""
    if not anywhere:
        return bool(GREETING_PHRASE.search(text) or GOODBYE_PHRASE.search(text))
    return any(not _TALKED_ABOUT.search(text[:match.start()]) for match in JARVIS_WORD.finditer(text))


_recent_frames: deque[np.ndarray] = deque(maxlen=BUFFER_FRAMES)
_levels: deque[float] = deque(maxlen=NOISE_FRAMES)
_pending = False  # a near miss is waiting for the end of the sentence to be checked
_frames_waited = 0
_quiet_run = 0
_near_miss_peak = 0.0
_wake_text = ""  # what the Whisper check heard, when it's what woke JARVIS


def create_model() -> Model:
    """openWakeWord ships a pretrained "Hey Jarvis" model — free, offline, no key needed.

    First run requires a one-time model download; see README setup step 3.
    """
    return Model(wakeword_models=[WAKE_MODEL_NAME], inference_framework="onnx")


def _whisper_confirms(peak: float, anywhere: bool) -> bool:
    global _wake_text
    text = stt.transcribe(np.concatenate(list(_recent_frames)).tolist())
    confirmed = is_wake_phrase(text, anywhere)
    if confirmed:
        _wake_text = text
    if confirmed or "jar" in text.lower() or "jer" in text.lower():
        # Shows how close a missed try came, for tuning WAKE_NEAR_MISS_THRESHOLD
        print(f"(wake check: score {peak:.2f}, heard {text!r}{'' if confirmed else ' - not a wake phrase'})")
    return confirmed


def is_goodbye(text: str) -> bool:
    return bool(GOODBYE_PHRASE.search(text))


def recent_audio() -> list[int]:
    """The last ~2.9s of audio, which ends with the wake phrase just detected."""
    return np.concatenate(list(_recent_frames)).tolist() if _recent_frames else []


def recent_frames() -> list[np.ndarray]:
    """recent_audio(), as the 80ms frames it was heard in."""
    return list(_recent_frames)


REQUEST_MIN_WORDS = 2


def wake_request() -> str:
    """What was said after the name, when that's a request in itself: "what time is it" from
    "Jarvis, what time is it?", "I had a weird day" from "So Jarvis, I had a weird day". Empty when
    the name came last ("Hey Jarvis", "Can you hear me Jarvis?") or the model woke JARVIS without a
    Whisper check (a clear "Hey Jarvis" is never transcribed)."""
    matches = list(JARVIS_WORD.finditer(_wake_text))
    if not matches:
        return ""
    rest = re.sub(r"^[\s,.!?;:-]+", "", _wake_text[matches[-1].end():]).strip()
    return rest if len(re.findall(r"[a-zA-Z']+", rest)) >= REQUEST_MIN_WORDS else ""


def heard_text() -> str:
    """What the Whisper check heard, when that check is what woke JARVIS (else empty)."""
    return _wake_text


def check_wake(audio: list[int], heard: str = "") -> str:
    """Right after a wake-up: "goodbye" ("Bye Jarvis"), "wake", or "not for me" ("my Jarvis is
    broken"). audio: recent_audio() at detection; heard: heard_text() then, to skip transcribing again."""
    text = heard or stt.transcribe(audio)
    if is_goodbye(text):
        return "goodbye"
    # A sure score with no name in the transcript is Whisper garbling it ("Hey Jarvis" came out "Age
    # Arbus"), not a mistake by the model: only words showing JARVIS being talked about veto it.
    if is_wake_phrase(text) or not JARVIS_WORD.search(text):
        return "wake"
    print(f"(not woken: heard {text!r} - talking about JARVIS, not to it)")
    return "not for me"


def said_goodbye(audio: list[int]) -> bool:
    """Right after a detection: was it actually "Bye Jarvis"? audio: recent_audio() at detection."""
    return bool(audio) and is_goodbye(stt.transcribe(audio))


def _clear_pending() -> None:
    global _pending, _frames_waited, _quiet_run, _near_miss_peak, _wake_text
    _pending, _frames_waited, _quiet_run, _near_miss_peak = False, 0, 0, 0.0
    _wake_text = ""


def detected(model: Model, frame: np.ndarray, anywhere: bool = True) -> bool:
    """True when JARVIS is called by name: "Hey Jarvis", "What's up Jarvis", "Jarvis, are you there?".

    anywhere=False only accepts a greeting right before the name ("Hey/Hi/Hello Jarvis", "Bye Jarvis").
    """
    global _pending, _frames_waited, _quiet_run, _near_miss_peak
    _recent_frames.append(frame)
    level = float(np.abs(frame).mean())
    _levels.append(level)
    score = model.predict(frame)[WAKE_MODEL_NAME]
    if score >= THRESHOLD:
        # A sure score wakes at once, and the popup opens right away. The model scores "my Jarvis is
        # broken" as high as "Hey Jarvis", so main still runs check_wake() on this audio while the
        # popup animates and backs out if JARVIS was only being talked about. Waiting for that check
        # before opening (tried first) made every wake-up feel over a second slow.
        _clear_pending()
        return True

    if score >= NEAR_MISS_THRESHOLD:
        # Restart the wait while the score is still up: it can cross the cutoff on "Hel-" and only
        # peak on "-vis", and checking too early would cut "Jarvis" off the end of the clip.
        _pending, _frames_waited, _quiet_run = True, 0, 0
        _near_miss_peak = max(_near_miss_peak, score)
        return False
    if not _pending:
        return False

    _frames_waited += 1
    noise = float(np.percentile(_levels, 20))
    _quiet_run = _quiet_run + 1 if level < noise * QUIET_OVER_NOISE else 0
    if _quiet_run < QUIET_FRAMES and _frames_waited < MAX_WAIT_FRAMES:
        return False
    peak = _near_miss_peak
    _clear_pending()
    # The audio isn't cleared after a miss: "Hello" alone can score above the cutoff and get checked
    # before "Jarvis" is said, and the next check (on "Jarvis") needs "Hello" still in the clip.
    # Nothing re-checks the same audio in a loop, since a check only follows a new above-cutoff score.
    return _whisper_confirms(peak, anywhere)


def reset(model: Model) -> None:
    """Clear the model's rolling audio buffer after a conversation so leftover scores from before
    can't fire a phantom wake-up."""
    _recent_frames.clear()
    _clear_pending()
    if hasattr(model, "reset"):
        model.reset()
