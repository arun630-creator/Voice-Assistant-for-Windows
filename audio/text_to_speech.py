"""
Nova Voice Assistant — Text‑to‑Speech
Uses pyttsx3 (Windows SAPI5 engine) for offline voice output.
"""

import threading
from typing import Optional

import pyttsx3

from config import TTS_RATE, TTS_VOLUME
from utils.logger import get_logger

log = get_logger(__name__)


class TextToSpeech:
    """
    Thread‑safe wrapper around pyttsx3.

    All calls to :meth:`speak` are serialised through a lock so the engine
    is never driven from two threads simultaneously.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._engine: Optional[pyttsx3.Engine] = None
        self._init_engine()

    # ── Engine management ─────────────────────────────────────────────────

    def _init_engine(self) -> None:
        """Create (or re‑create) the pyttsx3 engine."""
        try:
            self._engine = pyttsx3.init("sapi5")
            self._engine.setProperty("rate", TTS_RATE)
            self._engine.setProperty("volume", TTS_VOLUME)

            voices = self._engine.getProperty("voices")
            if voices:
                # Prefer a female voice if available, else first voice
                female = [v for v in voices if "female" in (v.name or "").lower()]
                chosen = female[0] if female else voices[0]
                self._engine.setProperty("voice", chosen.id)
                log.info("TTS voice: %s", chosen.name)
            log.info("pyttsx3 engine initialised (rate=%d, vol=%.1f)", TTS_RATE, TTS_VOLUME)
        except Exception:
            log.exception("Failed to initialise pyttsx3 engine")
            self._engine = None

    # ── Public API ────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """
        Speak *text* aloud.  Blocks until speech finishes.

        If the engine is not available the text is logged instead.
        """
        if not text:
            return
        log.info("TTS ▶ %s", text)
        with self._lock:
            if self._engine is None:
                self._init_engine()
            if self._engine is None:
                log.error("TTS engine unavailable — cannot speak")
                return
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except RuntimeError:
                # Engine loop already running — reinitialise
                log.warning("pyttsx3 RuntimeError — reinitialising engine")
                self._init_engine()
                if self._engine:
                    self._engine.say(text)
                    self._engine.runAndWait()
            except Exception:
                log.exception("TTS speak error")
