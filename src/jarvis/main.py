from pvrecorder import PvRecorder

from . import brain, config, stt, tts
from .wake_word import create_porcupine


def _record_command(recorder: PvRecorder, sample_rate: int) -> list[int]:
    num_frames = int(sample_rate * config.COMMAND_RECORD_SECONDS / recorder.frame_length)
    samples: list[int] = []
    for _ in range(num_frames):
        samples.extend(recorder.read())
    return samples


def main() -> None:
    config.require_keys()

    porcupine = create_porcupine()
    recorder = PvRecorder(frame_length=porcupine.frame_length)
    recorder.start()

    history: list[dict] = []

    print('JARVIS is listening. Say "Jarvis" to wake me up. (Ctrl+C to quit)')

    try:
        while True:
            frame = recorder.read()
            if porcupine.process(frame) >= 0:
                print("Wake word detected — listening...")
                samples = _record_command(recorder, porcupine.sample_rate)

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
    finally:
        recorder.stop()
        recorder.delete()
        porcupine.delete()


if __name__ == "__main__":
    main()
