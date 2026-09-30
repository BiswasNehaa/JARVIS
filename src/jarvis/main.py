import os
import re
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import webview

from . import brain, config, hud, speaker, stt, tts, wake_word
from .audio import SAMPLE_RATE, FRAME_SAMPLES, Microphone, SpeechDetector

ACTIVATING_FLASH_SECONDS = 0.35

FRAME_MS = 1000 * FRAME_SAMPLES / SAMPLE_RATE
SILENCE_HANG_FRAMES = int(config.SILENCE_HANG_MS / FRAME_MS)
MAX_FRAMES = int(config.MAX_COMMAND_SECONDS * 1000 / FRAME_MS)
NO_SPEECH_FRAMES = int(config.NO_SPEECH_TIMEOUT_SECONDS * 1000 / FRAME_MS)

_speech = SpeechDetector(config.VAD_AGGRESSIVENESS, config.SILENCE_RMS_THRESHOLD)
_last_recording: dict = {}  # stop_reason + seconds of the most recent _record_command, for timing logs
_background = ThreadPoolExecutor(max_workers=2)


MAX_SILENCE_HANG_FRAMES = int(config.MAX_SILENCE_HANG_MS / FRAME_MS)

# If the transcript so far ends on one of these, you're probably mid-thought ("I was thinking that...
# um"), so keep listening through the pause instead of replying.
UNFINISHED_ENDINGS = {
    "and", "but", "or", "so", "because", "cause", "the", "a", "an", "to", "of", "with", "for", "in",
    "on", "at", "about", "if", "that", "which", "when", "what", "like", "then", "my", "your", "um", "uh", "umm", "uhh", "hmm", "maybe", "also", "just", "than",
}


def _sounds_finished(text: str) -> bool:
    """Whisper punctuates a finished sentence ("...right?") and usually leaves a trailing-off one bare
    or with a comma/ellipsis — cheap, decent signal for "done talking" vs "pausing to think"."""
    text = text.strip()
    if not text:
        return True  # nothing intelligible, don't hang around waiting for it
    if text.endswith(("...", "…", ",", "-", "—")) or text[-1] not in ".?!":
        return False
    last_word = text.rstrip(".?!").split()[-1].lower().strip("\"'") if text.rstrip(".?!").split() else ""
    return last_word not in UNFINISHED_ENDINGS


def _record_command(mic: Microphone, no_speech_seconds: float | None = None, context: str = "") -> list[int]:
    """Record until you're done talking.

    A short pause (SILENCE_HANG_MS) only *might* be the end: JARVIS transcribes what it has so far,
    in the background while still listening, and only stops if that reads like a finished sentence.
    Otherwise it waits out pauses up to MAX_SILENCE_HANG_MS, so a 2-3s pause to think mid-sentence
    doesn't get cut off. The check's transcript is kept in _last_recording["text"] so the main loop
    doesn't transcribe the same audio twice.
    """
    samples: list[int] = []
    speech_started = False
    silent_frames = 0
    stop_reason = "max length"
    no_speech_frames = NO_SPEECH_FRAMES if no_speech_seconds is None else int(no_speech_seconds * 1000 / FRAME_MS)
    check = None  # background transcription of everything said before the current pause
    check_is_current = False  # False once you start talking again after that check was started
    _last_recording.pop("text", None)

    for frame_index in range(MAX_FRAMES):
        frame = mic.read_frame()
        samples.extend(frame.tolist())

        amplitude = np.abs(frame).mean()
        hud.set_audio_level(min(1.0, amplitude / config.AUDIO_LEVEL_REFERENCE))

        if _speech.is_speech(frame):
            speech_started = True
            silent_frames = 0
            check_is_current = False
        elif speech_started:
            silent_frames += 1
            if silent_frames >= MAX_SILENCE_HANG_FRAMES:
                stop_reason = "long pause"
                break
            if silent_frames >= SILENCE_HANG_FRAMES:
                if not check_is_current and (check is None or check.done()):
                    check = _background.submit(stt.transcribe, list(samples), keep_fillers=True, context=context)
                    check_is_current = True
                elif check_is_current and check.done() and _sounds_finished(check.result()):
                    stop_reason = "silence"
                    break
        elif frame_index >= no_speech_frames:
            stop_reason = "no speech"
            break

    if check_is_current and check is not None:
        # Audio after the check was all silence, so its transcript covers the whole recording.
        _last_recording["text"] = check.result()
    _last_recording["stop_reason"] = stop_reason
    _last_recording["seconds"] = len(samples) / SAMPLE_RATE
    return samples


