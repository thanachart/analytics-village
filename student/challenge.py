"""
Analytics Village — Challenge class (main student entry point).
"""
from __future__ import annotations

import os

from .db import DatabaseProxy
from .owner import Owner
from .loader import find_challenge_files, download_challenge
from .display import format_brief


class Challenge:
    """
    Main entry point for student interaction.
    Load once per session. Provides access to DB, owner, and submission tools.

    Usage:
        ch = Challenge.load("ch01")
        ch.brief()
        ch.db.tables()
        ch.owner.questions()
    """

    def __init__(
        self,
        challenge_id: str,
        db_path: str,
        qa_path: str | None = None,
        brief_path: str | None = None,
        schema_path: str | None = None,
        primary_business: str = "supermarket",
    ):
        self._challenge_id = challenge_id
        self._db_path = db_path
        self._qa_path = qa_path
        self._brief_path = brief_path
        self._schema_path = schema_path
        self._primary_business = primary_business

        self._db = DatabaseProxy(db_path, primary_business=primary_business)
        self._owner = Owner.from_json(qa_path) if qa_path else None

    @classmethod
    def load(
        cls,
        challenge_id: str,
        *,
        data_dir: str = None,
        github_repo: str = "thanachart/analytics-village",
        force_download: bool = False,
        primary_business: str = "supermarket",
        db_name: str = None,
    ) -> Challenge:
        """
        Load a challenge by ID.

        Parameters:
            db_name: Choose database: 'village_normalized.db' (default) or 'village_star.db'

        Examples:
            ch = Challenge.load("ch01", data_dir="challenges/ch01/data")
            ch = Challenge.load("ch01", data_dir="challenges/ch01/data", db_name="village_star.db")
        """
        if force_download:
            files = download_challenge(challenge_id, github_repo, data_dir, force=True)
        else:
            files = find_challenge_files(challenge_id, data_dir)
            if "db" not in files:
                files = download_challenge(challenge_id, github_repo, data_dir)

        # If specific db_name requested, look for it in data_dir
        if db_name and data_dir:
            import os
            specific = os.path.join(data_dir, db_name)
            if os.path.exists(specific):
                files["db"] = specific

        if "db" not in files:
            raise FileNotFoundError(
                f"Could not find database for challenge '{challenge_id}'.\n"
                f"Searched in: {data_dir or 'current directory and cache'}\n"
                f"Try: Challenge.load('{challenge_id}', data_dir='challenges/{challenge_id}/data')"
            )

        ch = cls(
            challenge_id=challenge_id,
            db_path=files["db"],
            qa_path=files.get("qa"),
            brief_path=files.get("brief"),
            schema_path=files.get("schema"),
            primary_business=primary_business,
        )

        # Print summary
        db_size = os.path.getsize(files["db"]) / (1024 * 1024)
        sku_count = len(ch.db.query("SELECT sku_id FROM skus"))
        hh_count = len(ch.db.query("SELECT household_id FROM households"))
        day_range = ch.db.query("SELECT MIN(day) AS mn, MAX(day) AS mx FROM transactions")
        days = "?"
        if len(day_range) > 0:
            mn, mx = day_range.iloc[0]["mn"], day_range.iloc[0]["mx"]
            days = f"{mn} to {mx}" if mn is not None else "?"

        print(f"+ Loaded challenge: {challenge_id.upper()}")
        print(f"+ Database: {db_size:.1f} MB | {sku_count} SKUs | {hh_count} households | days {days}")
        if ch._owner:
            print(f"+ Owner: {ch._owner._owner_name} | {len(ch._owner._qa)} questions available")
        print(f"Ready. Start with: ch.brief()  or  ch.db.tables()")

        return ch

    def brief(self) -> None:
        """Display the challenge brief."""
        if self._brief_path and os.path.exists(self._brief_path):
            with open(self._brief_path, encoding="utf-8") as f:
                text = f.read()
            result = format_brief(text)
            if result:
                print(result)
        else:
            print(f"No brief available for {self._challenge_id}.")
            print("Start exploring with: ch.db.tables()")

    @property
    def db(self) -> DatabaseProxy:
        """Access to the challenge database."""
        return self._db

    @property
    def owner(self) -> Owner:
        """Access to the simulated business owner."""
        if not self._owner:
            raise ValueError("No Q&A data available for this challenge.")
        return self._owner

    @property
    def db_path(self) -> str:
        return os.path.abspath(self._db_path)

    @property
    def qa_path(self) -> str | None:
        return os.path.abspath(self._qa_path) if self._qa_path else None

    @property
    def schema(self) -> dict | None:
        if self._schema_path and os.path.exists(self._schema_path):
            import json
            with open(self._schema_path) as f:
                return json.load(f)
        return None

    def status(self) -> None:
        """Display current challenge status."""
        print(f"\nChallenge: {self._challenge_id.upper()}")
        print(f"Business: {self._primary_business}")
        if self._owner:
            asked = len(self._owner.questions_asked)
            total = len(self._owner._qa)
            print(f"Questions asked: {asked}/{total}")
        txn_count = self.db.query("SELECT COUNT(*) AS n FROM transactions").iloc[0]["n"]
        print(f"Transactions in DB: {txn_count:,}")
