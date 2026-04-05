"""
Analytics Village — Persona Seeder (Phase 2).
Generates rich LLM personas for each household and store owner.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_client import OllamaClient
    from .world import WorldState, HouseholdState
    from .database import VillageDB

logger = logging.getLogger(__name__)

PERSONA_SYSTEM = """You are a creative writer generating realistic household personas for a Thai village simulation.
Each persona should be 150-200 words describing:
- Who lives in the household (family structure, ages, occupations)
- Their shopping habits and preferences
- Their personality and quirks
- What they care about (price, quality, convenience, health)
- Their routine and lifestyle

Make each persona unique, grounded in Thai village life, and internally consistent.
Always respond with valid JSON only."""

OWNER_PERSONA_SYSTEM = """You are creating a detailed business owner persona for a Thai village simulation.
The persona should be 200-250 words describing:
- Their background and why they started the business
- Their management style and decision-making approach
- Their relationship with customers and community
- Their strengths and weaknesses as a business owner
- Their goals and concerns

Make the persona realistic, with clear blind spots and biases.
Always respond with valid JSON only."""


class PersonaSeeder:
    """Phase 2: Generate rich personas via LLM."""

    def __init__(self, llm: OllamaClient):
        self.llm = llm

    async def seed_all(
        self, world: WorldState, db: VillageDB
    ) -> int:
        """
        Generate personas for all households and store owners.
        Returns total LLM calls made.
        """
        calls = 0

        # Seed households in batches
        households = list(world.households.values())
        batch_size = 5
        for i in range(0, len(households), batch_size):
            batch = households[i:i + batch_size]
            tasks = [self._seed_household(hh, world) for hh in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for hh, result in zip(batch, results):
                if isinstance(result, str) and result:
                    hh.persona_narrative = result
                    db.execute(
                        "UPDATE households SET persona_narrative = ? WHERE household_id = ?",
                        (result, hh.household_id)
                    )
                    calls += 1
                elif isinstance(result, Exception):
                    logger.warning(f"Persona seeding failed for {hh.household_id}: {result}")

        # Seed store owners
        for biz in world.active_businesses():
            owner_row = db.fetchone(
                "SELECT * FROM owners WHERE owner_id = ?", (biz.owner_id,)
            )
            if owner_row:
                persona = await self._seed_owner(biz, owner_row, world)
                if persona:
                    db.execute(
                        "UPDATE owners SET llm_persona_prompt = ? WHERE owner_id = ?",
                        (persona, biz.owner_id)
                    )
                    calls += 1

        db.commit()
        logger.info(f"Persona seeding complete: {calls} LLM calls")
        return calls

    async def _seed_household(
        self, hh: HouseholdState, world: WorldState
    ) -> str:
        """Generate persona narrative for one household."""
        traits = []
        if hh.price_sensitivity > 0.2:
            traits.append(f"price-sensitive ({hh.price_sensitivity:.0%})")
        if hh.routine_strength > 0.2:
            traits.append(f"routine-oriented ({hh.routine_strength:.0%})")
        if hh.health_orientation > 0.2:
            traits.append(f"health-conscious ({hh.health_orientation:.0%})")
        if hh.brand_loyalty > 0.2:
            traits.append(f"brand-loyal ({hh.brand_loyalty:.0%})")
        if hh.stock_anxiety > 0.2:
            traits.append(f"stock-anxious ({hh.stock_anxiety:.0%})")

        user_prompt = f"""Generate a persona for this household:

Household ID: {hh.household_id}
Size: {hh.household_size} people
Dwelling: {hh.dwelling_type}
Zone: {hh.location_zone}
Income: {hh.income_bracket} (weekly budget ~{hh.weekly_budget_thb:.0f} THB)
Key traits: {', '.join(traits)}
Lifecycle: {hh.lifecycle_state}

Respond with JSON:
{{"persona_narrative": "150-200 word persona..."}}"""

        result = await self.llm.complete_json(
            PERSONA_SYSTEM, user_prompt,
            temperature=world.config.persona_temp,
            max_tokens=400,
        )

        if result and isinstance(result, dict):
            return result.get("persona_narrative", "")
        return ""

    async def _seed_owner(
        self, biz, owner_row: dict, world: WorldState
    ) -> str:
        """Generate detailed owner persona for Q&A generation."""
        personality = owner_row.get("personality_traits", "[]")
        blind_spots = owner_row.get("known_blind_spots", "[]")

        user_prompt = f"""Generate a detailed business owner persona:

Owner: {owner_row['name']}
Age: {owner_row.get('age', 'unknown')}
Business: {biz.business_name} ({biz.business_type})
Background: {owner_row.get('background', 'N/A')}
Personality: {personality}
Blind spots: {blind_spots}
Communication style: {owner_row.get('communication_style', 'neutral')}

Create a system prompt that would make an LLM convincingly roleplay as this owner.
Include their speech patterns, typical reactions, and knowledge limitations.

Respond with JSON:
{{"persona_prompt": "detailed system prompt for LLM roleplay..."}}"""

        result = await self.llm.complete_json(
            OWNER_PERSONA_SYSTEM, user_prompt,
            temperature=world.config.persona_temp,
            max_tokens=600,
        )

        if result and isinstance(result, dict):
            return result.get("persona_prompt", "")
        return ""


def seed_personas_sync(llm: OllamaClient, world: WorldState, db: VillageDB) -> int:
    """Synchronous wrapper for persona seeding."""
    seeder = PersonaSeeder(llm)
    return asyncio.run(seeder.seed_all(world, db))
