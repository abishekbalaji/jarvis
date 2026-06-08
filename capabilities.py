"""
capabilities.py - Jarvis's "smart" powers beyond basic PC control.

  - get_weather   : live current weather for any place (Open-Meteo, free, no key)
  - web_answer    : real web search results so Jarvis can answer factual questions
  - read_document : find and read a file (.txt/.md/.pdf/.docx) so Jarvis can summarize it
  - remember_fact : save a fact about the user that persists across restarts

Memory is stored in jarvis_memory.json next to this file.
"""

import os
import re
import json
import pathlib
import datetime
import threading

import requests

# --------------------------------------------------------------------------
# 1) WEATHER  (Open-Meteo: free, no API key)
# --------------------------------------------------------------------------
_WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    56: "light freezing drizzle", 57: "dense freezing drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    66: "light freezing rain", 67: "heavy freezing rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow", 77: "snow grains",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    85: "slight snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with slight hail", 99: "thunderstorm with heavy hail",
}


# Words that mean "wherever I am" rather than a named place.
_VAGUE_LOCATIONS = {
    "", "outside", "here", "current", "currently", "now", "today", "local",
    "locally", "nearby", "my location", "current location", "my area",
    "where i am", "where i live", "my place", "this place", "around here",
}


def _ip_location():
    """Best-guess the user's city/coords from their IP (free, no key)."""
    r = requests.get("http://ip-api.com/json/", timeout=10).json()
    if r.get("status") == "success":
        return r["lat"], r["lon"], r.get("city", "your area"), r.get("country", "")
    return None


def _forecast(lat, lon, name, country) -> str:
    w = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto", "forecast_days": 1,
        }, timeout=10,
    ).json()
    c = w["current"]
    desc = _WEATHER_CODES.get(c["weather_code"], "unclear conditions")
    hi = w["daily"]["temperature_2m_max"][0]
    lo = w["daily"]["temperature_2m_min"][0]
    place = f"{name}, {country}".strip(", ")
    return (f"Weather in {place}: {desc}, currently {c['temperature_2m']}°C "
            f"(feels like {c['apparent_temperature']}°C). High {hi}°C, low {lo}°C. "
            f"Humidity {c['relative_humidity_2m']}%, wind {c['wind_speed_10m']} km/h.")


def get_weather(location: str) -> str:
    loc = (location or "").strip()
    try:
        # "weather outside / here / now" -> use the user's actual location.
        if loc.lower() in _VAGUE_LOCATIONS:
            ipl = _ip_location()
            if not ipl:
                return "I couldn't determine your location, sir. Which city?"
            return _forecast(*ipl)
        # Otherwise treat it as a named place and look it up.
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": loc, "count": 1}, timeout=10,
        ).json()
        if not geo.get("results"):
            return f"I couldn't find a place called '{loc}', sir."
        g = geo["results"][0]
        return _forecast(g["latitude"], g["longitude"], g["name"], g.get("country", ""))
    except Exception as e:
        return f"I couldn't get the weather right now ({type(e).__name__})."


# --------------------------------------------------------------------------
# 2) WEB ANSWER  (DuckDuckGo search results for the brain to answer from)
# --------------------------------------------------------------------------
def web_answer(query: str) -> str:
    try:
        from ddgs import DDGS
        # timeout stops it from hanging forever if DuckDuckGo is slow/rate-limited
        results = DDGS(timeout=10).text(query, max_results=5)
        if not results:
            return "I found nothing useful on the web, sir."
        lines = [f"- {r.get('title', '')}: {r.get('body', '')}" for r in results]
        return ("Web search results (use these to answer the user's question):\n"
                + "\n".join(lines))
    except Exception as e:
        return f"I couldn't search the web right now ({type(e).__name__})."


# --------------------------------------------------------------------------
# 3) READ A DOCUMENT  (find by name in common folders, extract text)
# --------------------------------------------------------------------------
def _search_dirs():
    # Only the user's document folders — NEVER the whole home directory
    # (that's slow and could expose unrelated/private files).
    home = pathlib.Path.home()
    candidates = [home / "Desktop", home / "Documents", home / "Downloads",
                  home / "OneDrive" / "Desktop", home / "OneDrive" / "Documents"]
    return [d for d in candidates if d.exists()]


def _find_file(name: str):
    name = name.lower().strip()
    exts = (".txt", ".md", ".pdf", ".docx")
    matches = []
    scanned = 0
    for d in _search_dirs():
        for root, dirs, files in os.walk(d):
            # Skip hidden/system folders (e.g. .claude, .git, AppData-like dirs).
            dirs[:] = [dd for dd in dirs if not dd.startswith(".")]
            for fn in files:
                scanned += 1
                if os.path.splitext(fn)[1].lower() in exts and name in fn.lower():
                    matches.append(pathlib.Path(root) / fn)
            if scanned > 20000 or len(matches) >= 20:
                break
    # Prefer the shortest filename match (usually the most relevant).
    matches.sort(key=lambda p: len(p.name))
    return matches[0] if matches else None


def _extract_text(path: pathlib.Path) -> str:
    suf = path.suffix.lower()
    if suf in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if suf == ".pdf":
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return "\n".join((pg.extract_text() or "") for pg in reader.pages)
    if suf == ".docx":
        import docx
        return "\n".join(par.text for par in docx.Document(str(path)).paragraphs)
    return ""


