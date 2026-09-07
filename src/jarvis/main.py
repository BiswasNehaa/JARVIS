import numpy as np

from . import brain, config, stt, tts, wake_word
from .audio import SAMPLE_RATE, FRAME_SAMPLES, Microphone

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

        if np.abs(frame).mean() >= config.SILENCE_RMS_THRESHOLD:
            speech_started = True
            silent_frames = 0
        elif speech_started:
            silent_frames += 1
            if silent_frames >= SILENCE_HANG_FRAMES:
                break

    return samples


def main() -> None:
    config.require_keys()

    model = wake_word.create_model()
    history: list[dict] = []

    print('JARVIS is listening. Say "Hey Jarvis" to wake me up. (Ctrl+C to quit)')

    with Microphone() as mic:
        try:
            while True:
                frame = mic.read_frame()
                if wake_word.detected(model, frame):
                    print("Wake word detected — listening...")
                    samples = _record_command(mic)

                    text = stt.transcribe(samples)
                    if not text:
                        print("(didn't catch that)")
                        continue
                    print(f"You: {text}")

                    reply = brain.respond(text, history)
                    print(f"JARVIS: {reply}")

                    history.append({"role": "user", "content": text})
                    history.append({"role": "assistant", "content": reply})
                    history[:] = history[-20:]  # keep token cost bounded

                    tts.speak(reply)
        except KeyboardInterrupt:
            print("\nShutting down.")


if __name__ == "__main__":
    main()
