"""
Analytics Village — Decision builder and submission.
Students build a structured decision, validate, and export as JSON.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from .display import format_validation


class Decision:
    """Structured decision submission for an episode."""

    def __init__(
        self,
        episode_id: str,
        student_ids: list[str],
        *,
        team_id: str = None,
    ):
        self.episode_id = episode_id
        self.student_ids = student_ids
        self.team_id = team_id

        # Finding
        self._headline: str | None = None
        self._evidence: str | None = None
        self._tables_used: list[str] = []
        self._questions_asked: list[str] = []
        self._methodology: str | None = None
        self._model_type: str | None = None
        self._eval_metric: str | None = None
        self._eval_result: float | None = None

        # Recommendation
        self._action_type: str | None = None
        self._recommendation: str | None = None
        self._target_description: str | None = None
        self._target_size: int | None = None
        self._target_ids: list[str] | None = None
        self._budget_thb: float | None = None
        self._expected_outcome: str | None = None
        self._timeline_days: int | None = None
        self._success_metric: str | None = None
        self._risk: str | None = None
        self._sku_recommendations: list[dict] | None = None
        self._model_output_summary: str | None = None

    def set_finding(
        self,
        headline: str,
        evidence: str,
        *,
        tables_used: list[str] = None,
        questions_asked: list[str] = None,
    ) -> Decision:
        self._headline = headline
        self._evidence = evidence
        if tables_used:
            self._tables_used = tables_used
        if questions_asked:
            self._questions_asked = questions_asked
        return self

    def set_methodology(
        self,
        approach: str,
        *,
        model_type: str = None,
        evaluation_metric: str = None,
        evaluation_result: float = None,
    ) -> Decision:
        self._methodology = approach
        self._model_type = model_type
        self._eval_metric = evaluation_metric
        self._eval_result = evaluation_result
        return self

    def set_recommendation(
        self,
        action_type: str,
        recommendation: str,
        *,
        target_description: str = None,
        target_size: int = None,
        target_ids: list[str] = None,
        budget_thb: float = None,
        expected_outcome: str = None,
        timeline_days: int = None,
        success_metric: str = None,
        risk: str = None,
        sku_recommendations: list[dict] = None,
        model_output_summary: str = None,
    ) -> Decision:
        self._action_type = action_type
        self._recommendation = recommendation
        self._target_description = target_description
        self._target_size = target_size
        self._target_ids = target_ids
        self._budget_thb = budget_thb
        self._expected_outcome = expected_outcome
        self._timeline_days = timeline_days
        self._success_metric = success_metric
        self._risk = risk
        self._sku_recommendations = sku_recommendations
        self._model_output_summary = model_output_summary
        return self

    def validate(self) -> bool:
        """Validate against submission requirements. Prints report."""
        checks = []

        # Required fields
        checks.append((
            bool(self.episode_id),
            f"Episode ID: {self.episode_id}" if self.episode_id else "Episode ID: MISSING"
        ))
        checks.append((
            bool(self.student_ids),
            f"Student IDs: {self.student_ids}" if self.student_ids else "Student IDs: MISSING"
        ))
        checks.append((
            bool(self._headline) and 30 <= len(self._headline) <= 200,
            f"Headline: Present ({len(self._headline or '')} chars)"
            if self._headline else "Headline: MISSING (required)"
        ))
        checks.append((
            bool(self._evidence) and len(self._evidence) >= 50,
            f"Evidence: Present ({len(self._evidence or '')} chars)"
            if self._evidence else "Evidence: MISSING (required)"
        ))
        checks.append((
            bool(self._methodology),
            f"Methodology: Present" if self._methodology else "Methodology: MISSING"
        ))
        checks.append((
            bool(self._action_type),
            f"Action type: '{self._action_type}'" if self._action_type else "Action type: MISSING"
        ))
        checks.append((
            bool(self._recommendation),
            f"Recommendation: Present ({len(self._recommendation or '')} chars)"
            if self._recommendation else "Recommendation: MISSING"
        ))
        checks.append((
            bool(self._expected_outcome),
            f"Expected outcome: Present" if self._expected_outcome else "Expected outcome: MISSING"
        ))
        checks.append((
            self._timeline_days is not None and 1 <= self._timeline_days <= 30,
            f"Timeline: {self._timeline_days} days"
            if self._timeline_days else "Timeline: MISSING"
        ))
        checks.append((
            bool(self._success_metric),
            f"Success metric: Present" if self._success_metric else "Success metric: MISSING"
        ))
        checks.append((
            bool(self._risk) and len(self._risk or "") >= 20,
            f"Risk: Present ({len(self._risk or '')} chars)"
            if self._risk else "Risk: MISSING or too short"
        ))

        # Budget check
        if self._budget_thb is not None:
            checks.append((
                self._budget_thb <= 10000,
                f"Budget: {self._budget_thb:,.0f} THB (within 10,000 THB limit)"
                if self._budget_thb <= 10000
                else f"Budget: {self._budget_thb:,.0f} THB EXCEEDS limit of 10,000 THB"
            ))

        print(format_validation(checks))
        return all(ok for ok, _ in checks)

    def preview(self) -> None:
        """Display formatted preview of the decision."""
        print(f"\n{'=' * 60}")
        print(f"DECISION PREVIEW: {self.episode_id}")
        print(f"{'=' * 60}")
        print(f"Students: {', '.join(self.student_ids)}")
        if self.team_id:
            print(f"Team: {self.team_id}")
        print(f"\nHeadline: {self._headline or '(not set)'}")
        print(f"\nEvidence: {self._evidence or '(not set)'}")
        print(f"\nMethodology: {self._methodology or '(not set)'}")
        print(f"\nAction: {self._action_type or '(not set)'}")
        print(f"Recommendation: {self._recommendation or '(not set)'}")
        print(f"Target: {self._target_description or '(not set)'}")
        print(f"Budget: {self._budget_thb or 0:,.0f} THB")
        print(f"Timeline: {self._timeline_days or 0} days")
        print(f"Success metric: {self._success_metric or '(not set)'}")
        print(f"Risk: {self._risk or '(not set)'}")
        print(f"{'=' * 60}")

    def export(self, output_dir: str = ".", filename: str = None) -> str:
        """Validate and export decision.json."""
        if not self.validate():
            raise ValueError("Decision is not valid. Fix errors before exporting.")

        data = {
            "metadata": {
                "analytics_village_version": "1.0.0",
                "episode_id": self.episode_id,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "student_ids": self.student_ids,
                "team_id": self.team_id,
            },
            "finding": {
                "headline": self._headline,
                "evidence": self._evidence,
                "tables_used": self._tables_used,
                "questions_asked": self._questions_asked,
                "methodology": self._methodology,
                "model_type": self._model_type,
                "evaluation_metric": self._eval_metric,
                "evaluation_result": self._eval_result,
            },
            "recommendation": {
                "action_type": self._action_type,
                "recommendation": self._recommendation,
                "target_description": self._target_description,
                "target_size": self._target_size,
                "target_ids": self._target_ids,
                "budget_thb": self._budget_thb,
                "expected_outcome": self._expected_outcome,
                "timeline_days": self._timeline_days,
                "success_metric": self._success_metric,
                "risk": self._risk,
                "sku_recommendations": self._sku_recommendations,
                "model_output_summary": self._model_output_summary,
            },
        }

        if not filename:
            sid = self.student_ids[0] if self.student_ids else "unknown"
            filename = f"{self.episode_id}_{sid}.json"

        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        size_kb = os.path.getsize(path) / 1024
        print(f"\n+ Validated successfully.")
        print(f"+ Saved: {filename} ({size_kb:.1f} KB)")
        print(f"\nNext steps:")
        print(f"  Submit this file to your instructor's submission endpoint.")
        return path
