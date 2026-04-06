# CH01 — Open for Business

**Village Fresh Supermarket** | 150 customers | 90 days (Aug–Nov 2024)

Khun Somchai runs the only supermarket in a small Thai village. You have his transaction and inventory data. Help him understand his business.

## Notebooks

| Notebook | Focus |
|----------|-------|
| [ch01_normalized.ipynb](ch01_normalized.ipynb) | SQL joins & data preparation |
| [ch01_star.ipynb](ch01_star.ipynb) | Analysis with pre-joined tables |
| [ch01_analytics.ipynb](ch01_analytics.ipynb) | Build cohort, churn, basket analysis |

## Data

Two SQLite databases with the same data in different structures:

- `data/village_normalized.db` — 4 separate tables (practice joins)
- `data/village_star.db` — star schema with fact/dimension tables

### Tables

| Table | Columns |
|-------|---------|
| products | product_id, product_name, product_name_th, category, subcategory, unit_description |
| calendar | date, day_number, day_of_week, day_of_month, month, year, is_weekend, is_payday_week, event_name, event_type |
| transactions | transaction_id, transaction_date, customer_id, product_id, quantity_sold, unit_price_thb |
| inventory | record_date, product_id, opening_stock, units_sold, units_received, closing_stock |

## Questions

See [questions.json](questions.json) or run `ch.questions()` in a notebook.

## Utilities

The `student/` folder contains Python helpers:
- `Challenge.load()` — load data and explore tables
- `ch.brief()` — read the challenge description
- `ch.questions()` — see guided analysis questions
- `ch.db.query()` — run SQL queries
