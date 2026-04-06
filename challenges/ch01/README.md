# CH01 — Open for Business

**Village Fresh Supermarket** | Tier 1 | Aug–Nov 2024

## Notebooks

| Notebook | Database | Focus |
|----------|----------|-------|
| [ch01_normalized.ipynb](ch01_normalized.ipynb) | `village_normalized.db` | SQL joins & data prep |
| [ch01_star.ipynb](ch01_star.ipynb) | `village_star.db` | Analysis with flat tables |
| [ch01_analytics.ipynb](ch01_analytics.ipynb) | Either | Build cohort, churn, basket analysis |

## Student Tables (4 only)

**`products`** — product_id, product_name, product_name_th, category, subcategory, unit_description

**`calendar`** — date, day_number, day_of_week, day_of_month, month, year, is_weekend, is_payday_week, event_name, event_type

**`transactions`** — transaction_id, transaction_date, customer_id, product_id, quantity_sold, unit_price_thb

**`inventory`** — record_date, product_id, opening_stock, units_sold, units_received, closing_stock
