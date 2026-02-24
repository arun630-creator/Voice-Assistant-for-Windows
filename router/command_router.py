"""
Nova Voice Assistant — Command Router (Enhanced)

Maps validated intents to the correct system module and returns a
natural-language response for TTS.

Supports 35+ intents across:
  - Information (time, date, greeting)
  - Messaging (WhatsApp, Telegram, email)
  - Media (YouTube, Spotify)
  - App control (open/close — desktop, UWP/Store, Chrome PWAs)
  - File management (create/delete/rename/open folders, list files, recycle bin)
  - System power (shutdown, restart, sleep, hibernate, lock, cancel)
  - Audio (volume, mute/unmute)
  - Display (brightness)
  - Network (Wi-Fi, Bluetooth, IP)
  - Battery, screenshot, clipboard
  - Timer
  - Web search, notes/memory
"""

from typing import Callable, Dict, Optional

import datetime
import random

from brain.intent_parser import Intent
from brain.memory import Memory
from brain.contacts import ContactBook
from system.app_control import AppControl
from system.system_control import SystemControl
from system.browser_control import BrowserControl
from system.file_manager import FileManager
from system import messaging
from utils.logger import get_logger

log = get_logger(__name__)


class CommandRouter:
    """
    Central dispatcher.

    Each supported intent string is mapped to a handler method.
    Handlers receive the :class:`Intent` and return a response string.
    """

    def __init__(self, memory: Memory, tts_callback: Optional[Callable] = None) -> None:
        self._memory = memory
        self._tts_callback = tts_callback  # for timer notifications
        self._app = AppControl()
        self._sys = SystemControl()
        self._browser = BrowserControl()
        self._contacts = ContactBook()
        self._files = FileManager()

        # Intent -> handler lookup
        self._handlers: Dict[str, Callable[[Intent], str]] = {
            # Informational
            "time": self._handle_time,
            "date": self._handle_date,
            "greeting": self._handle_greeting,
            # Compound / follow-up
            "send_message": self._handle_send_message,
            "send_email": self._handle_send_email,
            "play_media": self._handle_play_media,
            "open_url": self._handle_open_url,
            "add_contact": self._handle_add_contact,
            "list_contacts": self._handle_list_contacts,
            # App control
            "open_app": self._handle_open_app,
            "close_app": self._handle_close_app,
            # Power
            "shutdown": self._handle_shutdown,
            "restart": self._handle_restart,
            "cancel_shutdown": self._handle_cancel_shutdown,
            "lock_pc": self._handle_lock_pc,
            "sleep_pc": self._handle_sleep_pc,
            "hibernate_pc": self._handle_hibernate_pc,
            # Audio / display
            "set_volume": self._handle_set_volume,
            "mute": self._handle_mute,
            "unmute": self._handle_unmute,
            "set_brightness": self._handle_set_brightness,
            # Network
            "wifi_on": self._handle_wifi_on,
            "wifi_off": self._handle_wifi_off,
            "wifi_status": self._handle_wifi_status,
            "bluetooth_on": self._handle_bluetooth_on,
            "bluetooth_off": self._handle_bluetooth_off,
            # System info
            "battery_status": self._handle_battery_status,
            "ip_address": self._handle_ip_address,
            "screenshot": self._handle_screenshot,
            # Clipboard
            "read_clipboard": self._handle_read_clipboard,
            "clear_clipboard": self._handle_clear_clipboard,
            # Timer
            "set_timer": self._handle_set_timer,
            "cancel_timer": self._handle_cancel_timer,
            # File management
            "create_folder": self._handle_create_folder,
            "delete_folder": self._handle_delete_folder,
            "rename_folder": self._handle_rename_folder,
            "open_folder": self._handle_open_folder,
            "list_files": self._handle_list_files,
            "empty_recycle_bin": self._handle_empty_recycle_bin,
            # Web / search / notes
            "search_web": self._handle_search_web,
            "remember_note": self._handle_remember_note,
            "recall_note": self._handle_recall_note,
            # Fallback
            "unknown": self._handle_unknown,
        }

    # ── Public API ────────────────────────────────────────────────────────

    def route(self, intent: Intent) -> str:
        """
        Dispatch *intent* to the appropriate handler.
        Always returns a non-empty response string suitable for TTS.
        """
        handler = self._handlers.get(intent.intent, self._handle_unknown)
        log.info("Routing intent '%s' -> %s", intent.intent, handler.__name__)
        try:
            return handler(intent)
        except Exception:
            log.exception("Handler '%s' raised an exception", intent.intent)
            return "Sorry, something went wrong while processing your request."

    # ══════════════════════════════════════════════════════════════════════
    #  Informational
    # ══════════════════════════════════════════════════════════════════════

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

    # ══════════════════════════════════════════════════════════════════════
    #  Compound / follow-up
    # ══════════════════════════════════════════════════════════════════════

    def _handle_send_message(self, intent: Intent) -> str:
        contact_name = intent.parameters.get("contact", "")
        message = intent.parameters.get("message", "")
        app = intent.parameters.get("app", "whatsapp").lower()

        if not contact_name:
            return "I didn't catch who to send the message to."
        if not message:
            return "I didn't catch the message to send."

        contact = self._contacts.find(contact_name)

        if app in ("whatsapp", "signal", "sms"):
            phone = contact.get("phone", "") if contact else ""
            if not phone or phone.startswith("+91XXXX"):
                return (
                    f"I don't have a phone number for {contact_name}. "
                    f"Say: add contact {contact_name} phone <number>"
                )
            return messaging.send_whatsapp(phone, message)
        elif app == "telegram":
            phone = contact.get("phone", "") if contact else ""
            if not phone:
                return (
                    f"I don't have contact info for {contact_name}. "
                    f"Say: add contact {contact_name} phone <number>"
                )
            return messaging.send_telegram(phone, message)
        else:
            return f"I don't know how to send messages on {app} yet."

    def _handle_send_email(self, intent: Intent) -> str:
        recipient = intent.parameters.get("recipient", "")
        body = intent.parameters.get("body", "")
        subject = intent.parameters.get("subject", "")

        if not recipient:
            return "I didn't catch the email address."

        if "@" not in recipient:
            contact = self._contacts.find(recipient)
            if contact and contact.get("email"):
                recipient = contact["email"]
            else:
                return (
                    f"I don't have an email address for {recipient}. "
                    "Please provide the full email address."
                )
        return messaging.send_email(recipient, subject=subject, body=body)

    def _handle_play_media(self, intent: Intent) -> str:
        query = intent.parameters.get("query", "")
        platform = intent.parameters.get("platform", "youtube").lower()

        if not query:
            return "What should I play?"

        if platform == "youtube":
            return messaging.search_youtube(query)
        elif platform == "spotify":
            return messaging.play_spotify(query)
        else:
            return messaging.search_youtube(query)

    def _handle_open_url(self, intent: Intent) -> str:
        url = intent.parameters.get("url", "")
        if not url:
            return "I didn't catch the URL."
        return messaging.open_url(url)

    def _handle_add_contact(self, intent: Intent) -> str:
        name = intent.parameters.get("name", "")
        phone = intent.parameters.get("phone", "")
        email = intent.parameters.get("email", "")

        if not name:
            return "I didn't catch the contact name."
        if not phone and not email:
            return "Please provide a phone number or email for the contact."
        return self._contacts.add(name, phone=phone, email=email)

    def _handle_list_contacts(self, _intent: Intent) -> str:
        contacts = self._contacts.list_all()
        if not contacts:
            return "Your contact book is empty."

        lines = []
        for i, c in enumerate(contacts, 1):
            parts = [c["name"]]
            if c.get("phone"):
                parts.append(c["phone"])
            if c.get("email"):
                parts.append(c["email"])
            lines.append(f"{i}. {', '.join(parts)}")
        summary = ". ".join(lines)
        return f"You have {len(contacts)} contact(s): {summary}"

    # ══════════════════════════════════════════════════════════════════════
    #  App control
    # ══════════════════════════════════════════════════════════════════════

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

    # ══════════════════════════════════════════════════════════════════════
    #  Power management
    # ══════════════════════════════════════════════════════════════════════

    def _handle_shutdown(self, _intent: Intent) -> str:
        return self._sys.shutdown()

    def _handle_restart(self, _intent: Intent) -> str:
        return self._sys.restart()

    def _handle_cancel_shutdown(self, _intent: Intent) -> str:
        return self._sys.cancel_shutdown()

    def _handle_lock_pc(self, _intent: Intent) -> str:
        return self._sys.lock_pc()

    def _handle_sleep_pc(self, _intent: Intent) -> str:
        return self._sys.sleep_pc()

    def _handle_hibernate_pc(self, _intent: Intent) -> str:
        return self._sys.hibernate_pc()

    # ══════════════════════════════════════════════════════════════════════
    #  Audio / Display
    # ══════════════════════════════════════════════════════════════════════

    def _handle_set_volume(self, intent: Intent) -> str:
        level = intent.parameters.get("level")
        if level is None:
            return "I didn't catch the volume level."
        try:
            level = int(level)
        except (ValueError, TypeError):
            return "I couldn't understand the volume level."
        return self._sys.set_volume(level)

    def _handle_mute(self, _intent: Intent) -> str:
        return self._sys.mute()

    def _handle_unmute(self, _intent: Intent) -> str:
        return self._sys.unmute()

    def _handle_set_brightness(self, intent: Intent) -> str:
        level = intent.parameters.get("level")
        if level is None:
            return "I didn't catch the brightness level."
        try:
            level = int(level)
        except (ValueError, TypeError):
            return "I couldn't understand the brightness level."
        return self._sys.set_brightness(level)

    # ══════════════════════════════════════════════════════════════════════
    #  Network
    # ══════════════════════════════════════════════════════════════════════

    def _handle_wifi_on(self, _intent: Intent) -> str:
        return self._sys.wifi_on()

    def _handle_wifi_off(self, _intent: Intent) -> str:
        return self._sys.wifi_off()

    def _handle_wifi_status(self, _intent: Intent) -> str:
        return self._sys.wifi_status()

    def _handle_bluetooth_on(self, _intent: Intent) -> str:
        return self._sys.bluetooth_on()

    def _handle_bluetooth_off(self, _intent: Intent) -> str:
        return self._sys.bluetooth_off()

    # ══════════════════════════════════════════════════════════════════════
    #  System info
    # ══════════════════════════════════════════════════════════════════════

    def _handle_battery_status(self, _intent: Intent) -> str:
        return self._sys.battery_status()

    def _handle_ip_address(self, _intent: Intent) -> str:
        return self._sys.get_ip_address()

    def _handle_screenshot(self, _intent: Intent) -> str:
        return self._sys.take_screenshot()

    # ══════════════════════════════════════════════════════════════════════
    #  Clipboard
    # ══════════════════════════════════════════════════════════════════════

    def _handle_read_clipboard(self, _intent: Intent) -> str:
        return self._sys.read_clipboard()

    def _handle_clear_clipboard(self, _intent: Intent) -> str:
        return self._sys.clear_clipboard()

    # ══════════════════════════════════════════════════════════════════════
    #  Timer
    # ══════════════════════════════════════════════════════════════════════

    def _handle_set_timer(self, intent: Intent) -> str:
        total = intent.parameters.get("total_seconds", 0)
        if not total:
            # Try individual params
            hours = int(intent.parameters.get("hours", 0) or 0)
            minutes = int(intent.parameters.get("minutes", 0) or 0)
            seconds = int(intent.parameters.get("seconds", 0) or 0)
            total = hours * 3600 + minutes * 60 + seconds
        if total <= 0:
            return "I didn't catch the timer duration. Say something like: set timer for 5 minutes."
        return self._sys.set_timer(total, tts_callback=self._tts_callback)

    def _handle_cancel_timer(self, _intent: Intent) -> str:
        return self._sys.cancel_timer()

    # ══════════════════════════════════════════════════════════════════════
    #  File management
    # ══════════════════════════════════════════════════════════════════════

    def _handle_create_folder(self, intent: Intent) -> str:
        folder = intent.parameters.get("folder", "")
        location = intent.parameters.get("location", "desktop")
        if not folder:
            return "I didn't catch the folder name."
        return self._files.create_folder(folder, location=location)

    def _handle_delete_folder(self, intent: Intent) -> str:
        folder = intent.parameters.get("folder", "")
        if not folder:
            return "I didn't catch which folder to delete."
        return self._files.delete_folder(folder)

    def _handle_rename_folder(self, intent: Intent) -> str:
        old_name = intent.parameters.get("old_name", "")
        new_name = intent.parameters.get("new_name", "")
        if not old_name or not new_name:
            return "I need both the current and new folder names."
        return self._files.rename_folder(old_name, new_name)

    def _handle_open_folder(self, intent: Intent) -> str:
        folder = intent.parameters.get("folder", "")
        if not folder:
            return "I didn't catch which folder to open."
        return self._files.open_folder(folder)

    def _handle_list_files(self, intent: Intent) -> str:
        folder = intent.parameters.get("folder", "desktop")
        return self._files.list_files(folder)

    def _handle_empty_recycle_bin(self, _intent: Intent) -> str:
        return self._files.empty_recycle_bin()

    # ══════════════════════════════════════════════════════════════════════
    #  Web search / Notes
    # ══════════════════════════════════════════════════════════════════════

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
        log.info("Unknown intent - raw text: %s", raw)
        return "I'm not sure how to handle that. Could you try rephrasing?"
