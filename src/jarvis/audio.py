from collections import deque

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


VAD_SUBFRAME_SAMPLES = 320  # webrtcvad only accepts 10/20/30ms chunks; 1280 = 4 x 20ms

try:
    import webrtcvad
except ImportError:  # pragma: no cover - webrtcvad-wheels is in requirements.txt
    webrtcvad = None


NOISE_FLOOR_FRAMES = 50  # ~4s of idle audio remembered for the background-noise estimate
NOISE_FLOOR_MULTIPLIER = 2.0  # a frame must be this many times louder than the room to count as speech


class SpeechDetector:
    """Decides whether an 80ms frame contains speech.

    A fixed amplitude threshold broke in noisy rooms: a fan or hum sits above it, "quiet" never
    registers, and every command records to the max length. So the threshold adapts to the room
    (learned from idle audio while waiting for the wake word), and webrtcvad, when installed, must
    also agree the frame sounds like a voice.
    """

    def __init__(self, aggressiveness: int, rms_threshold: float) -> None:
        self._vad = webrtcvad.Vad(aggressiveness) if webrtcvad is not None else None
        self._min_threshold = rms_threshold
        self._idle_levels: deque[float] = deque(maxlen=NOISE_FLOOR_FRAMES)

    def observe_background(self, frame: np.ndarray) -> None:
        """Feed idle frames (while waiting for the wake word) to learn the room's noise level."""
        self._idle_levels.append(float(np.abs(frame).mean()))

    @property
    def threshold(self) -> float:
        if not self._idle_levels:
            return self._min_threshold
        noise_floor = float(np.percentile(self._idle_levels, 25))
        return max(self._min_threshold, noise_floor * NOISE_FLOOR_MULTIPLIER)

    def is_speech(self, frame: np.ndarray) -> bool:
        if float(np.abs(frame).mean()) < self.threshold:
            return False
        if self._vad is None:
            return True
        voiced = 0
        for start in range(0, len(frame) - VAD_SUBFRAME_SAMPLES + 1, VAD_SUBFRAME_SAMPLES):
            chunk = frame[start:start + VAD_SUBFRAME_SAMPLES].tobytes()
            if self._vad.is_speech(chunk, SAMPLE_RATE):
                voiced += 1
        return voiced >= 2
