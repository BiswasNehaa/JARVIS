from pathlib import Path

import webview

_HTML_PATH = Path(__file__).resolve().parent.parent.parent / "hud" / "index.html"

_window = None


def create_window() -> "webview.Window":
    global _window
    _window = webview.create_window(
        "JARVIS",
        url=_HTML_PATH.as_uri(),
        width=520,
        height=520,
        frameless=True,
        easy_drag=False,  # dragging on canvas orbits the camera instead
        on_top=True,
        background_color="#000000",
    )
    return _window


def set_state(state: str) -> None:
    """state: 'IDLE' | 'ACTIVATING' | 'LISTENING' | 'PROCESSING' | 'SPEAKING' | 'ERROR' | 'SLEEPING'"""
    if _window is not None:
        _window.evaluate_js(f"setState('{state}')")


def _demo_cycle() -> None:
    if _window is not None:
        _window.evaluate_js("demoCycle()")


def main() -> None:
    """Standalone visual test — cycles through every state automatically so you
    can see them without running the full voice loop."""
    create_window()
    webview.start(_demo_cycle)


if __name__ == "__main__":
    main()
