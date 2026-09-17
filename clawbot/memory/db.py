"""
Local-first persistence: conversation history + freeform memory notes,
stored in a single SQLite file (no server required, matches Clawbot's
local-first philosophy).
"""
from __future__ import annotations
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


class Memory:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    ts REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    ts REAL NOT NULL
                )
            """)

    # --- conversation history ---
    def add_message(self, channel: str, role: str, content: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (channel, role, content, ts) VALUES (?, ?, ?, ?)",
                (channel, role, content, time.time()),
            )

    def recent_history(self, channel: str, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE channel = ? "
                "ORDER BY id DESC LIMIT ?",
                (channel, limit),
            ).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    # --- freeform key/value notes (agent's long-term memory) ---
    def remember(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO notes (key, value, ts) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, ts = excluded.ts",
                (key, value, time.time()),
            )

    def recall(self, key: str) -> str | None:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM notes WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def all_notes(self) -> dict[str, str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT key, value FROM notes").fetchall()
        return dict(rows)
