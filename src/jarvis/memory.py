"""Long-term memory: facts each person has shared (likes, plans, people, preferences), one JSON file
per speaker under data/memory/ (gitignored, it's personal). The brain decides what's worth keeping
through the remember/forget skills; everything saved is shown to it at the start of every reply."""

import json
import re
from pathlib import Path

from . import config


def _path(speaker: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", speaker).strip("_") or "unknown"
    return config.MEMORY_DIR / f"{safe}.json"


def load(speaker: str) -> list[str]:
    path = _path(speaker)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _save(speaker: str, facts: list[str]) -> None:
    path = _path(speaker)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")


def add(speaker: str, fact: str) -> str:
    fact = fact.strip()
    if not fact:
        return "Nothing to remember."
    facts = load(speaker)
    if fact.lower() in (f.lower() for f in facts):
        return "Already remembered."
    facts.append(fact)
    _save(speaker, facts[-config.MEMORY_MAX_FACTS:])  # oldest drop off first
    return "Remembered."


def forget(speaker: str, numbers: list[int]) -> str:
    """numbers: 1-based positions from the list shown in the prompt."""
    facts = load(speaker)
    drop = {n - 1 for n in numbers if 1 <= n <= len(facts)}
    if not drop:
        return "Nothing matched, so nothing was forgotten."
    _save(speaker, [f for i, f in enumerate(facts) if i not in drop])
    return f"Forgot {len(drop)} thing{'s' if len(drop) > 1 else ''}."


# A word spelled out letter by letter, as Whisper writes it: "D-I-G-G-E-R", "D I G G E R", "D.I.G.G.E.R."
_SPELLED = re.compile(r"(?<![A-Za-z'’])[A-Za-z](?:[-‐‑.\s]{1,2}[A-Za-z](?![A-Za-z])){3,}")
MAX_WORDS = 50


def _words_path(speaker: str) -> Path:
    return _path(speaker).with_name(_path(speaker).stem + "_words.json")


def words(speaker: str) -> list[str]:
    """Names and titles this person has spelled out, so Whisper and the brain get them right next time."""
    try:
        return json.loads(_words_path(speaker).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def learn_spelled_words(speaker: str, text: str) -> list[str]:
    """Save any word spelled out letter by letter in `text`. Returns the newly learned words."""
    known = words(speaker)
    learned = []
    for match in _SPELLED.finditer(text):
        word = "".join(re.findall(r"[A-Za-z]", match.group())).capitalize()
        if word.lower() not in (w.lower() for w in known + learned):
            learned.append(word)
    if learned:
        path = _words_path(speaker)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps((known + learned)[-MAX_WORDS:], indent=2, ensure_ascii=False), encoding="utf-8")
    return learned


def for_prompt(speaker: str) -> str:
    facts = load(speaker)
    if not facts:
        return "(nothing yet)"
    return "\n".join(f"{i}. {fact}" for i, fact in enumerate(facts, 1))
