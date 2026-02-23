"""
Nova Voice Assistant — Messaging & Media Automation
Handles follow-up actions: WhatsApp messages, email, YouTube, Spotify, etc.

Strategy:
  1. Use URL schemes to pre-fill / open the correct app view.
  2. Optionally auto-send via ``pyautogui`` key-press after a delay.
  3. Gracefully degrade if pyautogui is unavailable (user sends manually).
"""

import threading
import time
import urllib.parse
import webbrowser
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)

# ── Optional pyautogui (for auto-send) ────────────────────────────────────────
try:
    import pyautogui

    pyautogui.FAILSAFE = True       # move mouse to corner to abort
    pyautogui.PAUSE = 0.15
    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False
    log.warning("pyautogui not installed — auto-send disabled. Install with: pip install pyautogui")


def _delayed_keypress(key: str = "enter", delay: float = 5.0) -> None:
    """Press *key* after *delay* seconds in a background thread."""
    if not _HAS_PYAUTOGUI:
        return

    def _worker():
        time.sleep(delay)
        try:
            pyautogui.press(key)
            log.info("Auto-pressed '%s' after %.1fs", key, delay)
        except Exception as exc:
            log.warning("pyautogui keypress failed: %s", exc)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


# ═══════════════════════════════════════════════════════════════════════════════
#  WhatsApp
# ═══════════════════════════════════════════════════════════════════════════════

def send_whatsapp(phone: str, message: str, auto_send: bool = True) -> str:
    """
    Open WhatsApp with a pre-filled message for *phone*.

    Uses the ``https://wa.me/`` URL scheme which works with both
    WhatsApp Desktop and WhatsApp Web.  If *auto_send* is True and
    pyautogui is available, it will press Enter after a delay.
    """
    if not phone or phone.startswith("+91XXXX"):
        return (
            "I don't have a valid phone number for that contact. "
            "Please update it with: add contact <name> phone <number>"
        )

    # Normalise phone: remove spaces, dashes, ensure + prefix
    clean_phone = phone.replace(" ", "").replace("-", "")
    if not clean_phone.startswith("+"):
        clean_phone = "+" + clean_phone

    encoded_msg = urllib.parse.quote(message)
    url = f"https://wa.me/{clean_phone[1:]}?text={encoded_msg}"

    log.info("WhatsApp URL: %s", url)
    try:
        webbrowser.open(url)
    except Exception as exc:
        log.error("Failed to open WhatsApp URL: %s", exc)
        return "Sorry, I couldn't open WhatsApp."

    if auto_send and _HAS_PYAUTOGUI:
        _delayed_keypress("enter", delay=6.0)
        return f"Sending \"{message}\" on WhatsApp. It will auto-send in a few seconds."
    else:
        return f"WhatsApp is open with the message ready. Just press Enter to send."


# ═══════════════════════════════════════════════════════════════════════════════
#  Telegram
# ═══════════════════════════════════════════════════════════════════════════════

def send_telegram(username_or_phone: str, message: str) -> str:
    """Open Telegram with a pre-filled message."""
    encoded_msg = urllib.parse.quote(message)
    # tg://resolve works for usernames; for phone we use the web link
    if username_or_phone.startswith("@"):
        user = username_or_phone.lstrip("@")
        url = f"https://t.me/{user}?text={encoded_msg}"
    else:
        url = f"https://t.me/{username_or_phone}?text={encoded_msg}"

    log.info("Telegram URL: %s", url)
    try:
        webbrowser.open(url)
        return f"Telegram is open with the message ready."
    except Exception as exc:
        log.error("Failed to open Telegram URL: %s", exc)
        return "Sorry, I couldn't open Telegram."


# ═══════════════════════════════════════════════════════════════════════════════
#  Email
# ═══════════════════════════════════════════════════════════════════════════════

def send_email(recipient: str, subject: str = "", body: str = "") -> str:
    """Open the default email client with a pre-filled compose window."""
    params = {}
    if subject:
        params["subject"] = subject
    if body:
        params["body"] = body

    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"mailto:{recipient}?{query}" if query else f"mailto:{recipient}"

    log.info("Email URL: %s", url)
    try:
        webbrowser.open(url)
        return f"Opening email to {recipient}."
    except Exception as exc:
        log.error("Failed to open email: %s", exc)
        return "Sorry, I couldn't open the email client."


# ═══════════════════════════════════════════════════════════════════════════════
#  YouTube
# ═══════════════════════════════════════════════════════════════════════════════

def search_youtube(query: str) -> str:
    """Open YouTube search results for *query*."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    log.info("YouTube URL: %s", url)
    try:
        webbrowser.open(url)
        return f"Searching YouTube for {query}."
    except Exception as exc:
        log.error("Failed to open YouTube: %s", exc)
        return "Sorry, I couldn't open YouTube."


def play_youtube(query: str) -> str:
    """Open YouTube search and auto-click first video (best effort)."""
    result = search_youtube(query)
    if _HAS_PYAUTOGUI:
        # After page loads, Tab to first video and press Enter
        def _auto_play():
            time.sleep(5)
            try:
                pyautogui.press("tab", presses=6, interval=0.15)
                pyautogui.press("enter")
                log.info("Auto-played first YouTube result")
            except Exception:
                pass

        threading.Thread(target=_auto_play, daemon=True).start()
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Spotify
# ═══════════════════════════════════════════════════════════════════════════════

def play_spotify(query: str) -> str:
    """Open Spotify search for *query*."""
    encoded = urllib.parse.quote(query)
    # spotify: URI for desktop app, fallback to web
    url = f"https://open.spotify.com/search/{encoded}"
    log.info("Spotify URL: %s", url)
    try:
        webbrowser.open(url)
        return f"Searching Spotify for {query}."
    except Exception as exc:
        log.error("Failed to open Spotify: %s", exc)
        return "Sorry, I couldn't open Spotify."


# ═══════════════════════════════════════════════════════════════════════════════
#  Generic URL
# ═══════════════════════════════════════════════════════════════════════════════

def open_url(url: str) -> str:
    """Open an arbitrary URL in the default browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    log.info("Opening URL: %s", url)
    try:
        webbrowser.open(url)
        return f"Opening {url}."
    except Exception as exc:
        log.error("Failed to open URL: %s", exc)
        return f"Sorry, I couldn't open {url}."
