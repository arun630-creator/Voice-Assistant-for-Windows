# Nova — Windows Voice Assistant

A fully offline, production‑grade voice assistant for Windows 10/11.
**Wake word → Speech‑to‑Text → LLM intent extraction → Command routing → System execution → TTS response.**

---

## Architecture

```
Microphone
  → Wake Word Detection   (Vosk — offline keyword spotting)
  → Record command
  → Speech to Text         (faster‑whisper — offline)
  → LLM Intent Extraction  (Ollama / llama3 — local, JSON output)
  → Command Router
  → System Execution       (subprocess / ctypes / PowerShell)
  → Text‑to‑Speech         (pyttsx3 / SAPI5)
```

## Folder Structure

```
assistant/
├── main.py                  # Entry point — orchestrator
├── config.py                # All tunable parameters
├── requirements.txt         # Python dependencies
├── README.md                # This file
│
├── audio/
│   ├── wake_word.py         # Vosk‑based wake word detector
│   ├── speech_to_text.py    # faster‑whisper transcription
│   └── text_to_speech.py    # pyttsx3 TTS wrapper
│
├── brain/
│   ├── llm_interface.py     # Ollama REST client
│   ├── intent_parser.py     # JSON validation & Intent dataclass
│   └── memory.py            # SQLite note storage
│
├── system/
│   ├── app_control.py       # Open / close whitelisted apps
│   ├── system_control.py    # Shutdown, restart, lock, volume
│   └── browser_control.py   # Web search, URL opening
│
├── router/
│   └── command_router.py    # Intent → handler dispatch
│
├── utils/
│   ├── logger.py            # Rotating file + console logging
│   └── helpers.py           # JSON parsing, audio helpers, security
│
├── data/                    # Created at runtime
│   ├── memory.db            # SQLite notes database
│   └── vosk-model/          # Vosk model directory (you provide)
│
└── logs/                    # Created at runtime
    └── nova.log
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.10+ | Runtime |
| **Ollama** | latest | Local LLM server |
| **Vosk model** | small‑en‑us | Wake word detection |
| **Microphone** | any | Audio input |

---

## Setup Instructions

### 1. Clone / copy the project

```bash
cd C:\Users\<you>\Documents\Voice\assistant
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

> **PyAudio on Windows:** If `pip install PyAudio` fails, install the wheel manually:
> ```powershell
> pip install pipwin
> pipwin install pyaudio
> ```
> Or download the `.whl` from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

### 4. Download and extract the Vosk model

```powershell
# Download the small English model (~40 MB)
Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip" -OutFile vosk-model.zip
Expand-Archive vosk-model.zip -DestinationPath data\
Rename-Item data\vosk-model-small-en-us-0.15 data\vosk-model
Remove-Item vosk-model.zip
```

The model must be at `assistant/data/vosk-model/`.

### 5. Install and start Ollama

1. Download Ollama from https://ollama.com/download/windows
2. Install and run.
3. Pull the model:

```powershell
ollama pull llama3
```

4. Verify it's running:

```powershell
curl http://localhost:11434/api/tags
```

### 6. Run Nova

```powershell
cd C:\Users\<you>\Documents\Voice\assistant
python main.py
```

You should hear: **"Nova is ready. Say nova to begin."**

---

## Example Commands

| You say | Intent | What happens |
|---------|--------|--------------|
| "Nova open Chrome" | `open_app` | Launches `chrome.exe` |
| "Nova close Notepad" | `close_app` | Kills `notepad.exe` |
| "Nova set volume to 50 percent" | `set_volume` | Sets master volume to 50% |
| "Nova shutdown" | `shutdown` | Schedules shutdown in 30s |
| "Nova restart" | `restart` | Schedules restart in 30s |
| "Nova lock the PC" | `lock_pc` | Locks workstation |
| "Nova search for Python tutorials" | `search_web` | Opens DuckDuckGo search |
| "Nova remember that I have an interview tomorrow" | `remember_note` | Saves note to SQLite |
| "Nova what did I tell you to remember" | `recall_note` | Reads back saved notes |

