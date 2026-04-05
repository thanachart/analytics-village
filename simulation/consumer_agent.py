"""
Analytics Village — Consumer Agent.
LLM-driven household shopping decisions.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_client import OllamaClient
    from .world import WorldState, HouseholdState, CalendarDay

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are simulating a household shopping decision agent in a Thai village.
You make realistic consumer decisions based on the household profile below.
You are NOT a helpful assistant - you ARE this household.
Make decisions the way this real household would, including:
- Being influenced by habit and routine
- Sometimes being irrational or emotionally driven
- Having a consistent but slowly-evolving character
- Making mistakes (buying too much, forgetting things, impulse purchases)

Always respond with valid JSON only. No prose, no markdown."""

REFLECT_SYSTEM = """You are updating the profile narrative for a simulated household.
Based on what happened this week, update the household's character profile.
Be specific about what changed and why. Keep it 150-200 words.
Always respond with valid JSON only."""


class ConsumerAgent:
    """LLM-driven decision making for a single household."""

    def __init__(self, llm: OllamaClient):
        self.llm = llm

    async def decide(
        self,
        hh: HouseholdState,
        world: WorldState,
        cal: CalendarDay,
        days_since_last_visit: int | None,
    ) -> dict | None:
        """
        Daily decision call. Returns structured decision dict or None on failure.

        Returns dict with:
            visits: bool
            store_choices: list[str]
            reasoning: str
            basket: list[{sku_id, qty, responded_to_promo}]
            satisfaction: str
            mood_next: str
            word_of_mouth: bool
        """
        persona = hh.persona_narrative or _default_persona(hh)
        system = SYSTEM_PROMPT + f"\n\nYOUR PROFILE:\n{persona}"

        # Build context
        primary_biz = world.config.primary_business
        biz = world.businesses.get(primary_biz)
        biz_skus = [s for s in world.skus.values() if s.business_id == primary_biz]

        # Build available products context (top items by category)
        products_text = _build_store_context(biz, biz_skus, world)

        user_prompt = f"""TODAY IS: Day {world.current_day}, {cal.day_of_week}, day {cal.day_of_month} of month
{'PAYDAY WEEK - you have extra money!' if cal.is_payday_week else ''}
Weather/events: {', '.join(cal.events) if cal.events else 'Normal day'}

YOUR PANTRY STATUS:
- Fridge: {hh.fridge_pct*100:.0f}% full
- Pantry: {hh.pantry_pct*100:.0f}% full
- Freezer: {hh.freezer_pct*100:.0f}% full
- Urgency to shop: {hh.pantry_urgency:.1f}/1.0

YOUR BUDGET:
- Weekly budget: {hh.weekly_budget_thb:.0f} THB
- Remaining this week: {hh.budget_remaining_thb:.0f} THB

YOUR RECENT HISTORY:
- Last visit: {'day ' + str(hh.last_visit_day) if hh.last_visit_day else 'never'}
- Days since last visit: {days_since_last_visit if days_since_last_visit else 'N/A'}
- Total visits: {hh.total_visits}
- Current mood: {hh.mood}

WHAT'S AT THE STORE:
{products_text}

DECIDE NOW:
1. Do you visit a store today? Which one(s)?
2. If visiting, what do you buy and how much?
3. How do you feel?

Respond with JSON:
{{
  "visits": true/false,
  "store_choices": ["supermarket"],
  "reasoning": "short explanation",
  "basket": [
    {{"sku_id": "SUP_MILK_1L", "qty": 2, "responded_to_promo": false}}
  ],
  "satisfaction": "neutral",
  "mood_next": "positive",
  "word_of_mouth": false
}}"""

        result = await self.llm.complete_json(
            system, user_prompt,
            temperature=hh.llm_temperature,
            max_tokens=512,
        )

        if result and isinstance(result, dict):
            return result

        logger.warning(f"Consumer agent failed for {hh.household_id}")
        return None

    async def reflect(
        self,
        hh: HouseholdState,
        world: WorldState,
        week_summary: dict,
    ) -> dict | None:
        """
        Weekly reflection — updates persona narrative.
        Only called if notable events occurred this week.
        """
        current_persona = hh.persona_narrative or _default_persona(hh)

        user_prompt = f"""Your profile from last week:
{current_persona}

What happened this week:
- Visits: {week_summary.get('visits', 0)}
- Stockouts experienced: {week_summary.get('stockouts', 0)}
- Satisfaction events: {week_summary.get('frustrations', 0)} frustrated, {week_summary.get('happy', 0)} happy
- Alternative store visits: {week_summary.get('alt_visits', 0)}
- Budget used: {week_summary.get('budget_used_pct', 0):.0f}%

Key events:
{json.dumps(week_summary.get('events', []), indent=2)}

Update your profile narrative. Be specific about what changed and why.

Respond with JSON:
{{
  "profile_narrative": "150-200 word updated profile...",
  "key_changes": ["change 1", "change 2"],
  "satisfaction_trend": "improving/stable/declining"
}}"""

        result = await self.llm.complete_json(
            REFLECT_SYSTEM, user_prompt,
            temperature=0.6,
            max_tokens=512,
        )

        if result and isinstance(result, dict):
            if "profile_narrative" in result:
                hh.persona_narrative = result["profile_narrative"]
            return result

        return None


def _default_persona(hh: HouseholdState) -> str:
    """Generate a basic persona description from household attributes."""
    size_desc = {1: "single person", 2: "couple"}.get(
        hh.household_size, f"family of {hh.household_size}"
    )
    income_desc = {"low": "budget-conscious", "medium": "middle-income",
                   "high": "comfortable"}.get(hh.income_bracket, "middle-income")

    traits = []
    if hh.price_sensitivity > 0.25:
        traits.append("very price-conscious")
    if hh.routine_strength > 0.25:
        traits.append("creature of habit")
    if hh.health_orientation > 0.25:
        traits.append("health-focused")
    if hh.brand_loyalty > 0.25:
        traits.append("brand-loyal")
    if hh.stock_anxiety > 0.25:
        traits.append("worries about running out")

    return (
        f"A {income_desc} {size_desc} living in a {hh.dwelling_type} "
        f"in the {hh.location_zone} area. "
        f"Traits: {', '.join(traits[:3]) if traits else 'balanced shopper'}. "
        f"Weekly budget: {hh.weekly_budget_thb:.0f} THB."
    )


def _build_store_context(biz, skus, world) -> str:
    """Build a concise text description of what's available at the store."""
    if not biz or not skus:
        return "Store information unavailable."

    lines = []
    categories = {}
    for sku in skus[:20]:  # Limit to avoid prompt bloat
        cat = sku.category
        if cat not in categories:
            categories[cat] = []
        price = biz.current_prices.get(sku.sku_id, sku.base_price_thb)
        stock = biz.current_stock.get(sku.sku_id, "?")
        categories[cat].append(f"  {sku.sku_name}: {price:.0f} THB")

    for cat, items in categories.items():
        lines.append(f"{cat.upper()}:")
        lines.extend(items[:4])

    # Active promos
    if biz.active_promos:
        lines.append("\nPROMOTIONS:")
        for p in biz.active_promos[:3]:
            sku = world.skus.get(p.get("sku_id", ""))
            if sku:
                lines.append(f"  {sku.sku_name}: {p.get('discount_pct', 0)}% off!")

    return "\n".join(lines)
