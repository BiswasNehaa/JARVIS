import pvporcupine

from . import config


def create_porcupine():
    """Porcupine ships a built-in "jarvis" keyword — no custom training needed."""
    return pvporcupine.create(
        access_key=config.PICOVOICE_ACCESS_KEY,
        keywords=[config.WAKE_WORD],
    )
