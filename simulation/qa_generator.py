"""
Analytics Village — Q&A Generator (Phase 4).
Generates owner Q&A pairs for each episode using LLM.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_client import OllamaClient
    from .database import VillageDB
    from .world import WorldState

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# Question templates per category
# ══════════════════════════════════════════════════════════════

QUESTION_TEMPLATES = {
    "business_context": [
        {"id": "BIZ_01", "q": "How long have you been running this business and how has it been going?", "difficulty": "surface", "data_keys": ["store_metrics.days", "revenue_trend"]},
        {"id": "BIZ_02", "q": "What products or services are your best sellers?", "difficulty": "surface", "data_keys": ["top_skus_by_revenue"]},
        {"id": "BIZ_03", "q": "Who are your main competitors in the village?", "difficulty": "surface", "data_keys": ["alt_transactions_summary"]},
        {"id": "BIZ_04", "q": "What is your biggest challenge running this business?", "difficulty": "intermediate", "data_keys": ["stockout_rate", "waste_rate", "churn_rate"]},
        {"id": "BIZ_05", "q": "How do you set your prices?", "difficulty": "intermediate", "data_keys": ["price_log_summary", "margin_pct"]},
        {"id": "BIZ_06", "q": "What does a typical busy day look like?", "difficulty": "surface", "data_keys": ["day_of_week_revenue", "peak_days"]},
        {"id": "BIZ_07", "q": "How has the village changed since you started?", "difficulty": "deep", "data_keys": ["population_trend", "revenue_trend"]},
        {"id": "BIZ_08", "q": "What do you wish you knew about your business that you currently don't?", "difficulty": "deep", "data_keys": ["hidden_patterns"]},
    ],
    "customer_knowledge": [
        {"id": "CUST_01", "q": "Have you noticed any regular customers you haven't seen lately?", "difficulty": "surface", "data_keys": ["at_risk_count", "churned_count"]},
        {"id": "CUST_02", "q": "Do your customers tend to buy the same things each time?", "difficulty": "surface", "data_keys": ["basket_consistency"]},
        {"id": "CUST_03", "q": "How important are new residents to your business?", "difficulty": "intermediate", "data_keys": ["new_acquisition_rate"]},
        {"id": "CUST_04", "q": "Do you notice different spending patterns at different times of month?", "difficulty": "intermediate", "data_keys": ["payday_uplift"]},
        {"id": "CUST_05", "q": "Which customers spend the most and what do they buy?", "difficulty": "intermediate", "data_keys": ["top_customers_spend"]},
        {"id": "CUST_06", "q": "Have you ever tried to bring back customers who stopped coming?", "difficulty": "deep", "data_keys": ["winback_history"]},
        {"id": "CUST_07", "q": "What do customers complain about most?", "difficulty": "surface", "data_keys": ["satisfaction_drivers"]},
        {"id": "CUST_08", "q": "Do families shop differently from single people or couples?", "difficulty": "deep", "data_keys": ["household_size_patterns"]},
    ],
    "operations": [
        {"id": "OPS_01", "q": "Have you had problems with products going out of stock?", "difficulty": "surface", "data_keys": ["stockout_rate", "stockout_skus"]},
        {"id": "OPS_02", "q": "How much product waste do you have?", "difficulty": "surface", "data_keys": ["waste_rate", "waste_value"]},
        {"id": "OPS_03", "q": "How reliable are your suppliers?", "difficulty": "intermediate", "data_keys": ["supplier_fill_rate"]},
        {"id": "OPS_04", "q": "What happens when a supplier delivers late or short?", "difficulty": "intermediate", "data_keys": ["supply_events_failures"]},
        {"id": "OPS_05", "q": "How do you decide how much of each product to order?", "difficulty": "intermediate", "data_keys": ["reorder_patterns"]},
        {"id": "OPS_06", "q": "Do you track which products expire before they sell?", "difficulty": "deep", "data_keys": ["waste_by_sku"]},
        {"id": "OPS_07", "q": "Have you considered changing any of your suppliers?", "difficulty": "deep", "data_keys": ["supplier_comparison"]},
        {"id": "OPS_08", "q": "What's your shelf restocking process like?", "difficulty": "surface", "data_keys": ["restock_patterns"]},
    ],
    "strategy": [
        {"id": "STRAT_01", "q": "What is your budget for improving the business this month?", "difficulty": "surface", "data_keys": ["po_budget"]},
        {"id": "STRAT_02", "q": "Would you consider running promotions to attract more customers?", "difficulty": "intermediate", "data_keys": ["campaign_history"]},
        {"id": "STRAT_03", "q": "What would you do with an extra 10,000 THB to invest in the business?", "difficulty": "intermediate", "data_keys": ["business_needs"]},
        {"id": "STRAT_04", "q": "Are you worried about losing customers to other stores?", "difficulty": "intermediate", "data_keys": ["churn_rate", "alt_visits"]},
        {"id": "STRAT_05", "q": "Have you thought about adding new products or services?", "difficulty": "deep", "data_keys": ["category_gaps"]},
        {"id": "STRAT_06", "q": "If you could change one thing about your business overnight, what would it be?", "difficulty": "deep", "data_keys": ["business_pain_points"]},
        {"id": "STRAT_07", "q": "How do you feel about the future of your business?", "difficulty": "surface", "data_keys": ["revenue_trend", "scenario"]},
        {"id": "STRAT_08", "q": "What advice would you give to someone opening a similar business?", "difficulty": "deep", "data_keys": ["owner_experience"]},
    ],
}


class QAGenerator:
    """Generates Q&A pairs using LLM with owner persona."""

    def __init__(self, llm: OllamaClient, db: VillageDB, world: WorldState):
        self.llm = llm
        self.db = db
        self.world = world

    async def generate_all(self, business_id: str) -> list[dict]:
        """Generate all Q&A pairs for an episode. Returns list of QAPair dicts."""
        owner_row = self._get_owner(business_id)
        if not owner_row:
            logger.error(f"No owner found for {business_id}")
            return []

        data_context = self._build_data_context(business_id)
        qa_pairs = []

        for category, questions in QUESTION_TEMPLATES.items():
            tasks = [
                self._generate_one(q, owner_row, data_context, category)
                for q in questions
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for q, result in zip(questions, results):
                if isinstance(result, dict):
                    qa_pairs.append(result)
                else:
                    logger.warning(f"Q&A generation failed for {q['id']}: {result}")
                    # Fallback: generic answer
                    qa_pairs.append(self._fallback_qa(q, category, owner_row))

        return qa_pairs

    async def _generate_one(
        self, question: dict, owner: dict, data_context: str, category: str,
    ) -> dict:
        """Generate one Q&A pair with LLM."""
        persona = owner.get("llm_persona_prompt") or (
            f"You are {owner['name']}, owner of a small business in a Thai village. "
            f"Background: {owner.get('background', 'local business owner')}. "
            f"Style: {owner.get('communication_style', 'friendly')}."
        )

        system = f"""{persona}