def _is_stop_command(text: str) -> bool:
    lowered = text.lower()
    if re.sub(r"[^a-z ]", "", lowered).strip() in {"stop", "stop it", "stop talking", "okay stop", "ok stop"}:
        return True
    return any(phrase in lowered for phrase in config.STOP_PHRASES)


BARGE_IN_WINDOW_FRAMES = 20  # ~1.6s of audio per "did she say stop?" check
BARGE_IN_CHECK_EVERY = 8  # ~0.64s between checks
def _words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _heard_stop(text: str, reply: str) -> bool:
    """The mic also hears JARVIS's own voice. If the reply itself says "stop" ("I'd rather stop the
    bad guys"), a "stop" heard with the same word before or after it is JARVIS's echo, not you."""
    heard, said = _words(text), _words(reply)
    echo_neighbors = [
        (said[i - 1] if i > 0 else None, said[i + 1] if i + 1 < len(said) else None)
        for i, word in enumerate(said) if word == "stop"
    ]
    for i, word in enumerate(heard):
        if word != "stop":
            continue
        before = heard[i - 1] if i > 0 else None
        after = heard[i + 1] if i + 1 < len(heard) else None
        is_echo = any(
            (before is not None and before == b) or (after is not None and after == a)
            for b, a in echo_neighbors
        )
        if not is_echo:
            return True
    return False


def _listen_for_stop(mic: Microphone, model, reply: str, done: threading.Event) -> None:
    """While JARVIS talks, listen for "stop" (or "Hey Jarvis") and cut the speech off."""
    window: deque[np.ndarray] = deque(maxlen=BARGE_IN_WINDOW_FRAMES)
    frames_since_check = 0
    while not done.is_set():
        frame = mic.read_frame()
        window.append(frame)
        if wake_word.detected(model, frame):
            tts.interrupt()
            return
        frames_since_check += 1
        if frames_since_check < BARGE_IN_CHECK_EVERY or not any(_speech.is_speech(f) for f in window):
            continue
        frames_since_check = 0
        if _heard_stop(stt.transcribe(np.concatenate(window).tolist()), reply):
            tts.interrupt()
            return


def _speak_interruptible(mic: Microphone, model, reply: str) -> dict:
    done = threading.Event()
    listener = threading.Thread(target=_listen_for_stop, args=(mic, model, reply, done), daemon=True)
    listener.start()
    try:
        timing = tts.speak(reply)
    finally:
        done.set()
        listener.join()
        wake_word.reset(model)
    if timing.get("interrupted"):
        print("(stopped talking — listening)")
    return timing


NAME_PREFIXES = ("my name is ", "i'm ", "i am ", "it's ", "this is ", "call me ")

# Whisper hallucinates short filler words on noise/silence fairly often — without this blocklist,
# a misheard "Hi"/"Okay"/etc. passes the 1-2-word-alpha check below and gets saved as a real name,
# splitting one person's voiceprint into several and breaking future recognition.
NON_NAME_WORDS = {
    "hi", "hello", "hey", "yo", "okay", "ok", "yes", "yeah", "yep", "no", "nope", "nah",
    "sure", "um", "uh", "uhh", "umm", "hmm", "what", "huh", "sorry", "thanks", "please",
    "stop", "bye", "goodbye",
}

MIN_SPEAKER_UTTERANCE_SECONDS = 1.5  # below this, resemblyzer embeddings are too unstable to trust
SHORT_UTTERANCE_SECONDS = 4.0  # below this, a weak match never triggers "what's your name?" for a known speaker


def _extract_name(text: str) -> str:
    """Pull a name out of the answer to "what's your name?" — falls back to config.USER_NAME
    rather than storing a mistranscribed sentence (or a misheard filler word) as a permanent
    voiceprint key."""
    lowered = text.strip().lower()
    for prefix in NAME_PREFIXES:
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix):]
            break
    name = lowered.strip().rstrip(".!?").split(",")[0].strip()
    words = name.split()
    if not (1 <= len(words) <= 2) or not all(w.isalpha() for w in words):
        return config.USER_NAME
    if any(w in NON_NAME_WORDS for w in words):
        return config.USER_NAME
    return " ".join(w.capitalize() for w in words)