---

## How to Add New Intents

### Step 1 — Register the intent name

Edit `config.py` → `SUPPORTED_INTENTS` and add your new intent string:

```python
SUPPORTED_INTENTS: List[str] = [
    ...
    "play_music",   # ← new
]
```

### Step 2 — Update the LLM system prompt

Edit `brain/llm_interface.py` → `_SYSTEM_PROMPT`.  Add a line describing
the new intent and its expected parameters.

### Step 3 — Create a handler

Add a handler method in `router/command_router.py`:

```python
def _handle_play_music(self, intent: Intent) -> str:
    song = intent.parameters.get("song", "")
    # ... your logic ...
    return f"Playing {song}."
```

### Step 4 — Register the handler

In `CommandRouter.__init__`, add:

```python
self._handlers["play_music"] = self._handle_play_music
```

### Step 5 — (Optional) Add a system module

Create a new file under `system/` if the feature needs complex OS interaction.

---

## Configuration

All tunables live in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `WAKE_WORD` | `"nova"` | The keyword that activates the assistant |
| `WHISPER_MODEL_SIZE` | `"base"` | Whisper model (`tiny` / `base` / `small` / `medium`) |
| `OLLAMA_MODEL` | `"llama3"` | Ollama model name |
| `OLLAMA_TIMEOUT` | `30` | LLM request timeout in seconds |
| `RECORD_SECONDS_MAX` | `10.0` | Max recording length after wake word |
| `TTS_RATE` | `175` | Speech rate (words per minute) |
| `APP_WHITELIST` | (dict) | Allowed applications for open/close |

---

## Security Considerations

1. **App whitelist** — Only applications listed in `config.APP_WHITELIST` can be opened or closed.  Unknown app names are rejected.
2. **Blocked commands** — Dangerous shell fragments (`format`, `del /s`, `rmdir /s`, etc.) in `config.BLOCKED_COMMANDS` are checked before any subprocess call.
3. **No arbitrary shell execution** — The assistant never passes unsanitised LLM output to a shell.  All subprocess calls use explicit argument lists (no `shell=True`).
4. **JSON validation** — LLM output is parsed with `safe_json_parse` which extracts JSON defensively.  Invalid output defaults to the `unknown` intent.
5. **Intent validation** — Only intents in `SUPPORTED_INTENTS` are routed.  Anything else maps to `unknown`.
6. **Full audit logging** — Every command, intent, and execution result is logged to `logs/nova.log` with rotating file backup.
7. **Fail‑safe** — Exceptions in any module are caught and logged; the assistant continues running.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Failed to load Vosk model` | Ensure `data/vosk-model/` exists and contains the model files |
| `Ollama is not reachable` | Run `ollama serve` or check that Ollama is running on port 11434 |
| `PyAudio not found` | Install via `pipwin install pyaudio` or download the `.whl` |
| No audio input | Check Windows microphone permissions (Settings → Privacy → Microphone) |
| TTS not working | Ensure Windows SAPI5 voices are installed (`Settings → Time & Language → Speech`) |
| High latency | Switch to `WHISPER_MODEL_SIZE = "tiny"` in `config.py` |

---

## Future Improvements

- **GUI / System tray** — Add a `pystray` icon for status and settings.
- **Conversation context** — Maintain multi‑turn history for follow‑up questions.
- **Plugin system** — Dynamic intent discovery via entry points or a `plugins/` directory.
- **Streaming TTS** — Replace pyttsx3 with Coqui TTS for higher quality.
- **GPU acceleration** — Use `WHISPER_DEVICE = "cuda"` with `float16` for faster transcription.
- **Wake word training** — Train a custom Vosk grammar or use OpenWakeWord.
- **REST API** — Expose the pipeline via FastAPI for remote / mobile control.
- **Unit tests** — Add pytest suite with mocked audio and LLM responses.
- **CI / CD** — GitHub Actions for linting, type‑checking (mypy), and packaging.

---

## License

This project is open‑source and provided as‑is for educational and personal use.
