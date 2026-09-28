import os
import time
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


def _record_command(mic: Microphone, no_speech_seconds: float | None = None) -> list[int]:
    samples: list[int] = []
    speech_started = False
    silent_frames = 0
    stop_reason = "max length"
    no_speech_frames = NO_SPEECH_FRAMES if no_speech_seconds is None else int(no_speech_seconds * 1000 / FRAME_MS)

    for frame_index in range(MAX_FRAMES):
        frame = mic.read_frame()
        samples.extend(frame.tolist())

        amplitude = np.abs(frame).mean()
        hud.set_audio_level(min(1.0, amplitude / config.AUDIO_LEVEL_REFERENCE))

        if _speech.is_speech(frame):
            speech_started = True
            silent_frames = 0
        elif speech_started:
            silent_frames += 1
            if silent_frames >= SILENCE_HANG_FRAMES:
                stop_reason = "silence"
                break
        elif frame_index >= no_speech_frames:
            stop_reason = "no speech"
            break

    _last_recording["stop_reason"] = stop_reason
    _last_recording["seconds"] = len(samples) / SAMPLE_RATE
    return samples


def _is_stop_command(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in config.STOP_PHRASES)


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
                    samples = _record_command(mic, no_speech_seconds=config.FOLLOW_UP_SECONDS if follow_up else None)
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
                    text = stt.transcribe(samples)
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
                        elif (
                            best_name is not None
                            and best_name == last_speaker_name
                            and score >= config.SPEAKER_STICKY_THRESHOLD
                        ):
                            # A near miss from whoever was just talking is almost always the same
                            # person on an off turn — re-asking their name here is what made JARVIS
                            # seem to forget people mid-session.
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
                    history[:] = history[-20:]  # keep token cost bounded

                    hud.set_state("SPEAKING")
                    tts_timing = tts.speak(reply)
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
