"""
Nova Voice Assistant — Application Control (Enhanced)

Launch and close Windows applications with comprehensive support:
  1. Traditional .exe apps (via whitelist + fuzzy matching)
  2. Microsoft Store / UWP apps (via Get-StartApps dynamic discovery)
  3. Chrome PWA shortcuts and Start Menu .lnk shortcuts
  4. URI protocol schemes (ms-settings:, ms-photos:, etc.)

Matching strategy (in order):
  1. Exact match against APP_WHITELIST keys
  2. Squeezed exact — "fileexplorer" → "file explorer"
  3. Prefix/starts-with — "file" → "file explorer"
  4. Fuzzy match — SequenceMatcher ≥ 60%
  5. Dynamic Start Menu search via Get-StartApps (catches UWP/Store apps)
  6. Last-resort — ask Windows ``start`` to resolve the name directly

Security:
  - Only whitelisted executables or discovered Start-Menu apps are launched
  - No arbitrary shell commands
  - taskkill only for known executables
"""

import difflib
import os
import re
import subprocess
import json
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from config import APP_WHITELIST
from utils.helpers import normalise_app_name, is_command_blocked
from utils.logger import get_logger

log = get_logger(__name__)

# Minimum similarity ratio for fuzzy matching (0–1)
_FUZZY_THRESHOLD = 0.60

# Cache duration for Start Menu apps (refreshed on each app session)
_start_apps_cache: Optional[Dict[str, str]] = None


# ══════════════════════════════════════════════════════════════════════════════
#  Start Menu / UWP Discovery
# ══════════════════════════════════════════════════════════════════════════════

def _get_start_apps() -> Dict[str, str]:
    """
    Discover all apps visible in the Windows Start Menu using
    ``Get-StartApps``.  Returns {lowercase_name: AppID}.

    This catches:
      - UWP / Microsoft Store apps (WhatsApp, Calculator, etc.)
      - Classic desktop apps with Start Menu shortcuts
      - Chrome PWAs with Start Menu entries
    """
    global _start_apps_cache
    if _start_apps_cache is not None:
        return _start_apps_cache

    log.info("Discovering Start Menu apps via Get-StartApps …")
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json"
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            raw = json.loads(result.stdout)
            # PowerShell returns a list of {Name, AppID} objects
            if isinstance(raw, dict):
                raw = [raw]
            apps = {}
            for entry in raw:
                name = entry.get("Name", "").strip()
                app_id = entry.get("AppID", "").strip()
                if name and app_id:
                    apps[name.lower()] = app_id
            _start_apps_cache = apps
            log.info("Discovered %d Start Menu apps", len(apps))
            return apps
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as exc:
        log.warning("Get-StartApps failed: %s", exc)

    _start_apps_cache = {}
    return _start_apps_cache


def _find_start_app(query: str) -> Optional[Tuple[str, str]]:
    """
    Search Start Menu apps for *query*.  Returns (display_name, AppID)
    or None.  Uses exact → prefix → fuzzy matching like the whitelist.
    """
    apps = _get_start_apps()
    normalised = query.lower().strip()

    # 1. Exact match
    if normalised in apps:
        return normalised, apps[normalised]

    # 2. Prefix / starts-with
    for name, app_id in apps.items():
        if name.startswith(normalised) or normalised.startswith(name):
            return name, app_id

    # 3. Fuzzy match
    best_score = 0.0
    best_name: Optional[str] = None
    for name in apps:
        score = difflib.SequenceMatcher(None, normalised, name).ratio()
        if score > best_score:
            best_score = score
            best_name = name

    if best_name and best_score >= _FUZZY_THRESHOLD:
        return best_name, apps[best_name]

    return None


# ══════════════════════════════════════════════════════════════════════════════
#  Whitelist Resolution
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_app(raw_name: str) -> Tuple[Optional[str], str]:
    """
    Resolve a user-supplied app name to an executable or launch command.

    Returns ``(executable_or_None, friendly_name_used)``.
    """
    normalised = normalise_app_name(raw_name)
    squeezed = re.sub(r"\s+", "", normalised)

    # ── 1. Exact match ────────────────────────────────────────────────────
    if normalised in APP_WHITELIST:
        return APP_WHITELIST[normalised], normalised

    # ── 2. Squeezed exact — "fileexplorer" → "file explorer" ─────────────
    for key, exe in APP_WHITELIST.items():
        if re.sub(r"\s+", "", key) == squeezed:
            log.info("Squeezed match: '%s' → '%s' (%s)", raw_name, key, exe)
            return exe, key

    # ── 3. Substring / starts-with — "file" → "file explorer" ────────────
    for key, exe in APP_WHITELIST.items():
        if key.startswith(normalised) or normalised.startswith(key):
            log.info("Prefix match: '%s' → '%s' (%s)", raw_name, key, exe)
            return exe, key

    # ── 4. Fuzzy match — best candidate by similarity ─────────────────────
    candidates = list(APP_WHITELIST.keys())
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

    log.debug(
        "No whitelist match for '%s' (best=%.2f '%s')",
        raw_name, best_score, best_key,
    )
    return None, normalised


