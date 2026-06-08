"""
tools.py - The "hands" of Jarvis.

Each function here is something Jarvis can DO on your PC.
The big dictionaries at the bottom describe these tools to the AI brain
so it knows when to use them. To give Jarvis a new ability, write a
function here and add an entry to TOOL_SCHEMAS + TOOL_FUNCTIONS.
"""

import os
import subprocess
import webbrowser
import datetime
import urllib.parse

import capabilities
import google_services


# Common Windows apps mapped to the command that launches them.
# Add your own here (e.g. "spotify": "spotify").
KNOWN_APPS = {
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "wt",
    "task manager": "taskmgr",
    "settings": "start ms-settings:",
    "control panel": "control",
    "snipping tool": "snippingtool",
    "camera": "start microsoft.windows.camera:",
}


def open_app(name: str) -> str:
    """Open an application on the PC by name."""
    key = name.strip().lower()
    cmd = KNOWN_APPS.get(key)
    try:
        if cmd:
            # Some entries are "start ..." shell commands.
            if cmd.startswith("start "):
                subprocess.Popen(cmd, shell=True)
            else:
                subprocess.Popen(cmd, shell=True)
            return f"Opened {name}."
        # Fall back: try to launch whatever they said directly.
        subprocess.Popen(key, shell=True)
        return f"Attempted to open '{name}'."
    except Exception as e:
        return f"Could not open '{name}': {e}"


def search_web(query: str) -> str:
    """Open the default browser and search the web for a query."""
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return f"Searching the web for '{query}'."


