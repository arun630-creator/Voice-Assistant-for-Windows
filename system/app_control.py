"""
Nova Voice Assistant — Application Control
Open and close Windows applications with Siri‑like smart matching.

Matching strategy (in order):
  1. Exact match against APP_WHITELIST keys
  2. Fuzzy match — best whitelist key by similarity (≥ 60 %)
  3. "Starts‑with" pass — e.g. "file" → "file explorer"
  4. Last‑resort — ask Windows ``start`` to resolve the name directly
"""

import difflib
import re
import subprocess
from typing import Optional, Tuple

from config import APP_WHITELIST
from utils.helpers import normalise_app_name, is_command_blocked
from utils.logger import get_logger

log = get_logger(__name__)

# Minimum similarity ratio for fuzzy matching (0–1)
_FUZZY_THRESHOLD = 0.60


def _resolve_app(raw_name: str) -> Tuple[Optional[str], str]:
    """
    Resolve a user‑supplied app name to an executable.

    Returns ``(executable_or_None, friendly_name_used)``.
    """
    normalised = normalise_app_name(raw_name)           # "fileexplorer" → "fileexplorer"
    squeezed   = re.sub(r"\s+", "", normalised)         # "file explorer" → "fileexplorer"

    # ── 1. Exact match ────────────────────────────────────────────────────
    if normalised in APP_WHITELIST:
        return APP_WHITELIST[normalised], normalised

    # ── 2. Squeezed exact — handles "fileexplorer" → "file explorer" ────
    for key, exe in APP_WHITELIST.items():
        if re.sub(r"\s+", "", key) == squeezed:
            log.info("Squeezed match: '%s' → '%s' (%s)", raw_name, key, exe)
            return exe, key

    # ── 3. Substring / starts‑with — "file" → "file explorer" ────────────
    for key, exe in APP_WHITELIST.items():
        if key.startswith(normalised) or normalised.startswith(key):
            log.info("Prefix match: '%s' → '%s' (%s)", raw_name, key, exe)
            return exe, key

    # ── 4. Fuzzy match — best candidate by similarity ─────────────────────
    candidates = list(APP_WHITELIST.keys())
    # Compare against both the spaced normalised form *and* the squeezed
    # form so "fikeexplorer" still matches "fileexplorer" → "file explorer".
    best_score = 0.0
    best_key: Optional[str] = None

    for key in candidates:
        key_squeezed = re.sub(r"\s+", "", key)
        score = max(
            difflib.SequenceMatcher(None, normalised, key).ratio(),
            difflib.SequenceMatcher(None, squeezed, key_squeezed).ratio(),
        )
        if score > best_score:
            best_score = score
            best_key = key

    if best_key and best_score >= _FUZZY_THRESHOLD:
        exe = APP_WHITELIST[best_key]
        log.info(
            "Fuzzy match: '%s' → '%s' (%s) [score=%.2f]",
            raw_name, best_key, exe, best_score,
        )
        return exe, best_key

    log.debug("No whitelist match for '%s' (best=%.2f '%s')", raw_name, best_score, best_key)
    return None, normalised


class AppControl:
    """Launch or terminate desktop applications by friendly name."""

    # ── Public API ────────────────────────────────────────────────────────

    @staticmethod
    def open_app(app_name: str) -> str:
        """
        Open an application by its friendly name.

        Uses smart matching (exact → squeezed → prefix → fuzzy → Windows start)
        so the user doesn't need to type the exact whitelist key.
        """
        executable, matched_name = _resolve_app(app_name)

        # ── Last‑resort: let Windows resolve the name directly ────────────
        if executable is None:
            log.info("Trying Windows 'start' fallback for '%s'", app_name)
            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", "", app_name],
                    shell=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return f"Trying to open {app_name}."
            except OSError as exc:
                log.error("Windows start fallback failed: %s", exc)
                return f"Sorry, I couldn't open {app_name}."

        log.info("Opening app: %s → %s", matched_name, executable)
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", executable],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Opening {matched_name}."
        except FileNotFoundError:
            log.error("Executable not found: %s", executable)
            return f"Could not find {matched_name} on this system."
        except OSError as exc:
            log.error("OS error opening %s: %s", executable, exc)
            return f"Failed to open {matched_name}."

    @staticmethod
    def close_app(app_name: str) -> str:
        """
        Close an application by its friendly name via ``taskkill``.
        """
        executable, matched_name = _resolve_app(app_name)

        if executable is None:
            log.warning("App '%s' not in whitelist — cannot close", app_name)
            return f"Sorry, I don't know how to close {app_name}."

        command = f"taskkill /IM {executable} /F"
        if is_command_blocked(command):
            return "That command is not allowed."

        log.info("Closing app: %s → taskkill /IM %s /F", matched_name, executable)
        try:
            result = subprocess.run(
                ["taskkill", "/IM", executable, "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return f"Closed {matched_name}."
            else:
                log.warning("taskkill stderr: %s", result.stderr.strip())
                return f"{matched_name} may not be running."
        except subprocess.TimeoutExpired:
            log.error("taskkill timed out for %s", executable)
            return f"Timed out trying to close {matched_name}."
        except OSError as exc:
            log.error("OS error closing %s: %s", executable, exc)
            return f"Failed to close {matched_name}."
