from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any


class Cache:
    """Small SQLite key/value cache with a time-to-live per entry.

    Every external search costs money or quota, so identical requests inside
    the TTL are answered from here.
    """

    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires REAL NOT NULL)"
        )
        self._db.commit()

    def get(self, key: str) -> Any | None:
        with self._lock:
            row = self._db.execute("SELECT value, expires FROM cache WHERE key = ?", (key,)).fetchone()
        if row is None or row[1] < time.time():
            return None
        return json.loads(row[0])

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time() + ttl_seconds),
            )
            self._db.commit()
