"""
Analytics Village — Database wrapper for village.db.
Provides convenient CRUD + bulk insert over SQLite.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .schema import VILLAGE_DDL


class VillageDB:
    """SQLite wrapper with WAL mode, Row factory, and bulk helpers."""

    def __init__(self, path: str, *, read_only: bool = False):
        if read_only:
            uri = f"file:{path}?mode=ro"
            self._conn = sqlite3.connect(uri, uri=True)
        else:
            self._conn = sqlite3.connect(path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self.path = path

    # ── Context manager ──────────────────────────────────────────

    def __enter__(self) -> VillageDB:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ── Core operations ──────────────────────────────────────────

    def execute(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, rows: list[tuple]) -> sqlite3.Cursor:
        return self._conn.executemany(sql, rows)

    def executescript(self, sql: str) -> None:
        self._conn.executescript(sql)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()

    # ── Query helpers ────────────────────────────────────────────

    def fetchone(self, sql: str, params: tuple | dict = ()) -> dict | None:
        row = self._conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple | dict = ()) -> list[dict]:
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def count(self, table: str) -> int:
        row = self._conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
        return row["n"] if row else 0

    # ── Insert helpers ───────────────────────────────────────────

    def insert(self, table: str, row: dict[str, Any]) -> int:
        cols = list(row.keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        cur = self._conn.execute(sql, [row[c] for c in cols])
        return cur.lastrowid

    def insert_many(self, table: str, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        cols = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        data = [[r[c] for c in cols] for r in rows]
        self._conn.executemany(sql, data)
        return len(data)

    def upsert(self, table: str, row: dict[str, Any], key_col: str) -> None:
        cols = list(row.keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != key_col)
        sql = (
            f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
            f"ON CONFLICT({key_col}) DO UPDATE SET {updates}"
        )
        self._conn.execute(sql, [row[c] for c in cols])

    # ── Metadata ─────────────────────────────────────────────────

    def get_meta(self, key: str) -> str | None:
        row = self.fetchone(
            "SELECT value FROM _simulation_meta WHERE key = ?", (key,)
        )
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.upsert("_simulation_meta", {"key": key, "value": value}, "key")

    def get_meta_json(self, key: str) -> Any:
        raw = self.get_meta(key)
        return json.loads(raw) if raw else None

    def set_meta_json(self, key: str, value: Any) -> None:
        self.set_meta(key, json.dumps(value, ensure_ascii=False))

    # ── Schema management ────────────────────────────────────────

    def init_schema(self) -> None:
        """Create all tables if they don't exist."""
        self._conn.executescript(VILLAGE_DDL)
        self._conn.commit()

    def table_names(self, include_hidden: bool = False) -> list[str]:
        rows = self.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        names = [r["name"] for r in rows]
        if not include_hidden:
            names = [n for n in names if not n.startswith("_")]
        return names

    def table_row_counts(self, include_hidden: bool = False) -> dict[str, int]:
        return {
            t: self.count(t)
            for t in self.table_names(include_hidden=include_hidden)
        }

    # ── Batch transaction support ────────────────────────────────

    def begin(self) -> None:
        self._conn.execute("BEGIN")

    def rollback(self) -> None:
        self._conn.rollback()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn
