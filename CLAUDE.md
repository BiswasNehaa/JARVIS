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
  starting point — this was an explicit user choice, not a default. **Reworked 2026-09-28**: user
  disliked the old version calling her "babe" and getting sassy/dismissive when she vented ("charming
  and flirty doesn't mean this"). She asked for Tom Cruise-style charm: confident, easygoing, upbeat,
  earnest, makes you feel like the most interesting person in the room. `brain.py`'s prompt now bans
  pet names outright, forbids roasting/scolding, and has a "read the room" rule (drop the jokes, be
  kind and specific when the user is stressed). Channel the vibe, never impersonate or quote him.
  Not yet confirmed live by the user.
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

- **Latency pass — 2026-09-28** (user reported 30-40s per reply). Main suspect: the fixed
  `SILENCE_RMS_THRESHOLD=300` sat below room/fan noise, so recordings rarely detected silence and ran
  to the 25s cap. Now `audio.SpeechDetector` learns the room's noise floor from idle frames and also
  requires webrtcvad to hear a voice; `MAX_COMMAND_SECONDS` 25→15, `SILENCE_HANG_MS` 2000→1200 (env
  overridable), plus a 6s no-speech timeout. Also: Whisper/voice encoder warm up at startup, greedy
  Whisper decoding, STT and speaker embedding run in parallel, gpt-oss `reasoning_effort=low`
  (`REASONING_EFFORT` env), TTS plays sentence 1 while synthesizing sentence 2, and HUD audio-level
  updates no longer block the recording loop. Each turn prints a `[timing]` line; `WAIT` is end of
  speech to first spoken word. Confirmed live 2026-09-28: WAIT ~3-5s (was 30-40s).
- **Conversation mode — 2026-09-28**: after answering, JARVIS keeps listening for a follow-up for
  `FOLLOW_UP_SECONDS` (default 8, env overridable, 0 disables) without the wake word; silence, a stop
  phrase or an error ends the conversation. `Microphone.drain()` discards audio buffered while JARVIS
  spoke (otherwise it hears its own reply), and the wake-word model is reset after each conversation.
  Confirmed live 2026-09-28. **Changed 2026-10-04** (user: it shouldn't close until "Bye Jarvis" or a
  long quiet spell): `FOLLOW_UP_SECONDS` default 8 → 600, `MAX_COMMAND_SECONDS` now counts from when
  she starts talking (only a 0.5s lead-in is kept while waiting), and an empty transcript mid-
  conversation keeps listening instead of ending it. Also fixed: the wake-word model is now reset
  right at detection; it still held "Hey Jarvis", so the stop-listener re-detected it and cut off the
  first reply before its first word ("tts first audio 0.00s").
- **Wake phrases — 2026-09-28**: "Hey/Hello/Hi Jarvis" all wake it. The pretrained model already
  scores most of these high; near misses (0.15-0.5) get a Whisper double-check (`wake_word.py`).
- **Pause-tolerant end of speech — 2026-09-28** (user: it cut her off when she paused 2-3s to think).
  After `SILENCE_HANG_MS` (1.2s) of quiet, `main._record_command` transcribes what it has in the
  background while still listening (Whisper with a filler-word prompt so "um" survives) and only
  stops if `_sounds_finished()` says it reads as a complete sentence (ends in . ? ! and not on
  "and/so/the/um/..."). Otherwise it waits through pauses up to `MAX_SILENCE_HANG_MS` (3.5s). That
  transcript is reused, so there's no second STT pass. Not yet confirmed live.

- **Answer-first replies — 2026-09-30** (user: asked for a movie, JARVIS talked about the mystery genre
  and she had to ask twice). `brain.py`'s prompt now opens with an answer-first rule (name a real
  title/name/dish, make a pick instead of asking what she's in the mood for) and bans blurb phrasing
  ("perfect for", "keeps you guessing", "Enjoy!", adjective lists). `TEMPERATURE` 0.4 (Groq default
  1.0; 0.6 once invented a movie title). History keeps the last `HISTORY_TURNS`=6 exchanges and is
  cleared when woken after `HISTORY_RESET_SECONDS`=600 of quiet. Not yet confirmed live.

- **Mishearing fixes — 2026-09-30** (log: "bunked" heard as "bumped", "scikit-learn" as "XK learn").
  Whisper now gets the recent conversation as its prompt (`stt.conversation_prompt`), so words already
  said come back spelled right (test clips: "sicket lung" became "scikit-learn"); optional `STT_HINTS`
  env for her own recurring vocabulary. `brain.py`'s prompt tells the model its input is speech-to-text
  and to answer the most likely intended words. No word-replacement lists (her rule: nothing
  hard-coded). Stayed on `base.en`: `small.en` hears better but measured ~2.3s vs ~0.7s per check on
  her laptop. "Bumped/bunked" is still not reliably recovered. `brain._single_reply` keeps only the
  first answer when gpt-oss glues alternatives together ("...?Got it...").
- **Quitting — 2026-09-30**: "Bye Jarvis" (mid-conversation, over a reply since 2026-10-05, or as the wake phrase) says bye and exits;
  Ctrl+C works via a Windows console handler (`main._quit_on_ctrl_c`), since the webview loop owns
  the main thread and swallowed KeyboardInterrupt.

- **Wake greeting — 2026-10-04** (user asked: say hi back, by name if it knows the voice, ask who it
  is if not). `main._greet`: if she starts talking within 0.8s of the wake word, no greeting (the
  audio heard so far starts the recording). Otherwise the wake phrase's own audio is matched: closest
  enrolled voice ≥ `SPEAKER_SHORT_CLIP_THRESHOLD` (0.55) → hi by name; < `SPEAKER_UNKNOWN_THRESHOLD`
  (0.40) → hi + "who are you?" via `_enroll_new_speaker(question=...)`; in between → plain hi, the
  first real sentence settles identity. Greetings are written by the model (`brain.greeting`,
  temperature 1.0, avoids the last 5) and pre-fetched on their own thread so the hi is instant.
- **Short-clip speaker matches — 2026-10-04**: short phrases (< 4s) give shaky embeddings (her "How
  about you?" scored 0.64 and got asked her name). Now a short clip whose closest voice is enrolled
  and ≥ 0.55 is taken as that person (not learned from). Only clearly low scores trigger "who are you".

- **Conversational, not advice — 2026-10-04** (user: "it's always suggesting something... it should be
  conversational"). Prompt now says JARVIS is a friend to talk with: react, share its own take, ask a
  curious follow-up; no tips/routines/recommendations unless asked; never suggest what she already
  did. "Answer first" now applies only when she actually asks something. Mishearing rule tightened:
  if not fairly sure what she meant, say it didn't catch that and ask (log: "Two likes and a night"
  got a movie list). Replaying her log: no unasked-for tips, the garbled line got a short "didn't
  catch that".

- **Polish — 2026-10-05** (her log): greeting said "afternoon" at 12:24 AM (`brain._time_of_day` fell
  through for 0-4 AM, fixed). Prompt: most replies just react (questions only now and then), play
  along with imaginative talk instead of pushing real kits/products, never three sentences;
  `_single_reply` also hard-cuts at `MAX_REPLY_SENTENCES` (3). Any clear goodbye ("bye for now,
  bye-bye") quits: the model calls the `end_conversation` skill, and main speaks the bye and exits.
  Tested: "hold on, let me grab water" / "let's talk about something else" don't trigger it.

- **Tone, human feel, memory — 2026-10-05** (her asks: catch sarcasm, stop sounding like a chatbot,
  remember things). `prosody.py` compares each turn's loudness/pitch/pitch-range/pace with her usual
  (running average, in memory per run) and passes notable differences as `[voice: ...]` after her
  words; the prompt says judge sincere vs sarcastic vs masking a mood and answer the real meaning.
  Prompt lists chatbot tells to avoid (stock openers, cheerleading, emoji, exclamation marks).
  `qwen/qwen3.8-27b` sounded most human in a side-by-side but hit free-tier rate limits, so it's
  opt-in via GROQ_MODEL. Long-term memory: `memory.py`, `data/memory/<speaker>.json` (gitignored),
  all facts shown in the system prompt as a numbered list; the model saves/removes via the
  `remember`/`forget` skills (forget by number). Tested: remember, recall in a new session, forget.
  Groq also offers `whisper-large-v3-turbo` (STT) and `canopylabs/orpheus-v1-english` (expressive
  TTS) on the free key; not tried yet.

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
similarity against the centroid of each speaker's stored samples (`config.SPEAKER_MATCH_THRESHOLD`, default
0.75, set from Neha's live scores of 0.77-0.91 on 2026-09-28). Recognized voices get addressed by their
enrolled name (`brain.respond(..., speaker_name=...)`); an unrecognized voice triggers
`main.py`'s `_enroll_new_speaker()` — JARVIS asks "I don't think we've met — what's your name?", the
reply's audio is embedded too (if ≥1.5s), and the samples are ADDED to that speaker's list (up to
`SPEAKER_MAX_SAMPLES`), never overwriting it — overwriting was why JARVIS "forgot" Neha mid-session.
Confident matches are also added, so the voiceprint keeps learning; a near miss (≥
`SPEAKER_STICKY_THRESHOLD`) from the last speaker stays with them. Confirmed live by the user 2026-09-28:
not asked her name again after the first turn of a session.

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
