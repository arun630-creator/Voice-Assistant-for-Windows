"""
Nova Voice Assistant — Browser Control
Web search and URL launching.
"""

import subprocess
import urllib.parse
import webbrowser
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)

# Default search engine template (DuckDuckGo — no tracking)
_SEARCH_URL = "https://duckduckgo.com/?q={query}"


class BrowserControl:
    """Open URLs and perform web searches in the default browser."""

    # ── Public API ────────────────────────────────────────────────────────

    @staticmethod
    def search_web(query: str) -> str:
        """
        Open a web search for *query* in the default browser.

        Returns a human‑readable confirmation string.
        """
        if not query or not query.strip():
            return "I didn't catch what to search for."

        encoded = urllib.parse.quote_plus(query.strip())
        url = _SEARCH_URL.format(query=encoded)
        log.info("Web search: '%s' → %s", query, url)

        try:
            webbrowser.open(url)
            return f"Searching the web for {query}."
        except Exception as exc:
            log.error("webbrowser.open failed: %s — trying fallback", exc)

        # Fallback: use start command
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", url],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Searching the web for {query}."
        except OSError as exc2:
            log.error("Fallback browser open failed: %s", exc2)
            return "Failed to open the browser for your search."

    @staticmethod
    def open_url(url: str) -> str:
        """Open *url* directly in the default browser."""
        if not url:
            return "No URL provided."
        log.info("Opening URL: %s", url)
        try:
            webbrowser.open(url)
            return f"Opening {url}."
        except Exception as exc:
            log.error("Failed to open URL %s: %s", url, exc)
            return f"Failed to open {url}."
