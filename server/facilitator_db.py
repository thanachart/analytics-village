"""Analytics Village — Facilitator database (facilitator.db)."""
from __future__ import annotations

import sqlite3
import json
from datetime import datetime


FACILITATOR_DDL = """
CREATE TABLE IF NOT EXISTS episodes (
    episode_id       TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    episode_number   INTEGER NOT NULL,
    primary_business TEXT NOT NULL DEFAULT 'supermarket',
    tier             INTEGER NOT NULL DEFAULT 1,
    challenge_type   TEXT NOT NULL DEFAULT 'reporting',
    status           TEXT NOT NULL DEFAULT 'draft',
    config_json      TEXT,
    village_db_path  TEXT,
    qa_json_path     TEXT,
    brief_md_path    TEXT,
    notebook_path    TEXT,
    github_release_url TEXT,
    submission_deadline TEXT,
    scoring_rubric   TEXT,
    max_score        INTEGER NOT NULL DEFAULT 100,
    notes            TEXT,
    created_at       TEXT NOT NULL,
    published_at     TEXT,
    closed_at        TEXT,
    archived_at      TEXT
);

CREATE TABLE IF NOT EXISTS submissions (
    submission_id    TEXT PRIMARY KEY,
    episode_id       TEXT NOT NULL,
    student_id       TEXT NOT NULL,
    team_id          TEXT,
    submitted_at     TEXT NOT NULL,
    decision_json    TEXT NOT NULL,
    validation_status TEXT NOT NULL DEFAULT 'pending',
    validation_errors TEXT,
    auto_score       REAL,
    manual_score     REAL,
    final_score      REAL,
    score_breakdown  TEXT,
    instructor_feedback TEXT,
    outcome_run      INTEGER NOT NULL DEFAULT 0,
    published_to_board INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scoreboard (
    entry_id         TEXT PRIMARY KEY,
    episode_id       TEXT NOT NULL,
    student_id       TEXT NOT NULL,
    display_name     TEXT NOT NULL,
    final_score      REAL NOT NULL,
    rank             INTEGER NOT NULL,
    score_breakdown  TEXT,
    outcome_summary  TEXT,
    published_at     TEXT NOT NULL,
    is_visible       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS instructor_prefs (
    pref_key    TEXT PRIMARY KEY,
    pref_value  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


class FacilitatorDB:
    """Wrapper for facilitator.db."""

    def __init__(self, path: str = "facilitator.db"):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(FACILITATOR_DDL)
        self._conn.commit()

    def close(self):
        self._conn.commit()
        self._conn.close()

    def fetchone(self, sql, params=()):
        row = self._conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql, params=()):
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def execute(self, sql, params=()):
        self._conn.execute(sql, params)
        self._conn.commit()

    # ── Episodes ─────────────────────────────────────────────

    def create_episode(self, data: dict) -> dict:
        now = datetime.utcnow().isoformat()
        ep = {
            "episode_id": data.get("episode_id", f"ep{data.get('episode_number', 1):02d}"),
            "title": data["title"],
            "episode_number": data.get("episode_number", 1),
            "primary_business": data.get("primary_business", "supermarket"),
            "tier": data.get("tier", 1),
            "challenge_type": data.get("challenge_type", "reporting"),
            "status": "draft",
            "config_json": json.dumps(data),
            "village_db_path": data.get("village_db_path"),
            "created_at": now,
        }
        cols = ", ".join(ep.keys())
        placeholders = ", ".join(["?"] * len(ep))
        self._conn.execute(
            f"INSERT OR REPLACE INTO episodes ({cols}) VALUES ({placeholders})",
            list(ep.values())
        )
        self._conn.commit()
        return ep

    def get_episode(self, episode_id: str) -> dict | None:
        return self.fetchone("SELECT * FROM episodes WHERE episode_id = ?", (episode_id,))

    def list_episodes(self, status: str = None) -> list[dict]:
        if status:
            return self.fetchall(
                "SELECT * FROM episodes WHERE status = ? ORDER BY created_at DESC", (status,)
            )
        return self.fetchall("SELECT * FROM episodes ORDER BY created_at DESC")

    def update_episode_status(self, episode_id: str, status: str) -> None:
        now = datetime.utcnow().isoformat()
        field_map = {"active": "published_at", "closed": "closed_at", "archived": "archived_at"}
        extra = ""
        if status in field_map:
            extra = f", {field_map[status]} = '{now}'"
        self.execute(
            f"UPDATE episodes SET status = ?{extra} WHERE episode_id = ?",
            (status, episode_id)
        )

    # ── Submissions ──────────────────────────────────────────

    def create_submission(self, data: dict) -> dict:
        now = datetime.utcnow().isoformat()
        sub_id = f"sub_{data['episode_id']}_{data['student_id']}_{now[:10]}"
        self._conn.execute(
            "INSERT OR REPLACE INTO submissions "
            "(submission_id, episode_id, student_id, team_id, submitted_at, "
            "decision_json, validation_status) VALUES (?,?,?,?,?,?,?)",
            (sub_id, data["episode_id"], data["student_id"],
             data.get("team_id"), now,
             json.dumps(data.get("decision_json", {})), "valid")
        )
        self._conn.commit()
        return {"submission_id": sub_id, "status": "accepted"}

    def list_submissions(self, episode_id: str = None) -> list[dict]:
        if episode_id:
            return self.fetchall(
                "SELECT * FROM submissions WHERE episode_id = ? ORDER BY submitted_at DESC",
                (episode_id,)
            )
        return self.fetchall("SELECT * FROM submissions ORDER BY submitted_at DESC")

    def get_submission(self, submission_id: str) -> dict | None:
        return self.fetchone("SELECT * FROM submissions WHERE submission_id = ?", (submission_id,))

    def update_submission_score(
        self, submission_id: str, auto_score: float = None,
        manual_score: float = None, feedback: str = None,
    ) -> None:
        parts = []
        params = []
        if auto_score is not None:
            parts.append("auto_score = ?")
            params.append(auto_score)
        if manual_score is not None:
            parts.append("manual_score = ?")
            params.append(manual_score)
        if feedback is not None:
            parts.append("instructor_feedback = ?")
            params.append(feedback)
        # Compute final
        final = manual_score if manual_score is not None else auto_score
        if final is not None:
            parts.append("final_score = ?")
            params.append(final)
        if parts:
            params.append(submission_id)
            self.execute(
                f"UPDATE submissions SET {', '.join(parts)} WHERE submission_id = ?",
                tuple(params)
            )

    # ── Preferences ──────────────────────────────────────────

    def get_pref(self, key: str) -> str | None:
        row = self.fetchone("SELECT pref_value FROM instructor_prefs WHERE pref_key = ?", (key,))
        return row["pref_value"] if row else None

    def set_pref(self, key: str, value: str) -> None:
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO instructor_prefs (pref_key, pref_value, updated_at) "
            "VALUES (?, ?, ?)", (key, value, now)
        )
        self._conn.commit()