def _enroll_new_speaker(mic: Microphone, first_utterance_samples: list[int]) -> str:
    tts.speak("I don't think we've met — what's your name?")

    hud.set_state("LISTENING")
    answer_samples = _record_command(mic)
    hud.set_audio_level(0)

    answer_text = stt.transcribe(answer_samples)
    name = _extract_name(answer_text) if answer_text else "friend"

    hud.set_state("PROCESSING")
    # The name answer is often a single word, too short for a trustworthy embedding — only keep it
    # as a voice sample when it's long enough. The first utterance always is (it had to be, to get here).
    clips = [first_utterance_samples]
    if len(answer_samples) >= int(MIN_SPEAKER_UTTERANCE_SECONDS * SAMPLE_RATE):
        clips.append(answer_samples)
    speaker.enroll(name, [speaker.embed(clip) for clip in clips])

    hud.set_state("SPEAKING")
    tts.speak(f"Nice to meet you, {name}. I'll remember your voice from now on.")
    return name


def _log_timing(
    t_start, t_recorded, t_transcribed, t_identified=None, t_replied=None, tts_timing=None, enroll_seconds=0.0
) -> None:
    """One line per turn showing where the time went. "wait" is the gap you actually feel: from the
    moment you stop talking (end of recording) to JARVIS's first word coming out of the speaker."""
    rec = _last_recording
    parts = [
        f"record {t_recorded - t_start:.1f}s (stopped by {rec.get('stop_reason')}, "
        f"{rec.get('seconds', 0):.1f}s audio, speech threshold {_speech.threshold:.0f})"
    ]
    parts.append(f"stt {t_transcribed - t_recorded:.2f}s")
    if t_identified is not None:
        parts.append(f"speaker {t_identified - t_transcribed - enroll_seconds:.2f}s")
        if enroll_seconds:
            parts.append(f"name enrollment {enroll_seconds:.1f}s (not counted in WAIT)")
    if t_replied is not None:
        parts.append(f"brain {t_replied - t_identified:.2f}s")
    if tts_timing is not None:
        parts.append(f"tts first audio {tts_timing['first_audio']:.2f}s")
        wait = (t_replied - t_recorded) - enroll_seconds + tts_timing["first_audio"]
        parts.append(f"WAIT {wait:.1f}s")
    print("[timing] " + " | ".join(parts))


def _warm_up() -> None:
    """Load Whisper and the voice encoder now, at startup, instead of on the first "Hey Jarvis" —
    otherwise the first reply pays several seconds of model loading."""
    t = time.perf_counter()
    stt.transcribe([0] * SAMPLE_RATE)
    speaker.embed((np.random.default_rng(0).normal(0, 2000, SAMPLE_RATE * 2)).astype(np.int16).tolist())
    brain.warm_up()
    print(f"[timing] models warmed up in {time.perf_counter() - t:.1f}s")


