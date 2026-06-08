"""
wakeword.py - Hands-free wake-word detection ("Hey Jarvis").

Unlike Whisper, openWakeWord is a dedicated wake-word engine: it listens to a
live audio stream and fires only when it hears the trained phrase. That makes
it far more reliable than transcribing a single short word.

Flow: wait_for_wake() blocks until it hears "Hey Jarvis", then Jarvis records
your actual command with Whisper (voice.listen_phrase).
"""

import numpy as np
import pyaudio
import openwakeword
from openwakeword.model import Model

WAKE_MODEL = "hey_jarvis"
THRESHOLD = 0.5     # 0..1 — raise to reduce false triggers, lower to catch more
FRAME = 1280        # 80 ms of audio at 16 kHz (what the model expects per step)

_model = None


def preload():
    """Load the wake-word engine once."""
    global _model
    if _model is None:
        print("[wake] Loading wake-word engine...")
        openwakeword.utils.download_models()  # no-op if already downloaded
        _model = Model(wakeword_models=[WAKE_MODEL], inference_framework="onnx")
    return _model


def wait_for_wake():
    """Block until 'Hey Jarvis' is heard. Returns True, or False if interrupted."""
    model = preload()
    model.reset()
    pa = pyaudio.PyAudio()
    stream = pa.open(rate=16000, channels=1, format=pyaudio.paInt16,
                     input=True, frames_per_buffer=FRAME)
    try:
        while True:
            data = stream.read(FRAME, exception_on_overflow=False)
            frame = np.frombuffer(data, dtype=np.int16)
            scores = model.predict(frame)
            if scores.get(WAKE_MODEL, 0.0) >= THRESHOLD:
                return True
    except KeyboardInterrupt:
        return False
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
