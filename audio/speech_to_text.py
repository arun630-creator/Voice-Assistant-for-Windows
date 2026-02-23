"""
Nova Voice Assistant — Speech-to-Text
Uses faster-whisper for offline, low-latency transcription.
Records at mic native rate, downsamples to 16000Hz for Whisper.
Shows a live visual countdown timer while recording.
"""

import sys
import time
import wave
import queue
import tempfile
import threading
from math import gcd
from pathlib import Path
from typing import Optional

import sounddevice as sd
import numpy as np
from scipy.signal import resample_poly
from faster_whisper import WhisperModel

from config import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHUNK_SIZE,
    RECORD_SECONDS_MAX,
    SILENCE_THRESHOLD,
    SILENCE_ENERGY,
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_LANGUAGE,
    WHISPER_BEAM_SIZE,
)
from utils.logger import get_logger

log = get_logger(__name__)


# ── Visual recording bar ─────────────────────────────────────────────────────

_BAR_WIDTH = 20
_BLOCK_FULL = "█"
_BLOCK_EMPTY = "░"


def _print_recording_bar(elapsed: float, max_sec: float, rms: float) -> None:
    """Overwrite the current line with a progress bar + level meter."""
    remaining = max(0.0, max_sec - elapsed)
    frac = min(elapsed / max_sec, 1.0)
    filled = int(frac * _BAR_WIDTH)
    bar = _BLOCK_FULL * filled + _BLOCK_EMPTY * (_BAR_WIDTH - filled)

    # Tiny level indicator (0‑5 bars)
    level = min(int(rms / 300), 5)
    level_str = "▮" * level + "▯" * (5 - level)

    line = (
        f"\r  \033[1;33m🎙  Recording\033[0m [{bar}] "
        f"{remaining:.1f}s left  vol {level_str}"
    )
    sys.stdout.write(line)
    sys.stdout.flush()


def _clear_recording_bar() -> None:
    sys.stdout.write(f"\r{' ' * 80}\r")
    sys.stdout.write("  ✅  Recording complete — transcribing …\n")
    sys.stdout.flush()


# ── SpeechToText class ────────────────────────────────────────────────────────

class SpeechToText:
    """
    Records audio after the wake word and transcribes with faster-whisper.
    Accepts mic device/rate from caller (after auto-detect).
    """

    def __init__(
        self,
        mic_device: int = 0,
        mic_rate: int = 44100,
    ) -> None:
        self._mic_device = mic_device
        self._mic_rate = mic_rate

        # Pre-compute resampling factors
        g = gcd(mic_rate, AUDIO_SAMPLE_RATE)
        self._up = AUDIO_SAMPLE_RATE // g
        self._down = mic_rate // g

        log.info(
            "Loading faster-whisper model '%s' on %s (%s) …",
            WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
        )
        self._model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        log.info("faster-whisper model ready")

    # ── Public API ────────────────────────────────────────────────────────

    def listen_and_transcribe(self) -> Optional[str]:
        """Record from mic until silence/timeout, return transcribed text."""
        frames_native = self._record_command()
        if not frames_native:
            log.warning("No audio frames captured")
            return None

        raw_audio = np.concatenate(frames_native)
        audio_16k = self._downsample(raw_audio)

        wav_path = self._array_to_wav(audio_16k)
        try:
            text = self._transcribe(wav_path)
        finally:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except OSError:
                pass
        return text

    # ── Recording with visual timer ───────────────────────────────────────

    def _record_command(self) -> list[np.ndarray]:
        """Capture PCM frames with a live countdown bar."""
        frames: list[np.ndarray] = []
        audio_q: queue.Queue[np.ndarray] = queue.Queue()

        native_chunk = int(AUDIO_CHUNK_SIZE * self._mic_rate / AUDIO_SAMPLE_RATE)
        max_silent = int(SILENCE_THRESHOLD * self._mic_rate / native_chunk) + 3
        max_chunks = int(RECORD_SECONDS_MAX * self._mic_rate / native_chunk)
        # Minimum chunks before silence-stop kicks in (give user ~2s to start talking)
        min_chunks_before_silence = int(2.0 * self._mic_rate / native_chunk)

        def _callback(indata, _frames, _ti, status):
            if status:
                log.warning("sounddevice status: %s", status)
            audio_q.put(indata[:, 0].copy())

        try:
            log.info(
                "Recording command (max %.1fs, device=%d, rate=%d) …",
                RECORD_SECONDS_MAX, self._mic_device, self._mic_rate,
            )

            # Visual prompt
            print(
                f"\n  \033[1;33m🎙  Speak now!\033[0m  "
                f"(up to {RECORD_SECONDS_MAX:.0f}s — silence stops recording)\n"
            )

            silent_chunks = 0
            rec_start = time.monotonic()

            with sd.InputStream(
                samplerate=self._mic_rate,
                blocksize=native_chunk,
                dtype="int16",
                channels=1,
                device=self._mic_device,
                callback=_callback,
            ):
                for _ in range(max_chunks):
                    try:
                        chunk_np = audio_q.get(timeout=1.0)
                    except queue.Empty:
                        continue

                    frames.append(chunk_np)
                    energy = float(np.sqrt(np.mean(chunk_np.astype(np.float64) ** 2)))

                    # Update visual bar
                    elapsed = time.monotonic() - rec_start
                    _print_recording_bar(elapsed, RECORD_SECONDS_MAX, energy)

                    if energy < SILENCE_ENERGY:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0

                    if silent_chunks > max_silent and len(frames) > min_chunks_before_silence:
                        log.debug("Silence detected — stopping recording")
                        break

            _clear_recording_bar()
            log.info("Recording finished — %d chunks captured", len(frames))

        except Exception:
            log.exception("Error during recording")

        return frames

    # ── Downsampling ──────────────────────────────────────────────────────

    def _downsample(self, audio: np.ndarray) -> np.ndarray:
        if self._mic_rate == AUDIO_SAMPLE_RATE:
            return audio
        resampled = resample_poly(audio.astype(np.float64), self._up, self._down)
        return resampled.astype(np.int16)

    # ── WAV conversion ────────────────────────────────────────────────────

    @staticmethod
    def _array_to_wav(audio_16k: np.ndarray) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(AUDIO_SAMPLE_RATE)
            wf.writeframes(audio_16k.tobytes())
        return tmp_path

    # ── Transcription ─────────────────────────────────────────────────────

    def _transcribe(self, wav_path: str) -> Optional[str]:
        log.debug("Transcribing %s …", wav_path)
        t0 = time.perf_counter()
        try:
            segments, info = self._model.transcribe(
                wav_path,
                language=WHISPER_LANGUAGE,
                beam_size=WHISPER_BEAM_SIZE,
                vad_filter=False,
            )
            text = " ".join(seg.text for seg in segments).strip()
        except Exception:
            log.exception("Transcription failed")
            return None

        elapsed = time.perf_counter() - t0
        log.info("Transcription (%.2fs): '%s'", elapsed, text)
        return text if text else None
