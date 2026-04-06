# Analytics Village

A simulated village economy for learning data analytics.

## How It Works

A Thai village with **150 households** shops at a local supermarket over 90 days. The simulation generates realistic transaction data — what people buy, when they buy it, how much they spend, and what goes in and out of stock.

You get the raw data. Your job: find patterns, answer questions, and recommend actions.

## Challenges

| Challenge | Title | What You'll Learn |
|-----------|-------|-------------------|
| [CH01](challenges/ch01/) | Open for Business | Revenue analysis, customer behavior, inventory patterns |

Each challenge folder contains everything you need:
- **Notebooks** — guided analysis with SQL examples
- **Data** — SQLite databases (normalized + star schema)
- **Questions** — 10 guided analysis questions
- **Utilities** — Python helpers to load and explore data

## Getting Started

1. Open a challenge folder (e.g. `challenges/ch01/`)
2. Pick a notebook:
   - `ch01_normalized.ipynb` — practice SQL joins
   - `ch01_star.ipynb` — focus on analysis
   - `ch01_analytics.ipynb` — build cohort, churn, segmentation
3. Run the first cell to download data and start exploring

## Student Data (4 Tables)

Every challenge gives you the same 4 clean tables:

| Table | What's in it |
|-------|-------------|
| **products** | Product catalogue — name, category, unit description |
| **calendar** | Dates with day-of-week, month, weekend/payday flags, events |
| **transactions** | Every item sold — date, customer, product, quantity, price |
| **inventory** | Daily stock levels — opening, sold, received, closing |

Everything else (customer segments, churn, revenue trends) — you derive from these tables.

## Requirements

```
pandas
tabulate
```

No API keys. No LLM. Everything runs locally or in Google Colab.
