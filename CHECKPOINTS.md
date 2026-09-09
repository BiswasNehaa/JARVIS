# JARVIS — Checkpoints

Progress tracker. ✅ = done, 🟡 = partial/in progress, ⬜ = not started.
Delete this file once JARVIS is fully built — it's just a temporary progress view.

**Overall: ~45% complete** (Phase 1 done + a turn-taking fix, Phase 2 visual redesigned to a minimal waveform line, wired into the live voice loop, and turned into a Win+H-style popup with a stop command and live mic reactivity — user confirmed live; transparency/boot animation/TTS-audio-reactivity tracked as GitHub issues #1-#3, revisit later. Phase 3 speaker recognition wired end-to-end, not yet confirmed live. Phases 4-6 not started)

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
- ✅ Win+H-style popup behavior (2026-09-09) — hidden by default, `hud.show_window()` on wake word,
      `hud.hide_window()` after each turn or on a stop command; small bar (300x76) docked bottom-center
      instead of a big centered square, matching a Windows-dictation-toolbar reference screenshot.
      User confirmed live: "yeah cool i like it"
- ✅ Voice stop command — saying "stop session" / "jarvis stop" / etc. (see `config.STOP_PHRASES`) ends
      the turn immediately and hides the popup, without waiting on the brain/TTS
- ✅ Live mic reactivity while listening — the waveform's amplitude now follows real mic RMS, not just a
      canned per-state animation; TTS/SPEAKING is still synthetic (see next item)
- ⬜ Transparent desktop-overlay window — tried pywebview (unsupported on Windows) and Qt
      QWebEngineView (renders opaque gray, not real transparency); deferred, revisit via a native
      OpenGL rewrite once the visual design itself is finalized (see CLAUDE.md). Tracked as
      [GitHub issue #1](https://github.com/BiswasNehaa/JARVIS/issues/1) — design-level, revisit later.
- ⬜ Boot-up sequence animation — [GitHub issue #2](https://github.com/BiswasNehaa/JARVIS/issues/2)
- ⬜ Real audio-level reactivity during SPEAKING — `playsound` gives no amplitude hook; would need a
      different TTS playback path to drive the waveform from actual voice output.
      [GitHub issue #3](https://github.com/BiswasNehaa/JARVIS/issues/3)
- ✅ Wire HUD into the live voice loop (main.py) — running `python -m src.jarvis.main` now opens the HUD
      and drives it through IDLE → ACTIVATING → LISTENING → PROCESSING → SPEAKING → ERROR live as you talk
      to it, instead of the old headless terminal loop / separate `hud.py` demo cycle

## Phase 3 — Speaker recognition
- ✅ Local voiceprint matching (know it's you) — `speaker.py` uses `resemblyzer` (deep-learning voice
      embeddings, chosen over a lighter classical MFCC approach for accuracy — user explicitly wants
      quality over install size: "it can be heavy, but it have to be very good"). Cosine similarity
      against enrolled voiceprints stored in `data/voiceprints/speakers.json` (gitignored).
- ✅ New-voice enrollment — unrecognized voice triggers "I don't think we've met — what's your name?",
      the reply is transcribed for the name and embedded alongside the original utterance to seed the
      new voiceprint (`main.py`'s `_enroll_new_speaker`)
- ✅ Identified speaker's name is passed into `brain.respond()` so JARVIS addresses whoever it recognizes
      by their actual name (falls back to `config.USER_NAME` only if no one is enrolled yet)
- ⬜ Not yet confirmed live by the user — needs a live test: one enrollment + one recognized-voice turn

## Phase 4 — Personality tuning
- ⬜ Dial in charm/flirt/wit balance by ear once we can hear it talk

## Phase 5 — Skills
- ⬜ Actions beyond conversation (open apps, system control, dev commands, timers, etc.)

## Phase 6 — Suit telemetry & protocols
- ⬜ System vitals as HUD flavor text ("power reserves at 34%, sir")
- ⬜ Voice-triggered macro "protocols"
