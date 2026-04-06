# Analytics Village

A simulated village economy for learning real-world data analytics.

## Challenges

| ID | Title | Business |
|----|-------|----------|
| [CH01](challenges/ch01/) | Open for Business | Village Fresh Supermarket |

## Quick Start

Open a notebook from the challenge folder:

- [CH01 Normalized](challenges/ch01/ch01_normalized.ipynb) — practice SQL joins
- [CH01 Star Schema](challenges/ch01/ch01_star.ipynb) — analysis with flat tables
- [CH01 Analytics](challenges/ch01/ch01_analytics.ipynb) — build cohort, churn, segmentation

## Student Tables

Each challenge has **4 tables**:

| Table | Columns |
|-------|---------|
| `products` | product_id, product_name, product_name_th, category, subcategory, unit_description |
| `calendar` | date, day_number, day_of_week, day_of_month, month, year, is_weekend, is_payday_week, event_name, event_type |
| `transactions` | transaction_id, transaction_date, customer_id, product_id, quantity_sold, unit_price_thb |
| `inventory` | record_date, product_id, opening_stock, units_sold, units_received, closing_stock |

## Two Database Formats

- **`village_normalized.db`** — 4 separate tables, practice SQL joins
- **`village_star.db`** — `dim_product`, `dim_date`, `fact_sales`, `fact_inventory` (pre-joined)

## Structure

```
challenges/ch01/
    data/
        village_normalized.db
        village_star.db
    brief.md
    questions.json
    ch01_normalized.ipynb
    ch01_star.ipynb
    ch01_analytics.ipynb

student/                Python utilities (Challenge class)
```

## Requirements

```
pandas
tabulate
```
