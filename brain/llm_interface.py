"""
Nova Voice Assistant — LLM Interface
Communicates with a local Ollama instance to extract structured intents.
"""

import json
import time
from typing import Any, Dict, Optional

import requests

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_TEMPERATURE,
    SUPPORTED_INTENTS,
)
from utils.logger import get_logger

log = get_logger(__name__)

# ─── System Prompt ────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = f"""\
You are Nova, a voice‑controlled Windows assistant.
Your ONLY job is to classify the user's spoken command into a JSON object.

RULES — follow them exactly:
1. Reply with a SINGLE JSON object — nothing else. No explanation, no markdown.
2. The JSON MUST have exactly two keys: "intent" and "parameters".
3. "intent" MUST be one of: {json.dumps(SUPPORTED_INTENTS)}.
4. "parameters" is a dict of key/value pairs relevant to the intent.
   - open_app / close_app  → {{"app_name": "<name>"}}
   - set_volume             → {{"level": <0‑100>}}
   - search_web             → {{"query": "<search query>"}}
   - remember_note          → {{"note": "<text to save>"}}
   - recall_note            → {{}}
   - shutdown / restart / lock_pc → {{}}
   - unknown                → {{"raw": "<original text>"}}
5. If you cannot determine the intent, use "unknown".
"""


class LLMInterface:
    """
    Stateless wrapper around the Ollama REST API.

    Sends the user utterance together with a strict system prompt
    and returns the raw JSON string from the model.
    """

    def __init__(self) -> None:
        self._api_url = f"{OLLAMA_BASE_URL}/api/generate"
        self._model = OLLAMA_MODEL
        log.info("LLMInterface ready — model=%s, url=%s", self._model, self._api_url)

    # ── Health check ──────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    # ── Public API ────────────────────────────────────────────────────────

    def classify(self, user_text: str) -> Optional[str]:
        """
        Send *user_text* to the local LLM and return its raw response text.

        Returns ``None`` on any communication / timeout error.
        """
        if not user_text:
            return None

        payload: Dict[str, Any] = {
            "model": self._model,
            "prompt": user_text,
            "system": _SYSTEM_PROMPT,
            "stream": False,
            "options": {
                "temperature": OLLAMA_TEMPERATURE,
            },
            "format": "json",
        }

        log.debug("LLM request: model=%s, prompt='%s'", self._model, user_text)
        t0 = time.perf_counter()
        try:
            resp = requests.post(
                self._api_url,
                json=payload,
                timeout=OLLAMA_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.Timeout:
            log.error("LLM request timed out after %ds", OLLAMA_TIMEOUT)
            return None
        except requests.RequestException as exc:
            log.error("LLM request failed: %s", exc)
            return None

        elapsed = time.perf_counter() - t0
        body = resp.json()
        raw_response: str = body.get("response", "")
        log.info("LLM response (%.2fs): %s", elapsed, raw_response[:300])
        return raw_response
