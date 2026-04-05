"""
Analytics Village — Owner Q&A interface.
All answers are pre-generated — no LLM calls at runtime.
"""
from __future__ import annotations

import json
from typing import Any

from .display import format_table, format_qa_answer


class Owner:
    """Interface to the simulated business owner. Static Q&A lookup."""

    def __init__(self, qa_data: dict, owner_name: str = "Owner"):
        self._qa = {q["question_id"]: q for q in qa_data.get("questions", [])}
        self._owner_name = owner_name
        self._asked: list[str] = []

    @classmethod
    def from_json(cls, path: str) -> Owner:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("owner_name", "Owner")
        return cls(data, owner_name=name)

    def questions(
        self,
        category: str = None,
        difficulty: str = None,
    ) -> None:
        """Display available questions."""
        rows = []
        for qid, q in sorted(self._qa.items()):
            if category and q.get("category") != category:
                continue
            if difficulty and q.get("difficulty") != difficulty:
                continue
            asked = "*" if qid in self._asked else ""
            rows.append([
                qid + asked,
                q.get("category", ""),
                q.get("difficulty", ""),
                q["question"][:60] + ("..." if len(q["question"]) > 60 else ""),
            ])

        print(format_table(
            ["ID", "Category", "Level", "Question"],
            rows,
            f"Available Questions ({len(rows)} total)"
        ))
        print(f"\n{len(self._qa)} questions available. Ask any with: ep.owner.ask(\"ID\")")
        if self._asked:
            print(f"* = already asked ({len(self._asked)} asked)")

    def ask(self, question_id: str) -> None:
        """Get the owner's answer to a specific question."""
        q = self._qa.get(question_id.upper())
        if not q:
            # Try case-insensitive
            for qid, qq in self._qa.items():
                if qid.upper() == question_id.upper():
                    q = qq
                    break
        if not q:
            available = ", ".join(sorted(self._qa.keys()))
            print(f"Question '{question_id}' not found.")
            print(f"Available: {available}")
            return

        if question_id.upper() not in self._asked:
            self._asked.append(question_id.upper())

        print(format_qa_answer(
            q["question_id"], q["question"], q["answer"], self._owner_name
        ))

    def ask_all(self, category: str = None) -> None:
        """Print all available answers at once."""
        for qid in sorted(self._qa.keys()):
            q = self._qa[qid]
            if category and q.get("category") != category:
                continue
            self.ask(qid)

    def profile(self) -> None:
        """Display the owner's persona narrative."""
        print(f"\n{'=' * 50}")
        print(f"{self._owner_name}")
        print(f"{'=' * 50}")
        # Profile is derived from Q&A context
        biz_q = self._qa.get("BIZ_01")
        if biz_q:
            print(f"\n{biz_q['answer']}")
        print(f"\n{'=' * 50}")

    def search(self, keyword: str) -> None:
        """Search questions by keyword in question and answer text."""
        keyword_lower = keyword.lower()
        matches = []
        for qid, q in self._qa.items():
            if (keyword_lower in q["question"].lower() or
                keyword_lower in q["answer"].lower()):
                matches.append(qid)

        if matches:
            print(f"\nFound {len(matches)} questions mentioning '{keyword}':")
            for qid in matches:
                q = self._qa[qid]
                print(f"  {qid}: {q['question'][:70]}")
        else:
            print(f"\nNo questions found mentioning '{keyword}'.")

    @property
    def questions_asked(self) -> list[str]:
        """List of question IDs that have been asked."""
        return list(self._asked)