def open_website(url: str) -> str:
    """Open a specific website in the browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}."


def get_datetime(_: str = "") -> str:
    """Return the current date and time."""
    now = datetime.datetime.now()
    return now.strftime("It is %A, %B %d, %Y, %I:%M %p.")


def set_volume(level: str) -> str:
    """Set system volume. 'mute', 'unmute', 'up', or 'down'."""
    # Uses Windows key simulation via nircmd-free approach (keybd sends).
    # Simple approach: use the 'powershell' SendKeys for volume keys.
    import ctypes
    VK = {"up": 0xAF, "down": 0xAE, "mute": 0xAD}
    action = level.strip().lower()
    presses = {"up": ("up", 5), "down": ("down", 5), "mute": ("mute", 1),
               "unmute": ("mute", 1)}
    if action not in presses:
        return "Say 'up', 'down', 'mute', or 'unmute'."
    key, times = presses[action]
    code = VK[key]
    for _ in range(times):
        ctypes.windll.user32.keybd_event(code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(code, 0, 2, 0)
    return f"Volume {action}."


def lock_pc(_: str = "") -> str:
    """Lock the Windows session."""
    import ctypes
    ctypes.windll.user32.LockWorkStation()
    return "Locking the workstation."


def media_control(action: str) -> str:
    """Control whatever media is playing using the keyboard's media keys."""
    import ctypes
    codes = {
        "play": 0xB3, "pause": 0xB3, "play_pause": 0xB3, "playpause": 0xB3,
        "toggle": 0xB3, "resume": 0xB3,
        "next": 0xB0, "skip": 0xB0, "forward": 0xB0,
        "previous": 0xB1, "prev": 0xB1, "back": 0xB1,
        "stop": 0xB2,
    }
    a = action.strip().lower().replace(" ", "_")
    code = codes.get(a)
    if code is None:
        return "I can play, pause, skip, go back, or stop, sir."
    ctypes.windll.user32.keybd_event(code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(code, 0, 2, 0)
    said = {0xB3: "Play/pause toggled", 0xB0: "Skipped to the next track",
            0xB1: "Back to the previous track", 0xB2: "Playback stopped"}[code]
    return f"{said}, sir."


def play_media(query: str) -> str:
    """Open YouTube with a search for a song/video so it can be played."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return f"Pulling up '{query}' on YouTube, sir."


# ---- Tell the AI brain about these tools (Claude tool-use format) ----

TOOL_SCHEMAS = [
    {
        "name": "open_app",
        "description": "Open an application or program on the user's Windows PC, "
                       "such as Notepad, Calculator, Paint, File Explorer, Settings, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The app to open, e.g. 'notepad'"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "search_web",
        "description": "Search the web for something using the default browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "open_website",
        "description": "Open a specific website/URL in the browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The website, e.g. 'youtube.com'"}
            },
            "required": ["url"],
        },
    },
    {
        "name": "get_datetime",
        "description": "Get the current date and time.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_volume",
        "description": "Adjust the PC volume: 'up', 'down', 'mute', or 'unmute'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "description": "up, down, mute, or unmute"}
            },
            "required": ["level"],
        },
    },
    {
        "name": "lock_pc",
        "description": "Lock the Windows workstation (requires password to get back in).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_weather",
        "description": "Get the live, current weather. Use whenever the user asks about "
                       "weather, temperature, or forecast. If the user does NOT name a "
                       "specific city (e.g. 'weather outside', 'weather here', 'is it "
                       "cold today'), pass 'here' as the location and it will use the "
                       "user's own location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string",
                             "description": "City name, e.g. 'London'. Use 'here' for the "
                                            "user's current location."}
            },
            "required": ["location"],
        },
    },
    {
        "name": "web_answer",
        "description": "Search the web and get back result snippets so you can ANSWER a "
                       "factual question (news, facts, who/what/when, current events). "
                       "Use this instead of search_web when the user wants an answer, not "
                       "just a browser tab. Read the results and reply in your own words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The question or search query"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_document",
        "description": "Read a specific FILE the user explicitly asks you to open, read, "
                       "or summarize (e.g. 'read my resume', 'summarize report.pdf'). "
                       "Finds it by name in Desktop/Documents/Downloads. Supports .txt, "
                       ".md, .pdf, .docx. Do NOT use this to answer questions about the "
                       "user themselves (their name, etc.) — that comes from memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Part of the file name, e.g. 'resume'"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "remember_fact",
        "description": "Save a fact about the user to long-term memory so you remember it "
                       "in future sessions (their name, preferences, important details). "
                       "Use when the user tells you something worth remembering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "The fact to remember, in a short sentence"}
            },
            "required": ["fact"],
        },
    },
    {
        "name": "media_control",
        "description": "Control media that is currently playing (Spotify, YouTube, any "
                       "player): play, pause, skip to next, go to previous, or stop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string",
                           "description": "play, pause, next, previous, or stop"}
            },
            "required": ["action"],
        },
    },
    {
        "name": "play_media",
        "description": "Play a specific song, artist, or video by opening it on YouTube. "
                       "Use when the user asks to play music or a particular song/video.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Song/artist/video to play"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "set_timer",
        "description": "Set a timer or reminder; Jarvis will speak aloud when the time is "
                       "up. Use for 'set a timer for 5 minutes' or 'remind me in 10 minutes "
                       "to call mom'. Put the thing to remind about in 'message'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "duration": {"type": "string", "description": "e.g. '5 minutes', '30 seconds', '1 hour'"},
                "message": {"type": "string", "description": "Optional: what to remind about, e.g. 'call mom'"}
            },
            "required": ["duration"],
        },
    },
    {
        "name": "add_to_list",
        "description": "Add an item to one of the user's lists (e.g. to-do, shopping). "
                       "Use for 'add milk to my shopping list', 'remind me to buy X'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "The item to add"},
                "list_name": {"type": "string", "description": "Which list, e.g. 'shopping' or 'to-do' (default to-do)"}
            },
            "required": ["item"],
        },
    },
    {
        "name": "show_list",
        "description": "Read out the items on one of the user's lists (to-do, shopping, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "list_name": {"type": "string", "description": "Which list (default to-do)"}
            },
        },
    },
    {
        "name": "remove_from_list",
        "description": "Remove an item from one of the user's lists.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "The item to remove"},
                "list_name": {"type": "string", "description": "Which list (default to-do)"}
            },
            "required": ["item"],
        },
    },
    {
        "name": "daily_briefing",
        "description": "Give the user a daily briefing: current time, local weather, and "
                       "top news headlines. Use for 'good morning', 'brief me', 'what's "
                       "my briefing'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "check_email",
        "description": "Check the user's Gmail inbox and summarize recent unread emails "
                       "(who they're from and the subject). Use for 'any new email', "
                       "'check my inbox', 'do I have mail'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "send_email",
        "description": "Send an email from the user's Gmail. Use when the user asks to "
                       "email someone. Needs the recipient's email address.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "The message body"}
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "get_calendar_events",
        "description": "Check the user's Google Calendar and list upcoming events. Use for "
                       "'what's on my calendar', 'what's my next meeting', 'am I free'.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

# Maps a tool name to the Python function that runs it.
TOOL_FUNCTIONS = {
    "open_app": lambda args: open_app(args.get("name", "")),
    "search_web": lambda args: search_web(args.get("query", "")),
    "open_website": lambda args: open_website(args.get("url", "")),
    "get_datetime": lambda args: get_datetime(),
    "set_volume": lambda args: set_volume(args.get("level", "")),
    "lock_pc": lambda args: lock_pc(),
    "get_weather": lambda args: capabilities.get_weather(args.get("location", "")),
    "web_answer": lambda args: capabilities.web_answer(args.get("query", "")),
    "read_document": lambda args: capabilities.read_document(args.get("name", "")),
    "remember_fact": lambda args: capabilities.remember_fact(args.get("fact", "")),
    "media_control": lambda args: media_control(args.get("action", "")),
    "play_media": lambda args: play_media(args.get("query", "")),
    "set_timer": lambda args: capabilities.set_timer(args.get("duration", ""), args.get("message", "")),
    "add_to_list": lambda args: capabilities.add_to_list(args.get("item", ""), args.get("list_name", "to-do")),
    "show_list": lambda args: capabilities.show_list(args.get("list_name", "to-do")),
    "remove_from_list": lambda args: capabilities.remove_from_list(args.get("item", ""), args.get("list_name", "to-do")),
    "daily_briefing": lambda args: capabilities.daily_briefing(),
    "check_email": lambda args: google_services.check_email(),
    "send_email": lambda args: google_services.send_email(
        args.get("to", ""), args.get("subject", ""), args.get("body", "")),
    "get_calendar_events": lambda args: google_services.get_calendar_events(),
}