def read_document(name: str) -> str:
    path = _find_file(name)
    if not path:
        return f"I couldn't find a document matching '{name}' in your Desktop, Documents, or Downloads."
    try:
        text = _extract_text(path).strip()
    except Exception as e:
        return f"I found {path.name} but couldn't read it ({type(e).__name__})."
    if not text:
        return f"I found {path.name}, but it appears to have no readable text."
    text = text[:6000]  # keep it brief for the brain
    return f"Contents of '{path.name}' (located at {path}):\n{text}"


# --------------------------------------------------------------------------
# 4) MEMORY  (facts that persist across restarts)
# --------------------------------------------------------------------------
_MEMORY_FILE = os.path.join(os.path.dirname(__file__), "jarvis_memory.json")


def get_memories() -> list:
    try:
        with open(_MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("facts", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def remember_fact(fact: str) -> str:
    fact = fact.strip()
    if not fact:
        return "There was nothing to remember, sir."
    facts = get_memories()
    if fact in facts:
        return "I already have that noted, sir."
    facts.append(fact)
    with open(_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"facts": facts}, f, indent=2)
    return f"Noted, sir. I'll remember that: {fact}"


def memory_block() -> str:
    """A snippet injected into the system prompt so Jarvis 'knows' the user."""
    facts = get_memories()
    if not facts:
        return ""
    return ("\n\nFacts you remember about the user:\n"
            + "\n".join(f"- {f}" for f in facts))


# --------------------------------------------------------------------------
# 5) TIMERS & REMINDERS  (Jarvis speaks up when time is up)
# --------------------------------------------------------------------------
_TIMERS = []  # keep references so the threads aren't garbage-collected


def _parse_duration(text) -> int:
    """Turn '5 minutes', '1 hour 30 min', '45 seconds' into seconds."""
    text = str(text).lower()
    total = 0
    for amount, unit in re.findall(
            r"(\d+)\s*(hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)\b", text):
        n = int(amount)
        total += n * 3600 if unit.startswith("h") else n * 60 if unit.startswith("m") else n
    if total == 0:
        m = re.search(r"\d+", text)  # a bare number means minutes
        if m:
            total = int(m.group()) * 60
    return total


def _human_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h} hour{'s' if h != 1 else ''}")
    if m:
        parts.append(f"{m} minute{'s' if m != 1 else ''}")
    if s and not h:
        parts.append(f"{s} second{'s' if s != 1 else ''}")
    return " ".join(parts) or "0 seconds"


def set_timer(duration: str, message: str = "") -> str:
    """Set a timer/reminder. Speaks aloud when the time is up."""
    seconds = _parse_duration(duration)
    if seconds <= 0:
        return "How long should I set it for, sir?"
    message = (message or "").strip()

    def fire():
        import tts
        tts.speak(f"Sir, {message}." if message else "Sir, your timer is up.")

    t = threading.Timer(seconds, fire)
    t.daemon = True
    t.start()
    _TIMERS.append(t)
    when = _human_duration(seconds)
    if message:
        return f"I'll remind you to {message} in {when}, sir."
    return f"Timer set for {when}, sir."


# --------------------------------------------------------------------------
# 6) NOTES & LISTS  (to-do, shopping, etc. — persists across restarts)
# --------------------------------------------------------------------------
_LISTS_FILE = os.path.join(os.path.dirname(__file__), "jarvis_lists.json")


def _load_lists() -> dict:
    try:
        with open(_LISTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_lists(d: dict):
    with open(_LISTS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def add_to_list(item: str, list_name: str = "to-do") -> str:
    item = (item or "").strip()
    name = (list_name or "to-do").strip().lower()
    if not item:
        return "What should I add, sir?"
    d = _load_lists()
    d.setdefault(name, []).append(item)
    _save_lists(d)
    return f"Added '{item}' to your {name} list, sir."


def show_list(list_name: str = "to-do") -> str:
    name = (list_name or "to-do").strip().lower()
    items = _load_lists().get(name, [])
    if not items:
        return f"Your {name} list is empty, sir."
    return f"Your {name} list has {len(items)} items: " + "; ".join(items) + "."


def remove_from_list(item: str, list_name: str = "to-do") -> str:
    name = (list_name or "to-do").strip().lower()
    needle = (item or "").strip().lower()
    d = _load_lists()
    items = d.get(name, [])
    for i, x in enumerate(items):
        if needle and needle in x.lower():
            removed = items.pop(i)
            _save_lists(d)
            return f"Removed '{removed}' from your {name} list, sir."
    return f"I couldn't find '{item}' on your {name} list, sir."


# --------------------------------------------------------------------------
# 7) DAILY BRIEFING  (time + weather + headlines in one go)
# --------------------------------------------------------------------------
def _headlines() -> str:
    try:
        from ddgs import DDGS
        ddg = DDGS(timeout=10)
        try:
            results = ddg.news("today", max_results=4)   # real article titles
        except Exception:
            results = ddg.text("today's top news headlines", max_results=4)
        titles = [r.get("title", "").strip() for r in results if r.get("title")]
        return " ".join(f"{t}." for t in titles) or "no headlines available."
    except Exception as e:
        return f"couldn't fetch the news ({type(e).__name__})."


def daily_briefing(_: str = "") -> str:
    now = datetime.datetime.now().strftime("It's %A, %B %d, %I:%M %p.")
    weather = get_weather("here")
    news = _headlines()
    return (f"Daily briefing. {now}\n{weather}\n"
            f"Top headlines: {news}\n"
            "(Read this to the user as a brief, natural spoken summary.)")
