"""
Nova Voice Assistant — Central Configuration
All tunable parameters and constants live here.
"""

import sys
from pathlib import Path
from typing import Dict, List

# ─── Paths ────────────────────────────────────────────────────────────────────
# When frozen by PyInstaller, _MEIPASS points to the temp extraction dir.
# For one-dir builds, sys._MEIPASS == the dir containing the .exe.
if getattr(sys, "frozen", False):
    BASE_DIR: Path = Path(sys._MEIPASS).resolve()
else:
    BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"
LOG_DIR: Path = BASE_DIR / "logs"
ASSETS_DIR: Path = BASE_DIR / "assets"
DB_PATH: Path = DATA_DIR / "memory.db"
VOSK_MODEL_DIR: Path = DATA_DIR / "vosk-model"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ─── Wake Word ────────────────────────────────────────────────────────────────
WAKE_WORD: str = "hello"              # primary wake word (Vosk recognises well)
WAKE_WORDS: list[str] = ["hello", "hi", "hey"]  # any of these triggers wake
WAKE_WORD_SENSITIVITY: float = 0.6  # 0‑1  (lower = stricter)

# ─── Audio / Microphone ──────────────────────────────────────────────────────
# Auto-detect: try these (device_index, sample_rate) candidates at startup
MIC_CANDIDATES: list[tuple[int, int]] = [
    (1,  44100),   # MME Intel SST
    (5,  44100),   # DirectSound Intel SST
    (9,  48000),   # WASAPI Intel SST
    (0,  44100),   # MME Sound Mapper
    (4,  44100),   # DirectSound Primary
]
MIC_DEVICE_INDEX: int | None = None   # None = auto-detect at startup
MIC_NATIVE_RATE: int = 44100          # overwritten by auto-detect
MIC_WARMUP_SECONDS: float = 5.0       # seconds to wait during each probe
AUDIO_SAMPLE_RATE: int = 16000   # Target rate for Whisper/Vosk
AUDIO_CHANNELS: int = 1
AUDIO_CHUNK_SIZE: int = 4096
RECORD_SECONDS_MAX: float = 10.0  # max command length after wake word
SILENCE_THRESHOLD: float = 1.5    # seconds of silence to stop recording
SILENCE_ENERGY: int = 100         # RMS energy below which counts as silence

# ─── Speech‑to‑Text (faster‑whisper) ─────────────────────────────────────────
WHISPER_MODEL_SIZE: str = "base"        # "tiny", "base", "small", "medium"
WHISPER_DEVICE: str = "cpu"             # "cpu" or "cuda"
WHISPER_COMPUTE_TYPE: str = "int8"      # "int8" for CPU, "float16" for CUDA
WHISPER_LANGUAGE: str = "en"
WHISPER_BEAM_SIZE: int = 5

# ─── Text‑to‑Speech (pyttsx3) ────────────────────────────────────────────────
TTS_RATE: int = 175          # words per minute
TTS_VOLUME: float = 1.0      # 0.0 – 1.0

# ─── LLM / Ollama ────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_MODEL: str = "llama3"
OLLAMA_TIMEOUT: int = 30  # seconds
OLLAMA_TEMPERATURE: float = 0.1  # low = deterministic

# ─── Intent Schema ────────────────────────────────────────────────────────────
SUPPORTED_INTENTS: List[str] = [
    # Informational
    "time",
    "date",
    "greeting",
    # Compound / follow-up
    "send_message",
    "send_email",
    "play_media",
    "open_url",
    "add_contact",
    "list_contacts",
    # App control
    "open_app",
    "close_app",
    # System — power
    "shutdown",
    "restart",
    "cancel_shutdown",
    "lock_pc",
    "sleep_pc",
    "hibernate_pc",
    # System — audio / display
    "set_volume",
    "volume_up",
    "volume_down",
    "mute",
    "unmute",
    "set_brightness",
    # System — network
    "wifi_on",
    "wifi_off",
    "wifi_status",
    "bluetooth_on",
    "bluetooth_off",
    # System — quick settings
    "night_light_on",
    "night_light_off",
    "airplane_mode_on",
    "airplane_mode_off",
    "energy_saver_on",
    "energy_saver_off",
    "hotspot_on",
    "hotspot_off",
    # System — info
    "battery_status",
    "ip_address",
    "screenshot",
    # Clipboard
    "read_clipboard",
    "clear_clipboard",
    # Timer
    "set_timer",
    "cancel_timer",
    # File management
    "create_folder",
    "delete_folder",
    "rename_folder",
    "open_folder",
    "list_files",
    "empty_recycle_bin",
    # Web / search / notes
    "search_web",
    "remember_note",
    "recall_note",
    # Fallback
    "unknown",
]

# ─── Contacts ─────────────────────────────────────────────────────────────
CONTACTS_FILE = DATA_DIR / "contacts.json"

