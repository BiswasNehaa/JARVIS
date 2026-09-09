import time

import numpy as np
import webview

from . import brain, config, hud, speaker, stt, tts, wake_word
from .audio import SAMPLE_RATE, FRAME_SAMPLES, Microphone

ACTIVATING_FLASH_SECONDS = 0.35

FRAME_MS = 1000 * FRAME_SAMPLES / SAMPLE_RATE
SILENCE_HANG_FRAMES = int(config.SILENCE_HANG_MS / FRAME_MS)
MAX_FRAMES = int(config.MAX_COMMAND_SECONDS * 1000 / FRAME_MS)


def _record_command(mic: Microphone) -> list[int]:
    samples: list[int] = []
    speech_started = False
    silent_frames = 0

    for _ in range(MAX_FRAMES):
        frame = mic.read_frame()
        samples.extend(frame.tolist())

        amplitude = np.abs(frame).mean()
        hud.set_audio_level(min(1.0, amplitude / config.AUDIO_LEVEL_REFERENCE))

        if amplitude >= config.SILENCE_RMS_THRESHOLD:
            speech_started = True
            silent_frames = 0
        elif speech_started:
            silent_frames += 1
            if silent_frames >= SILENCE_HANG_FRAMES:
                break

    return samples


def _is_stop_command(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in config.STOP_PHRASES)


NAME_PREFIXES = ("my name is ", "i'm ", "i am ", "it's ", "this is ", "call me ")


def _extract_name(text: str) -> str:
    lowered = text.strip().lower()
    for prefix in NAME_PREFIXES:
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix):]
            break
    name = lowered.strip().rstrip(".!?")
    return name[:1].upper() + name[1:] if name else "friend"


def _enroll_new_speaker(mic: Microphone, first_utterance_samples: list[int]) -> str:
    tts.speak("I don't think we've met — what's your name?")

    hud.set_state("LISTENING")
    answer_samples = _record_command(mic)
    hud.set_audio_level(0)

    answer_text = stt.transcribe(answer_samples)
    name = _extract_name(answer_text) if answer_text else "friend"

    hud.set_state("PROCESSING")
    speaker.enroll(name, [speaker.embed(first_utterance_samples), speaker.embed(answer_samples)])

    hud.set_state("SPEAKING")
    tts.speak(f"Nice to meet you, {name}. I'll remember your voice from now on.")
    return name


def _run_voice_loop() -> None:
    model = wake_word.create_model()
    history: list[dict] = []

    print('JARVIS is listening. Say "Hey Jarvis" to wake me up. (Close the HUD window to quit)')
    hud.set_state("IDLE")

    with Microphone() as mic:
        while True:
            frame = mic.read_frame()
            if not wake_word.detected(model, frame):
                continue

            print("Wake word detected — listening...")
            hud.show_window()
            hud.set_state("ACTIVATING")
            time.sleep(ACTIVATING_FLASH_SECONDS)
            hud.set_state("LISTENING")

            try:
                samples = _record_command(mic)
                hud.set_audio_level(0)

                text = stt.transcribe(samples)
                if not text:
                    print("(didn't catch that)")
                    hud.set_state("IDLE")
                    hud.hide_window()
                    continue
                print(f"You: {text}")

                if _is_stop_command(text):
                    print("(session stopped)")
                    hud.set_state("IDLE")
                    hud.hide_window()
                    continue

                speaker_name = speaker.identify(speaker.embed(samples))
                if speaker_name is None:
                    speaker_name = _enroll_new_speaker(mic, samples)
                else:
                    print(f"(recognized voice: {speaker_name})")

                hud.set_state("PROCESSING")
                reply = brain.respond(text, history, speaker_name=speaker_name)
                print(f"JARVIS: {reply}")

                history.append({"role": "user", "content": text})
                history.append({"role": "assistant", "content": reply})
                history[:] = history[-20:]  # keep token cost bounded

                hud.set_state("SPEAKING")
                tts.speak(reply)
            except Exception as exc:  # noqa: BLE001 - keep the loop alive across one bad turn
                print(f"(error handling that: {exc})")
                hud.set_state("ERROR")
                time.sleep(1.0)

            hud.set_state("IDLE")
            hud.hide_window()


def main() -> None:
    config.require_keys()
    hud.create_window()
    webview.start(_run_voice_loop)


if __name__ == "__main__":
    main()
