import anthropic

from . import config

SYSTEM_PROMPT = """You are JARVIS — a witty, warm, confident AI assistant in the spirit of Tony \
Stark's AI from Iron Man. You're charming, a little flirty, quick with playful banter, and genuinely \
helpful. Address the user as "sir" or by name, keep replies natural and conversational like real \
speech rather than customer-service phrasing, and don't be afraid to tease or push back with \
personality when it fits. Keep responses fairly short and punchy since they'll be spoken aloud."""

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def respond(user_text: str, history: list[dict]) -> str:
    messages = history + [{"role": "user", "content": user_text}]
    response = _get_client().messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text
