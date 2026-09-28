import threading
from pathlib import Path

import webview

_HTML_PATH = Path(__file__).resolve().parent.parent.parent / "hud" / "index.html"

# Small and docked bottom-center, like Windows' own voice-typing toolbar (Win+H)
# — not a persistent dashboard, a brief compact bar that appears on the wake
# word and vanishes after.
POPUP_WIDTH = 300
POPUP_HEIGHT = 76
BOTTOM_MARGIN = 110  # clears the taskbar + a small gap; nudge if it sits wrong

_window = None


def create_window() -> "webview.Window":
    global _window
    x = y = None
    if webview.screens:
        screen = webview.screens[0]
        x = max(0, (screen.width - POPUP_WIDTH) // 2)
        y = max(0, screen.height - POPUP_HEIGHT - BOTTOM_MARGIN)
    _window = webview.create_window(
        "JARVIS",
        url=_HTML_PATH.as_uri(),
        width=POPUP_WIDTH,
        height=POPUP_HEIGHT,
        x=x,
        y=y,
        frameless=True,
        easy_drag=False,
        on_top=True,
        background_color="#000000",
        hidden=True,  # starts invisible; main.py shows it on wake word, hides it after
    )
    return _window


def show_window() -> None:
    if _window is not None:
        _window.show()


def hide_window() -> None:
    if _window is not None:
        _window.hide()


def set_state(state: str) -> None:
    """state: 'IDLE' | 'ACTIVATING' | 'LISTENING' | 'PROCESSING' | 'SPEAKING' | 'ERROR' | 'SLEEPING'"""
    if _window is not None:
        _window.evaluate_js(f"setState('{state}')")


_pending_level: float | None = None
_level_ready = threading.Event()


def _level_sender() -> None:
    global _pending_level
    while True:
        _level_ready.wait()
        _level_ready.clear()
        level, _pending_level = _pending_level, None
        if level is not None and _window is not None:
            try:
                _window.evaluate_js(f"setAudioLevel({level})")
            except Exception:  # noqa: BLE001 - a dropped waveform update is harmless
                pass


threading.Thread(target=_level_sender, daemon=True).start()


def set_audio_level(level: float) -> None:
    """level: 0.0-1.0, how much the waveform should react to live audio right now.

    Non-blocking: evaluate_js waits on the GUI thread, and calling it inline every 80ms mic frame
    made recording fall behind real time. Only the newest level is sent; stale ones are dropped."""
    global _pending_level
    _pending_level = level
    _level_ready.set()


def _demo_cycle() -> None:
    if _window is not None:
        show_window()
        _window.evaluate_js("demoCycle()")


def main() -> None:
    """Standalone visual test — cycles through every state automatically so you
    can see them without running the full voice loop."""
    create_window()
    webview.start(_demo_cycle)


if __name__ == "__main__":
    main()
