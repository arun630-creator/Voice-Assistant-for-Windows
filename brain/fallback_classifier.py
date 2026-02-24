"""
Nova Voice Assistant — Fallback Intent Parser (Enhanced)

Regex-based intent classification used when Ollama is unavailable.
35+ patterns covering all supported intents.  ORDER MATTERS — first match wins.
Compound/follow-up patterns placed before simpler catch-all patterns.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

log = get_logger(__name__)

# ── Pattern definitions ───────────────────────────────────────────────────────
# Each tuple: (intent_name, compiled_regex, parameter_extractor_function)

_PATTERNS: List[Tuple[str, re.Pattern, Any]] = []


# ══════════════════════════════════════════════════════════════════════════════
#  Parameter extractors
# ══════════════════════════════════════════════════════════════════════════════

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


def _timer_params(m: re.Match) -> Dict[str, Any]:
    """Extract timer duration from various formats."""
    params: Dict[str, Any] = {}
    total_seconds = 0

    for key in ("hours", "minutes", "seconds"):
        try:
            val = m.group(key)
            if val:
                num = int(val)
                params[key] = num
                if key == "hours":
                    total_seconds += num * 3600
                elif key == "minutes":
                    total_seconds += num * 60
                else:
                    total_seconds += num
        except (IndexError, ValueError):
            pass

    params["total_seconds"] = total_seconds
    return params


def _folder_params(m: re.Match) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for key in ("folder", "location", "new_name", "old_name"):
        try:
            val = m.group(key)
            if val:
                params[key] = val.strip()
        except IndexError:
            pass
    return params


# ══════════════════════════════════════════════════════════════════════════════
#  Pattern definitions (ORDER MATTERS — first match wins)
# ══════════════════════════════════════════════════════════════════════════════

_RAW_PATTERNS = [
    # ── Informational ──────────────────────────────────────────────────
    ("time",
     r"(?:what(?:'s|\s+is)\s+the\s+)?(?:current\s+)?\btime\b|tell\s+(?:me\s+)?the\s+time|what\s+time\s+is\s+it",
     _empty),
    ("date",
     r"(?:what(?:'s|\s+is)\s+)?(?:today(?:'s)?\s+)?date|what\s+day\s+is\s+it|today(?:'s)?\s+date|what(?:'s|\s+is)\s+the\s+date",
     _empty),
    ("greeting",
     r"^(?:hi|hello|hey|howdy|good\s+(?:morning|afternoon|evening)|what(?:'s)?\s*up|yo)(?:\s+nova)?$",
     _empty),

    # ── Volume / Audio ─────────────────────────────────────────────────
    ("set_volume",
     r"(?:set|change|adjust|turn|make|put)\s+(?:the\s+)?volume\s+(?:to\s+|at\s+)?(?P<level>\d{1,3})\s*(?:%|percent)?",
     _pct),
    ("volume_up",
     r"(?:volume\s+up|(?:turn|make)\s+(?:it\s+|the\s+volume\s+)?(?:up|louder|higher))",
     _empty),
    ("volume_down",
     r"(?:volume\s+down|(?:turn|make)\s+(?:it\s+|the\s+volume\s+)?(?:down|quieter|softer|lower))",
     _empty),
    ("mute",
     r"\b(?:mute|silence)\b(?:\s+(?:the\s+)?(?:volume|audio|sound|speakers?))?",
     _empty),
    ("unmute",
     r"\b(?:unmute|unsilence)\b(?:\s+(?:the\s+)?(?:volume|audio|sound|speakers?))?",
     _empty),

    # ── Brightness ─────────────────────────────────────────────────────
    ("set_brightness",
     r"(?:set|change|adjust)\s+(?:the\s+)?(?:screen\s+)?brightness\s+(?:to\s+)?(?P<level>\d{1,3})\s*(?:%|percent)?",
     _pct),

    # ── Timer ──────────────────────────────────────────────────────────
    ("set_timer",
     r"(?:set|start|create)\s+(?:a\s+)?timer\s+(?:for\s+)?(?:(?P<hours>\d+)\s*(?:hours?|hrs?)\s*(?:and\s*)?)?"
     r"(?:(?P<minutes>\d+)\s*(?:minutes?|mins?)\s*(?:and\s*)?)?(?:(?P<seconds>\d+)\s*(?:seconds?|secs?)\s*)?",
     _timer_params),
    ("set_timer",
     r"(?:timer|remind\s+me)\s+(?:for\s+|in\s+)?(?:(?P<hours>\d+)\s*(?:hours?|hrs?)\s*(?:and\s*)?)?"
     r"(?:(?P<minutes>\d+)\s*(?:minutes?|mins?)\s*(?:and\s*)?)?(?:(?P<seconds>\d+)\s*(?:seconds?|secs?)\s*)?",
     _timer_params),
    ("cancel_timer",
     r"(?:cancel|stop|clear|remove)\s+(?:the\s+)?timer",
     _empty),

    # ══ COMPOUND / FOLLOW-UP PATTERNS (before open_app!) ═══════════════

    # -- Send message: "send hi to varun on whatsapp" ──────────────────
    ("send_message",
     r"send\s+(?P<message>.+?)\s+to\s+(?P<contact>.+?)\s+(?:on|via|through|in|using)\s+(?P<app>whatsapp|telegram|signal|sms)",
     _msg_app_contact),
    ("send_message",
     r"(?:open\s+)?(?P<app>whatsapp|telegram|signal)\s+(?:and\s+)?send\s+(?P<message>.+?)\s+to\s+(?P<contact>.+)",
     _msg_app_contact),
    ("send_message",
     r"(?:text|message|msg|dm)\s+(?P<contact>.+?)\s+(?:saying|that|with)\s+(?P<message>.+?)(?:\s+(?:on|via)\s+(?P<app>whatsapp|telegram|signal))?$",
     _msg_app_contact),
    # "send hi to +919876543210" — phone number as contact
    ("send_message",
     r"send\s+(?P<message>.+?)\s+to\s+(?P<contact>\+?\d[\d\s\-]{7,})",
     _msg_app_contact),
    ("send_message",
     r"(?P<app>whatsapp|telegram)\s+(?P<contact>.+?)\s+(?:saying\s+)?(?P<message>.{2,})",
     _msg_app_contact),

    # -- Email ─────────────────────────────────────────────────────────
    ("send_email",
     r"(?:send\s+)?(?:an?\s+)?(?:email|mail)\s+(?:to\s+)?(?P<recipient>\S+@\S+)\s+(?:saying|about|with\s+subject|that)\s+(?P<body>.+)",
     _email_params),
    ("send_email",
     r"(?:email|mail)\s+(?P<recipient>\S+@\S+)\s+(?:about\s+)?(?P<body>.+)",
     _email_params),
    ("send_email",
     r"(?:send\s+)?(?:an?\s+)?(?:email|mail)\s+(?:to\s+)?(?P<recipient>[A-Za-z][\w\s]+?)\s+(?:saying|about|with|that)\s+(?P<body>.+)",
     _email_params),

    # -- Play media: "play song on spotify" / "watch video on youtube" ─
    ("play_media",
     r"(?:play|search|watch|find|listen\s+to)\s+(?P<query>.+?)\s+(?:on|in)\s+(?P<platform>youtube|spotify)",
     _media_params),
    ("play_media",
     r"(?:open\s+)?(?P<platform>youtube|spotify)\s+(?:and\s+)?(?:play|search|watch|find|listen)\s+(?P<query>.+)",
     _media_params),

    # -- Add contact ───────────────────────────────────────────────────
    ("add_contact",
     r"(?:add|save|create|new)\s+contact\s+(?P<name>.+?)\s+(?:phone|number|mobile)\s+(?P<phone>\+?\d[\d\s\-]+)",
     _contact_params),
    ("add_contact",
     r"(?:add|save|create|new)\s+contact\s+(?P<name>.+?)\s+(?:email|mail)\s+(?P<email>\S+@\S+)",
     _contact_params),
    ("list_contacts",
     r"(?:show|list|display|see)\s+(?:my\s+)?contacts",
     _empty),

    # -- Open URL: "open google.com" / "go to example.com" ────────────
    ("open_url",
     r"(?:open|go\s+to|visit|browse)\s+(?P<url>(?:https?://)?[\w\-]+\.[\w\-.]+\S*)",
     _url_params),

    # ══ FILE / FOLDER MANAGEMENT ═══════════════════════════════════════

    # -- Create folder ─────────────────────────────────────────────────
    ("create_folder",
     r"(?:create|make|new)\s+(?:a\s+)?(?:folder|directory)\s+(?:named?\s+|called\s+)?(?P<folder>[^\s]+(?:\s+\w+)*?)(?:\s+(?:on|in|at)\s+(?P<location>\w+))?$",
     _folder_params),

    # -- Delete folder ─────────────────────────────────────────────────
    ("delete_folder",
     r"(?:delete|remove)\s+(?:the\s+)?(?:folder|directory)\s+(?:named?\s+|called\s+)?(?P<folder>.+)",
     _folder_params),

    # -- Rename folder ─────────────────────────────────────────────────
    ("rename_folder",
     r"rename\s+(?:the\s+)?(?:folder|directory)\s+(?P<old_name>.+?)\s+to\s+(?P<new_name>.+)",
     _folder_params),

    # -- Open folder ───────────────────────────────────────────────────
    ("open_folder",
     r"(?:open|show|go\s+to)\s+(?:the\s+)?(?:folder|directory)\s+(?P<folder>.+)",
     _folder_params),
    ("open_folder",
     r"(?:open|show|go\s+to)\s+(?:(?:my|the)\s+)?(?P<folder>desktop|documents|downloads|music|pictures|videos|recycle\s*bin|recent\s*files?)",
     _folder_params),

    # -- List files ────────────────────────────────────────────────────
    ("list_files",
     r"(?:list|show|what(?:'s|\s+is)\s+in|what\s+files?\s+(?:are\s+)?in)\s+(?:the\s+)?(?:files?\s+(?:in|on)\s+)?(?:my\s+)?(?P<folder>\w+(?:\s+\w+)*)",
     _folder_params),

    # -- Empty recycle bin ─────────────────────────────────────────────
    ("empty_recycle_bin",
     r"(?:empty|clear|clean)\s+(?:the\s+)?(?:recycle\s*bin|trash|dustbin)",
     _empty),

    # ══ SIMPLE APP / SYSTEM PATTERNS ═══════════════════════════════════

    # -- App control ───────────────────────────────────────────────────
    ("open_app",
     r"(?:^|\b)(?:open|launch|(?<!re)start|run)\s+(?P<app>.+)",
     _app),
    ("close_app",
     r"(?:close|quit|exit|kill|stop)\s+(?P<app>.+)",
     _app),

    # -- Power control ─────────────────────────────────────────────────
    ("cancel_shutdown",
     r"(?:cancel|abort|stop)\s+(?:the\s+)?(?:shut\s*down|restart|reboot)",
     _empty),
    ("shutdown",
     r"(?:shut\s*down|power\s+off|turn\s+off\s+(?:the\s+)?(?:pc|computer|system))",
     _empty),
    ("restart",
     r"\b(?:restart|reboot)(?:\s+(?:the\s+)?(?:pc|computer|system))?\s*$",
     _empty),
    ("lock_pc",
     r"\block\b(?:\s+(?:the\s+)?(?:pc|computer|screen|system))?",
     _empty),
    ("sleep_pc",
     r"\bsleep\b(?:\s+(?:the\s+)?(?:pc|computer|system))?|put.+\bto\s+sleep\b|\bsuspend\b(?:\s+(?:the\s+)?(?:pc|computer))?",
     _empty),
    ("hibernate_pc",
     r"\bhibernate\b(?:\s+(?:the\s+)?(?:pc|computer))?",
     _empty),

    # -- Network ───────────────────────────────────────────────────────
    ("wifi_on",
     r"(?:turn\s+on|enable|connect|switch\s+on)\s+(?:the\s+)?wi[\s\-]?fi|wi[\s\-]?fi\s+(?:turn\s+)?on",
     _empty),
    ("wifi_off",
     r"(?:turn\s+off|disable|disconnect|switch\s+off)\s+(?:the\s+)?(?:wi[\s\-]?fi|wifi)|wi[\s\-]?fi\s+(?:turn\s+)?off",
     _empty),
    ("wifi_status",
     r"(?:wi[\s\-]?fi\s+status|(?:am\s+i|are\s+we)\s+connected|what(?:'s|\s+is)\s+(?:my\s+)?wi[\s\-]?fi)",
     _empty),
    ("bluetooth_on",
     r"(?:turn\s+on|enable|connect|switch\s+on)\s+(?:the\s+)?bluetooth|bluetooth\s+(?:turn\s+)?on",
     _empty),
    ("bluetooth_off",
     r"(?:turn\s+off|disable|disconnect|switch\s+off)\s+(?:the\s+)?bluetooth|bluetooth\s+(?:turn\s+)?off",
     _empty),
    # -- Quick Settings: Night Light, Airplane, Energy Saver, Hotspot ──
    ("night_light_on",
     r"(?:turn\s+on|enable|switch\s+on)\s+(?:the\s+)?night\s*light|night\s*light\s+(?:turn\s+)?on",
     _empty),
    ("night_light_off",
     r"(?:turn\s+off|disable|switch\s+off)\s+(?:the\s+)?night\s*light|night\s*light\s+(?:turn\s+)?off",
     _empty),
    ("airplane_mode_on",
     r"(?:turn\s+on|enable|switch\s+on)\s+(?:the\s+)?(?:airplane|aeroplane|flight)\s*mode|(?:airplane|aeroplane|flight)\s*mode\s+(?:turn\s+)?on",
     _empty),
    ("airplane_mode_off",
     r"(?:turn\s+off|disable|switch\s+off)\s+(?:the\s+)?(?:airplane|aeroplane|flight)\s*mode|(?:airplane|aeroplane|flight)\s*mode\s+(?:turn\s+)?off",
     _empty),
    ("energy_saver_on",
     r"(?:turn\s+on|enable|switch\s+on)\s+(?:the\s+)?(?:energy|battery)\s*saver|(?:energy|battery)\s*saver\s+(?:turn\s+)?on",
     _empty),
    ("energy_saver_off",
     r"(?:turn\s+off|disable|switch\s+off)\s+(?:the\s+)?(?:energy|battery)\s*saver|(?:energy|battery)\s*saver\s+(?:turn\s+)?off",
     _empty),
    ("hotspot_on",
     r"(?:turn\s+on|enable|switch\s+on)\s+(?:the\s+)?(?:mobile\s+)?hotspot|(?:mobile\s+)?hotspot\s+(?:turn\s+)?on",
     _empty),
    ("hotspot_off",
     r"(?:turn\s+off|disable|switch\s+off)\s+(?:the\s+)?(?:mobile\s+)?hotspot|(?:mobile\s+)?hotspot\s+(?:turn\s+)?off",
     _empty),
    # -- Clipboard (before ip_address — "clipboard" contains "ip") ────
    ("read_clipboard",
     r"(?:read|show|what(?:'s|\s+is)\s+(?:on|in)\s+(?:the\s+)?|paste)\s*(?:the\s+)?clipboard",
     _empty),
    ("clear_clipboard",
     r"(?:clear|empty|wipe)\s+(?:the\s+)?clipboard",
     _empty),

    # -- System info ───────────────────────────────────────────────────
    ("battery_status",
     r"(?:battery|charge|power)\s+(?:status|level|percentage|left|remaining)|(?:battery|charge)\s*$|how\s+much\s+(?:battery|charge|power)|check\s+(?:the\s+)?battery",
     _empty),
    ("ip_address",
     r"(?:what(?:'s|\s+is)\s+)?(?:my\s+)?\bip\b\s*(?:address)?|show\s+(?:my\s+)?\bip\b",
     _empty),
    ("screenshot",
     r"(?:take|capture|grab)\s+(?:a\s+)?(?:screen\s*shot|screen\s*cap|snip)",
     _empty),

    # -- Web search ────────────────────────────────────────────────────
    ("search_web",
     r"(?:search|google|look\s+up|find\s+(?:online|on\s+the\s+web))\s+(?:for\s+|the\s+web\s+for\s+)?(?P<query>.+)",
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


# ══════════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════════

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
