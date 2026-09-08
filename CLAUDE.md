# JARVIS — project context

Personal voice assistant, Tony Stark AI vibe. Wake word "Hey Jarvis" → listens → responds via Groq/Llama →
speaks back in a charming, witty, flirty personality. See `README.md` for setup/run instructions and
the phase roadmap.

## Key decisions (don't relitigate without reason)

- **Voice engine is free-tier by design**: `edge-tts` (TTS) + `faster-whisper` (STT), both free/local,
  because the user expects to talk to this a lot and cost-per-use would add up.
- **Brain is Groq (Llama 3.3 70B), not Claude, by explicit user choice**: user is a student, currently
  unemployed, and asked for a genuinely free option rather than the Anthropic API (which is usage-based,
  ~$2-6/month even at heavy use, but still real money). Plan is to switch back to Claude once employed —
  `brain.py` is the only file that talks to the LLM, so that swap is intentionally a one-file change
  (see commented-out Anthropic lines in `.env.example`). Don't re-suggest paid APIs unless the user
  brings up budget again.
- **Wake word**: openWakeWord's pretrained "hey_jarvis" model — switched off Picovoice/Porcupine
  (2026-09-07) after the user found Picovoice discontinued its free tier. openWakeWord is open-source,
  fully offline, no key/signup, and ships this exact wake word pretrained — no custom training needed.
  Requires a one-time model download on first setup (see README step 5). Audio capture uses
  `sounddevice` (`src/jarvis/audio.py`) instead of Picovoice's `pvrecorder`.
- **Personality**: full charm from day one (confident, witty, flirty banter), not a subtle/professional
  starting point — this was an explicit user choice, not a default.
- **HUD visual concept — replaced 2026-09-09.** The old cyan holographic orbital-arc/filament Three.js
  scene (~10 rounds to converge on, 2026-09-07/08) was scrapped outright: user found it "looking really
  bad." New direction, explicitly requested with a reference image (Arctic Monkeys "Do I Wanna Know?"
  single cover): a single continuous white waveform-style line, monochrome, on a transparent/black
  canvas — NOT concentric rings (a first attempt at "minimal line-art" using layered noise-perturbed
  loops was also rejected as "weird looking" before landing on the literal-waveform version, which the
  user confirmed "this is good"). Implementation is now plain 2D Canvas, not WebGL/Three.js — `hud/`
  has no vendored library anymore. The line is `POINTS` samples of `sin(...) * envelope(...)`, where
  `envelope()` sums a few Gaussian "bursts" positioned along the line so it reads as dense oscillation
  in a couple of places tapering to near-flat elsewhere (matches the reference), not one uniform sine
  wave. State scaffold (`IDLE/ACTIVATING/LISTENING/PROCESSING/SPEAKING/ERROR/SLEEPING`) drives
  amplitude/frequency/speed/hump-count rather than color — still monochrome white throughout, including
  ERROR (a fast opacity flicker, not a color change). `window.setAudioLevel()` is wired in (feeds
  amplitude) but not yet fed real mic/TTS levels — a natural next step given this is now literally a
  waveform shape. **Don't rebuild the structural concept again** without the user explicitly asking —
  iterate within it.
- **Transparent desktop-overlay window — deferred, not solved**: tried `pywebview`'s `transparent=True`
  (confirmed via their own docs: unsupported on Windows), then PyQt6 `QWebEngineView` with
  `WA_TranslucentBackground` (rendered a flat opaque gray, not real transparency — matches multiple
  unresolved reports of this exact Chromium-in-Qt issue). Decision: defer true transparency until the
  visual design is finalized, then do a one-time port to native OpenGL (Qt `QOpenGLWidget` +
  PyOpenGL/moderngl + GLSL) instead of an embedded browser view, since Qt's own GL transparency is
  reliable where Chromium-embedded transparency is not. Reverted to plain `pywebview` + solid dark
  background for now (`src/jarvis/hud.py`, `requirements.txt` back to `pywebview`, not PyQt6). Don't
  re-attempt browser-based transparency tricks — go straight to the OpenGL rewrite when this is revisited.
- **Repo is public** on GitHub under the user's account by explicit choice — never commit `.env` or
  real API keys.

## Current status

Phase 1 (core terminal loop: wake word → STT → Groq/GPT-OSS → TTS) works end-to-end, confirmed live by
the user (2026-09-07). Default Groq model is `openai/gpt-oss-120b` (the originally-planned
`llama-3.3-70b-versatile` was retired from Groq's free tier — check `client.models.list()` again if
another swap is ever needed, their lineup has shifted before). `TTS_VOICE`/`TTS_RATE`/`TTS_PITCH` and
`USER_NAME` are configurable via `.env` (see `config.py`) — current voice is `en-CA-LiamNeural`, picked
as "best of the free options so far" but user still finds it lacks real emotional delivery (known free
Edge-TTS ceiling; ElevenLabs is the fallback if ever worth the free-tier limit — see `feedback_commit_after_milestones`-adjacent context, not re-litigated unless user brings up budget/voice again).

Phase 2 (HUD): visual design was rebuilt 2026-09-09 into the minimal white-waveform-line look (see
above) and wired into the live voice loop (2026-09-08) — `python -m src.jarvis.main` opens the HUD
window and drives it through IDLE → ACTIVATING → LISTENING → PROCESSING → SPEAKING (ERROR on a failed
turn) as you actually talk to it. `python -m src.jarvis.hud` still exists separately as the standalone
demo-cycle visual test. Also fixed 2026-09-09: the voice loop was cutting users off mid-sentence and
mis-firing on natural speech pauses — `MAX_COMMAND_SECONDS` 8→25 and `SILENCE_HANG_MS` 1200→2000 in
`config.py` (not yet re-confirmed live by the user after the change). Remaining Phase 2 items:
transparent overlay window (deferred, see above), a boot-up animation, and real audio-level reactivity
on the waveform (`window.setAudioLevel()` exists but isn't fed real mic/TTS levels yet).

## Architecture

```
src/jarvis/
  config.py      env vars, constants (model, voice, user name, record duration)
  audio.py       sounddevice microphone wrapper (16kHz mono int16 frames)
  wake_word.py   openWakeWord model (pretrained "hey_jarvis")
  stt.py         faster-whisper transcription
  brain.py       Groq API call (GPT-OSS 120B) + JARVIS system prompt/personality
  tts.py         edge-tts synthesis + playback (markdown/emoji stripped before speaking)
  hud.py         pywebview window hosting hud/index.html + set_state() JS bridge; `python -m
                 src.jarvis.hud` still runs it standalone as a demo-cycle visual test
  main.py        orchestrates the voice loop AND drives the HUD live via hud.set_state() at each
                 IDLE/ACTIVATING/LISTENING/PROCESSING/SPEAKING/ERROR transition
hud/
  index.html     the HUD itself — plain 2D Canvas, self-contained (envelope fn, state machine), see
                 "HUD visual concept" above before editing. No external libraries/vendor dir anymore.
```
