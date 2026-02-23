"""
Nova Voice Assistant - Fallback Intent Parser
Regex-based intent classification used when Ollama is unavailable.
Provides basic functionality without an LLM.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

log = get_logger(__name__)

# ── Pattern definitions ───────────────────────────────────────────────────────
# Each tuple: (intent_name, compiled_regex, parameter_extractor_function)

_PATTERNS: List[Tuple[str, re.Pattern, Any]] = []


# ── Extractors ────────────────────────────────────────────────────────────────

def _empty(_m: re.Match) -> Dict[str, Any]:
    return {}


def _pct(m: re.Match) -> Dict[str, Any]:
    level = m.group("level")
    return {"level": int(level)} if level else {}


def _app(m: re.Match) -> Dict[str, Any]:
    name = m.group("app")
    return {"app_name": name.strip()} if name else {}


def _query(m: re.Match) -> Dict[str, Any]:
    q = m.group("query")
    return {"query": q.strip()} if q else {}


def _note(m: re.Match) -> Dict[str, Any]:
    n = m.group("note")
    return {"note": n.strip()} if n else {}


# ── Compound / follow-up extractors ──────────────────────────────────────────

def _msg_app_contact(m: re.Match) -> Dict[str, Any]:
    """Extract app, contact, message from compound messaging patterns."""
    params: Dict[str, Any] = {}
    for key in ("app", "contact", "message"):
        try:
            val = m.group(key)
            if val:
                params[key] = val.strip()
        except IndexError:
            pass
    return params


def _email_params(m: re.Match) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for key in ("recipient", "subject", "body"):
        try:
            val = m.group(key)
            if val:
                params[key] = val.strip()
        except IndexError:
            pass
    return params


def _media_params(m: re.Match) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for key in ("query", "platform"):
        try:
            val = m.group(key)
            if val:
                params[key] = val.strip()
        except IndexError:
            pass
    return params


def _contact_params(m: re.Match) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for key in ("name", "phone", "email"):
        try:
            val = m.group(key)
            if val:
                params[key] = val.strip()
        except IndexError:
            pass
    return params


def _url_params(m: re.Match) -> Dict[str, Any]:
    url = m.group("url")
    return {"url": url.strip()} if url else {}


# ── Build pattern list (ORDER MATTERS - first match wins) ────────────────────
#    Compound / follow-up patterns MUST come BEFORE simple open_app.

_RAW_PATTERNS = [
    # ── Informational ─────────────────────────────────────────────────
    ("time",
     r"(?:what(?:'s|\s+is)\s+the\s+)?(?:current\s+)?time|tell\s+(?:me\s+)?the\s+time|what\s+time\s+is\s+it",
     _empty),
    ("date",
     r"(?:what(?:'s|\s+is)\s+)?(?:today(?:'s)?\s+)?date|what\s+day\s+is\s+it|today(?:'s)?\s+date|what(?:'s|\s+is)\s+the\s+date",
     _empty),
    ("greeting",
     r"^(?:hi|hello|hey|howdy|good\s+(?:morning|afternoon|evening)|what(?:'s)?\s*up|yo)(?:\s+nova)?$",
     _empty),

    # ── Volume ────────────────────────────────────────────────────────
    ("set_volume",
     r"(?:set|change|adjust)\s+(?:the\s+)?volume\s+(?:to\s+)?(?P<level>\d{1,3})\s*(?:%|percent)?",
     _pct),

    # ══ COMPOUND / FOLLOW-UP PATTERNS (before open_app!) ═════════════

    # -- Send message: "send hi to varun on whatsapp" ─────────────────
    ("send_message",
     r"send\s+(?P<message>.+?)\s+to\s+(?P<contact>.+?)\s+(?:on|via|through|in|using)\s+(?P<app>whatsapp|telegram|signal|sms)",
     _msg_app_contact),

    # -- Send message: "open whatsapp and send hi to varun" ───────────
    ("send_message",
     r"(?:open\s+)?(?P<app>whatsapp|telegram|signal)\s+(?:and\s+)?send\s+(?P<message>.+?)\s+to\s+(?P<contact>.+)",
     _msg_app_contact),

    # -- Send message: "message varun saying hello on whatsapp" ───────
    ("send_message",
     r"(?:text|message|msg|dm)\s+(?P<contact>.+?)\s+(?:saying|that|with)\s+(?P<message>.+?)(?:\s+(?:on|via)\s+(?P<app>whatsapp|telegram|signal))?$",
     _msg_app_contact),

    # -- Send message: "whatsapp varun hi" (short form) ───────────────
    ("send_message",
     r"(?P<app>whatsapp|telegram)\s+(?P<contact>.+?)\s+(?:saying\s+)?(?P<message>.{2,})",
     _msg_app_contact),

    # -- Email: "send email to john@x.com saying meeting" ─────────────
    ("send_email",
     r"(?:send\s+)?(?:an?\s+)?(?:email|mail)\s+(?:to\s+)?(?P<recipient>\S+@\S+)\s+(?:saying|about|with\s+subject|that)\s+(?P<body>.+)",
     _email_params),

    # -- Email: "email john@x.com about meeting" ──────────────────────
    ("send_email",
     r"(?:email|mail)\s+(?P<recipient>\S+@\S+)\s+(?:about\s+)?(?P<body>.+)",
     _email_params),

    # -- Play media: "play shape of you on spotify" ───────────────────
    ("play_media",
     r"(?:play|search|watch|find|listen\s+to)\s+(?P<query>.+?)\s+(?:on|in)\s+(?P<platform>youtube|spotify)",
     _media_params),

    # -- Play media: "open youtube and search python tutorials" ────────
    ("play_media",
     r"(?:open\s+)?(?P<platform>youtube|spotify)\s+(?:and\s+)?(?:play|search|watch|find|listen)\s+(?P<query>.+)",
     _media_params),

    # -- Add contact: "add contact mom phone +91..." ──────────────────
    ("add_contact",
     r"(?:add|save|create|new)\s+contact\s+(?P<name>.+?)\s+(?:phone|number|mobile)\s+(?P<phone>\+?\d[\d\s\-]+)",
     _contact_params),

    # -- Add contact with email: "add contact john email j@x.com" ─────
    ("add_contact",
     r"(?:add|save|create|new)\s+contact\s+(?P<name>.+?)\s+(?:email|mail)\s+(?P<email>\S+@\S+)",
     _contact_params),

    # -- List contacts ─────────────────────────────────────────────────
    ("list_contacts",
     r"(?:show|list|display|see)\s+(?:my\s+)?contacts",
     _empty),

    # -- Open URL: "open google.com" / "go to example.com" ────────────
    ("open_url",
     r"(?:open|go\s+to|visit|browse)\s+(?P<url>(?:https?://)?[\w\-]+\.[\w\-.]+\S*)",
     _url_params),

    # ══ SIMPLE APP / SYSTEM PATTERNS ═════════════════════════════════

    # -- App control ───────────────────────────────────────────────────
    ("open_app",
     r"(?:^|\b)(?:open|launch|(?<!re)start|run)\s+(?P<app>.+)",
     _app),
    ("close_app",
     r"(?:close|quit|exit|kill|stop)\s+(?P<app>.+)",
     _app),

    # -- System control ────────────────────────────────────────────────
    ("shutdown",
     r"(?:shut\s*down|power\s+off|turn\s+off)(?:\s+the\s+(?:pc|computer))?",
     _empty),
    ("restart",
     r"\b(?:restart|reboot)(?:\s+(?:the\s+)?(?:pc|computer))?",
     _empty),
    ("lock_pc",
     r"(?:lock)(?:\s+(?:the\s+)?(?:pc|computer|screen))?",
     _empty),

    # -- Web search ────────────────────────────────────────────────────
    ("search_web",
     r"(?:search|google|look\s+up|find)\s+(?:for\s+|the\s+web\s+for\s+)?(?P<query>.+)",
     _query),

    # -- Notes / memory ────────────────────────────────────────────────
    ("remember_note",
     r"(?:remember|save|note|store)\s+(?:that\s+)?(?P<note>.+)",
     _note),
    ("recall_note",
     r"(?:what\s+did\s+(?:i|you)\s+(?:tell|ask|say)|recall|show)\s*(?:you\s+to\s+)?(?:remember|notes?)?",
     _empty),
]

for intent, pattern, extractor in _RAW_PATTERNS:
    _PATTERNS.append((intent, re.compile(pattern, re.IGNORECASE), extractor))


# ── Public API ────────────────────────────────────────────────────────────────

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
    cleaned = re.sub(
        r"^(?:hey\s+)?nova\s*,?\s*", "", cleaned, flags=re.IGNORECASE
    ).strip()

    for intent, pattern, extractor in _PATTERNS:
        match = pattern.search(cleaned)
        if match:
            params = extractor(match)
            log.info("Fallback classifier matched: %s (params=%s)", intent, params)
            return {"intent": intent, "parameters": params}

    log.debug("Fallback classifier: no pattern matched for '%s'", text)
    return None
