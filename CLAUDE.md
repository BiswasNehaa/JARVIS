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
  ERROR (a fast opacity flicker, not a color change). `window.setAudioLevel()` is fed real mic RMS
  during `LISTENING` (`main.py`'s `_record_command`); `SPEAKING` still uses synthetic per-state motion,
  not real TTS playback levels (`playsound` gives no amplitude hook — would need a different playback
  path to do properly; deferred). **Don't rebuild the structural concept again** without the user
  explicitly asking — iterate within it.
- **Popup behavior — added 2026-09-09, modeled on Windows' own voice-typing toolbar (Win+H).** The HUD
  is no longer a persistent always-open window: `hud.create_window()` now creates it `hidden=True`, and
  `main.py` calls `hud.show_window()` right when the wake word fires and `hud.hide_window()` once the
  turn ends (normally, on STT returning nothing, or on a stop command — see below). Size/position also
  changed from a big centered square to a small bar docked bottom-center, matching the reference
  screenshot the user sent of Windows' own dictation toolbar: `POPUP_WIDTH=300`, `POPUP_HEIGHT=76`,
  `BOTTOM_MARGIN=110` in `hud.py`. Confirmed live by the user 2026-09-09 ("yeah cool i like it") — size
  and position are good as-is, no further nudging needed unless they bring it up again. True
  rounded/transparent corners are still the deferred item above — for now it's a small rectangular dark
  bar, not a literal rounded pill (hasn't come up as an issue).
- **Stop command — added 2026-09-09**: saying a phrase from `config.STOP_PHRASES` ("stop session", "end
  session", "jarvis stop", "stop listening") while JARVIS is listening ends the turn immediately
  (skips the brain/TTS call) and hides the popup, via `main.py`'s `_is_stop_command()`. Silent by
  design (no spoken acknowledgment) so it dismisses quickly — revisit if the user wants a confirmation
  sound/line instead.
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
- **Speaker recognition (Phase 3) uses `resemblyzer`, not a lightweight classical approach** — explicit
  user choice: offered a lighter MFCC/cosine option with no heavy deps, user chose accuracy instead
  ("it can be heavy, but it have to be very good, like, very impressive" — this is meant to be a dream
  project, not a minimal one). Pulls in PyTorch (~200MB+), breaking from the project's earlier
  lightweight-dependency pattern (faster-whisper uses CTranslate2, not torch) — an intentional
  exception for this one feature, not a reversal of the free-tier-by-design principle (still $0 cost,
  just a bigger download). **Windows install gotcha**: resemblyzer's own package metadata declares a
  dependency on the real `webrtcvad` PyPI package, which ships no prebuilt Windows wheel and fails to
  build without Microsoft's C++ Build Tools. Fix: `requirements.txt` installs `webrtcvad-wheels` (a
  prebuilt equivalent, same importable module name) plus resemblyzer's actual runtime deps (torch,
  librosa, soundfile, numba, scipy) as ordinary lines; resemblyzer itself must be installed separately
  with `pip install resemblyzer --no-deps` (see README step 6) so pip never resolves its declared
  `webrtcvad` requirement. Voiceprints live in `data/voiceprints/speakers.json` (gitignored — biometric
  data, never commit). Deferred HUD polish items (transparent overlay, boot animation, real
  SPEAKING-state audio reactivity) were moved to GitHub issues #1-#3 instead of tracking here —
  explicit user request to park design-level work and move to code-level Phase 3.

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
turn) as you actually talk to it. It's now also popup-style (2026-09-09, see above): hidden until the
wake word, small bar docked bottom-center, hides again after each turn — confirmed live by the user.
`python -m src.jarvis.hud` still exists separately as the standalone demo-cycle visual test (shows
immediately, ignores the hide/show choreography). Also fixed 2026-09-09: the voice loop was cutting
users off mid-sentence and mis-firing on natural speech pauses — `MAX_COMMAND_SECONDS` 8→25 and
`SILENCE_HANG_MS` 1200→2000 in `config.py` (not yet explicitly re-confirmed live by the user, unlike the
popup). Remaining Phase 2 polish items (transparent overlay window, boot-up animation, real
SPEAKING-state audio reactivity) are parked as GitHub issues #1-#3 — design-level, revisit later.

Phase 3 (speaker recognition, 2026-09-10): every recorded utterance is embedded via `speaker.py`
(`resemblyzer`, see key decisions above) and matched against `data/voiceprints/speakers.json` by cosine
similarity (`config.SPEAKER_MATCH_THRESHOLD`, default 0.78). Recognized voices get addressed by their
enrolled name (`brain.respond(..., speaker_name=...)`); an unrecognized voice triggers
`main.py`'s `_enroll_new_speaker()` — JARVIS asks "I don't think we've met — what's your name?", the
reply's audio is embedded too, and both embeddings are averaged into a new voiceprint. Not yet
confirmed live by the user.

## Architecture

```
src/jarvis/
  config.py      env vars, constants (model, voice, user name, record duration)
  audio.py       sounddevice microphone wrapper (16kHz mono int16 frames)
  wake_word.py   openWakeWord model (pretrained "hey_jarvis")
  stt.py         faster-whisper transcription
  brain.py       Groq API call (GPT-OSS 120B) + JARVIS system prompt/personality
  speaker.py     resemblyzer voice embeddings + voiceprint matching/enrollment (Phase 3)
  tts.py         edge-tts synthesis + playback (markdown/emoji stripped before speaking)
  hud.py         pywebview window hosting hud/index.html + set_state() JS bridge; `python -m
                 src.jarvis.hud` still runs it standalone as a demo-cycle visual test
  main.py        orchestrates the voice loop AND drives the HUD live via hud.set_state() at each
                 IDLE/ACTIVATING/LISTENING/PROCESSING/SPEAKING/ERROR transition
hud/
  index.html     the HUD itself — plain 2D Canvas, self-contained (envelope fn, state machine), see
                 "HUD visual concept" above before editing. No external libraries/vendor dir anymore.
```
