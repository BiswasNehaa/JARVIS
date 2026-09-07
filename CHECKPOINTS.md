# JARVIS — Checkpoints

Progress tracker. ✅ = done, 🟡 = partial/in progress, ⬜ = not started.
Delete this file once JARVIS is fully built — it's just a temporary progress view.

**Overall: ~20% complete** (Phase 1 done and tested live, Phases 2-6 not started)

## Phase 1 — Core loop (terminal only)
- ✅ Repo scaffolded + pushed to GitHub
- ✅ Wake word wired (openWakeWord, "Hey Jarvis", fully free/offline)
- ✅ Speech-to-text wired (faster-whisper, local)
- ✅ Brain wired (Groq/Llama 3.3 70B, free tier)
- ✅ Text-to-speech wired (edge-tts, free)
- ✅ Groq API key added
- ✅ Wake word model downloaded
- ✅ First live end-to-end test — wake word, STT, brain, and TTS all confirmed working together

## Phase 2 — HUD widget
- ⬜ Small always-on-top popup window (pywebview)
- ⬜ Boot-up sequence animation
- ⬜ Glowing orb visual (Age of Ultron style), idle/listening/thinking/speaking states

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