You are being interviewed by a student analyst.
Answer the question the way {owner['name']} would:
- Speak from memory and feeling, not from data
- Be warm and specific but imprecise on numbers
- Include your personality and blind spots
- Answer in 3-5 sentences. Natural, conversational.
- Do NOT use data-analysis language

Business context (for accuracy - your answer should be CLOSE but not exact):
{data_context}"""

        user_prompt = f"""Question: {question['q']}

Respond with JSON:
{{
  "answer": "Your answer in character, 3-5 sentences...",
  "confidence": "high/medium/low"
}}"""

        result = await self.llm.complete_json(
            system, user_prompt,
            temperature=self.world.config.qa_temp,
            max_tokens=300,
        )

        answer = ""
        if result and isinstance(result, dict):
            answer = result.get("answer", "")

        # Auto-generate data_truth
        data_truth = self._compute_data_truth(question, self.world.config.primary_business)

        return {
            "question_id": question["id"],
            "category": category,
            "difficulty": question["difficulty"],
            "question": question["q"],
            "answer": answer or f"Hmm, that's a good question. Let me think... (answer unavailable)",
            "data_truth": data_truth,
            "teaching_note": f"Compare owner's answer with actual data from {', '.join(question.get('data_keys', []))}.",
        }

    def _fallback_qa(self, question: dict, category: str, owner: dict) -> dict:
        return {
            "question_id": question["id"],
            "category": category,
            "difficulty": question["difficulty"],
            "question": question["q"],
            "answer": f"Well, you know, that's something I think about... I'd say things are going okay overall. We do our best here at the shop.",
            "data_truth": {},
            "teaching_note": "LLM generation failed - using fallback answer.",
        }

    def _get_owner(self, business_id: str) -> dict | None:
        biz = self.db.fetchone("SELECT * FROM businesses WHERE business_id = ?", (business_id,))
        if not biz:
            return None
        return self.db.fetchone("SELECT * FROM owners WHERE owner_id = ?", (biz["owner_id"],))

    def _build_data_context(self, business_id: str) -> str:
        """Build a concise data summary for the LLM context."""
        lines = []

        # Revenue summary
        rev = self.db.fetchone(
            "SELECT SUM(gross_revenue_thb) AS total, AVG(gross_revenue_thb) AS avg_daily, "
            "COUNT(*) AS days FROM store_metrics WHERE business_id = ?",
            (business_id,)
        )
        if rev and rev["total"]:
            lines.append(f"Total revenue: {rev['total']:.0f} THB over {rev['days']} days")
            lines.append(f"Average daily revenue: {rev['avg_daily']:.0f} THB")

        # Customer count
        cust = self.db.fetchone(
            "SELECT COUNT(DISTINCT household_id) AS n FROM transactions WHERE business_id = ?",
            (business_id,)
        )
        if cust:
            lines.append(f"Unique customers: {cust['n']}")

        # Top SKUs
        top = self.db.fetchall(
            "SELECT s.sku_name, SUM(bi.line_value_thb) AS rev "
            "FROM basket_items bi JOIN transactions t ON bi.transaction_id = t.transaction_id "
            "JOIN skus s ON bi.sku_id = s.sku_id "
            "WHERE t.business_id = ? GROUP BY s.sku_name ORDER BY rev DESC LIMIT 5",
            (business_id,)
        )
        if top:
            lines.append("Top sellers: " + ", ".join(f"{r['sku_name']}" for r in top))

        # Stockout rate
        so = self.db.fetchone(
            "SELECT AVG(stockout_rate) AS rate FROM store_metrics WHERE business_id = ?",
            (business_id,)
        )
        if so and so["rate"]:
            lines.append(f"Average stockout rate: {so['rate']*100:.1f}%")

        # Waste
        waste = self.db.fetchone(
            "SELECT SUM(estimated_cost_thb) AS total FROM waste_events WHERE actor_id = ?",
            (business_id,)
        )
        if waste and waste["total"]:
            lines.append(f"Total waste value: {waste['total']:.0f} THB")

        return "\n".join(lines) if lines else "Limited data available."

    def _compute_data_truth(self, question: dict, business_id: str) -> dict:
        """Compute actual data values for the data_truth field."""
        truth = {}
        for key in question.get("data_keys", []):
            if key == "revenue_trend":
                row = self.db.fetchone(
                    "SELECT AVG(CASE WHEN day > -15 THEN gross_revenue_thb END) AS recent, "
                    "AVG(CASE WHEN day <= -15 THEN gross_revenue_thb END) AS earlier "
                    "FROM store_metrics WHERE business_id = ?",
                    (business_id,)
                )
                if row and row["earlier"] and row["earlier"] > 0:
                    change = (row["recent"] - row["earlier"]) / row["earlier"] * 100
                    truth["revenue_trend_pct"] = round(change, 1)
            elif key == "stockout_rate":
                row = self.db.fetchone(
                    "SELECT AVG(stockout_rate) AS rate FROM store_metrics WHERE business_id = ?",
                    (business_id,)
                )
                if row and row["rate"] is not None:
                    truth["stockout_rate_pct"] = round(row["rate"] * 100, 1)
            elif key == "waste_rate":
                row = self.db.fetchone(
                    "SELECT SUM(estimated_cost_thb) AS waste FROM waste_events WHERE actor_id = ?",
                    (business_id,)
                )
                if row:
                    truth["waste_total_thb"] = round(row["waste"] or 0, 0)
        return truth


def generate_qa_sync(
    llm: OllamaClient, db: VillageDB, world: WorldState, business_id: str
) -> list[dict]:
    """Synchronous wrapper."""
    gen = QAGenerator(llm, db, world)
    return asyncio.run(gen.generate_all(business_id))
