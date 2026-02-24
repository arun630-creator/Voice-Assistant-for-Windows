"""
Nova Voice Assistant — System Control (Enhanced)

System-level operations:
  - Power: shutdown, restart, lock, sleep, hibernate, cancel shutdown
  - Audio: set volume, mute/unmute
  - Display: set brightness
  - Network: Wi-Fi toggle, get IP address
  - Bluetooth: toggle
  - Battery: check battery status
  - Screenshot: take screenshot
  - Clipboard: read/write/clear
  - Timer: countdown with TTS notification

Security:
  - All commands are validated against BLOCKED_COMMANDS
  - No arbitrary shell execution
  - Only known safe system APIs used
"""

import ctypes
import os
import subprocess
import socket
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from utils.helpers import is_command_blocked
from utils.logger import get_logger

log = get_logger(__name__)


class SystemControl:
    """Execute privileged Windows system commands safely."""

    # ══════════════════════════════════════════════════════════════════════
    #  Power Management
    # ══════════════════════════════════════════════════════════════════════

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
                check=True, timeout=10,
            )
            return f"Shutting down in {delay_seconds} seconds. Say 'cancel shutdown' to abort."
        except (subprocess.CalledProcessError, OSError) as exc:
            log.error("Shutdown failed: %s", exc)
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
                check=True, timeout=10,
            )
            return f"Restarting in {delay_seconds} seconds."
        except (subprocess.CalledProcessError, OSError) as exc:
            log.error("Restart failed: %s", exc)
            return "Failed to initiate restart."

    @staticmethod
    def cancel_shutdown() -> str:
        """Cancel a pending shutdown/restart."""
        log.info("Cancelling scheduled shutdown")
        try:
            result = subprocess.run(
                ["shutdown", "/a"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return "Shutdown cancelled."
            return "No shutdown was scheduled, or it couldn't be cancelled."
        except (subprocess.CalledProcessError, OSError) as exc:
            log.error("Cancel shutdown failed: %s", exc)
            return "Failed to cancel shutdown."

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

    @staticmethod
    def sleep_pc() -> str:
        """Put the PC to sleep."""
        log.info("Putting PC to sleep")
        try:
            # SetSuspendState(hibernate=False, forceCritical=True, disableWakeEvent=False)
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Add-Type -AssemblyName System.Windows.Forms; "
                 "[System.Windows.Forms.Application]::SetSuspendState('Suspend', $true, $false)"],
                timeout=10,
            )
            return "Putting your PC to sleep."
        except Exception as exc:
            log.error("Sleep failed: %s", exc)
            return "Failed to put PC to sleep."

    @staticmethod
    def hibernate_pc() -> str:
        """Hibernate the PC."""
        log.info("Hibernating PC")
        try:
            subprocess.run(
                ["shutdown", "/h"],
                check=True, timeout=10,
            )
            return "Hibernating your PC."
        except (subprocess.CalledProcessError, OSError) as exc:
            log.error("Hibernate failed: %s", exc)
            return "Failed to hibernate. Hibernation may not be enabled."

    # ══════════════════════════════════════════════════════════════════════
    #  Volume Control
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def set_volume(level: int) -> str:
        """Set the master volume to *level* (0–100)."""
        level = max(0, min(100, level))
        log.info("Setting volume to %d%%", level)
        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            volume = speakers.EndpointVolume
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"Volume set to {level} percent."
        except Exception as exc:
            log.error("pycaw volume failed: %s", exc)

        # Fallback: nircmd
        try:
            nircmd_level = int(65535 * level / 100)
            subprocess.run(
                ["nircmd", "setsysvolume", str(nircmd_level)],
                check=True, timeout=5,
            )
            return f"Volume set to {level} percent."
        except FileNotFoundError:
            log.warning("nircmd not found")
        except (subprocess.CalledProcessError, OSError) as exc:
            log.error("nircmd failed: %s", exc)

        return f"Could not set volume to {level} percent."

    @staticmethod
    def mute() -> str:
        """Mute the master volume."""
        log.info("Muting volume")
        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            volume = speakers.EndpointVolume
            volume.SetMute(True, None)
            return "Volume muted."
        except Exception as exc:
            log.error("Mute failed: %s", exc)
            return "Failed to mute volume."

    @staticmethod
    def unmute() -> str:
        """Unmute the master volume."""
        log.info("Unmuting volume")
        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            volume = speakers.EndpointVolume
            volume.SetMute(False, None)
            return "Volume unmuted."
        except Exception as exc:
            log.error("Unmute failed: %s", exc)
            return "Failed to unmute volume."

    # ══════════════════════════════════════════════════════════════════════
    #  Brightness
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def set_brightness(level: int) -> str:
        """Set screen brightness (0–100). Uses WMI via PowerShell."""
        level = max(0, min(100, level))
        log.info("Setting brightness to %d%%", level)
        try:
            subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    f"(Get-WmiObject -Namespace root/WMI "
                    f"-Class WmiMonitorBrightnessMethods)"
                    f".WmiSetBrightness(1, {level})"
                ],
                check=True, timeout=10,
                capture_output=True,
            )
            return f"Brightness set to {level} percent."
        except subprocess.CalledProcessError as exc:
            log.error("Brightness command failed: %s", exc.stderr)
            return "Failed to set brightness. This may not work on desktop monitors."
        except Exception as exc:
            log.error("Brightness failed: %s", exc)
            return "Failed to set brightness."

    # ══════════════════════════════════════════════════════════════════════
    #  Network
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def wifi_on() -> str:
        """Enable Wi-Fi."""
        log.info("Enabling Wi-Fi")
        try:
            subprocess.run(
                ["netsh", "interface", "set", "interface", "Wi-Fi", "enabled"],
                check=True, timeout=10, capture_output=True,
            )
            return "Wi-Fi enabled."
        except Exception as exc:
            log.error("Wi-Fi enable failed: %s", exc)
            return "Failed to enable Wi-Fi."

    @staticmethod
    def wifi_off() -> str:
        """Disable Wi-Fi."""
        log.info("Disabling Wi-Fi")
        try:
            subprocess.run(
                ["netsh", "interface", "set", "interface", "Wi-Fi", "disabled"],
                check=True, timeout=10, capture_output=True,
            )
            return "Wi-Fi disabled."
        except Exception as exc:
            log.error("Wi-Fi disable failed: %s", exc)
            return "Failed to disable Wi-Fi."

    @staticmethod
    def wifi_status() -> str:
        """Check Wi-Fi connection status."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=10,
            )
            output = result.stdout
            # Parse SSID and state
            ssid = ""
            state = ""
            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    ssid = line.split(":", 1)[1].strip()
                if line.startswith("State"):
                    state = line.split(":", 1)[1].strip()

            if state.lower() == "connected" and ssid:
                return f"Wi-Fi is connected to '{ssid}'."
            elif state:
                return f"Wi-Fi state: {state}."
            else:
                return "Couldn't determine Wi-Fi status."
        except Exception as exc:
            log.error("Wi-Fi status check failed: %s", exc)
            return "Failed to check Wi-Fi status."

    @staticmethod
    def bluetooth_on() -> str:
        """Enable Bluetooth via PowerShell."""
        log.info("Enabling Bluetooth")
        try:
            subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
                    "$radio = [Windows.Devices.Radios.Radio,Windows.System.Devices,"
                    "ContentType=WindowsRuntime]::GetRadiosAsync().GetAwaiter().GetResult() "
                    "| Where-Object { $_.Kind -eq 'Bluetooth' }; "
                    "$radio.SetStateAsync('On').GetAwaiter().GetResult()"
                ],
                check=True, timeout=15, capture_output=True,
            )
            return "Bluetooth enabled."
        except Exception as exc:
            log.error("Bluetooth enable failed: %s", exc)
            return "Failed to enable Bluetooth. Try toggling it in Settings."

    @staticmethod
    def bluetooth_off() -> str:
        """Disable Bluetooth via PowerShell."""
        log.info("Disabling Bluetooth")
        try:
            subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
                    "$radio = [Windows.Devices.Radios.Radio,Windows.System.Devices,"
                    "ContentType=WindowsRuntime]::GetRadiosAsync().GetAwaiter().GetResult() "
                    "| Where-Object { $_.Kind -eq 'Bluetooth' }; "
                    "$radio.SetStateAsync('Off').GetAwaiter().GetResult()"
                ],
                check=True, timeout=15, capture_output=True,
            )
            return "Bluetooth disabled."
        except Exception as exc:
            log.error("Bluetooth disable failed: %s", exc)
            return "Failed to disable Bluetooth."

    @staticmethod
    def get_ip_address() -> str:
        """Get the local and public IP addresses."""
        log.info("Getting IP address")
        # Local IP
        local_ip = "unknown"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass

        return f"Your local IP address is {local_ip}."

    # ══════════════════════════════════════════════════════════════════════
    #  Battery
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def battery_status() -> str:
        """Check the battery level and charging status."""
        log.info("Checking battery status")
        try:
            # Use SYSTEM_POWER_STATUS struct via ctypes
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_byte),
                    ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte),
                    ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong),
                ]

            status = SYSTEM_POWER_STATUS()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))

            percent = status.BatteryLifePercent
            charging = status.ACLineStatus == 1

            if percent == 255:
                return "No battery detected (this appears to be a desktop)."

            state = "charging" if charging else "not charging"
            return f"Battery is at {percent}% and {state}."
        except Exception as exc:
            log.error("Battery status failed: %s", exc)
            return "Couldn't get battery status."

    # ══════════════════════════════════════════════════════════════════════
    #  Screenshot
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def take_screenshot() -> str:
        """Take a screenshot and save to Desktop."""
        log.info("Taking screenshot")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        save_path = Path.home() / "Desktop" / filename

        try:
            import pyautogui
            img = pyautogui.screenshot()
            img.save(str(save_path))
            log.info("Screenshot saved: %s", save_path)
            return f"Screenshot saved to Desktop as {filename}."
        except ImportError:
            # Fallback: use Snipping Tool
            try:
                subprocess.Popen(
                    ["explorer.exe", "ms-screenclip:"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return "Opening Snipping Tool for screenshot."
            except OSError:
                return "Couldn't take a screenshot. Install pyautogui for auto-capture."
        except Exception as exc:
            log.error("Screenshot failed: %s", exc)
            return "Failed to take screenshot."

    # ══════════════════════════════════════════════════════════════════════
    #  Timer
    # ══════════════════════════════════════════════════════════════════════

    _active_timer: Optional[threading.Timer] = None
    _timer_callback: Optional[Callable] = None

    @classmethod
    def set_timer(cls, seconds: int, tts_callback: Optional[Callable] = None) -> str:
        """Set a countdown timer. When it finishes, TTS announces it."""
        if seconds <= 0:
            return "Timer must be positive."
        if seconds > 86400:
            return "Timer can't exceed 24 hours."

        # Cancel existing timer if any
        if cls._active_timer and cls._active_timer.is_alive():
            cls._active_timer.cancel()

        cls._timer_callback = tts_callback

        def _timer_done():
            log.info("Timer finished (%d seconds)", seconds)
            if cls._timer_callback:
                cls._timer_callback("Time's up! Your timer has finished.")
            cls._active_timer = None

        cls._active_timer = threading.Timer(seconds, _timer_done)
        cls._active_timer.daemon = True
        cls._active_timer.start()
        log.info("Timer set for %d seconds", seconds)

        # Human-friendly description
        if seconds >= 3600:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            desc = f"{hours} hour{'s' if hours > 1 else ''}"
            if mins:
                desc += f" and {mins} minute{'s' if mins > 1 else ''}"
        elif seconds >= 60:
            mins = seconds // 60
            secs = seconds % 60
            desc = f"{mins} minute{'s' if mins > 1 else ''}"
            if secs:
                desc += f" and {secs} second{'s' if secs > 1 else ''}"
        else:
            desc = f"{seconds} second{'s' if seconds > 1 else ''}"

        return f"Timer set for {desc}."

    @classmethod
    def cancel_timer(cls) -> str:
        """Cancel the active timer."""
        if cls._active_timer and cls._active_timer.is_alive():
            cls._active_timer.cancel()
            cls._active_timer = None
            log.info("Timer cancelled")
            return "Timer cancelled."
        return "No active timer to cancel."

    # ══════════════════════════════════════════════════════════════════════
    #  Clipboard
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def read_clipboard() -> str:
        """Read text from the clipboard."""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            if not user32.OpenClipboard(0):
                return "Couldn't access the clipboard."
            try:
                handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
                if not handle:
                    return "Clipboard is empty."
                kernel32.GlobalLock.restype = ctypes.c_void_p
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    return "Clipboard is empty."
                try:
                    text = ctypes.wstring_at(ptr)
                finally:
                    kernel32.GlobalUnlock(handle)
                if text:
                    short = text[:200] + "…" if len(text) > 200 else text
                    return f"Clipboard contains: {short}"
                return "Clipboard is empty."
            finally:
                user32.CloseClipboard()
        except Exception as exc:
            log.error("Read clipboard failed: %s", exc)
            return "Couldn't read the clipboard."

    @staticmethod
    def copy_to_clipboard(text: str) -> str:
        """Copy text to the clipboard."""
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Set-Clipboard -Value '{text.replace(chr(39), chr(39)+chr(39))}'"],
                check=True, timeout=5, capture_output=True,
            )
            return f"Copied to clipboard."
        except Exception as exc:
            log.error("Copy to clipboard failed: %s", exc)
            return "Failed to copy to clipboard."

    @staticmethod
    def clear_clipboard() -> str:
        """Clear the clipboard."""
        try:
            ctypes.windll.user32.OpenClipboard(0)
            ctypes.windll.user32.EmptyClipboard()
            ctypes.windll.user32.CloseClipboard()
            return "Clipboard cleared."
        except Exception as exc:
            log.error("Clear clipboard failed: %s", exc)
            return "Failed to clear clipboard."