def _launch_executable(executable: str, matched_name: str) -> str:
    """Launch an executable via ``cmd /c start``."""
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


def _launch_start_app(display_name: str, app_id: str) -> str:
    """Launch an app by its Start Menu AppID."""
    log.info("Opening Start Menu app: %s → %s", display_name, app_id)
    try:
        subprocess.Popen(
            ["explorer.exe", f"shell:AppsFolder\\{app_id}"],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Opening {display_name}."
    except OSError as exc:
        log.error("Failed to launch Start app '%s': %s", display_name, exc)
        return f"Failed to open {display_name}."


# ══════════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════════

class AppControl:
    """Launch or terminate desktop/UWP applications by friendly name."""

    @staticmethod
    def open_app(app_name: str) -> str:
        """
        Open an application by its friendly name.

        Resolution order:
          1. Static whitelist (exact → squeezed → prefix → fuzzy)
          2. Dynamic Start Menu discovery (UWP/Store apps + Chrome PWAs)
          3. Windows ``start`` fallback
        """
        executable, matched_name = _resolve_app(app_name)

        # Whitelist match found → launch it
        if executable is not None:
            return _launch_executable(executable, matched_name)

        # ── Try Start Menu discovery (catches UWP/Store apps) ─────────────
        start_match = _find_start_app(app_name)
        if start_match:
            display_name, app_id = start_match
            return _launch_start_app(display_name, app_id)

        # ── Last-resort: let Windows resolve the name directly ────────────
        # Only allow safe alphanumeric names (no shell metacharacters)
        import re as _re
        if _re.fullmatch(r"[\w\s.+\-]+", app_name):
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
        else:
            log.warning("Blocked unsafe app_name for 'start' fallback: %s", app_name)
        return f"Sorry, I couldn't open {app_name}."

    @staticmethod
    def close_app(app_name: str) -> str:
        """
        Close an application by its friendly name via ``taskkill``.
        Works for traditional .exe apps.  UWP apps are closed via
        their process name if discoverable.
        """
        executable, matched_name = _resolve_app(app_name)

        if executable is None:
            # For UWP apps, try finding the process by name
            normalised = app_name.lower().strip()
            # Common UWP process names
            _uwp_processes = {
                "whatsapp": "WhatsApp.exe",
                "calculator": "CalculatorApp.exe",
                "clock": "Time.exe",
                "camera": "WindowsCamera.exe",
                "photos": "Microsoft.Photos.exe",
                "weather": "Microsoft.Msn.Weather.exe",
                "mail": "HxOutlook.exe",
                "calendar": "HxCalendarAppImm.exe",
                "store": "WinStore.App.exe",
                "notepad": "Notepad.exe",
                "paint": "mspaint.exe",
                "snipping tool": "ScreenClippingHost.exe",
            }
            exe = _uwp_processes.get(normalised)
            if exe:
                executable = exe
                matched_name = normalised
            else:
                log.warning("App '%s' not in whitelist — cannot close", app_name)
                return f"Sorry, I don't know how to close {app_name}."

        # Skip URI protocol entries (can't taskkill a protocol)
        if executable.endswith(":"):
            return f"Sorry, I can't close {matched_name} directly. Please close it manually."

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
                msg = result.stderr.strip() or result.stdout.strip()
                log.warning("taskkill returned %d: %s", result.returncode, msg)
                return f"{matched_name} doesn't seem to be running."
        except subprocess.TimeoutExpired:
            return f"Timed out trying to close {matched_name}."
        except OSError as exc:
            log.error("OS error closing %s: %s", matched_name, exc)
            return f"Failed to close {matched_name}."

    @staticmethod
    def list_running_apps() -> str:
        """List notable running applications (for user info)."""
        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return "Couldn't retrieve running apps."

            # Build reverse lookup: exe → friendly name
            reverse: Dict[str, str] = {}
            for name, exe in APP_WHITELIST.items():
                if exe not in reverse and not exe.endswith(":"):
                    reverse[exe.lower()] = name

            running = set()
            for line in result.stdout.strip().split("\n"):
                parts = line.strip().strip('"').split('","')
                if parts:
                    exe_name = parts[0].strip('"').lower()
                    if exe_name in reverse:
                        running.add(reverse[exe_name])

            if not running:
                return "No notable apps are currently running."
            return "Running apps: " + ", ".join(sorted(running))
        except Exception as exc:
            log.error("list_running_apps failed: %s", exc)
            return "Couldn't retrieve running apps."
