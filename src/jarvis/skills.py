import datetime
import subprocess
import threading

from . import config, tts

SKILL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current local time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Get the current local date.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on the user's computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {
                        "type": "string",
                        "enum": sorted(config.ALLOWED_APPS.keys()),
                        "description": "Which app to open.",
                    }
                },
                "required": ["app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_timer",
            "description": "Start a countdown timer that announces itself out loud when it finishes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {"type": "integer", "description": "How long to count down, in seconds."},
                    "label": {"type": "string", "description": "What the timer is for, e.g. 'pasta'."},
                },
                "required": ["seconds"],
            },
        },
    },
]


def _get_current_time() -> str:
    return datetime.datetime.now().strftime("%I:%M %p").lstrip("0")


def _get_current_date() -> str:
    return datetime.datetime.now().strftime("%A, %B %d, %Y")


def _open_app(app: str) -> str:
    key = (app or "").strip().lower()
    exe = config.ALLOWED_APPS.get(key)
    if not exe:
        return f"'{app}' isn't in the list of apps I'm allowed to open."
    try:
        subprocess.Popen([exe])
    except OSError as exc:
        return f"Tried to open {key} but it failed: {exc}"
    return f"Opened {key}."


def _start_timer(seconds: int, label: str = "") -> str:
    def fire() -> None:
        tts.speak(f"{label} timer's up." if label else "Timer's up.")

    threading.Timer(max(seconds, 0), fire).start()
    return f"Timer started for {seconds} seconds{f' ({label})' if label else ''}. Will announce out loud when it's done."


def dispatch(name: str, arguments: dict) -> str:
    if name == "get_current_time":
        return _get_current_time()
    if name == "get_current_date":
        return _get_current_date()
    if name == "open_app":
        return _open_app(arguments.get("app", ""))
    if name == "start_timer":
        return _start_timer(int(arguments.get("seconds", 0)), arguments.get("label", ""))
    return f"Unknown skill: {name}"
