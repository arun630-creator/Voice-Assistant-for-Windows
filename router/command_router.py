"""
Nova Voice Assistant — Command Router
Maps validated intents to the correct system module and returns a
natural‑language response for TTS.
"""

from typing import Callable, Dict

import datetime
import random

from brain.intent_parser import Intent
from brain.memory import Memory
from system.app_control import AppControl
from system.system_control import SystemControl
from system.browser_control import BrowserControl
from utils.logger import get_logger

log = get_logger(__name__)


class CommandRouter:
    """
    Central dispatcher.

    Each supported intent string is mapped to a handler method.
    Handlers receive the :class:`Intent` and return a response string.
    """

    def __init__(self, memory: Memory) -> None:
        self._memory = memory
        self._app = AppControl()
        self._sys = SystemControl()
        self._browser = BrowserControl()

        # Intent → handler lookup
        self._handlers: Dict[str, Callable[[Intent], str]] = {
            "time": self._handle_time,
            "date": self._handle_date,
            "greeting": self._handle_greeting,
            "open_app": self._handle_open_app,
            "close_app": self._handle_close_app,
            "set_volume": self._handle_set_volume,
            "shutdown": self._handle_shutdown,
            "restart": self._handle_restart,
            "lock_pc": self._handle_lock_pc,
            "search_web": self._handle_search_web,
            "remember_note": self._handle_remember_note,
            "recall_note": self._handle_recall_note,
            "unknown": self._handle_unknown,
        }

    # ── Public API ────────────────────────────────────────────────────────

    def route(self, intent: Intent) -> str:
        """
        Dispatch *intent* to the appropriate handler.

        Always returns a non‑empty response string suitable for TTS.
        """
        handler = self._handlers.get(intent.intent, self._handle_unknown)
        log.info("Routing intent '%s' → %s", intent.intent, handler.__name__)
        try:
            return handler(intent)
        except Exception:
            log.exception("Handler '%s' raised an exception", intent.intent)
            return "Sorry, something went wrong while processing your request."

    # ── Handlers ──────────────────────────────────────────────────────────
    @staticmethod
    def _handle_time(_intent: Intent) -> str:
        now = datetime.datetime.now()
        return f"It's currently {now.strftime('%I:%M %p')}."

    @staticmethod
    def _handle_date(_intent: Intent) -> str:
        today = datetime.date.today()
        return f"Today is {today.strftime('%A, %B %d, %Y')}."

    @staticmethod
    def _handle_greeting(_intent: Intent) -> str:
        replies = [
            "Hey there! How can I help you?",
            "Hello! What can I do for you?",
            "Hi! I'm ready to help.",
            "Hey! What do you need?",
        ]
        return random.choice(replies)
    def _handle_open_app(self, intent: Intent) -> str:
        app_name = intent.parameters.get("app_name", "")
        if not app_name:
            return "I didn't catch which app to open."
        return self._app.open_app(app_name)

    def _handle_close_app(self, intent: Intent) -> str:
        app_name = intent.parameters.get("app_name", "")
        if not app_name:
            return "I didn't catch which app to close."
        return self._app.close_app(app_name)

    def _handle_set_volume(self, intent: Intent) -> str:
        level = intent.parameters.get("level")
        if level is None:
            return "I didn't catch the volume level."
        try:
            level = int(level)
        except (ValueError, TypeError):
            return "I couldn't understand the volume level."
        return self._sys.set_volume(level)

    def _handle_shutdown(self, _intent: Intent) -> str:
        return self._sys.shutdown()

    def _handle_restart(self, _intent: Intent) -> str:
        return self._sys.restart()

    def _handle_lock_pc(self, _intent: Intent) -> str:
        return self._sys.lock_pc()

    def _handle_search_web(self, intent: Intent) -> str:
        query = intent.parameters.get("query", "")
        if not query:
            return "What should I search for?"
        return self._browser.search_web(query)

    def _handle_remember_note(self, intent: Intent) -> str:
        note = intent.parameters.get("note", "")
        if not note:
            return "I didn't catch what to remember."
        success = self._memory.save_note(note)
        if success:
            return f"Got it. I'll remember that: {note}"
        return "Sorry, I couldn't save that note."

    def _handle_recall_note(self, _intent: Intent) -> str:
        notes = self._memory.recall_notes(limit=5)
        if not notes:
            return "I don't have any saved notes."
        lines = [f"{i + 1}. {content}" for i, (content, _ts) in enumerate(notes)]
        summary = ". ".join(lines)
        return f"Here's what I remember: {summary}"

    def _handle_unknown(self, intent: Intent) -> str:
        raw = intent.parameters.get("raw", intent.raw_text)
        log.info("Unknown intent — raw text: %s", raw)
        return "I'm not sure how to handle that. Could you try rephrasing?"
