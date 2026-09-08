# JARVIS — Checkpoints

Progress tracker. ✅ = done, 🟡 = partial/in progress, ⬜ = not started.
Delete this file once JARVIS is fully built — it's just a temporary progress view.

**Overall: ~34% complete** (Phase 1 done + a turn-taking fix, Phase 2 visual redesigned to a minimal waveform line and wired into the live voice loop, transparency/boot animation/audio-reactivity + Phases 3-6 not started)

## Phase 1 — Core loop (terminal only)
- ✅ Repo scaffolded + pushed to GitHub
- ✅ Wake word wired (openWakeWord, "Hey Jarvis", fully free/offline)
- ✅ Speech-to-text wired (faster-whisper, local)
- ✅ Brain wired (Groq/Llama 3.3 70B, free tier)
- ✅ Text-to-speech wired (edge-tts, free)
- ✅ Groq API key added
- ✅ Wake word model downloaded
- ✅ First live end-to-end test — wake word, STT, brain, and TTS all confirmed working together
- ✅ Fixed premature cutoff / mid-sentence interruption bug — `MAX_COMMAND_SECONDS` 8→25,
      `SILENCE_HANG_MS` 1200→2000 in `config.py` (2026-09-09; not yet re-confirmed live)

## Phase 2 — HUD widget
- ✅ Small always-on-top popup window (pywebview)
- ✅ Visual redesign (2026-09-09) — scrapped the cyan holographic orbital-arc/filament Three.js scene
      ("looking really bad") for a minimal monochrome single-line waveform on plain 2D Canvas, matching
      a reference image (Arctic Monkeys "Do I Wanna Know?" cover) the user provided. User confirmed
      "this is good." Full IDLE/ACTIVATING/LISTENING/PROCESSING/SPEAKING/ERROR/SLEEPING state scaffold
      drives amplitude/frequency/speed/hump-count, not color.
- ⬜ Transparent desktop-overlay window — tried pywebview (unsupported on Windows) and Qt
      QWebEngineView (renders opaque gray, not real transparency); deferred, revisit via a native
      OpenGL rewrite once the visual design itself is finalized (see CLAUDE.md)
- ⬜ Boot-up sequence animation
- ⬜ Real audio-level reactivity — `window.setAudioLevel()` exists and feeds the waveform's amplitude
      but nothing calls it yet with real mic/TTS levels
- ✅ Wire HUD into the live voice loop (main.py) — running `python -m src.jarvis.main` now opens the HUD
      and drives it through IDLE → ACTIVATING → LISTENING → PROCESSING → SPEAKING → ERROR live as you talk
      to it, instead of the old headless terminal loop / separate `hud.py` demo cycle

## Phase 3 — Speaker recognition
- ⬜ Local voiceprint matching (know it's you)
- ⬜ New-voice enrollment ("I don't think we've met — what's your name?")

## Phase 4 — Personality tuning
- ⬜ Dial in charm/flirt/wit balance by ear once we can hear it talk

## Phase 5 — Skills
- ⬜ Actions beyond conversation (open apps, system control, dev commands, timers, etc.)

## Phase 6 — Suit telemetry & protocols
- ⬜ System vitals as HUD flavor text ("power reserves at 34%, sir")
- ⬜ Voice-triggered macro "protocols"
