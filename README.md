# JARVIS

A personal voice assistant with a Tony Stark AI vibe: say **"Jarvis"** to wake it up, talk to it
naturally, and it talks back — charming, witty, a little flirty, and genuinely helpful.

## How it works (v1)

```
mic → wake word ("jarvis") → record your request → speech-to-text
    → Claude (the brain/personality) → text-to-speech → spoken reply
```

- **Wake word** — [Porcupine](https://picovoice.ai/) with its built-in "Jarvis" keyword (free, offline, no training needed)
- **Speech-to-text** — [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) running locally (free, private)
- **Brain** — [Claude API](https://console.anthropic.com/) with a custom JARVIS personality prompt
- **Text-to-speech** — [`edge-tts`](https://github.com/rany2/edge-tts) (free Microsoft neural voices, no API key)

Everything is free except the Claude API calls, which are usage-based but cheap for personal use.

## Setup

1. **Python 3.10+** and a working microphone.
2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Get your API keys:
   - Anthropic: https://console.anthropic.com/ → create an API key
   - Picovoice: https://console.picovoice.ai/ → sign up free → copy your AccessKey
4. Copy `.env.example` to `.env` and fill in both keys.
5. Run it:
   ```
   python -m src.jarvis.main
   ```
   Say **"Jarvis"**, wait for "listening...", then speak your request.

## Roadmap

- [x] **Phase 1 — Core loop** — wake word → STT → Claude → TTS, terminal only
- [ ] **Phase 2 — HUD widget** — small always-on-top popup with a glowing orb (Age of Ultron style),
      boot-up sequence, listening/thinking/speaking animation states
- [ ] **Phase 3 — Speaker recognition** — local voiceprint matching; greets known voices by name,
      asks new voices to introduce themselves
- [ ] **Phase 4 — Personality tuning** — dial in the charm/flirt/wit balance by ear
- [ ] **Phase 5 — Skills** — actions beyond conversation (open apps, system control, dev-workflow
      commands, timers, etc.)
- [ ] **Phase 6 — Suit telemetry & protocols** — system vitals framed as HUD stats, voice-triggered
      macro "protocols"

See `CLAUDE.md` for project context and architecture decisions.
