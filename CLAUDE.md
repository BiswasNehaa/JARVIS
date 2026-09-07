# JARVIS — project context

Personal voice assistant, Tony Stark AI vibe. Wake word "Jarvis" → listens → responds via Claude →
speaks back in a charming, witty, flirty personality. See `README.md` for setup/run instructions and
the phase roadmap.

## Key decisions (don't relitigate without reason)

- **Voice engine is free-tier by design**: `edge-tts` (TTS) + `faster-whisper` (STT), both free/local,
  because the user expects to talk to this a lot and cost-per-use would add up. Claude API calls are
  the one unavoidable recurring cost.
- **Wake word**: Porcupine's *built-in* "jarvis" keyword — deliberately avoided custom wake-word
  training (would require a Picovoice Console account + manual `.ppn` file generation).
- **Personality**: full charm from day one (confident, witty, flirty banter), not a subtle/professional
  starting point — this was an explicit user choice, not a default.
- **HUD visual target**: a glowing, swirling orb of light — reference is JARVIS's holographic form
  from *Avengers: Age of Ultron*, not a generic waveform bar. Planned for Phase 2 via
  `pywebview` (HTML/CSS/JS visuals in a small always-on-top native window).
- **Repo is public** on GitHub under the user's account by explicit choice — never commit `.env` or
  real API keys.

## Current status

Phase 1 (core terminal loop: wake word → STT → Claude → TTS) is scaffolded in `src/jarvis/`. Not yet
tested end-to-end — needs the user's Anthropic + Picovoice API keys in `.env` first.

## Architecture

```
src/jarvis/
  config.py      env vars, constants (wake word, model, record duration)
  wake_word.py   Porcupine handle (built-in "jarvis" keyword)
  stt.py         faster-whisper transcription
  brain.py       Claude API call + JARVIS system prompt/personality
  tts.py         edge-tts synthesis + playback
  main.py        orchestrates the loop
```
