"""Tiny SQLite key-value cache so re-evaluating the same page/answer is instant."""
import hashlib
import json
import sqlite3
import threading

from app.config import get_settings

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(get_settings().storage_dir / "cache.db", check_same_thread=False)
        _conn.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
    return _conn


def key(*parts: str | bytes) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else p.encode())
        h.update(b"\x00")
    return h.hexdigest()


def get(k: str):
    with _lock:
        row = _db().execute("SELECT v FROM kv WHERE k = ?", (k,)).fetchone()
    return json.loads(row[0]) if row else None


def put(k: str, value) -> None:
    with _lock:
        _db().execute("INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)", (k, json.dumps(value)))
        _db().commit()
