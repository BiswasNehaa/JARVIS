import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280  # 80ms @ 16kHz — the chunk size openWakeWord expects


class Microphone:
    def __init__(self) -> None:
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SAMPLES
        )

    def __enter__(self) -> "Microphone":
        self._stream.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stream.stop()
        self._stream.close()

    def read_frame(self) -> np.ndarray:
        data, _ = self._stream.read(FRAME_SAMPLES)
        return np.frombuffer(data, dtype=np.int16)
