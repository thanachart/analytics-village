"""
Analytics Village — Store Manager Agent.
LLM-driven store management decisions: pricing, promotions, win-back, restocking.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_client import OllamaClient
    from .world import WorldState, BusinessState

logger = logging.getLogger(__name__)

STORE_SYSTEM = """You are a store manager agent for a small retail business in a Thai village.
You make daily business decisions based on your sales data, stock levels, and customer metrics.
Make realistic decisions - not always optimal, sometimes reactive or emotionally driven.

Always respond with valid JSON only. No prose, no markdown."""

REFLECT_SYSTEM = """You are updating the strategic direction for a village store.
Based on this week's performance, update the strategy narrative.
Be specific about what to change and why.

Always respond with valid JSON only."""


class StoreManagerAgent:
    """LLM-driven store management. One per business."""

    def __init__(self, llm: OllamaClient):
        self.llm = llm

    async def decide(
        self,
        business: BusinessState,
        world: WorldState,
        day: int,
        metrics_7d: list[dict],
        low_stock_skus: list[dict],
        lifecycle_counts: dict,
    ) -> dict | None:
        """
        Daily store decision. Returns decision dict.

        Returns:
            {
                "pricing_changes": [{sku_id, new_price, reason}],
                "promotion": {skus, discount_pct, duration_days, channel, target},
                "winback_offers": [{household_id, offer_type, discount_pct}],
                "reorder_urgent": [{sku_id, qty, supplier_preference}],
                "reasoning": "..."
            }
        """
        # Build metrics summary
        if metrics_7d:
            avg_rev = sum(m.get("gross_revenue_thb", 0) for m in metrics_7d) / len(metrics_7d)
            total_visitors = sum(m.get("unique_visitors", 0) for m in metrics_7d)
            stockout_days = sum(1 for m in metrics_7d if m.get("stockout_incidents", 0) > 0)
        else:
            avg_rev = 0
            total_visitors = 0
            stockout_days = 0

        low_stock_text = ""
        if low_stock_skus:
            lines = [f"  {s['sku_name']}: {s['stock']} units left" for s in low_stock_skus[:10]]
            low_stock_text = "LOW STOCK ITEMS:\n" + "\n".join(lines)

        user_prompt = f"""STORE: {business.business_name} ({business.business_type})
DAY: {day}

LAST 7 DAYS PERFORMANCE:
- Avg daily revenue: {avg_rev:.0f} THB
- Total visitors: {total_visitors}
- Days with stockouts: {stockout_days}/7
- PO budget remaining: {business.po_budget_remaining_thb:.0f} THB

CUSTOMER LIFECYCLE:
- Retained: {lifecycle_counts.get('retained', 0)}
- At-risk: {lifecycle_counts.get('at_risk', 0)}
- Churned: {lifecycle_counts.get('churned', 0)}
- Winback candidates: {lifecycle_counts.get('winback_candidate', 0)}

{low_stock_text}

DECIDE:
1. Any price changes needed today?
2. Should we run a promotion?
3. Any win-back offers to send?
4. Any urgent reorders?

Respond with JSON:
{{
  "pricing_changes": [],
  "promotion": null,
  "winback_offers": [],
  "reorder_urgent": [],
  "reasoning": "explanation"
}}"""

        result = await self.llm.complete_json(
            STORE_SYSTEM, user_prompt,
            temperature=world.config.store_temp,
            max_tokens=512,
        )

        if result and isinstance(result, dict):
            return result

        logger.warning(f"Store agent failed for {business.business_id}")
        return None

    async def reflect(
        self,
        business: BusinessState,
        world: WorldState,
        week_number: int,
        week_metrics: dict,
    ) -> dict | None:
        """Weekly strategy reflection."""
        user_prompt = f"""STORE: {business.business_name}
WEEK: {week_number}

THIS WEEK'S RESULTS:
- Revenue: {week_metrics.get('revenue', 0):.0f} THB
- Revenue change vs last week: {week_metrics.get('revenue_change_pct', 0):+.1f}%
- New customers: {week_metrics.get('new_acquisitions', 0)}
- Customers lost to at-risk: {week_metrics.get('new_at_risk', 0)}
- Stockout incidents: {week_metrics.get('stockouts', 0)}
- Waste value: {week_metrics.get('waste_value', 0):.0f} THB

Update your strategic direction for next week.

Respond with JSON:
{{
  "strategy_narrative": "200 word strategy update...",
  "key_observations": ["obs 1", "obs 2"],
  "strategic_shifts": ["shift 1"]
}}"""

        result = await self.llm.complete_json(
            REFLECT_SYSTEM, user_prompt,
            temperature=0.5,
            max_tokens=512,
        )
        return result if isinstance(result, dict) else None
