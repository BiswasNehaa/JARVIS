import numpy as np
from openwakeword.model import Model

WAKE_MODEL_NAME = "hey_jarvis"
THRESHOLD = 0.5


def create_model() -> Model:
    """openWakeWord ships a pretrained "Hey Jarvis" model — free, offline, no key needed.

    First run requires a one-time model download; see README setup step 3.
    """
    return Model(wakeword_models=[WAKE_MODEL_NAME], inference_framework="onnx")


def detected(model: Model, frame: np.ndarray) -> bool:
    scores = model.predict(frame)
    return scores[WAKE_MODEL_NAME] >= THRESHOLD


def reset(model: Model) -> None:
    """Clear the model's rolling audio buffer after a conversation so leftover scores from before
    can't fire a phantom wake-up."""
    if hasattr(model, "reset"):
        model.reset()
