"""
tts.py - Jarvis's voice (text-to-speech).

Primary:  edge-tts neural voices — free, very natural, with British accents.
          Needs internet for speech only (your brain still runs locally).
Fallback: the built-in Windows SAPI voice via COM, fully offline, used
          automatically if edge-tts can't be reached.

Change EDGE_VOICE to pick a different voice. Nice British options:
  en-GB-RyanNeural   (male, calm — Jarvis-like, default)
  en-GB-ThomasNeural (male)
  en-GB-SoniaNeural  (female)
  en-GB-LibbyNeural  (female)
"""

import os
import asyncio
import tempfile
import threading

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

EDGE_VOICE = "en-GB-RyanNeural"  # the natural British voice Jarvis speaks with
EDGE_RATE = "+0%"                # speaking speed, e.g. "+10%" faster, "-10%" slower

_sapi = None
_mixer_ready = False
_tmp = os.path.join(tempfile.gettempdir(), "jarvis_tts.mp3")
# Serialize speech so a background reminder can't talk over the main loop.
_speak_lock = threading.Lock()


def _sapi_speak(text: str):
    """Offline fallback using the Windows SAPI voice."""
    global _sapi
    import comtypes.client
    if _sapi is None:
        _sapi = comtypes.client.CreateObject("SAPI.SpVoice")
        voices = _sapi.GetVoices()
        for i in range(voices.Count):
            if "david" in voices.Item(i).GetDescription().lower():
                _sapi.Voice = voices.Item(i)
                break
    _sapi.Speak(text)


def _play(path: str):
    """Play an mp3 file and block until it finishes."""
    global _mixer_ready
    import pygame
    if not _mixer_ready:
        pygame.mixer.init()
        _mixer_ready = True
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    clock = pygame.time.Clock()
    while pygame.mixer.music.get_busy():
        clock.tick(20)
    pygame.mixer.music.unload()  # release the file so we can overwrite it next time


async def _edge_to_file(text: str, path: str):
    import edge_tts
    await edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE).save(path)


def speak(text: str):
    print(f"JARVIS: {text}")
    with _speak_lock:
        try:
            asyncio.run(_edge_to_file(text, _tmp))
            _play(_tmp)
        except Exception as e:
            print(f"  [voice] neural voice unavailable ({type(e).__name__}); using offline voice.")
            _sapi_speak(text)
