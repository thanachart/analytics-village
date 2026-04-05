# CH01 - Analytics Challenge

## Your client: Khun Somchai, Village Fresh Supermarket

Khun Somchai has been running Village Fresh for 8 years. He needs your help understanding his business performance and making data-driven decisions.

## Your Task

1. **Explore the data** - Use SQL and Python to understand the business
2. **Consult the owner** - Ask questions to understand context beyond the numbers
3. **Analyse patterns** - Find insights the owner might not see
4. **Make a recommendation** - Propose a specific, actionable plan

## Data Available

SQLite database with transaction records, customer data, inventory logs, and more. Use `ch.db.tables()` to see what's available.

## Budget

Up to **10,000 THB** for any recommended actions.

## Getting Started

```python
from student import Challenge, Decision
ch = Challenge.load('ch01', data_dir='challenges/ch01/data')
ch.brief()
ch.db.tables()
ch.owner.questions()
```
