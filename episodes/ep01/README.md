# EP01 — Open for Business

**Business:** Village Fresh Supermarket (Khun Somchai)
**Tier:** 1 — Reporting
**Challenge:** Sales reporting, aggregation, time series, KPIs

## Quick Start

```python
from student import Episode, Decision
ep = Episode.load('ep01', data_dir='../../data/ep01')
ep.brief()
ep.db.tables()
ep.owner.questions()
```

## Data

- `data/ep01/village.db` — SQLite database with all simulation tables
- `episodes/ep01/schema.json` — Submission field requirements
- `episodes/ep01/brief.md` — Episode brief

## Submission

Export your `decision.json` to `submissions/ep01/` and open a Pull Request.