# ─── Security — App Whitelist ─────────────────────────────────────────────────
# Keys are lowercase friendly names.  Values are executable names that
# Windows can resolve via PATH or the Start menu.
APP_WHITELIST: Dict[str, str] = {
    # ── Browsers ──────────────────────────────────────────────────────────
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "mozilla firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "brave": "brave.exe",
    "brave browser": "brave.exe",
    "opera": "opera.exe",
    "opera gx": "opera.exe",
    "vivaldi": "vivaldi.exe",
    "tor": "firefox.exe",           # Tor Browser uses firefox.exe internally
    "tor browser": "firefox.exe",
    # ── System Utilities ──────────────────────────────────────────────────
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "this pc": "explorer.exe",
    "my computer": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    "settings": "ms-settings:",
    "windows settings": "ms-settings:",
    "device manager": "devmgmt.msc",
    "disk management": "diskmgmt.msc",
    "registry editor": "regedit.exe",
    "regedit": "regedit.exe",
    "snipping tool": "ms-screenclip:",
    "snip": "ms-screenclip:",
    "screenshot": "ms-screenclip:",
    "magnifier": "magnify.exe",
    "on screen keyboard": "osk.exe",
    "character map": "charmap.exe",
    "resource monitor": "resmon.exe",
    "event viewer": "eventvwr.msc",
    "services": "services.msc",
    "system information": "msinfo32.exe",
    "remote desktop": "mstsc.exe",
    # ── Microsoft Office ──────────────────────────────────────────────────
    "word": "WINWORD.EXE",
    "microsoft word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "microsoft excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "microsoft powerpoint": "POWERPNT.EXE",
    "outlook": "OUTLOOK.EXE",
    "microsoft outlook": "OUTLOOK.EXE",
    "onenote": "onenote.exe",
    "access": "MSACCESS.EXE",
    "publisher": "MSPUB.EXE",
    "teams": "ms-teams.exe",
    "microsoft teams": "ms-teams.exe",
    # ── Media & Creative ──────────────────────────────────────────────────
    "paint": "mspaint.exe",
    "ms paint": "mspaint.exe",
    "photos": "ms-photos:",
    "spotify": "Spotify.exe",
    "vlc": "vlc.exe",
    "vlc media player": "vlc.exe",
    "media player": "wmplayer.exe",
    "windows media player": "wmplayer.exe",
    "movies and tv": "mswindowsvideo:",
    "groove music": "mswindowsmusic:",
    "audacity": "audacity.exe",
    "obs": "obs64.exe",
    "obs studio": "obs64.exe",
    "handbrake": "HandBrake.exe",
    # ── Development ───────────────────────────────────────────────────────
    "code": "Code.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "visual studio": "devenv.exe",
    "android studio": "studio64.exe",
    "intellij": "idea64.exe",
    "pycharm": "pycharm64.exe",
    "sublime": "sublime_text.exe",
    "sublime text": "sublime_text.exe",
    "atom": "atom.exe",
    "notepad++": "notepad++.exe",
    "notepad plus plus": "notepad++.exe",
    "git bash": "git-bash.exe",
    "postman": "Postman.exe",
    "docker": "Docker Desktop.exe",
    "docker desktop": "Docker Desktop.exe",
    # ── Communication ─────────────────────────────────────────────────────
    "discord": "Discord.exe",
    "telegram": "Telegram.exe",
    "whatsapp": "WhatsApp.exe",
    "zoom": "Zoom.exe",
    "skype": "Skype.exe",
    "slack": "slack.exe",
    "signal": "Signal.exe",
    # ── Gaming ────────────────────────────────────────────────────────────
    "steam": "steam.exe",
    "epic games": "EpicGamesLauncher.exe",
    "epic games launcher": "EpicGamesLauncher.exe",
    "xbox": "xbox:",
    "xbox game bar": "xbox:",
    # ── Productivity / Other ──────────────────────────────────────────────
    "notion": "Notion.exe",
    "obsidian": "Obsidian.exe",
    "todoist": "Todoist.exe",
    "bitwarden": "Bitwarden.exe",
    "1password": "1Password.exe",
    "7zip": "7zFM.exe",
    "7 zip": "7zFM.exe",
    "winrar": "WinRAR.exe",
    "everything": "Everything.exe",
    "blender": "blender.exe",
    "gimp": "gimp-2.10.exe",
    "inkscape": "inkscape.exe",
    "libreoffice": "soffice.exe",
    "filezilla": "filezilla.exe",
    "putty": "putty.exe",
    "winscp": "WinSCP.exe",
}

# Commands that are NEVER allowed through shell execution
BLOCKED_COMMANDS: List[str] = [
    "format",
    "del /s",
    "rmdir /s",
    "rd /s",
    "rm -rf",
    "reg delete",
    "net user",
    "bcdedit",
    "diskpart",
]

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL: str = "DEBUG"
LOG_FORMAT: str = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"
LOG_FILE: Path = LOG_DIR / "nova.log"
LOG_MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT: int = 3
