"""
Nova Voice Assistant — Fallback Intent Parser
Regex‑based intent classification used when Ollama is unavailable.
Provides basic functionality without an LLM.
"""

import re
from typing import Optional, Dict, Any, List, Tuple

from utils.logger import get_logger

log = get_logger(__name__)

# ─── Pattern definitions ──────────────────────────────────────────────────────
# Each tuple: (intent_name, compiled_regex, parameter_extractor_function)

_PATTERNS: List[Tuple[str, re.Pattern, Any]] = []


def _pct(match: re.Match) -> Dict[str, Any]:
    """Extract volume level from a regex match."""
    level = match.group("level")
    return {"level": int(level)} if level else {}


def _app(match: re.Match) -> Dict[str, Any]:
    """Extract app name from a regex match."""
    name = match.group("app")
    return {"app_name": name.strip()} if name else {}


def _query(match: re.Match) -> Dict[str, Any]:
    """Extract search query from a regex match."""
    q = match.group("query")
    return {"query": q.strip()} if q else {}


def _note(match: re.Match) -> Dict[str, Any]:
    """Extract note content from a regex match."""
    n = match.group("note")
    return {"note": n.strip()} if n else {}


def _empty(_match: re.Match) -> Dict[str, Any]:
    return {}


# Build pattern list (order matters — first match wins)
_RAW_PATTERNS = [
    # ── Informational ────────────────────────────────────────────────
    ("time",          r"(?:what(?:'s|\s+is)\s+the\s+)?(?:current\s+)?time|tell\s+(?:me\s+)?the\s+time|what\s+time\s+is\s+it", _empty),
    ("date",          r"(?:what(?:'s|\s+is)\s+)?(?:today(?:'s)?\s+)?date|what\s+day\s+is\s+it|today(?:'s)?\s+date|what(?:'s|\s+is)\s+the\s+date", _empty),
    ("greeting",      r"^(?:hi|hello|hey|howdy|good\s+(?:morning|afternoon|evening)|what(?:'s)?\s*up|yo)(?:\s+nova)?$", _empty),
    # ── Volume ────────────────────────────────────────────────────────
    ("set_volume",    r"(?:set|change|adjust)\s+(?:the\s+)?volume\s+(?:to\s+)?(?P<level>\d{1,3})\s*(?:%|percent)?", _pct),
    # ── App control ───────────────────────────────────────────────────
    ("open_app",      r"(?:^|\b)(?:open|launch|(?<!re)start|run)\s+(?P<app>.+)", _app),
    ("close_app",     r"(?:close|quit|exit|kill|stop)\s+(?P<app>.+)", _app),
    # ── System control ────────────────────────────────────────────────────────────
    ("shutdown",      r"(?:shut\s*down|power\s+off|turn\s+off)(?:\s+the\s+(?:pc|computer))?", _empty),
    ("restart",       r"\b(?:restart|reboot)(?:\s+(?:the\s+)?(?:pc|computer))?", _empty),
    ("lock_pc",       r"(?:lock)(?:\s+(?:the\s+)?(?:pc|computer|screen))?", _empty),
    # ── Web search ────────────────────────────────────────────────────
    ("search_web",    r"(?:search|google|look\s+up|find)\s+(?:for\s+|the\s+web\s+for\s+)?(?P<query>.+)", _query),
    # ── Notes / memory ────────────────────────────────────────────────
    ("remember_note", r"(?:remember|save|note|store)\s+(?:that\s+)?(?P<note>.+)", _note),
    ("recall_note",   r"(?:what\s+did\s+(?:i|you)\s+(?:tell|ask|say)|recall|show)\s*(?:you\s+to\s+)?(?:remember|notes?)?", _empty),
]

for intent, pattern, extractor in _RAW_PATTERNS:
    _PATTERNS.append((intent, re.compile(pattern, re.IGNORECASE), extractor))


# ─── Public API ───────────────────────────────────────────────────────────────

def fallback_classify(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to classify *text* using regex patterns.

    Returns a dict ``{"intent": ..., "parameters": {...}}`` on match,
    or ``None`` if no pattern matches.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    # Strip leading wake word if present
    cleaned = re.sub(r"^(?:hey\s+)?nova\s*,?\s*", "", cleaned, flags=re.IGNORECASE).strip()

    for intent, pattern, extractor in _PATTERNS:
        match = pattern.search(cleaned)
        if match:
            params = extractor(match)
            log.info("Fallback classifier matched: %s (params=%s)", intent, params)
            return {"intent": intent, "parameters": params}

    log.debug("Fallback classifier: no pattern matched for '%s'", text)
    return None
