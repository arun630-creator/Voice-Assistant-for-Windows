"""
Nova Voice Assistant — Speech‑to‑Text
Uses faster‑whisper for offline, low‑latency transcription.
"""

import io
import time
import wave
import tempfile
from pathlib import Path
from typing import Optional

import sounddevice as sd
import numpy as np
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
from utils.helpers import rms_energy

log = get_logger(__name__)


class SpeechToText:
    """
    Records audio after the wake word and transcribes it with faster‑whisper.

    The model is loaded once at construction and reused for every call to
    :meth:`listen_and_transcribe`.
    """

    def __init__(self) -> None:
        log.info(
            "Loading faster‑whisper model '%s' on %s (%s) …",
            WHISPER_MODEL_SIZE,
            WHISPER_DEVICE,
            WHISPER_COMPUTE_TYPE,
        )
        self._model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        log.info("faster‑whisper model ready")

    # ── Public API ────────────────────────────────────────────────────────

    def listen_and_transcribe(self) -> Optional[str]:
        """
        Record from the mic until silence or timeout, then return text.

        Returns ``None`` if nothing useful was captured.
        """
        frames = self._record_command()
        if not frames:
            log.warning("No audio frames captured")
            return None

        wav_path = self._frames_to_wav(frames)
        try:
            text = self._transcribe(wav_path)
        finally:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except OSError:
                pass
        return text

    # ── Recording ─────────────────────────────────────────────────────────

    def _record_command(self) -> list[bytes]:
        """Capture PCM frames from the microphone until silence or timeout."""
        frames: list[bytes] = []
        try:
            log.info("🎙  Recording command (max %.1fs) …", RECORD_SECONDS_MAX)

            silent_chunks = 0
            max_silent = int(SILENCE_THRESHOLD * AUDIO_SAMPLE_RATE / AUDIO_CHUNK_SIZE) + 3
            max_chunks = int(RECORD_SECONDS_MAX * AUDIO_SAMPLE_RATE / AUDIO_CHUNK_SIZE)

            # Small initial delay to let user start speaking
            time.sleep(0.25)

            with sd.RawInputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                blocksize=AUDIO_CHUNK_SIZE,
                dtype="int16",
                channels=1,
            ) as stream:
                for _ in range(max_chunks):
                    try:
                        data, overflowed = stream.read(AUDIO_CHUNK_SIZE)
                        data = bytes(data)
                    except Exception as exc:
                        log.warning("Mic read error during recording: %s", exc)
                        continue

                    frames.append(data)
                    energy = rms_energy(data)

                    if energy < SILENCE_ENERGY:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0

                    if silent_chunks > max_silent and len(frames) > 5:
                        log.debug("Silence detected — stopping recording")
                        break

            log.info("Recording finished — %d frames captured", len(frames))
        except Exception:
            log.exception("Error during recording")
        return frames

    # ── WAV conversion ────────────────────────────────────────────────────

    @staticmethod
    def _frames_to_wav(frames: list[bytes]) -> str:
        """Write raw PCM frames to a temporary WAV file and return the path."""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()

        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16‑bit
            wf.setframerate(AUDIO_SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return tmp_path

    # ── Transcription ─────────────────────────────────────────────────────

    def _transcribe(self, wav_path: str) -> Optional[str]:
        """Run faster‑whisper on the WAV file and return the text."""
        log.debug("Transcribing %s …", wav_path)
        t0 = time.perf_counter()
        try:
            segments, info = self._model.transcribe(
                wav_path,
                language=WHISPER_LANGUAGE,
                beam_size=WHISPER_BEAM_SIZE,
                vad_filter=True,
            )
            text_parts = [seg.text for seg in segments]
            text = " ".join(text_parts).strip()
        except Exception:
            log.exception("Transcription failed")
            return None

        elapsed = time.perf_counter() - t0
        log.info("Transcription (%.2fs): '%s'", elapsed, text)
        return text if text else None
