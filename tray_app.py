"""
Nova Voice Assistant — System Tray Application
Runs Nova as a background desktop app with a system-tray icon.

Features:
    • Start / Stop assistant toggle
    • Microphone state indicator (icon colour)
    • Start-with-Windows toggle (registry)
    • Quit

Usage (no console window):
    pythonw tray_app.py

Or from a terminal:
    python tray_app.py
"""

import os
import sys
import threading
import time
import winreg
from pathlib import Path

# ── Fix for windowless exe (pythonw / PyInstaller --noconsole) ────────────────
# sys.stdout and sys.stderr are None when there's no console.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Ensure package root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Prevent hf_xet download failures
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

import pystray
from PIL import Image, ImageDraw, ImageFont

from config import ASSETS_DIR
from utils.logger import setup_logging, get_logger

log = get_logger("nova.tray")

# ─── Constants ────────────────────────────────────────────────────────────────
APP_NAME = "Nova Voice Assistant"
ICON_SIZE = 64
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_VALUE_NAME = "NovaVoiceAssistant"

# ─── Icon with status indicator dot ──────────────────────────────────────────
#   Uses the real Nova logo with a small coloured dot in the bottom-right
#   corner to indicate state:
#     green  = listening for wake word
#     orange = recording command
#     grey   = stopped
#     red    = error

_LOGO_PATH = ASSETS_DIR / "nova_logo.png"


def _load_base_icon() -> Image.Image:
    """Load the Nova logo and resize to tray icon size."""
    try:
        logo = Image.open(str(_LOGO_PATH)).convert("RGBA")
        return logo.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
    except Exception:
        # Fallback: plain circle with N
        img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([2, 2, ICON_SIZE - 2, ICON_SIZE - 2], fill=(100, 100, 200))
        try:
            font = ImageFont.truetype("arialbd.ttf", 32)
        except OSError:
            font = ImageFont.load_default()
        draw.text((18, 14), "N", fill="white", font=font)
        return img


def _make_icon_with_dot(colour: str) -> Image.Image:
    """Overlay a coloured status dot on the Nova logo."""
    base = _load_base_icon()
    draw = ImageDraw.Draw(base)
    colours = {
        "green": (46, 204, 113),
        "orange": (243, 156, 18),
        "grey": (149, 165, 166),
        "red": (231, 76, 60),
    }
    rgb = colours.get(colour, colours["grey"])
    # Status dot in bottom-right corner (12px diameter)
    dot_size = 14
    x1 = ICON_SIZE - dot_size - 1
    y1 = ICON_SIZE - dot_size - 1
    x2 = ICON_SIZE - 1
    y2 = ICON_SIZE - 1
    # White border ring
    draw.ellipse([x1 - 1, y1 - 1, x2 + 1, y2 + 1], fill=(255, 255, 255))
    # Coloured dot
    draw.ellipse([x1, y1, x2, y2], fill=rgb)
    return base


# Pre-render icons with the Nova logo + status dots
ICON_IDLE = _make_icon_with_dot("green")
ICON_LISTENING = _make_icon_with_dot("orange")
ICON_STOPPED = _make_icon_with_dot("grey")
ICON_ERROR = _make_icon_with_dot("red")


# ─── Windows startup (registry) ──────────────────────────────────────────────

def _get_launch_command() -> str:
    """Build the command that Windows should run at login."""
    # Use pythonw.exe so no console window appears
    venv_pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not venv_pythonw.exists():
        venv_pythonw = Path(sys.executable).with_name("pythonw.exe")
    python_exe = str(venv_pythonw) if venv_pythonw.exists() else sys.executable
    script = str(Path(__file__).resolve())
    return f'"{python_exe}" "{script}"'


def is_startup_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable_startup() -> None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, _get_launch_command())
        winreg.CloseKey(key)
        log.info("Startup entry added to registry")
    except OSError as exc:
        log.error("Failed to set startup registry key: %s", exc)


def disable_startup() -> None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, REG_VALUE_NAME)
        winreg.CloseKey(key)
        log.info("Startup entry removed from registry")
    except FileNotFoundError:
        pass
    except OSError as exc:
        log.error("Failed to remove startup registry key: %s", exc)


# ─── Nova Tray Application ───────────────────────────────────────────────────

