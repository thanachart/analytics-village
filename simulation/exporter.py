"""
Analytics Village — Episode Exporter (Phase 5).
Packages simulation output into student-facing files.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .database import VillageDB
    from .world import SimConfig


class EpisodeExporter:
    """Packages simulation output for student release."""

    def __init__(self, source_db_path: str, config: SimConfig):
        self.source_db = source_db_path
        self.config = config

    def write_student_db(self, output_path: str) -> str:
        """
        Create filtered SQLite for students.
        Strips hidden fields, keeps all standard tables.
        """
        # Copy full DB (skip if same file)
        src = os.path.abspath(self.source_db)
        dst = os.path.abspath(output_path)
        if src != dst:
            shutil.copy2(self.source_db, output_path)

        conn = sqlite3.connect(output_path)
        cur = conn.cursor()

        # Strip hidden owner fields
        cur.execute("UPDATE owners SET hidden_goal = NULL, llm_persona_prompt = NULL")

        # Remove simulation metadata
        cur.execute("DROP TABLE IF EXISTS _simulation_meta")

        # Remove anomaly log (unless EP08)
        if self.config.episode_number != 8:
            cur.execute("DROP TABLE IF EXISTS _anomaly_log")

        # Vacuum to reclaim space
        conn.commit()
        cur.execute("VACUUM")
        conn.close()

        return output_path

    def write_qa_json(
        self,
        qa_pairs: list[dict],
        output_path: str,
        *,
        include_truth: bool = False,
    ) -> str:
        """
        Write Q&A JSON file.
        Student version strips data_truth, teaching_note, instructor_hint.
        """
        output = {
            "schema_version": "1.0",
            "episode_id": self.config.episode_id,
            "episode_number": self.config.episode_number,
            "total_questions": len(qa_pairs),
            "questions": [],
        }

        for qa in qa_pairs:
            entry = {
                "question_id": qa["question_id"],
                "category": qa["category"],
                "difficulty": qa["difficulty"],
                "question": qa["question"],
                "answer": qa["answer"],
            }
            if include_truth:
                entry["data_truth"] = qa.get("data_truth", {})
                entry["teaching_note"] = qa.get("teaching_note", "")
            output["questions"].append(entry)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        return output_path

    def write_brief(self, output_path: str, brief_text: str = None) -> str:
        """Write episode brief markdown."""
        if not brief_text:
            brief_text = self._generate_default_brief()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(brief_text)

        return output_path

    def write_schema_json(self, output_path: str) -> str:
        """Write submission schema JSON."""
        schema = {
            "episode_id": self.config.episode_id,
            "episode_number": self.config.episode_number,
            "action_types": ["reorder_policy", "winback", "discount",
                             "promote", "segment_target", "investigate", "silent"],
            "required_fields": [
                "headline", "evidence_summary", "questions_asked",
                "methodology", "recommendation", "target_description",
                "expected_outcome", "timeline_days", "success_metric",
                "risk_assessment",
            ],
            "budget_constraint_thb": 10000,
            "timeline_max_days": 30,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)

        return output_path

    def export_all(self, output_dir: str, qa_pairs: list[dict] = None) -> dict:
        """Export all episode files to output directory."""
        os.makedirs(output_dir, exist_ok=True)

        ep_id = self.config.episode_id
        paths = {}

        # Student DB
        db_path = os.path.join(output_dir, f"{ep_id}_village.db")
        self.write_student_db(db_path)
        paths["db"] = db_path

        # Q&A
        if qa_pairs:
            # Student version (no truth)
            qa_student = os.path.join(output_dir, "qa.json")
            self.write_qa_json(qa_pairs, qa_student, include_truth=False)
            paths["qa_student"] = qa_student

            # Instructor version (with truth)
            qa_instructor = os.path.join(output_dir, "qa_full.json")
            self.write_qa_json(qa_pairs, qa_instructor, include_truth=True)
            paths["qa_instructor"] = qa_instructor

        # Brief
        brief_path = os.path.join(output_dir, "brief.md")
        self.write_brief(brief_path)
        paths["brief"] = brief_path

        # Schema
        schema_path = os.path.join(output_dir, "schema.json")
        self.write_schema_json(schema_path)
        paths["schema"] = schema_path

        return paths

    def _generate_default_brief(self) -> str:
        """Generate a default episode brief."""
        return f"""# {self.config.episode_id.upper()} - Analytics Challenge

## Your Client

You've been hired as a data analyst consultant for a small business in a Thai village.

## The Situation

The business owner has {self.config.history_days} days of historical data and needs your help understanding their business performance and making data-driven decisions.

## Your Task

1. **Explore the data** - Use SQL and Python to understand the business
2. **Consult the owner** - Ask questions to understand context beyond the numbers
3. **Analyse patterns** - Find insights that the owner might not see
4. **Make a recommendation** - Propose a specific, actionable plan

## Data Available

You have access to a SQLite database with transaction records, customer data, inventory logs, and more. Use `ep.db.tables()` to see what's available.

## Budget

You have up to **10,000 THB** for any recommended actions.

## Deadline

Submit your `decision.json` before the deadline shown in `ep.status()`.

## Getting Started

```python
from analytics_village import Episode, Decision
ep = Episode.load("{self.config.episode_id}")
ep.brief()
ep.owner.questions()
ep.db.tables()
```
"""
