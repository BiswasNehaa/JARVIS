# JARVIS

A personal voice assistant with a Tony Stark AI vibe. Say **"Hey Jarvis"**, talk to it like a friend,
and it talks back: charming, warm, a little witty, and it knows who you are.

Everything runs on free tools. No credit card needed anywhere.

## What it does

- **Wakes on "Hey Jarvis", "Hi Jarvis" or "Hello Jarvis"** and says hi back, by name if it knows your
  voice. If you go straight into a question ("Hey Jarvis, what time is it?") it skips the hello and
  answers.
- **Knows who's talking.** It recognizes enrolled voices, and asks a new voice for their name once.
  Your voiceprint keeps learning from every confident match.
- **Holds a real conversation.** After it answers, it keeps listening without the wake word. It stays
  open until you say goodbye or nobody talks for 10 minutes.
- **Talks like a friend, not a chatbot.** It reacts to what you say, plays along with jokes and
  what-ifs, and only gives advice or recommendations when you ask. Replies are kept to one or two
  short spoken sentences.
- **Reads tone and sarcasm.** Besides your words, it compares how you said them (loudness, pitch,
  how flat you sound, pace) with your usual voice, so a flat "my day was amazing" doesn't get a
  cheerful answer.
- **Remembers you.** It saves lasting things you share (plans, exams, likes, people) and uses them in
  later conversations. Say "remember ...", "forget ...", or "what do you know about me?".
- **Copes with mishearing.** Speech-to-text gets the recent conversation as context, and the brain
  works out what you most likely meant, or asks if it can't tell.
- **Can be interrupted.** Say "stop" (or "Hey Jarvis") while it's talking and it stops.
- **Does a few things:** tells the time and date, opens a few apps (Notepad, Calculator, Paint, File
  Explorer, WordPad), and sets spoken timers.
- **Shows a small HUD popup** at the bottom of the screen while it's awake: a white waveform line that
  moves with listening, thinking and speaking.

## How it works

```
mic → wake word → greeting → record until you finish → speech-to-text ─┐
                                      voice match + tone of voice ──────┤
                                                                        ↓
               spoken reply ← text-to-speech ← brain (Groq) + memory + skills
```

| Part | Tool | Runs |
|---|---|---|
| Wake word | [openWakeWord](https://github.com/dscripka/openWakeWord), pretrained "Hey Jarvis" model | locally, offline |
| Speech-to-text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`base.en`) | locally |
| Brain | [Groq API](https://console.groq.com/), `openai/gpt-oss-120b` | free tier |
| Text-to-speech | [edge-tts](https://github.com/rany2/edge-tts) (Microsoft neural voices) | free, no key |
| Speaker recognition | [Resemblyzer](https://github.com/resemble-ai/Resemblyzer) voice embeddings | locally |
| Tone of voice | [librosa](https://librosa.org/) loudness and pitch tracking | locally |
| HUD | [pywebview](https://pywebview.flowrl.com/) window with a 2D canvas | locally |

`brain.py` is the only file that talks to the LLM, so switching to another model later is a one-file
change (see the commented-out lines in `.env.example`).

## Setup

1. **Python 3.10+** (Windows is what it's built and tested on) and a working microphone.
2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Get a free Groq API key at https://console.groq.com/keys (no credit card).
4. Copy `.env.example` to `.env` and paste in the key.
5. Download the wake-word model once (openWakeWord doesn't bundle it in the pip package):
   ```
   python -c "from openwakeword.utils import download_models; download_models()"
   ```
6. Install Resemblyzer separately, without its declared dependencies. Its metadata pulls in the real
   `webrtcvad` package, which has no prebuilt Windows wheel and fails to build without Microsoft's
   C++ Build Tools. `requirements.txt` already installs `webrtcvad-wheels` (a prebuilt equivalent)
   and Resemblyzer's actual runtime dependencies, so this is safe:
   ```
   pip install resemblyzer --no-deps
   ```
7. Run it from the project folder:
   ```
   python -m src.jarvis.main
   ```

The first start takes a few seconds while the speech, voice and tone models load.

## Using it

| Say | What happens |
|---|---|
| "Hey Jarvis" / "Hi Jarvis" / "Hello Jarvis" | Wakes up and says hi |
| Anything, after it answers | Keeps the conversation going, no wake word needed |
| "Stop" while it's talking | Stops talking and listens |
| "Stop session" / "Stop listening" | Ends the conversation; it goes back to waiting for the wake word |
| "Remember that ..." / "Forget ..." | Saves or removes something in its memory |
| "What do you know about me?" | Tells you what it remembers |
| "Bye Jarvis", or any clear goodbye | Says bye and quits the program |

Ctrl+C in the terminal also quits.

Each turn prints a `[timing]` line in the terminal. `WAIT` is the time from when you stop talking
to JARVIS's first spoken word (usually 2 to 3 seconds).

## Settings

All optional, set in `.env`:

| Setting | Default | What it does |
|---|---|---|
| `USER_NAME` | `Neha` | Your name, used before your voice is enrolled |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | The brain. `qwen/qwen3.8-27b` sounds more natural but hits free-tier rate limits faster |
| `TTS_VOICE`, `TTS_RATE`, `TTS_PITCH` | `en-CA-LiamNeural`, `+0%`, `+0Hz` | The voice ([browse voices](https://speech.microsoft.com/portal/voicegallery)) |
| `FOLLOW_UP_SECONDS` | `600` | How long a conversation stays open with nobody talking (0 = wake word every time) |
| `MAX_REPLY_SENTENCES` | `3` | Replies are cut after this many sentences |
| `WHISPER_MODEL_SIZE` | `base.en` | `small.en` hears accents and technical words better but adds about 1.5s per reply |
| `STT_HINTS` | empty | A sentence of words you use a lot that it keeps mishearing |
| `SILENCE_HANG_MS`, `MAX_SILENCE_HANG_MS` | `1200`, `3500` | How long a pause has to be before it decides you've finished |
| `SPEAKER_MATCH_THRESHOLD` | `0.75` | How close a voice has to be to count as recognized |
| `SPEAKER_SHORT_CLIP_THRESHOLD` | `0.55` | Same, for short phrases, which give shakier matches |
| `SPEAKER_UNKNOWN_THRESHOLD` | `0.40` | Below this on the wake phrase, it asks who you are |
| `HISTORY_TURNS`, `HISTORY_RESET_SECONDS` | `6`, `600` | How much of the current chat it keeps, and when it starts fresh |
| `MEMORY_MAX_FACTS` | `100` | How many remembered facts it keeps per person |

## Your data stays on your laptop

Voiceprints (`data/voiceprints/`) and memories (`data/memory/`) are stored locally and are in
`.gitignore`, so they're never pushed to GitHub. Never commit your `.env` either; it holds your API
key.

## Roadmap

- [x] **Phase 1, core loop:** wake word, speech-to-text, Groq brain, text-to-speech
- [x] **Phase 2, HUD:** popup with the white waveform line, driven live by JARVIS's state. Still open:
      transparent window, boot animation, and a waveform that follows the spoken reply (GitHub
      issues #1 to #3)
- [x] **Phase 3, speaker recognition:** voiceprints, greetings by name, enrollment for new voices
- [x] **Phase 4, personality:** conversational, reads tone and sarcasm, long-term memory
- [ ] **Phase 5, skills:** time, date, apps and timers work; more actions to come
- [ ] **Phase 6, suit telemetry and protocols:** system vitals as HUD stats, voice-triggered macros

See `CLAUDE.md` for project context and the reasoning behind design decisions.
