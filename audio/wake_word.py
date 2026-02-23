"""
Nova Voice Assistant — Wake Word Detection
Uses Vosk free recognition for lightweight offline keyword spotting.
Detects "hello", "hi", or "hey" — common words Vosk recognises well.
Accepts mic device/rate from caller (set after auto-detect).
"""

import json
import threading
import queue
import sys
from math import gcd
from typing import Callable, Optional

import sounddevice as sd
import numpy as np
from scipy.signal import resample_poly
from vosk import Model, KaldiRecognizer

from config import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHUNK_SIZE,
    WAKE_WORDS,
    VOSK_MODEL_DIR,
)
from utils.logger import get_logger

log = get_logger(__name__)


# ── Resampling helpers ────────────────────────────────────────────────────────

def _make_resample_params(native: int, target: int):
    g = gcd(native, target)
    return target // g, native // g


def _downsample_chunk(data_int16: np.ndarray, up: int, down: int) -> bytes:
    if up == 1 and down == 1:
        return data_int16.tobytes()
    resampled = resample_poly(data_int16.astype(np.float64), up, down)
    return resampled.astype(np.int16).tobytes()


# ── Wake-word matching ────────────────────────────────────────────────────────

_WAKE_SET = set(WAKE_WORDS)          # {"hello", "hi", "hey"}


def _matches_wake(text: str) -> bool:
    """Return True if *text* contains any wake word."""
    if not text:
        return False
    for w in text.split():
        if w in _WAKE_SET:
            return True
    return False


# ── Visual status indicator ───────────────────────────────────────────────────

_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class _StatusPrinter:
    """Prints an animated 'Listening …' line that refreshes in-place."""

    def __init__(self):
        self._idx = 0
        self._lock = threading.Lock()

    def tick(self) -> None:
        with self._lock:
            ch = _SPINNER[self._idx % len(_SPINNER)]
            msg = (
                f"\r  {ch}  Listening ... say "
                f"\033[1;36mhello\033[0m or \033[1;36mhi\033[0m to wake Nova"
            )
            sys.stdout.write(msg)
            sys.stdout.flush()
            self._idx += 1

    def clear(self, replacement: str = "") -> None:
        with self._lock:
            sys.stdout.write(f"\r{' ' * 80}\r")
            if replacement:
                sys.stdout.write(replacement + "\n")
            sys.stdout.flush()
            self._idx = 0


# ── Detector class ────────────────────────────────────────────────────────────

class WakeWordDetector:
    """
    Continuously listens on the microphone using Vosk.
    When any of the WAKE_WORDS is detected the *callback* fires.
    """

    def __init__(
        self,
        callback: Callable[[], None],
        mic_device: int = 0,
        mic_rate: int = 44100,
    ) -> None:
        self._callback = callback
        self._running = threading.Event()
        self._paused = threading.Event()          # when SET the listener pauses
        self._thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._status = _StatusPrinter()

        # Mic settings (set by caller after auto-detect)
        self._mic_device = mic_device
        self._mic_rate = mic_rate
        self._up, self._down = _make_resample_params(self._mic_rate, AUDIO_SAMPLE_RATE)

        # Load Vosk model
        model_path = str(VOSK_MODEL_DIR)
        log.info("Loading Vosk model from %s ...", model_path)
        try:
            self._model = Model(model_path)
        except Exception as exc:
            log.error(
                "Failed to load Vosk model — download one from "
                "https://alphacephei.com/vosk/models and extract to %s.  Error: %s",
                model_path, exc,
            )
            raise

        # Free recognition — no grammar; Vosk already knows "hello"/"hi"/"hey"
        self._recogniser = KaldiRecognizer(self._model, AUDIO_SAMPLE_RATE)
        self._recogniser.SetWords(True)
        log.info(
            "WakeWordDetector ready — device=%d, native=%dHz, target=%dHz, words=%s",
            self._mic_device, self._mic_rate, AUDIO_SAMPLE_RATE, WAKE_WORDS,
        )

    @property
    def status_printer(self) -> _StatusPrinter:
        return self._status

    # ── Public API ────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            log.warning("WakeWordDetector already running")
            return
        self._running.set()
        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="wake-word",
        )
        self._thread.start()
        log.info("Wake-word listener thread started")

    def stop(self) -> None:
        self._running.clear()
        self._paused.clear()                    # unblock if paused
        self._status.clear()
        if self._thread:
            self._thread.join(timeout=3.0)
            log.info("Wake-word listener thread stopped")

    def pause(self) -> None:
        """Pause listening (while STT records). The mic stream stays open
        but audio chunks are discarded so there's no device conflict."""
        self._paused.set()
        # Drain queued audio so stale chunks aren't processed on resume
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        log.debug("Wake-word listener PAUSED")

    def resume(self) -> None:
        """Resume listening after STT finishes."""
        # Drain again and reset Vosk so old audio doesn't trigger false wake
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        self._recogniser.Reset()
        self._paused.clear()
        log.debug("Wake-word listener RESUMED")

    # ── Internal ──────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            log.warning("sounddevice status: %s", status)
        self._audio_queue.put(indata[:, 0].copy())

    def _listen_loop(self) -> None:
        try:
            native_block = int(AUDIO_CHUNK_SIZE * self._mic_rate / AUDIO_SAMPLE_RATE)

            with sd.InputStream(
                samplerate=self._mic_rate,
                blocksize=native_block,
                dtype="int16",
                channels=1,
                device=self._mic_device,
                callback=self._audio_callback,
            ):
                log.debug(
                    "Mic stream opened (device=%d, rate=%d, block=%d)",
                    self._mic_device, self._mic_rate, native_block,
                )

                tick_counter = 0
                while self._running.is_set():
                    # If paused, discard audio and skip processing
                    if self._paused.is_set():
                        try:
                            self._audio_queue.get(timeout=0.1)
                        except queue.Empty:
                            pass
                        continue

                    try:
                        raw_chunk = self._audio_queue.get(timeout=0.3)
                    except queue.Empty:
                        tick_counter += 1
                        if tick_counter % 2 == 0:
                            self._status.tick()
                        continue

                    # Animate spinner (~3 Hz)
                    tick_counter += 1
                    if tick_counter % 4 == 0:
                        self._status.tick()

                    data_16k = _downsample_chunk(raw_chunk, self._up, self._down)

                    if self._recogniser.AcceptWaveform(data_16k):
                        result = json.loads(self._recogniser.Result())
                        text: str = result.get("text", "").lower().strip()
                        if text:
                            log.debug("Vosk heard: %s", text)
                        if _matches_wake(text):
                            self._status.clear("  \u2705  Wake word detected!")
                            log.info("Wake word detected! (%s)", text)
                            self._recogniser.Reset()
                            self._callback()
                    else:
                        partial = json.loads(self._recogniser.PartialResult())
                        partial_text = partial.get("partial", "").lower().strip()
                        if _matches_wake(partial_text):
                            self._status.clear("  \u2705  Wake word detected!")
                            log.info("Wake word detected (partial)! (%s)", partial_text)
                            self._recogniser.Reset()
                            self._callback()

        except Exception:
            log.exception("Fatal error in wake-word listener loop")
