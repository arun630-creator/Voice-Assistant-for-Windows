"""
Nova Voice Assistant — Main Entry Point
Orchestrates wake‑word detection → STT → LLM → routing → TTS in a
threaded, non‑blocking pipeline with graceful shutdown.

Usage:
    python main.py              # voice mode (microphone)
    python main.py --keyboard   # type commands instead of speaking
"""

import argparse
import json
import os
import sys
import signal
import threading
import time
from typing import Optional

# Ensure the package root is on sys.path so relative imports work
# when running ``python main.py`` from the assistant/ directory.
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Prevent hf_xet download failures on some Windows setups
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

from config import WAKE_WORD
from utils.logger import setup_logging, get_logger
from audio.text_to_speech import TextToSpeech
from brain.llm_interface import LLMInterface
from brain.intent_parser import IntentParser
from brain.fallback_classifier import fallback_classify
from brain.memory import Memory
from router.command_router import CommandRouter

log = get_logger("nova.main")


class Nova:
    """
    Top‑level application object.

    Lifecycle:
        nova = Nova()
        nova.run()                  # voice mode (default)
        nova.run_keyboard()         # keyboard / typing mode
    """

    def __init__(self, keyboard_mode: bool = False) -> None:
        setup_logging()
        self._keyboard_mode = keyboard_mode
        log.info("=" * 60)
        log.info("  Nova Voice Assistant — Initialising …")
        log.info("  Mode: %s", "KEYBOARD" if keyboard_mode else "VOICE")
        log.info("=" * 60)

        # ── Components ────────────────────────────────────────────────────
        self._tts = TextToSpeech()
        self._llm = LLMInterface()
        self._parser = IntentParser()
        self._memory = Memory()
        self._router = CommandRouter(self._memory)

        # Voice‑only components (lazy init)
        self._stt = None
        self._detector = None

        if not keyboard_mode:
            from audio.speech_to_text import SpeechToText
            from audio.wake_word import WakeWordDetector
            self._stt = SpeechToText()
            # ── Threading primitives ──────────────────────────────────────
            self._wake_event = threading.Event()
            self._detector = WakeWordDetector(callback=self._on_wake)
        else:
            self._wake_event = threading.Event()

        self._shutdown_event = threading.Event()
        log.info("All components initialised")

    # ── Signal handling ───────────────────────────────────────────────────

    def _setup_signals(self) -> None:
        """Register Ctrl‑C / SIGINT for graceful shutdown."""

        def _handler(sig: int, _frame) -> None:  # type: ignore[override]
            log.info("Received signal %d — shutting down …", sig)
            self._shutdown_event.set()
            self._wake_event.set()  # unblock main loop if waiting

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)

    # ── Wake‑word callback ────────────────────────────────────────────────

    def _on_wake(self) -> None:
        """Called from the wake‑word thread when the keyword is heard."""
        log.debug("_on_wake triggered")
        self._wake_event.set()

    # ── Intent classification (shared) ────────────────────────────────────

    def _classify(self, text: str) -> str:
        """Classify user text via LLM or fallback, return router response."""
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

        # 1. Audible acknowledgement
        self._tts.speak("Yes?")

        # 2. Record & transcribe
        text = self._stt.listen_and_transcribe()
        if not text:
            self._tts.speak("Sorry, I didn't catch that.")
            return

        log.info("User said: '%s'", text)

        # 3‑6. Classify → route → speak
        response = self._classify(text)
        self._tts.speak(response)

    # ── Run loops ─────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start in the configured mode."""
        if self._keyboard_mode:
            self._run_keyboard()
        else:
            self._run_voice()

    def _run_voice(self) -> None:
        """Voice mode — microphone wake word + STT."""
        self._setup_signals()
        self._detector.start()
        self._tts.speak(f"Nova is ready. Say {WAKE_WORD} to begin.")
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
        """Keyboard mode — type commands instead of speaking."""
        self._setup_signals()
        print()
        print("=" * 60)
        print("  Nova Voice Assistant — KEYBOARD MODE")
        print("  Type your commands below. Type 'quit' or 'exit' to stop.")
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
                import re
                cleaned = re.sub(
                    r"^(?:hey\s+)?nova[\s,]*",
                    "",
                    user_input,
                    flags=re.IGNORECASE,
                ).strip()
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
        """Release all resources."""
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
    args = parser.parse_args()
    nova = Nova(keyboard_mode=args.keyboard)
    nova.run()


if __name__ == "__main__":
    main()
