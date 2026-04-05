"""
Analytics Village — Episode class (main student entry point).
"""
from __future__ import annotations

import os

from .db import DatabaseProxy
from .owner import Owner
from .loader import find_episode_files, download_episode
from .display import format_brief


class Episode:
    """
    Main entry point for student interaction.
    Load once per session. Provides access to DB, owner, and submission tools.
    """

    def __init__(
        self,
        episode_id: str,
        db_path: str,
        qa_path: str | None = None,
        brief_path: str | None = None,
        schema_path: str | None = None,
        primary_business: str = "supermarket",
    ):
        self._episode_id = episode_id
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
        episode_id: str,
        *,
        data_dir: str = None,
        github_repo: str = "analytics-village",
        force_download: bool = False,
        primary_business: str = "supermarket",
    ) -> Episode:
        """
        Load an episode by ID. Downloads from GitHub if not cached locally.

        Examples:
            ep = Episode.load("ep01")
            ep = Episode.load("ep03", primary_business="pharmacy")
        """
        # Find or download files
        if force_download:
            files = download_episode(episode_id, github_repo, data_dir, force=True)
        else:
            files = find_episode_files(episode_id, data_dir)
            if "db" not in files:
                files = download_episode(episode_id, github_repo, data_dir)

        if "db" not in files:
            raise FileNotFoundError(
                f"Could not find database for episode '{episode_id}'.\n"
                f"Searched in: {data_dir or 'current directory and cache'}\n"
                f"Try: Episode.load('{episode_id}', data_dir='/path/to/files')"
            )

        ep = cls(
            episode_id=episode_id,
            db_path=files["db"],
            qa_path=files.get("qa"),
            brief_path=files.get("brief"),
            schema_path=files.get("schema"),
            primary_business=primary_business,
        )

        # Print summary
        db_size = os.path.getsize(files["db"]) / (1024 * 1024)
        sku_count = len(ep.db.query("SELECT sku_id FROM skus"))
        hh_count = len(ep.db.query("SELECT household_id FROM households"))
        day_range = ep.db.query("SELECT MIN(day) AS mn, MAX(day) AS mx FROM transactions")
        days = "?"
        if len(day_range) > 0:
            mn, mx = day_range.iloc[0]["mn"], day_range.iloc[0]["mx"]
            days = f"{mn} to {mx}" if mn is not None else "?"

        print(f"+ Found episode: {episode_id.upper()}")
        print(f"+ Database: {db_size:.1f} MB | {sku_count} SKUs | {hh_count} households | days {days}")
        if ep._owner:
            total_q = len(ep._owner._qa)
            print(f"+ Owner: {ep._owner._owner_name} | {total_q} questions available")
        print(f"Ready. Start with: ep.brief()  or  ep.db.tables()")

        return ep

    def brief(self) -> None:
        """Display the episode brief."""
        if self._brief_path and os.path.exists(self._brief_path):
            with open(self._brief_path, encoding="utf-8") as f:
                text = f.read()
            result = format_brief(text)
            if result:
                print(result)
        else:
            print(f"No brief available for {self._episode_id}.")
            print("Start exploring with: ep.db.tables()")

    @property
    def db(self) -> DatabaseProxy:
        """Access to the episode database."""
        return self._db

    @property
    def owner(self) -> Owner:
        """Access to the simulated business owner."""
        if not self._owner:
            raise ValueError("No Q&A data available for this episode.")
        return self._owner

    @property
    def db_path(self) -> str:
        """Absolute path to the local SQLite file."""
        return os.path.abspath(self._db_path)

    @property
    def qa_path(self) -> str | None:
        """Absolute path to the raw qa.json file."""
        return os.path.abspath(self._qa_path) if self._qa_path else None

    @property
    def schema(self) -> dict | None:
        """Submission schema for this episode."""
        if self._schema_path and os.path.exists(self._schema_path):
            import json
            with open(self._schema_path) as f:
                return json.load(f)
        return None

    def status(self) -> None:
        """Display current episode status."""
        print(f"\nEpisode: {self._episode_id.upper()}")
        print(f"Business: {self._primary_business}")
        if self._owner:
            asked = len(self._owner.questions_asked)
            total = len(self._owner._qa)
            print(f"Questions asked: {asked}/{total}")
        txn_count = self.db.query("SELECT COUNT(*) AS n FROM transactions").iloc[0]["n"]
        print(f"Transactions in DB: {txn_count:,}")
