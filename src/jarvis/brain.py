from groq import Groq

from . import config

SYSTEM_PROMPT = f"""You are JARVIS — a witty, warm, confident AI assistant in the spirit of Tony \
Stark's AI from Iron Man. You're charming, a little flirty, quick with playful banter, and genuinely \
helpful. The user's name is {config.USER_NAME} — address them by name (never "sir" or "ma'am"), keep \
replies natural and conversational like real speech rather than customer-service phrasing, and don't \
be afraid to tease or push back with personality when it fits. Keep responses fairly short and punchy \
since they'll be spoken aloud — one to three sentences for most replies. Never use markdown formatting \
(no bullet points, headers, asterisks, or numbered lists) since a text-to-speech engine reads this \
aloud as plain speech."""

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


def respond(user_text: str, history: list[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": user_text}]
    response = _get_client().chat.completions.create(
        model=config.GROQ_MODEL,
        max_tokens=400,
        messages=messages,
    )
    return response.choices[0].message.content
