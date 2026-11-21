"""Replay lines that used to get therapist-style replies and count how JARVIS answers now.

This calls Groq for real (needs GROQ_API_KEY in .env), so it's not part of the offline tests.
Tools are faked: nothing is opened, remembered or switched off while it runs.

    python -m evals.voice_check

Each line is sent in order as one conversation, the way she said them, with a pause between calls so
Groq's free-tier per-minute limit doesn't skew the result. A reply gets a flag for each therapist or
chatbot tell found in it; the score at the end is how many replies came back clean.
"""

import re
import sys
import time

from src.jarvis import brain, skills

# Lines from her own logs that got coaching questions, tips or counsellor mode before.
CONVERSATION = [
    # 2026-10-27 ("such a depressing AI")
    "I don't know, I'm a little frightened about my future. I have some interviews upcoming, but I "
    "don't know what to do. I think I'm not prepared, and I'm not feeling motivated to study also.",
    "I don't know.",
    "That they will pay me at the end of the month.",
    "I'm trying for AI engineer or an intern, but these days companies expect lots from our side. I "
    "don't know where to start, and I haven't been practicing DSA lately, and I hate DSA.",
    "I wanted you to be like a charming person, but you are such a depressing AI.",
    # 2026-10-28: Whisper's version of "Do you think I can crack a job?", once treated as a command
    "Do the thing, I can crack a job.",
    # 2026-11-11 (a productivity tip every turn)
    "I'm feeling so lost. I stopped studying for weeks and I feel like I've forgotten everything.",
    # 2026-10-09 (banter taken seriously)
    "There's a boy in my class who eats my brain, little monkey. I swear I'll kill him one day.",
]

TELLS = {
    "coaching question": re.compile(
        r"\b(what would make you|what's one thing|what is one thing|if you could (pick|nail)|how does that make you feel|"
        r"what do you think would help)\b",
        re.I,
    ),
    "tip or plan": re.compile(
        r"\b(set a timer|pomodoro|start with|try to|make a (list|plan|schedule)|break it (down|into)|"
        r"consistency|routine|step by step)\b",
        re.I,
    ),
    "therapist-speak": re.compile(
        r"\b(that sounds (really )?(intense|tough|hard|rough)|it's (totally |completely )?(okay|ok|valid|normal|fine) to feel|"
        r"your feelings|i hear you|that must be|you're not alone)\b",
        re.I,
    ),
    "stock opener": re.compile(r"^(sounds like|totally get|haha|got it|great question|absolutely)", re.I),
    "cheerleading": re.compile(r"\b(you've got this|you can do it|believe in yourself)\b", re.I),
    "refusal": re.compile(r"\b(i can't help with that|i'm sorry,? but)\b", re.I),
    "emoji": re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]"),
}
MAX_WORDS = 25
PAUSE_SECONDS = 15  # 8s still ran into the 8,000 tokens/minute limit


def _flags(reply: str, asked_before: bool) -> list[str]:
    reply = reply.replace("\u2019", "'")  # the model writes curly apostrophes
    found = [name for name, pattern in TELLS.items() if pattern.search(reply)]
    if len(reply.split()) > MAX_WORDS:
        found.append(f"over {MAX_WORDS} words")
    if reply.rstrip().endswith("?") and asked_before:
        found.append("second question in a row")
    return found


def main() -> int:
    tool_calls = []
    skills.dispatch = lambda name, args: tool_calls.append(name) or "done"

    history: list[dict] = []
    clean = 0
    questions = 0
    asked_before = False
    for i, said in enumerate(CONVERSATION):
        if i:
            time.sleep(PAUSE_SECONDS)
        tool_calls.clear()
        reply = brain.respond(said, history)
        flags = _flags(reply, asked_before)
        if tool_calls:
            flags.append("called " + ", ".join(tool_calls))
        asked_before = reply.rstrip().endswith("?")
        questions += asked_before
        clean += not flags
        history += [{"role": "user", "content": said}, {"role": "assistant", "content": reply}]
        print(f"\nYou:    {said}\nJARVIS: {reply}\n        {'clean' if not flags else 'FLAG: ' + '; '.join(flags)}")

    total = len(CONVERSATION)
    print(f"\n{clean}/{total} replies clean, {questions}/{total} ended in a question.")
    return 0 if clean == total else 1


if __name__ == "__main__":
    sys.exit(main())
