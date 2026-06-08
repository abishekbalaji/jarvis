# JARVIS — your personal AI assistant

A hands-free voice assistant that controls your Windows PC — runs **100% free
and locally**. Built with Python + Ollama (the brain) + Whisper (the ears) +
edge-tts (a natural British voice).

## What it can do right now
- **Hands-free wake word** — say "Hey Jarvis" and it listens.
- Have a real conversation with a Jarvis personality.
- **Speak its replies out loud** in a natural British voice.
- Control your PC:
  - Open apps (Notepad, Calculator, Paint, Settings, File Explorer…)
  - Open a website / search the web in the browser
  - Tell the date & time
  - Change the volume (up / down / mute)
  - Lock the PC
- **Smart abilities:**
  - 🌤️ **Live weather** — real current conditions for any city, or "weather outside" auto-detects your location
  - 🔎 **Web answers** — reads search results and answers factual / current-events questions out loud
  - 📄 **Read documents** — finds a file in your Desktop/Documents/Downloads (.txt, .md, .pdf, .docx) and summarizes or answers questions about it
  - 🧠 **Memory** — remembers facts about you (name, preferences) across restarts; stored in `jarvis_memory.json`
  - ⏰ **Timers & reminders** — "set a timer for 5 minutes", "remind me in 10 minutes to call mom" — speaks up when it's time
  - 🎵 **Music & media** — play/pause/skip whatever's playing, or "play <song>" on YouTube
  - 📝 **Notes & lists** — "add milk to my shopping list", "what's on my to-do list" (saved in `jarvis_lists.json`)
  - 📰 **Daily briefing** — "good morning" / "brief me" → time, local weather, and top headlines in one go

---

## How to run it
**Double-click `run-jarvis.bat`.** That's it — no setup, no API key, no cost.

Jarvis says "Jarvis online" and then **listens for the wake word**.

### Talking to Jarvis (hands-free — the default)
Say **"Hey Jarvis"**, wait for "Yes, sir?", then speak your command:
- "Hey Jarvis" → *"What time is it?"*
- "Hey Jarvis" → *"What's the weather in London?"*
- "Hey Jarvis" → *"Open notepad"*
- "Hey Jarvis" → *"Lock my pc"*

To stop, press **Ctrl+C** in the window.

> Why "Hey Jarvis" specifically? Hands-free detection uses a dedicated
> wake-word engine (openWakeWord) with a reliable pre-trained "Hey Jarvis"
> model — much better than making Whisper guess a single word.

### Other input modes (set `INPUT_MODE` at the top of `jarvis.py`)
- `"wake"` — hands-free "Hey Jarvis" (default)
- `"push"` — press ENTER, then speak (or type) — the most reliable
- `"text"` — type only
- `"voice"` — hands-free using the `WAKE_WORD` via Whisper (least reliable)

---

## Settings you can change (top of `jarvis.py`)
- `BRAIN` — `"local"` (free, default) or `"claude"` (smarter, needs an API key in `.env`)
- `LOCAL_MODEL` — the free model (default `"qwen2.5:7b"` — good at using tools)
- `INPUT_MODE` — `"wake"` (default), `"push"`, `"text"`, or `"voice"`
- `WAKE_WORD` — used only in `"voice"` mode (default `"jarvis"`)
- Wake sensitivity — `THRESHOLD` in `wakeword.py` (raise if it false-triggers, lower if it misses you)
- Voice — `EDGE_VOICE` in `tts.py` (British options listed there)

## Costs
- Everything here is **free**: Python, the local brain (Ollama/qwen2.5), the
  speech-to-text (Whisper on your GPU), the wake word, and weather/web all run at $0.
- The British neural voice (edge-tts) and weather/web lookups use the internet,
  but they're **free** — no API key, no bill.
- Optional: switching `BRAIN` to `"claude"` uses the paid Anthropic API (a few
  cents per chat) for top-tier replies. A Claude.ai Pro subscription does **not**
  cover the API — that needs separate credits in the Anthropic console.

---

## Make it yours
- **Personality:** edit `SYSTEM_PROMPT` in `jarvis.py`.
- **Voice:** edit `EDGE_VOICE` in `tts.py`.
- **Basic PC tools:** add a function + schema in `tools.py`.
- **Smart abilities:** add a function in `capabilities.py`, then register it in
  `tools.py` (`TOOL_SCHEMAS` + `TOOL_FUNCTIONS`).

## Project files
- `jarvis.py` — main brain + the input loops (wake / push / text / voice)
- `tools.py` — basic PC control tools
- `capabilities.py` — weather, web answers, file reading, memory
- `voice.py` — microphone + Whisper speech-to-text
- `wakeword.py` — "Hey Jarvis" detection
- `tts.py` — the spoken voice
- `jarvis_memory.json` — what Jarvis remembers about you

## Next upgrades (the roadmap)
- ✅ **Voice input:** mic + Whisper + "Hey Jarvis" wake word. **Done.**
- ✅ **Capability pack:** live weather, web answers, file reading, memory. **Done.**
- ✅ **Productivity & media:** timers/reminders, music control, notes/lists, daily briefing. **Done.**
- **Email & calendar:** read/send email, check calendar (needs Google sign-in — next).
- **Smart home:** lights/plugs/thermostat via Home Assistant.
- **Always-on / proactive:** scheduled morning briefing, "meeting in 5 min" alerts.
