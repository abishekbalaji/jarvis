"""
voice.py - Jarvis's ears (speech-to-text + wake word).

Uses:
  - SpeechRecognition + PyAudio to capture phrases from the microphone
    (it automatically detects when you start and stop talking).
  - faster-whisper to turn that audio into text, fully offline/free.
    Runs on the NVIDIA GPU when available (much faster), else falls back
    to the CPU automatically.

The first time it runs, faster-whisper downloads a small model (~140 MB).
"""

import os
import glob

import paths

# --- Let Windows find the CUDA DLLs that ship inside the pip nvidia packages.
# Must happen before faster-whisper/CTranslate2 tries to use the GPU.
def _enable_cuda_dlls():
    base = os.path.join(paths.VENV, "Lib", "site-packages", "nvidia")
    bindirs = glob.glob(os.path.join(base, "*", "bin"))
    for bindir in bindirs:
        try:
            os.add_dll_directory(bindir)
        except (FileNotFoundError, OSError):
            pass
    # CTranslate2 loads cublas/cudnn via the legacy Windows search, which uses
    # PATH — so prepend the dirs there too, or the GPU load fails at runtime.
    if bindirs:
        os.environ["PATH"] = os.pathsep.join(bindirs) + os.pathsep + os.environ.get("PATH", "")


_enable_cuda_dlls()

import numpy as np
import speech_recognition as sr
from faster_whisper import WhisperModel

# "medium.en" is the most accurate English model that still runs fast on the
# GPU (~1.5 GB). Drop to "small.en" if you want a smaller/faster model.
WHISPER_SIZE = "medium.en"
DEVICE = "auto"  # "auto" (GPU if possible, else CPU), or force "cuda" / "cpu"

# A hint about the kind of things you'll say — biases Whisper toward these
# words so it mishears less. Add your own common words (names, places, etc.).
WHISPER_HINT = ("Voice commands for an assistant named Jarvis: weather, time, "
                "open app, search the web, cricket match score, news, reminder, "
                "lock the PC, volume.")

_model = None
_recognizer = sr.Recognizer()
_recognizer.dynamic_energy_threshold = False
# Higher = needs louder/clearer speech to start capturing (cuts noise triggers).
_recognizer.energy_threshold = 500
# Wait this long (seconds) of silence before deciding a phrase is finished.
_recognizer.pause_threshold = 0.9


def _build_model():
    """Try GPU first, fall back to CPU if CUDA isn't usable."""
    if DEVICE in ("auto", "cuda"):
        try:
            m = WhisperModel(WHISPER_SIZE, device="cuda", compute_type="float16")
            print("[voice] Speech recognition running on GPU (CUDA).")
            return m
        except Exception as e:
            if DEVICE == "cuda":
                raise
            print(f"[voice] GPU unavailable ({type(e).__name__}); using CPU instead.")
    m = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")
    print("[voice] Speech recognition running on CPU.")
    return m


def _get_model():
    """Load the Whisper model once, on first use."""
    global _model
    if _model is None:
        print("[voice] Loading speech recognition model (first run downloads it)...")
        _model = _build_model()
    return _model


def calibrate(seconds: float = 1.5):
    """Sample background noise once so silence detection works well."""
    with sr.Microphone(sample_rate=16000) as source:
        print("[voice] Calibrating microphone for background noise...")
        _recognizer.adjust_for_ambient_noise(source, duration=seconds)
    # Keep a sensible floor so a quiet room doesn't make it trigger on every sound.
    _recognizer.energy_threshold = max(_recognizer.energy_threshold, 500)
    print(f"[voice] Ready to listen. (mic sensitivity: {_recognizer.energy_threshold:.0f})")


def listen_phrase(timeout=None, phrase_time_limit=15):
    """Block until a spoken phrase is captured, then return it as text.
    Returns '' if nothing intelligible was heard."""
    with sr.Microphone(sample_rate=16000) as source:
        try:
            audio = _recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
        except sr.WaitTimeoutError:
            return ""
    return _transcribe(audio)


def _transcribe(audio: "sr.AudioData") -> str:
    """Convert captured audio to text with faster-whisper."""
    raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if samples.size == 0:
        return ""
    segments, _ = _get_model().transcribe(
        samples,
        language="en",
        # Drop non-speech (silence/noise) BEFORE transcribing — this is what
        # stops Whisper hallucinating phrases like "Thank you" / "We have no".
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        # Don't let one utterance's text bias the next — avoids repeated junk.
        condition_on_previous_text=False,
        # Bias the decoder toward the words you're likely to say.
        initial_prompt=WHISPER_HINT,
        beam_size=5,
    )
    return " ".join(seg.text for seg in segments).strip()
