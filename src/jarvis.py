"""
jarvis.py - Your AI assistant's brain.

The loop:
  1. You type (later: speak) a command.
  2. The AI brain decides whether to just reply, or to use a tool.
  3. Jarvis runs any tools, then speaks the final reply out loud.

Jarvis can run on TWO brains. Change BRAIN below to switch:
  "local"  -> free model on your PC via Ollama (no API key, no cost)
  "claude" -> Anthropic Claude API (smartest; needs a key + credits in .env)

Run it with the run-jarvis.bat launcher, or:
  venv/Scripts/python.exe jarvis.py
"""

import os
import sys
from dotenv import load_dotenv

# Make console output safe for any character (weather °, arrows, accents, etc.)
# so printing tool results can never crash on Windows' default code page.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import paths
import tools
import tts
import capabilities


def _system_prompt():
    """The personality prompt plus anything Jarvis remembers about the user."""
    return SYSTEM_PROMPT + capabilities.memory_block()

# ---------------------------------------------------------------------------
# Choose your brain
# ---------------------------------------------------------------------------
BRAIN = "local"               # "local" (free) or "claude" (API)
LOCAL_MODEL = "qwen2.5:7b"    # free model Ollama runs (better at tools than llama3.1:8b)
CLAUDE_MODEL = "claude-opus-4-8"

# How you talk to Jarvis:
#   "wake"  - hands-free; say "Hey Jarvis", then your command (uses a real
#             wake-word engine — reliable)
#   "push"  - press ENTER, then speak a full command (no mic guesswork)
#   "voice" - hands-free via Whisper + the WAKE_WORD below (least reliable)
#   "text"  - just type
INPUT_MODE = "wake"
WAKE_WORD = "jarvis"          # used only in "voice" mode

# Jarvis's personality. Tweak this to change how he talks.
SYSTEM_PROMPT = (
    "You are Jarvis, the witty, loyal, highly capable AI assistant from Iron "
    "Man. You address the user as 'sir' and keep replies short and "
    "natural — one or two spoken sentences, since they are read aloud.\n"
    "Use your tools to take real actions and get real data: weather, web "
    "search, the time, reading files, opening apps, volume, locking the PC. "
    "Always call the relevant tool rather than guessing — never invent facts "
    "such as the weather, the time, or search results. After a tool runs, tell "
    "the user the actual result in plain words (for example, 'It's 19 degrees "
    "and raining in Paris, sir').\n"
    "For the current time or date, always call get_datetime — you cannot know "
    "it otherwise. For ANY question about weather or temperature, always call "
    "get_weather (pass 'here' when no city is named, e.g. 'weather outside', "
    "'weather here', 'is it cold') — never state a temperature you did not get "
    "from get_weather. For current events, news, prices, sports, people in "
    "office, or any fact that may have changed since your training, always use "
    "web_answer instead of answering from memory; your built-in knowledge is "
    "out of date.\n"
    "If you already know a fact about the user from your memory (listed below), "
    "just answer it directly — no tool needed for that. Use read_document only "
    "when the user explicitly asks you to read or summarize a file."
)

load_dotenv(os.path.join(paths.ROOT, ".env"))

# ---------------------------------------------------------------------------
# Voice (text-to-speech) lives in tts.py (neural British voice + offline
# fallback). Pick the voice by editing EDGE_VOICE there.
# ---------------------------------------------------------------------------
speak = tts.speak


# ===========================================================================
# BRAIN A: Local model via Ollama (free)
# ===========================================================================
def _ollama_tools():
    """Translate our tool list into the format Ollama expects."""
    out = []
    for t in tools.TOOL_SCHEMAS:
        params = t.get("input_schema") or {"type": "object", "properties": {}}
        out.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": params,
            },
        })
    return out


def think_local(conversation):
    import ollama
    for _ in range(6):  # safety cap on tool rounds
        resp = ollama.chat(
            model=LOCAL_MODEL,
            messages=conversation,
            tools=_ollama_tools(),
            # Low temperature = consistent, literal, follows instructions better
            # (high values made it wander into meta-commentary).
            options={"temperature": 0.3},
        )
        msg = resp["message"]
        tool_calls = msg.get("tool_calls") or []

        assistant_entry = {"role": "assistant", "content": msg.get("content", "") or ""}
        if tool_calls:
            assistant_entry["tool_calls"] = tool_calls
        conversation.append(assistant_entry)

        if not tool_calls:
            return assistant_entry["content"].strip() or "Done, sir."

        for tc in tool_calls:
            name = tc["function"]["name"]
            args = tc["function"]["arguments"]
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            func = tools.TOOL_FUNCTIONS.get(name)
            try:
                output = func(args) if func else f"Unknown tool: {name}"
            except Exception as e:
                output = f"Tool error: {e}"
            print(f"  [action] {name}({args}) -> {output}")
            conversation.append({"role": "tool", "name": name, "content": str(output)})
    return "I seem to be stuck in a loop, sir."


# ===========================================================================
# BRAIN B: Claude API (smartest)
# ===========================================================================
def think_claude(conversation):
    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    while True:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=_system_prompt(),
            tools=tools.TOOL_SCHEMAS,
            messages=conversation,
        )
        conversation.append({"role": "assistant", "content": response.content})
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        texts = [b.text for b in response.content if b.type == "text"]
        if not tool_uses:
            return " ".join(texts).strip() or "Done, sir."
        results = []
        for tu in tool_uses:
            func = tools.TOOL_FUNCTIONS.get(tu.name)
            try:
                output = func(tu.input) if func else f"Unknown tool: {tu.name}"
            except Exception as e:
                output = f"Tool error: {e}"
            print(f"  [action] {tu.name}({tu.input}) -> {output}")
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": output,
            })
        conversation.append({"role": "user", "content": results})


# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------
def preflight():
    if BRAIN == "claude":
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("\n[!] BRAIN is 'claude' but no API key found.")
            print("    Put your key in the .env file, or set BRAIN = 'local'.\n")
            sys.exit(1)
    elif BRAIN == "local":
        try:
            import ollama
            ollama.list()  # is the Ollama server reachable?
        except Exception:
            print("\n[!] Can't reach Ollama. Make sure Ollama is installed and running.")
            print("    (It usually starts automatically. Try opening the Ollama app.)\n")
            sys.exit(1)
    else:
        print(f"[!] Unknown BRAIN '{BRAIN}'. Use 'local' or 'claude'.")
        sys.exit(1)


def think(conversation):
    return think_local(conversation) if BRAIN == "local" else think_claude(conversation)


def _new_conversation():
    # Local brain takes the personality as a system message; Claude takes it
    # via the API's system field, so it only needs seeding for local.
    return [{"role": "system", "content": _system_prompt()}] if BRAIN == "local" else []


def _is_quit(text: str) -> bool:
    return text.strip().lower() in ("quit", "exit", "goodbye", "bye",
                                    "goodbye.", "stop", "shut down")


def _strip_wake_word(text: str):
    """If the wake word is in the text, return whatever comes after it.
    Returns None if the wake word isn't present at all."""
    low = text.lower()
    # tolerate common Whisper mishearings of the name
    for variant in (WAKE_WORD, "jarvis", "jervis", "travis"):
        idx = low.find(variant)
        if idx != -1:
            after = text[idx + len(variant):]
            return after.lstrip(" ,.!?:;-").strip()
    return None


def run_text_loop():
    conversation = _new_conversation()
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if _is_quit(user_input):
            speak("Goodbye, sir.")
            break
        conversation.append({"role": "user", "content": user_input})
        _respond(conversation)


def run_wake_loop():
    """Hands-free: say 'Hey Jarvis' to wake, then keep chatting. After each
    answer Jarvis listens a few seconds for a follow-up (no wake word needed);
    if you stay quiet, it goes back to sleep until the next 'Hey Jarvis'."""
    import voice
    import wakeword
    wakeword.preload()
    voice.calibrate()
    conversation = _new_conversation()
    FOLLOWUP_SECONDS = 10  # how long to wait for a follow-up before sleeping
    print("\n[Hands-free: say 'Hey Jarvis', then your command. Ctrl+C to stop.]")
    while True:
        print("\n[listening for 'Hey Jarvis'...]")
        try:
            if not wakeword.wait_for_wake():
                break
        except KeyboardInterrupt:
            break
        speak("Yes, sir?")

        # Conversation turn(s): keep taking commands without the wake word
        # until you go quiet for FOLLOWUP_SECONDS, then drop back to sleep.
        while True:
            command = voice.listen_phrase(timeout=FOLLOWUP_SECONDS)
            if not command:
                break  # no follow-up -> go back to waiting for "Hey Jarvis"
            print(f"  (heard: {command})")
            if _is_quit(command):
                speak("Goodbye, sir.")
                return
            conversation.append({"role": "user", "content": command})
            _respond(conversation)
            print("  [listening for a follow-up — or stay quiet to sleep]")


def run_push_loop():
    """Press ENTER, then speak a full command. Most reliable — no wake word.
    You can also just type a command instead of speaking."""
    import voice
    voice.calibrate()
    conversation = _new_conversation()
    print("\n[Push-to-talk: press ENTER then speak your command — or type it and "
          "press ENTER. Type 'quit' to stop.]")
    while True:
        try:
            typed = input("\n>> Press ENTER to speak (or type): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if _is_quit(typed):
            speak("Goodbye, sir.")
            break

        if typed:
            command = typed                      # they typed a command
        else:
            print("Listening... (speak now)")
            command = voice.listen_phrase(timeout=6)
            print(f"  (heard: {command})")

        if not command:
            print("  (didn't catch anything — try again)")
            continue
        if _is_quit(command):
            speak("Goodbye, sir.")
            break
        conversation.append({"role": "user", "content": command})
        _respond(conversation)


def run_voice_loop():
    import voice
    voice.calibrate()
    conversation = _new_conversation()
    print(f"\n[Listening — say '{WAKE_WORD.capitalize()}' to wake me. "
          f"Ctrl+C to stop.]\n")
    while True:
        try:
            heard = voice.listen_phrase()
        except KeyboardInterrupt:
            print()
            break
        if not heard:
            continue
        print(f"  (heard: {heard})")

        command = _strip_wake_word(heard)
        if command is None:
            continue  # wake word not spoken — ignore

        if not command:
            # They only said the name; ask what they want, then listen again.
            speak("Yes, sir?")
            command = voice.listen_phrase()
            print(f"  (heard: {command})")
            if not command:
                continue

        if _is_quit(command):
            speak("Goodbye, sir.")
            break
        conversation.append({"role": "user", "content": command})
        _respond(conversation)


def _respond(conversation):
    try:
        print("  [thinking...]")
        reply = think(conversation)
        speak(reply)
    except Exception as e:
        speak("I'm afraid I ran into a problem, sir.")
        print(f"  [error] {e}")


def main():
    preflight()
    speak("Jarvis online. How may I help you, sir?")
    if INPUT_MODE == "wake":
        run_wake_loop()
    elif INPUT_MODE == "push":
        run_push_loop()
    elif INPUT_MODE == "voice":
        run_voice_loop()
    else:
        run_text_loop()


if __name__ == "__main__":
    main()
