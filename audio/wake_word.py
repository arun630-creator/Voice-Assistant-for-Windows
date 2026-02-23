"""
Nova Voice Assistant — Wake Word Detection
Uses Vosk for lightweight offline keyword spotting.
Runs in a dedicated background thread.
"""

import json
import threading
import queue
from typing import Callable, Optional

import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer

from config import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHUNK_SIZE,
    WAKE_WORD,
    VOSK_MODEL_DIR,
)
from utils.logger import get_logger

log = get_logger(__name__)


class WakeWordDetector:
    """
    Continuously listens on the default microphone using Vosk.

    When the wake word is detected the registered *callback* is invoked
    from the listener thread.  Call :meth:`stop` for a clean shutdown.
    """

    def __init__(self, callback: Callable[[], None]) -> None:
        self._callback = callback
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue[bytes] = queue.Queue()

        model_path = str(VOSK_MODEL_DIR)
        log.info("Loading Vosk model from %s …", model_path)
        try:
            self._model = Model(model_path)
        except Exception as exc:
            log.error(
                "Failed to load Vosk model.  "
                "Download a small model from https://alphacephei.com/vosk/models "
                "and extract it to %s.  Error: %s",
                model_path,
                exc,
            )
            raise

        self._recogniser = KaldiRecognizer(self._model, AUDIO_SAMPLE_RATE)
        self._recogniser.SetWords(True)
        log.info("WakeWordDetector initialised — listening for '%s'", WAKE_WORD)

    # ── Public API ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Launch the listener in a daemon thread."""
        if self._thread and self._thread.is_alive():
            log.warning("WakeWordDetector already running")
            return
        self._running.set()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="wake-word")
        self._thread.start()
        log.info("Wake‑word listener thread started")

    def stop(self) -> None:
        """Signal the listener to exit and wait for the thread."""
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=3.0)
            log.info("Wake‑word listener thread stopped")

    # ── Internal ──────────────────────────────────────────────────────────

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Called by sounddevice for each audio block — push raw bytes to queue."""
        if status:
            log.warning("sounddevice status: %s", status)
        self._audio_queue.put(bytes(indata))

    def _listen_loop(self) -> None:
        """Open sounddevice stream and continuously feed chunks to Vosk."""
        try:
            with sd.RawInputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                blocksize=AUDIO_CHUNK_SIZE,
                dtype="int16",
                channels=1,
                callback=self._audio_callback,
            ):
                log.debug("Microphone stream opened for wake‑word detection")

                while self._running.is_set():
                    try:
                        data = self._audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if self._recogniser.AcceptWaveform(data):
                        result = json.loads(self._recogniser.Result())
                        text: str = result.get("text", "").lower().strip()
                        if text:
                            log.debug("Vosk heard: %s", text)
                        if WAKE_WORD in text:
                            log.info("🔔 Wake word detected!")
                            self._callback()
                    else:
                        partial = json.loads(self._recogniser.PartialResult())
                        partial_text: str = partial.get("partial", "").lower().strip()
                        if WAKE_WORD in partial_text:
                            log.info("🔔 Wake word detected (partial)!")
                            self._recogniser.Reset()
                            self._callback()

        except Exception:
            log.exception("Fatal error in wake‑word listener loop")
