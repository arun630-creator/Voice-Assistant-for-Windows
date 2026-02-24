"""
Nova Voice Assistant — Main Entry Point
Orchestrates wake‑word detection → STT → classify → route → TTS.

Usage:
    python main.py              # voice mode (microphone)
    python main.py --keyboard   # type commands instead of speaking
"""

import argparse
import json
import os
import re
import sys
import signal
import threading
import time
from typing import Optional

from pathlib import Path

# Ensure the package root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Prevent hf_xet download failures on some Windows setups
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

from config import WAKE_WORD, WAKE_WORDS
from utils.logger import setup_logging, get_logger
from audio.text_to_speech import TextToSpeech
from brain.llm_interface import LLMInterface
from brain.intent_parser import IntentParser
from brain.fallback_classifier import fallback_classify
from brain.memory import Memory
from router.command_router import CommandRouter

log = get_logger("nova.main")

# Regex to strip any leading wake word from the transcription
_WAKE_RE = re.compile(
    r"^(?:" + "|".join(re.escape(w) for w in WAKE_WORDS) + r")[\s,.:!?]*",
    re.IGNORECASE,
)


class Nova:
    """
    Top‑level application object.

    Lifecycle:
        nova = Nova()
        nova.run()                  # voice mode (default)
        nova.run(keyboard=True)     # keyboard / typing mode
    """

    def __init__(self, keyboard_mode: bool = False) -> None:
        setup_logging()
        self._keyboard_mode = keyboard_mode
        log.info("=" * 60)
        log.info("  Nova Voice Assistant — Initialising …")
        log.info("  Mode: %s", "KEYBOARD" if keyboard_mode else "VOICE")
        log.info("=" * 60)

        # ── Common components ─────────────────────────────────────────────
        self._tts = TextToSpeech()
        self._llm = LLMInterface()
        self._parser = IntentParser()
        self._memory = Memory()
        self._router = CommandRouter(self._memory, tts_callback=self._tts.speak)

        # Voice‑only components (lazy init)
        self._stt = None
        self._detector = None
        self._wake_event = threading.Event()
        self._shutdown_event = threading.Event()

        if not keyboard_mode:
            self._init_voice()

        log.info("All components initialised")

    # ── Voice init (mic auto‑detect → wake + STT) ────────────────────────

    def _init_voice(self) -> None:
        from audio.mic_finder import find_working_mic
        from audio.speech_to_text import SpeechToText
        from audio.wake_word import WakeWordDetector

        # Auto‑detect a working mic
        mic_dev, mic_rate = find_working_mic()
        print(f"\n  🎤  Using mic device {mic_dev} @ {mic_rate} Hz\n")

        self._stt = SpeechToText(mic_device=mic_dev, mic_rate=mic_rate)
        self._detector = WakeWordDetector(
            callback=self._on_wake,
            mic_device=mic_dev,
            mic_rate=mic_rate,
        )

    # ── Signal handling ───────────────────────────────────────────────────

    def _setup_signals(self) -> None:
        def _handler(sig: int, _frame):
            log.info("Received signal %d — shutting down …", sig)
            self._shutdown_event.set()
            self._wake_event.set()

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)

    # ── Wake‑word callback ────────────────────────────────────────────────

    def _on_wake(self) -> None:
        log.debug("_on_wake triggered")
        self._wake_event.set()

    # ── Intent classification ─────────────────────────────────────────────

    def _classify(self, text: str) -> str:
        raw_response = None
        if self._llm.is_available():
            raw_response = self._llm.classify(text)
        else:
            log.warning("Ollama unavailable — using fallback regex classifier")
            fb = fallback_classify(text)
            if fb:
                raw_response = json.dumps(fb)

        intent = self._parser.parse(raw_response, original_text=text)
        log.info("Resolved intent: %s", intent)

        response = self._router.route(intent)
        log.info("Response: %s", response)
        return response

    # ── Main pipeline (voice) ─────────────────────────────────────────────

    def _process_command(self) -> None:
        """Record → transcribe → classify → route → speak."""

        # Pause the wake-word detector so it doesn't fight for the mic
        # and doesn't trigger again on the user's speech
        if self._detector:
            self._detector.pause()

        # Audible + visual acknowledgement
        self._tts.speak("Yes?")

        # Brief pause so TTS playback fully finishes before mic records
        time.sleep(0.4)

        # Record & transcribe (STT shows its own visual timer)
        text = self._stt.listen_and_transcribe()

        # Resume wake-word detector
        if self._detector:
            self._detector.resume()

        if not text:
            self._tts.speak("Sorry, I didn't catch that.")
            return

        # Strip leading wake word from the transcription
        cleaned = _WAKE_RE.sub("", text).strip()
        text = cleaned if cleaned else text

        log.info("User said: '%s'", text)
        print(f"  🗣  You said: \033[1m{text}\033[0m")

        response = self._classify(text)
        print(f"  🤖  Nova: {response}\n")
        self._tts.speak(response)

    # ── Run loops ─────────────────────────────────────────────────────────

    def run(self) -> None:
        if self._keyboard_mode:
            self._run_keyboard()
        else:
            self._run_voice()

    def _run_voice(self) -> None:
        self._setup_signals()
        self._detector.start()

        print()
        print("=" * 60)
        print("  🟢  Nova Voice Assistant — VOICE MODE")
        print(f"  Say \033[1;36mhello\033[0m or \033[1;36mhi\033[0m to wake me up,")
        print("  then speak your command.")
        print("  Press Ctrl+C to quit.")
        print("=" * 60)
        print()

        self._tts.speak("Nova is ready. Say hello or hi to begin.")
        log.info("Entering main loop — waiting for wake word …")

        try:
            while not self._shutdown_event.is_set():
                triggered = self._wake_event.wait(timeout=0.5)
                if not triggered:
                    continue
                self._wake_event.clear()

                if self._shutdown_event.is_set():
                    break

                try:
                    self._process_command()
                except Exception:
                    log.exception("Unhandled error in _process_command")
                    self._tts.speak("An error occurred. Please try again.")
        finally:
            self._cleanup()

    def _run_keyboard(self) -> None:
        self._setup_signals()
        print()
        print("=" * 60)
        print("  Nova Voice Assistant — KEYBOARD MODE")
        print("  Type your commands below.  Type 'quit' or 'exit' to stop.")
        print("=" * 60)
        print()
        self._tts.speak("Nova is ready in keyboard mode.")

        try:
            while not self._shutdown_event.is_set():
                try:
                    user_input = input("You > ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "bye", "stop"):
                    self._tts.speak("Goodbye!")
                    break

                # Strip wake word prefix if typed
                cleaned = _WAKE_RE.sub("", user_input).strip()
                text = cleaned if cleaned else user_input

                log.info("User typed: '%s'", text)
                response = self._classify(text)
                print(f"Nova > {response}")
                self._tts.speak(response)
        except KeyboardInterrupt:
            print()
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        log.info("Cleaning up …")
        if self._detector:
            self._detector.stop()
        self._memory.close()
        log.info("Nova shut down cleanly. Goodbye!")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Nova Voice Assistant")
    parser.add_argument(
        "--keyboard", "-k",
        action="store_true",
        help="Run in keyboard mode (type commands instead of speaking)",
    )
    parser.add_argument(
        "--tray", "-t",
        action="store_true",
        help="Run as a background desktop app with system tray icon",
    )
    args = parser.parse_args()

    if args.tray:
        from tray_app import NovaTrayApp
        app = NovaTrayApp()
        app.run()
    else:
        nova = Nova(keyboard_mode=args.keyboard)
        nova.run()


if __name__ == "__main__":
    main()