def _run_voice_loop() -> None:
    _background.submit(_warm_up).add_done_callback(
        lambda f: f.exception() and print(f"(warm-up failed, first reply will be slower: {f.exception()})")
    )
    model = wake_word.create_model()
    history: list[dict] = []
    last_turn_at = 0.0
    last_speaker_name: str | None = None
    min_speaker_samples = int(MIN_SPEAKER_UTTERANCE_SECONDS * SAMPLE_RATE)

    print('JARVIS is listening. Say "Hey Jarvis", "Hello Jarvis" or "Hi Jarvis" to wake me up. (Close the HUD window to quit)')
    hud.set_state("IDLE")

    with Microphone() as mic:
        while True:
            frame = mic.read_frame()
            if not wake_word.detected(model, frame):
                _speech.observe_background(frame)
                continue

            print("Wake word detected — listening...")
            # A new chat after a long gap starts fresh: old topics left in the history can pull
            # answers toward what was said earlier instead of what was just asked.
            if history and time.monotonic() - last_turn_at > config.HISTORY_RESET_SECONDS:
                history.clear()
            hud.show_window()
            hud.set_state("ACTIVATING")
            time.sleep(ACTIVATING_FLASH_SECONDS)

            # Conversation mode: after JARVIS answers, keep listening for a follow-up without
            # needing "Hey Jarvis" again. Goes back to sleep after FOLLOW_UP_SECONDS of silence,
            # a stop phrase, or an error.
            follow_up = False
            while True:
                keep_listening = False
                hud.set_state("LISTENING")
                if follow_up:
                    mic.drain()  # drop JARVIS's own voice, captured by the mic while it was speaking
                    print("(listening for a follow-up...)")
                try:
                    t_start = time.perf_counter()
                    enroll_seconds = 0.0  # the "what's your name?" exchange is a conversation, not lag
                    # What's been said so far helps Whisper hear the same words right the next time.
                    stt_context = stt.conversation_prompt(history, last_speaker_name or config.USER_NAME)
                    samples = _record_command(
                        mic, no_speech_seconds=config.FOLLOW_UP_SECONDS if follow_up else None, context=stt_context
                    )
                    hud.set_audio_level(0)
                    t_recorded = time.perf_counter()
                    if follow_up and _last_recording["stop_reason"] == "no speech":
                        print("(no follow-up — say \"Hey Jarvis\" to wake me again)")
                        break

                    # Transcription and the voiceprint embedding are independent, so run them side by
                    # side instead of one after the other (both release the GIL while they crunch).
                    long_enough = len(samples) >= min_speaker_samples
                    embedding_future = _background.submit(speaker.embed, samples) if long_enough else None
                    hud.set_state("PROCESSING")
                    text = _last_recording.get("text")
                    if text is None:
                        text = stt.transcribe(samples, context=stt_context)
                    t_transcribed = time.perf_counter()
                    if not text:
                        print("(didn't catch that)")
                        _log_timing(t_start, t_recorded, t_transcribed)
                        break
                    print(f"You: {text}")

                    if _is_stop_command(text):
                        print("(session stopped)")
                        break

                    if embedding_future is None:
                        speaker_name = last_speaker_name or config.USER_NAME
                    else:
                        embedding = embedding_future.result()
                        best_name, score = speaker.best_match(embedding)
                        if best_name is not None and score >= config.SPEAKER_MATCH_THRESHOLD:
                            speaker_name = best_name
                            print(f"(recognized voice: {speaker_name}, {score:.2f})")
                            # Keep learning from confident matches so the voiceprint tracks how you
                            # actually sound day to day, not just the enrollment clips.
                            speaker.enroll(speaker_name, [embedding])
                        elif best_name is not None and score >= config.SPEAKER_STICKY_THRESHOLD:
                            # A near miss is almost always the enrolled person on an off turn: Neha's
                            # own saved samples score as low as 0.69 against her voiceprint, while
                            # other voices tested (2026-09-28) topped out at 0.67. Asking her name here
                            # is what made JARVIS "forget" her on the first turn of every run.
                            # Near misses aren't learned from, so they can't drag the voiceprint off.
                            speaker_name = best_name
                            print(f"(near match, assuming still {speaker_name}, {score:.2f})")
                        elif last_speaker_name and (
                            follow_up or len(samples) < SHORT_UTTERANCE_SECONDS * SAMPLE_RATE
                        ):
                            # Short phrases ("How about you?") and mid-conversation follow-ups give
                            # shaky embeddings (Neha scored 0.65 on one); asking her name there cost
                            # 14s and broke the flow. Only a confident match to someone else switches.
                            speaker_name = last_speaker_name
                            print(f"(weak match {score:.2f}, staying with {speaker_name} mid-conversation)")
                        else:
                            print(f"(voice not recognized — best {best_name}, {score:.2f} — asking for a name)")
                            t_enroll = time.perf_counter()
                            speaker_name = _enroll_new_speaker(mic, samples)
                            enroll_seconds = time.perf_counter() - t_enroll
                    last_speaker_name = speaker_name
                    t_identified = time.perf_counter()

                    hud.set_state("PROCESSING")
                    reply = brain.respond(text, history, speaker_name=speaker_name)
                    t_replied = time.perf_counter()
                    print(f"JARVIS: {reply}")

                    history.append({"role": "user", "content": text})
                    history.append({"role": "assistant", "content": reply})
                    history[:] = history[-2 * config.HISTORY_TURNS:]  # recent context only, stays on topic
                    last_turn_at = time.monotonic()

                    hud.set_state("SPEAKING")
                    tts_timing = _speak_interruptible(mic, model, reply)
                    _log_timing(t_start, t_recorded, t_transcribed, t_identified, t_replied, tts_timing, enroll_seconds)
                    keep_listening = True
                except Exception as exc:  # noqa: BLE001 - keep the loop alive across one bad turn
                    print(f"(error handling that: {exc})")
                    hud.set_state("ERROR")
                    time.sleep(1.0)
                    break

                if not keep_listening:
                    break
                follow_up = True

            hud.set_state("IDLE")
            hud.hide_window()
            mic.drain()
            wake_word.reset(model)


def main() -> None:
    config.require_keys()
    hud.create_window()
    webview.start(_run_voice_loop)
    # webview.start() returns once the HUD window is closed. Python then starts shutting down, but the
    # voice loop thread kept going on its own, and its next background task died with "cannot schedule
    # new futures after shutdown". Closing the window means quit, so actually quit.
    print("HUD window closed — JARVIS shutting down.")
    os._exit(0)


if __name__ == "__main__":
    main()
