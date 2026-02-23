"""
Nova Voice Assistant — Shared Helpers
Reusable utility functions used across multiple modules.
"""

import json
import re
import struct
import math
from typing import Any, Dict, Optional

from utils.logger import get_logger

log = get_logger(__name__)


# ─── JSON Helpers ─────────────────────────────────────────────────────────────

def safe_json_parse(raw: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to extract the first valid JSON object from *raw*.

    Handles cases where the LLM wraps JSON in markdown fences or
    includes preamble text.  Returns ``None`` on failure.
    """
    if not raw or not raw.strip():
        log.warning("safe_json_parse received empty input")
        return None

    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Attempt to find first { ... } block (greedy)
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    log.error("Failed to parse JSON from LLM output: %.200s", raw)
    return None


# ─── Audio Helpers ────────────────────────────────────────────────────────────

def rms_energy(data: bytes, sample_width: int = 2) -> float:
    """Compute the RMS energy of a PCM‑16 audio chunk."""
    count = len(data) // sample_width
    if count == 0:
        return 0.0
    fmt = f"<{count}h"
    try:
        samples = struct.unpack(fmt, data)
    except struct.error:
        return 0.0
    sum_sq = sum(s * s for s in samples)
    return math.sqrt(sum_sq / count)


# ─── Text Normalisation ──────────────────────────────────────────────────────

def normalise_app_name(text: str) -> str:
    """Lower‑case and strip punctuation (keeping ``+``) for app lookup."""
    return re.sub(r"[^a-z0-9+ ]", "", text.lower()).strip()


def extract_percentage(text: str) -> Optional[int]:
    """Return first integer percentage found in *text*, or None."""
    match = re.search(r"(\d{1,3})\s*(?:%|percent)", text, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        return max(0, min(100, val))
    return None


# ─── Security ─────────────────────────────────────────────────────────────────

def is_command_blocked(command: str) -> bool:
    """Return True if *command* contains any blocked substrings."""
    from config import BLOCKED_COMMANDS
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            log.warning("Blocked dangerous command fragment: %s", blocked)
            return True
    return False
