"""
Nova Voice Assistant — Microphone Auto-Detection

Intel SST mics are unreliable across host APIs and can go to sleep.
This module probes candidate devices at startup and returns the first
one that delivers real audio.  Does 2 passes: quick scan then a longer
retry with extended warmup if the mic is deeply asleep.
"""

import time
import queue

import sounddevice as sd
import numpy as np

from config import MIC_CANDIDATES, MIC_WARMUP_SECONDS
from utils.logger import get_logger

log = get_logger(__name__)

_RMS_ALIVE_THRESHOLD = 10.0  # RMS above this = mic is delivering real audio


def _probe_device(dev_idx: int, rate: int, warmup: float) -> float | None:
    """Try to read audio from *dev_idx* for up to *warmup* seconds.
    Return the first RMS above threshold, or None."""
    audio_q: queue.Queue[np.ndarray] = queue.Queue()

    def _cb(indata, _frames, _ti, status, q=audio_q):
        q.put(indata[:, 0].copy())

    try:
        with sd.InputStream(
            samplerate=rate,
            blocksize=4096,
            dtype="int16",
            channels=1,
            device=dev_idx,
            callback=_cb,
        ):
            start = time.monotonic()
            while (time.monotonic() - start) < warmup:
                try:
                    chunk = audio_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))
                if rms > _RMS_ALIVE_THRESHOLD:
                    return rms
    except Exception:
        pass
    return None


def find_working_mic() -> tuple[int, int]:
    """
    Probe *MIC_CANDIDATES* and return ``(device_index, sample_rate)``
    for the first device that produces audio with RMS > threshold.

    Does 2 passes:
      1. Quick scan (MIC_WARMUP_SECONDS each)
      2. Retry with 2× warmup — Intel SST sometimes needs >10s to wake

    Raises ``RuntimeError`` if no working mic is found after both passes.
    """
    for attempt, warmup_mult in enumerate([1.0, 2.0], start=1):
        warmup = MIC_WARMUP_SECONDS * warmup_mult
        if attempt == 1:
            print("\n🔍  Scanning microphones …")
        else:
            print(f"\n🔄  Retry #{attempt} (longer warmup {warmup:.0f}s) …")

        for dev_idx, rate in MIC_CANDIDATES:
            try:
                info = sd.query_devices(dev_idx)
            except Exception:
                continue
            if info["max_input_channels"] < 1:
                continue

            name = info["name"]
            label = f"Device {dev_idx} ({name}, {rate} Hz)"
            print(f"   ▸ Trying {label} ", end="", flush=True)

            t0 = time.monotonic()
            rms = _probe_device(dev_idx, rate, warmup)

            if rms is not None:
                elapsed = time.monotonic() - t0
                print(f"✅  alive (RMS={rms:.0f}, {elapsed:.1f}s)")
                log.info(
                    "Auto-detected mic: device=%d (%s), rate=%d, RMS=%.0f",
                    dev_idx, name, rate, rms,
                )
                return dev_idx, rate
            else:
                print("❌  silent")

    raise RuntimeError(
        "No working microphone found!  "
        "Check: Settings → System → Sound → Input → make sure mic is enabled."
    )
