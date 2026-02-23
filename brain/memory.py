"""
Nova Voice Assistant — Memory Module
Persistent note storage backed by SQLite.
"""

import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from config import DB_PATH
from utils.logger import get_logger

log = get_logger(__name__)


class Memory:
    """
    Simple key‑value note store using SQLite.

    Thread‑safe: every public method acquires a lock before touching the
    database connection.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    # ── Connection ────────────────────────────────────────────────────────

    def _connect(self) -> None:
        try:
            self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    content     TEXT    NOT NULL,
                    created_at  TEXT    NOT NULL
                );
                """
            )
            self._conn.commit()
            log.info("Memory database ready at %s", DB_PATH)
        except sqlite3.Error:
            log.exception("Failed to initialise memory database")
            self._conn = None

    # ── Public API ────────────────────────────────────────────────────────

    def save_note(self, content: str) -> bool:
        """
        Persist *content* as a note.  Returns True on success.
        """
        if not content:
            return False
        with self._lock:
            if self._conn is None:
                log.error("Memory DB not available")
                return False
            try:
                now = datetime.now(timezone.utc).isoformat()
                self._conn.execute(
                    "INSERT INTO notes (content, created_at) VALUES (?, ?)",
                    (content.strip(), now),
                )
                self._conn.commit()
                log.info("Note saved: %s", content.strip()[:80])
                return True
            except sqlite3.Error:
                log.exception("Failed to save note")
                return False

    def recall_notes(self, limit: int = 5) -> List[Tuple[str, str]]:
        """
        Return up to *limit* most recent notes as ``(content, created_at)`` tuples.
        """
        with self._lock:
            if self._conn is None:
                log.error("Memory DB not available")
                return []
            try:
                cursor = self._conn.execute(
                    "SELECT content, created_at FROM notes ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                log.info("Recalled %d note(s)", len(rows))
                return rows
            except sqlite3.Error:
                log.exception("Failed to recall notes")
                return []

    def clear_notes(self) -> bool:
        """Delete all notes."""
        with self._lock:
            if self._conn is None:
                return False
            try:
                self._conn.execute("DELETE FROM notes")
                self._conn.commit()
                log.info("All notes cleared")
                return True
            except sqlite3.Error:
                log.exception("Failed to clear notes")
                return False

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                log.info("Memory database closed")
