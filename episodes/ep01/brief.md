# EP01 - Analytics Challenge

## Your Client

You've been hired as a data analyst consultant for a small business in a Thai village.

## The Situation

The business owner has 30 days of historical data and needs your help understanding their business performance and making data-driven decisions.

## Your Task

1. **Explore the data** - Use SQL and Python to understand the business
2. **Consult the owner** - Ask questions to understand context beyond the numbers
3. **Analyse patterns** - Find insights that the owner might not see
4. **Make a recommendation** - Propose a specific, actionable plan

## Data Available

You have access to a SQLite database with transaction records, customer data, inventory logs, and more. Use `ep.db.tables()` to see what's available.

## Budget

You have up to **10,000 THB** for any recommended actions.

## Deadline

Submit your `decision.json` before the deadline shown in `ep.status()`.

## Getting Started

```python
from analytics_village import Episode, Decision
ep = Episode.load("ep01")
ep.brief()
ep.owner.questions()
ep.db.tables()
```
