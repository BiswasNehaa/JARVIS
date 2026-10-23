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

    def drain(self) -> None:
        """Throw away audio that piled up while nobody was reading (e.g. JARVIS talking), so the
        next read is live — otherwise JARVIS hears its own reply as your next command."""
        available = self._stream.read_available
        if available > 0:
            self._stream.read(available)

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
VOICE_LEVEL_PERCENTILE = 85  # of the wake-phrase frames: the loud ones, i.e. your voice, not the gap before it
VOICE_LEVEL_FRACTION = 0.35  # speech counts from this fraction of how loud your "Hey Jarvis" was


class SpeechDetector:
    """Decides whether an 80ms frame contains speech.

    A fixed amplitude threshold broke in noisy rooms: a fan or hum sits above it, "quiet" never
    registers, and every command records to the max length. So the threshold adapts to the room
    (learned from idle audio while waiting for the wake word), and webrtcvad, when installed, must
    also agree the frame sounds like a voice.

    The reverse broke too: with a quiet mic (or speaking from across the room) normal speech never
    reached the threshold, so every command ended with "no speech". So the threshold is also capped
    by how loud you said the wake phrase, which is the best sample there is of your voice right now.
    """

    def __init__(self, aggressiveness: int, rms_threshold: float) -> None:
        self._vad = webrtcvad.Vad(aggressiveness) if webrtcvad is not None else None
        self._min_threshold = rms_threshold
        self._idle_levels: deque[float] = deque(maxlen=NOISE_FLOOR_FRAMES)
        self._voice_level: float | None = None

    def observe_background(self, frame: np.ndarray) -> None:
        """Feed idle frames (while waiting for the wake word) to learn the room's noise level."""
        self._idle_levels.append(float(np.abs(frame).mean()))

    def observe_voice(self, samples: list[int]) -> None:
        """Feed the wake-phrase audio to learn how loud you sound through this mic right now."""
        audio = np.asarray(samples, dtype=np.int16)
        frames = len(audio) // FRAME_SAMPLES
        if frames == 0:
            return
        levels = np.abs(audio[:frames * FRAME_SAMPLES].reshape(frames, FRAME_SAMPLES)).mean(axis=1)
        self._voice_level = float(np.percentile(levels, VOICE_LEVEL_PERCENTILE))

    @property
    def threshold(self) -> float:
        noise_floor = float(np.percentile(self._idle_levels, 25)) if self._idle_levels else 0.0
        threshold = max(self._min_threshold, noise_floor * NOISE_FLOOR_MULTIPLIER)
        if self._voice_level is not None:
            # Never below the room's own noise, or a fan would count as talking.
            threshold = min(threshold, max(self._voice_level * VOICE_LEVEL_FRACTION, noise_floor * 1.3))
        return threshold

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
