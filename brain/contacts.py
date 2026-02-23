"""
Nova Voice Assistant — Contact Book
JSON-backed contact manager with fuzzy name matching.
"""

import difflib
import json
import os
import re
import threading
from typing import Any, Dict, List, Optional

from config import DATA_DIR
from utils.logger import get_logger

log = get_logger(__name__)

CONTACTS_FILE = DATA_DIR / "contacts.json"
_FUZZY_THRESHOLD = 0.55


class ContactBook:
    """Thread-safe contact manager backed by a JSON file."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._contacts: List[Dict[str, str]] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load(self) -> None:
        if not CONTACTS_FILE.exists():
            self._save()  # create empty file
            return
        try:
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._contacts = data.get("contacts", [])
            log.info("Loaded %d contact(s) from %s", len(self._contacts), CONTACTS_FILE)
        except (json.JSONDecodeError, OSError) as exc:
            log.error("Failed to load contacts: %s", exc)
            self._contacts = []

    def _save(self) -> None:
        try:
            with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
                json.dump({"contacts": self._contacts}, f, indent=4, ensure_ascii=False)
        except OSError as exc:
            log.error("Failed to save contacts: %s", exc)

    # ── Public API ────────────────────────────────────────────────────────

    def find(self, name: str) -> Optional[Dict[str, str]]:
        """
        Find a contact by name using exact then fuzzy matching.

        Returns the contact dict or ``None``.
        """
        normalised = name.strip().lower()
        with self._lock:
            # 1. Exact match
            for c in self._contacts:
                if c["name"].lower() == normalised:
                    return dict(c)

            # 2. Substring / starts-with
            for c in self._contacts:
                cn = c["name"].lower()
                if cn.startswith(normalised) or normalised.startswith(cn):
                    log.info("Prefix contact match: '%s' → '%s'", name, c["name"])
                    return dict(c)

            # 3. Fuzzy match
            best_score = 0.0
            best_contact = None
            for c in self._contacts:
                score = difflib.SequenceMatcher(
                    None, normalised, c["name"].lower()
                ).ratio()
                if score > best_score:
                    best_score = score
                    best_contact = c

            if best_contact and best_score >= _FUZZY_THRESHOLD:
                log.info(
                    "Fuzzy contact match: '%s' → '%s' [score=%.2f]",
                    name, best_contact["name"], best_score,
                )
                return dict(best_contact)

        log.debug("No contact match for '%s'", name)
        return None

    def add(self, name: str, phone: str = "", email: str = "") -> str:
        """Add a new contact. Returns a confirmation message."""
        normalised = name.strip().lower()
        with self._lock:
            # Check for duplicate
            for c in self._contacts:
                if c["name"].lower() == normalised:
                    # Update existing
                    if phone:
                        c["phone"] = phone
                    if email:
                        c["email"] = email
                    self._save()
                    return f"Updated contact {name}."

            entry = {"name": name.strip(), "phone": phone.strip(), "email": email.strip()}
            self._contacts.append(entry)
            self._save()
            log.info("Contact added: %s", entry)
            return f"Contact {name} added successfully."

    def remove(self, name: str) -> str:
        """Remove a contact by name. Returns a confirmation message."""
        normalised = name.strip().lower()
        with self._lock:
            before = len(self._contacts)
            self._contacts = [
                c for c in self._contacts if c["name"].lower() != normalised
            ]
            if len(self._contacts) < before:
                self._save()
                return f"Contact {name} removed."
            return f"No contact named {name} found."

    def list_all(self) -> List[Dict[str, str]]:
        """Return a copy of all contacts."""
        with self._lock:
            return [dict(c) for c in self._contacts]
