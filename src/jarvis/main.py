from . import brain, config, stt, tts, wake_word
from .audio import SAMPLE_RATE, FRAME_SAMPLES, Microphone


def _record_command(mic: Microphone) -> list[int]:
    num_frames = int(SAMPLE_RATE * config.COMMAND_RECORD_SECONDS / FRAME_SAMPLES)
    samples: list[int] = []
    for _ in range(num_frames):
        samples.extend(mic.read_frame().tolist())
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
