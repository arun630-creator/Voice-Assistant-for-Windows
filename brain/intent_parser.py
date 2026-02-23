"""
Nova Voice Assistant — Intent Parser
Validates and normalises the JSON output from the LLM.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from config import SUPPORTED_INTENTS
from utils.helpers import safe_json_parse
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class Intent:
    """Immutable representation of a parsed intent."""

    intent: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""

    @property
    def is_valid(self) -> bool:
        return self.intent in SUPPORTED_INTENTS

    def __str__(self) -> str:
        return f"Intent({self.intent}, params={self.parameters})"


class IntentParser:
    """
    Parses raw LLM output into a validated :class:`Intent`.

    If the LLM returns garbage or an unsupported intent the parser
    falls back to ``unknown``.
    """

    # ── Public API ────────────────────────────────────────────────────────

    @staticmethod
    def parse(raw_llm_output: Optional[str], original_text: str = "") -> Intent:
        """
        Parse *raw_llm_output* and return a validated :class:`Intent`.

        Parameters
        ----------
        raw_llm_output:
            The raw string returned by the LLM.
        original_text:
            The user's original spoken text (used as fallback context).
        """
        if raw_llm_output is None:
            log.warning("LLM returned None — defaulting to 'unknown'")
            return Intent(intent="unknown", parameters={"raw": original_text}, raw_text=original_text)

        parsed = safe_json_parse(raw_llm_output)
        if parsed is None:
            log.warning("Invalid JSON from LLM — defaulting to 'unknown'")
            return Intent(intent="unknown", parameters={"raw": original_text}, raw_text=original_text)

        intent_name = str(parsed.get("intent", "unknown")).lower().strip()
        parameters = parsed.get("parameters", {})

        if not isinstance(parameters, dict):
            log.warning("'parameters' is not a dict — resetting")
            parameters = {}

        if intent_name not in SUPPORTED_INTENTS:
            log.warning("Unsupported intent '%s' — mapping to 'unknown'", intent_name)
            intent_name = "unknown"
            parameters["raw"] = original_text

        log.info("Parsed intent: %s | params: %s", intent_name, parameters)
        return Intent(intent=intent_name, parameters=parameters, raw_text=original_text)
