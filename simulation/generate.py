"""
Analytics Village — Main Generation CLI (Entry Point).
Orchestrates Phases 0-5 of episode generation.
"""
from __future__ import annotations

import os
import sys
import time
import logging

import click

from .world import SimConfig
from .database import VillageDB
from .history_runner import run_history, print_progress
from .exporter import EpisodeExporter

logger = logging.getLogger(__name__)


@click.command()
@click.option("--config", "config_path", type=click.Path(exists=True),
              help="YAML config file path")
@click.option("--output", "output_dir", default="output",
              help="Output directory for generated files")
@click.option("--households", type=int, default=150,
              help="Number of households (overrides config)")
@click.option("--days", type=int, default=90,
              help="History days (overrides config)")
@click.option("--live-days", type=int, default=30,
              help="Live simulation days with LLM")
@click.option("--seed", type=int, default=42,
              help="Random seed")
@click.option("--no-llm", is_flag=True, default=False,
              help="Skip LLM phases (history only)")
@click.option("--episode-id", default="ep01",
              help="Episode identifier")
@click.option("--business", default="supermarket",
              help="Primary business for episode")
@click.option("--verbose", "-v", is_flag=True, default=False,
              help="Verbose logging")
def main(
    config_path, output_dir, households, days, live_days, seed,
    no_llm, episode_id, business, verbose
):
    """Generate an Analytics Village episode."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    t0 = time.time()

    # Build config
    if config_path:
        config = SimConfig.from_yaml(config_path)
    else:
        config = SimConfig()

    # Override from CLI flags
    config.num_households = households
    config.history_days = days
    config.live_days = live_days if not no_llm else 0
    config.random_seed = seed
    config.episode_id = episode_id
    config.primary_business = business

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    db_path = os.path.join(output_dir, f"{episode_id}_village.db")

    # Remove existing DB
    if os.path.exists(db_path):
        os.remove(db_path)

    print(f"=== Analytics Village Generator ===")
    print(f"  Episode:    {episode_id}")
    print(f"  Business:   {business}")
    print(f"  Households: {households}")
    print(f"  History:    {days} days")
    print(f"  Live:       {live_days if not no_llm else 0} days")
    print(f"  Seed:       {seed}")
    print(f"  Output:     {output_dir}/")
    print()

    # ── Phase 1: History ─────────────────────────────────────
    print("Phase 1: Compressed History Run")
    run_history(db_path, config, progress_callback=print_progress)
    print()

    # ── Phase 2-3: LLM phases ───────────────────────────────
    if not no_llm and live_days > 0:
        print("Phase 2: LLM Persona Seeding")
        try:
            from .llm_client import OllamaClient
            llm = OllamaClient(
                base_url=config.ollama_base_url,
                model=config.ollama_model,
                max_concurrent=config.max_concurrent_llm,
            )
            if llm.is_available():
                print(f"  Connected to Ollama ({config.ollama_model})")

                db = VillageDB(db_path)
                world = WorldState.from_db(db, config)

                from .persona_seeder import seed_personas_sync
                calls = seed_personas_sync(llm, world, db)
                print(f"  Persona seeding: {calls} LLM calls")

                print(f"\nPhase 3: Live Simulation ({live_days} days)")
                from .live_runner import run_live_sync
                stats = run_live_sync(db, world, llm, config, live_days, print_progress)
                print(f"  Live sim complete: {stats['total_txns']} txns, "
                      f"{stats['llm_calls']} LLM calls")

                # Phase 4: Q&A
                print(f"\nPhase 4: Q&A Generation")
                from .qa_generator import generate_qa_sync
                qa_pairs = generate_qa_sync(llm, db, world, business)
                print(f"  Generated {len(qa_pairs)} Q&A pairs")

                db.close()
            else:
                print("  WARNING: Ollama not available. Skipping LLM phases.")
                qa_pairs = []
        except Exception as e:
            logger.error(f"LLM phases failed: {e}")
            print(f"  ERROR: {e}. Skipping LLM phases.")
            qa_pairs = []
    else:
        qa_pairs = []
        if no_llm:
            print("Skipping LLM phases (--no-llm)")
        print()

    # ── Phase 5: Export ──────────────────────────────────────
    print("Phase 5: Export")
    exporter = EpisodeExporter(db_path, config)
    paths = exporter.export_all(output_dir, qa_pairs=qa_pairs)
    for name, path in paths.items():
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  {name:20s} {path} ({size/1024:.1f} KB)")

    # Summary
    elapsed = time.time() - t0
    print(f"\n=== Generation Complete ===")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Output: {output_dir}/")

    # Quick stats from DB
    db = VillageDB(db_path, read_only=True)
    print(f"  Transactions: {db.count('transactions'):,}")
    print(f"  Households:   {db.count('households'):,}")
    print(f"  SKUs:         {db.count('skus'):,}")
    print(f"  Days:         {config.history_days + (live_days if not no_llm else 0)}")
    db.close()


if __name__ == "__main__":
    main()