class NovaTrayApp:
    """
    Wraps the Nova voice assistant into a system-tray application.

    States:
        stopped   → assistant not running, grey icon
        idle      → wake-word detector active, green icon
        listening → wake word heard, recording command, orange icon
    """

    def __init__(self) -> None:
        setup_logging()
        log.info("=" * 60)
        log.info("  Nova Voice Assistant — Tray Mode")
        log.info("=" * 60)

        self._nova = None              # Lazy-init Nova instance
        self._assistant_thread = None
        self._running = False          # Is assistant running?
        self._state = "stopped"        # stopped | idle | listening | error
        self._lock = threading.Lock()

        # Build the tray icon
        self._icon = pystray.Icon(
            name="nova",
            icon=ICON_STOPPED,
            title=f"{APP_NAME} — Stopped",
            menu=self._build_menu(),
        )

    # ── Menu ──────────────────────────────────────────────────────────────

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                "Start Assistant",
                self._on_toggle,
                visible=lambda item: not self._running,
            ),
            pystray.MenuItem(
                "Stop Assistant",
                self._on_toggle,
                visible=lambda item: self._running,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start with Windows",
                self._on_startup_toggle,
                checked=lambda item: is_startup_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                self._status_text,
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Nova", self._on_quit),
        )

    def _status_text(self, item) -> str:
        states = {
            "stopped": "Status: Stopped",
            "idle": "Status: Listening for wake word…",
            "listening": "Status: Recording command…",
            "error": "Status: Error",
        }
        return states.get(self._state, "Status: Unknown")

    # ── State management ──────────────────────────────────────────────────

    def _set_state(self, state: str) -> None:
        with self._lock:
            self._state = state
        icons = {
            "stopped": ICON_STOPPED,
            "idle": ICON_IDLE,
            "listening": ICON_LISTENING,
            "error": ICON_ERROR,
        }
        titles = {
            "stopped": f"{APP_NAME} — Stopped",
            "idle": f"{APP_NAME} — Listening…",
            "listening": f"{APP_NAME} — Recording…",
            "error": f"{APP_NAME} — Error",
        }
        self._icon.icon = icons.get(state, ICON_STOPPED)
        self._icon.title = titles.get(state, APP_NAME)
        # Force menu refresh
        self._icon.update_menu()

    # ── Assistant lifecycle ───────────────────────────────────────────────

    def _start_assistant(self) -> None:
        """Initialise and start the Nova voice pipeline in a background thread."""
        if self._running:
            return

        self._running = True
        self._assistant_thread = threading.Thread(
            target=self._assistant_loop, daemon=True, name="nova-assistant",
        )
        self._assistant_thread.start()

    def _stop_assistant(self) -> None:
        """Stop the voice pipeline gracefully."""
        if not self._running:
            return
        self._running = False

        # Signal Nova to shut down
        if self._nova:
            self._nova._shutdown_event.set()
            self._nova._wake_event.set()  # unblock the wait

        if self._assistant_thread:
            self._assistant_thread.join(timeout=5.0)
            self._assistant_thread = None

        # Clean up Nova
        if self._nova:
            try:
                self._nova._cleanup()
            except Exception:
                log.exception("Error during Nova cleanup")
            self._nova = None

        self._set_state("stopped")
        log.info("Assistant stopped")

    def _assistant_loop(self) -> None:
        """Run the Nova voice pipeline (called in background thread)."""
        try:
            self._set_state("idle")

            # Import and create Nova (heavyweight — loads models)
            from main import Nova
            self._nova = Nova(keyboard_mode=False)

            # Monkey-patch the _process_command to track state transitions
            original_process = self._nova._process_command

            def _patched_process():
                self._set_state("listening")
                try:
                    original_process()
                finally:
                    if self._running:
                        self._set_state("idle")

            self._nova._process_command = _patched_process

            # Start the wake-word detector
            if self._nova._detector:
                self._nova._detector.start()

            self._set_state("idle")
            log.info("Assistant started — waiting for wake word")

            # Speak ready notification
            self._nova._tts.speak("Nova is ready.")

            # Main loop — mirrors Nova._run_voice() but checks self._running
            while self._running:
                triggered = self._nova._wake_event.wait(timeout=0.5)
                if not triggered:
                    continue
                self._nova._wake_event.clear()

                if not self._running:
                    break

                try:
                    self._nova._process_command()
                except Exception:
                    log.exception("Error processing command")
                    try:
                        self._nova._tts.speak("An error occurred.")
                    except Exception:
                        pass

        except Exception:
            log.exception("Fatal error in assistant loop")
            self._set_state("error")
            self._running = False

    # ── Menu callbacks ────────────────────────────────────────────────────

    def _on_toggle(self, icon, item) -> None:
        if self._running:
            log.info("User requested: Stop assistant")
            threading.Thread(target=self._stop_assistant, daemon=True).start()
        else:
            log.info("User requested: Start assistant")
            self._start_assistant()

    def _on_startup_toggle(self, icon, item) -> None:
        if is_startup_enabled():
            disable_startup()
            log.info("Start-with-Windows disabled")
        else:
            enable_startup()
            log.info("Start-with-Windows enabled")

    def _on_quit(self, icon, item) -> None:
        log.info("User requested: Quit")
        self._stop_assistant()
        icon.stop()

    # ── Run ───────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the tray icon and auto-start the assistant."""
        log.info("Starting system tray icon")

        # Auto-start the assistant after a short delay (let tray init first)
        def _auto_start():
            time.sleep(1.5)
            self._start_assistant()

        threading.Thread(target=_auto_start, daemon=True).start()

        # This blocks until icon.stop() is called
        self._icon.run()

        log.info("Tray app exited cleanly")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    app = NovaTrayApp()
    app.run()


if __name__ == "__main__":
    main()
