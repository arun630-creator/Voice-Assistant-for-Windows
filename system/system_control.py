"""
Nova Voice Assistant — System Control
Shutdown, restart, lock, volume, and other OS‑level operations.
"""

import ctypes
import subprocess
from typing import Optional

from utils.helpers import is_command_blocked
from utils.logger import get_logger

log = get_logger(__name__)


class SystemControl:
    """Execute privileged Windows system commands safely."""

    # ── Power ─────────────────────────────────────────────────────────────

    @staticmethod
    def shutdown(delay_seconds: int = 30) -> str:
        """Schedule a system shutdown."""
        cmd = f"shutdown /s /t {delay_seconds}"
        if is_command_blocked(cmd):
            return "That command is not allowed."
        log.info("Scheduling shutdown in %d seconds", delay_seconds)
        try:
            subprocess.run(
                ["shutdown", "/s", "/t", str(delay_seconds)],
                check=True,
                timeout=10,
            )
            return f"Shutting down in {delay_seconds} seconds. Say 'shutdown /a' to cancel."
        except subprocess.CalledProcessError as exc:
            log.error("Shutdown command failed: %s", exc)
            return "Failed to initiate shutdown."
        except OSError as exc:
            log.error("OS error during shutdown: %s", exc)
            return "Failed to initiate shutdown."

    @staticmethod
    def restart(delay_seconds: int = 30) -> str:
        """Schedule a system restart."""
        cmd = f"shutdown /r /t {delay_seconds}"
        if is_command_blocked(cmd):
            return "That command is not allowed."
        log.info("Scheduling restart in %d seconds", delay_seconds)
        try:
            subprocess.run(
                ["shutdown", "/r", "/t", str(delay_seconds)],
                check=True,
                timeout=10,
            )
            return f"Restarting in {delay_seconds} seconds."
        except subprocess.CalledProcessError as exc:
            log.error("Restart command failed: %s", exc)
            return "Failed to initiate restart."
        except OSError as exc:
            log.error("OS error during restart: %s", exc)
            return "Failed to initiate restart."

    @staticmethod
    def lock_pc() -> str:
        """Lock the workstation immediately."""
        log.info("Locking workstation")
        try:
            ctypes.windll.user32.LockWorkStation()
            return "Locking your PC."
        except Exception as exc:
            log.error("Failed to lock PC: %s", exc)
            return "Failed to lock the PC."

    # ── Volume ────────────────────────────────────────────────────────────

    @staticmethod
    def set_volume(level: int) -> str:
        """
        Set the master volume to *level* (0–100) using pycaw
        (Python Core Audio Windows).
        """
        level = max(0, min(100, level))
        log.info("Setting volume to %d%%", level)

        try:
            from pycaw.pycaw import AudioUtilities

            speakers = AudioUtilities.GetSpeakers()
            volume = speakers.EndpointVolume
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"Volume set to {level} percent."
        except Exception as exc:
            log.error("pycaw volume control failed: %s", exc)

        # Fallback: nircmd (if installed)
        try:
            nircmd_level = int(65535 * level / 100)
            subprocess.run(
                ["nircmd", "setsysvolume", str(nircmd_level)],
                check=True,
                timeout=5,
            )
            return f"Volume set to {level} percent."
        except FileNotFoundError:
            log.warning("nircmd not found — cannot set volume via fallback")
        except (subprocess.CalledProcessError, OSError) as exc:
            log.error("nircmd volume set failed: %s", exc)

        return f"Could not set volume to {level} percent. Please try manually."
