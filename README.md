# JARVIS

A personal voice assistant with a Tony Stark AI vibe: say **"Hey Jarvis"** to wake it up, talk to it
naturally, and it talks back — charming, witty, a little flirty, and genuinely helpful.

## How it works (v1)

```
mic → wake word ("hey jarvis") → record your request → speech-to-text
    → Groq/Llama (the brain/personality) → text-to-speech → spoken reply
```

- **Wake word** — [openWakeWord](https://github.com/dscripka/openWakeWord) with its pretrained "Hey Jarvis" model (free, open-source, fully offline, no key/signup needed)
- **Speech-to-text** — [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) running locally (free, private)
- **Brain** — [Groq API](https://console.groq.com/) running Llama 3.3 70B, free tier, with a custom JARVIS personality prompt
- **Text-to-speech** — [`edge-tts`](https://github.com/rany2/edge-tts) (free Microsoft neural voices, no API key)
- **Speaker recognition** — [`resemblyzer`](https://github.com/resemble-ai/Resemblyzer) (free, local, deep-learning voice embeddings) matches your voice against enrolled voiceprints in `data/voiceprints/` (gitignored); an unrecognized voice gets a quick enrollment ("what's your name?")

Everything here is free — no credit card needed anywhere. `brain.py` is intentionally the only file
that talks to the LLM, so swapping to a paid model later (e.g. Claude, once you want the extra
polish) is a one-file change — see the commented-out lines in `.env.example`.

## Setup

1. **Python 3.10+** and a working microphone.
2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Get your API key (free, no credit card):
   - Groq: https://console.groq.com/keys → sign up free → create an API key
4. Copy `.env.example` to `.env` and fill in the key.
5. One-time download of the wake-word model (openWakeWord doesn't bundle it in the pip package):
   ```
   python -c "from openwakeword.utils import download_models; download_models()"
   ```
6. Install `resemblyzer` (speaker recognition) separately, without its declared dependencies —
   its metadata pulls in the real `webrtcvad` package, which has no prebuilt Windows wheel and fails
   to build without Microsoft's C++ Build Tools. `requirements.txt` already installs
   `webrtcvad-wheels` (a prebuilt equivalent) plus resemblyzer's actual runtime deps, so this is safe:
   ```
   pip install resemblyzer --no-deps
   ```
7. Run it:
   ```
   python -m src.jarvis.main
   ```
   Say **"Hey Jarvis"**, wait for "listening...", then speak your request.

## Roadmap

- [x] **Phase 1 — Core loop** — wake word → STT → Groq/Llama → TTS, terminal only
- [ ] **Phase 2 — HUD widget** — small always-on-top popup with a glowing orb (Age of Ultron style),
      boot-up sequence, listening/thinking/speaking animation states
- [x] **Phase 3 — Speaker recognition** — local voiceprint matching; greets known voices by name,
      asks new voices to introduce themselves
- [ ] **Phase 4 — Personality tuning** — dial in the charm/flirt/wit balance by ear
- [ ] **Phase 5 — Skills** — actions beyond conversation (open apps, system control, dev-workflow
      commands, timers, etc.)
- [ ] **Phase 6 — Suit telemetry & protocols** — system vitals framed as HUD stats, voice-triggered
      macro "protocols"

See `CLAUDE.md` for project context and architecture decisions.
