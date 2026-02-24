# -*- mode: python ; coding: utf-8 -*-
"""
Nova Voice Assistant — PyInstaller Spec File
Build with:  pyinstaller nova.spec
Output:      dist/Nova/Nova.exe
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJ = Path(SPECPATH)
VENV_SITE = Path(sys.executable).parent.parent / "Lib" / "site-packages"

# ── Data files to bundle ─────────────────────────────────────────────────────
# (source_path, dest_folder_inside_bundle)
datas = [
    # Vosk speech-recognition model (~68 MB)
    (str(PROJ / "data" / "vosk-model"), os.path.join("data", "vosk-model")),
    # Contacts JSON
    (str(PROJ / "data" / "contacts.json"), "data"),
    # Assets (logo, icons)
    (str(PROJ / "assets" / "nova_logo.png"), "assets"),
    (str(PROJ / "assets" / "nova.ico"), "assets"),
    # sounddevice's PortAudio DLLs
    (
        str(VENV_SITE / "_sounddevice_data" / "portaudio-binaries"),
        os.path.join("_sounddevice_data", "portaudio-binaries"),
    ),
]

# Vosk native DLLs
vosk_dir = VENV_SITE / "vosk"
for dll in vosk_dir.glob("*.dll"):
    datas.append((str(dll), "vosk"))

# ctranslate2 native DLLs (faster-whisper backend)
ct2_dir = VENV_SITE / "ctranslate2"
for f in ct2_dir.glob("*.dll"):
    datas.append((str(f), "ctranslate2"))
for f in ct2_dir.glob("*.pyd"):
    datas.append((str(f), "ctranslate2"))

# onnxruntime DLLs
ort_dir = VENV_SITE / "onnxruntime"
ort_libs = ort_dir / "capi"
if ort_libs.is_dir():
    for f in ort_libs.glob("*.dll"):
        datas.append((str(f), os.path.join("onnxruntime", "capi")))

# Collect tokenizers data
datas += collect_data_files("tokenizers")

# ── Hidden imports ────────────────────────────────────────────────────────────
# Packages PyInstaller doesn't auto-detect
hiddenimports = [
    # Core audio
    "sounddevice",
    "_sounddevice_data",
    "scipy.signal",
    "scipy.fft",
    "scipy.fft._pocketfft",
    # Vosk
    "vosk",
    # faster-whisper / ctranslate2
    "faster_whisper",
    "ctranslate2",
    "ctranslate2._ext",
    # onnxruntime
    "onnxruntime",
    # TTS
    "pyttsx3",
    "pyttsx3.drivers",
    "pyttsx3.drivers.sapi5",
    # System tray
    "pystray",
    "pystray._win32",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    # Volume control
    "pycaw",
    "pycaw.pycaw",
    "pycaw.utils",
    "pycaw.api",
    "pycaw.api.endpointvolume",
    "comtypes",
    "comtypes.client",
    "comtypes.stream",
    # UI automation
    "pyautogui",
    "pyperclip",
    # System
    "win32api",
    "win32con",
    "win32gui",
    "winreg",
    "psutil",
    # Networking / HTTP (for Ollama + HuggingFace)
    "requests",
    "httpx",
    "httpcore",
    "certifi",
    "huggingface_hub",
    # Our own packages
    "audio",
    "audio.mic_finder",
    "audio.speech_to_text",
    "audio.text_to_speech",
    "audio.wake_word",
    "brain",
    "brain.fallback_classifier",
    "brain.intent_parser",
    "brain.llm_interface",
    "brain.memory",
    "brain.contacts",
    "router",
    "router.command_router",
    "system",
    "system.app_control",
    "system.browser_control",
    "system.file_manager",
    "system.messaging",
    "system.system_control",
    "utils",
    "utils.logger",
    "utils.helpers",
    "config",
]

# Also pull all onnxruntime submodules
hiddenimports += collect_submodules("onnxruntime")

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [str(PROJ / "tray_app.py")],          # Entry point = tray app (no console)
    pathex=[str(PROJ)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "_tkinter", "matplotlib",
        "xmlrpc", "lib2to3", "ensurepip",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],                       # NOT one-file — use one-dir for speed + model size
    exclude_binaries=True,
    name="Nova",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # Don't compress — faster startup
    console=False,            # No console window (tray app)
    icon=str(PROJ / "assets" / "nova.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Nova",
)
