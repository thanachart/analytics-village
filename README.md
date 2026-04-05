# Analytics Village

A simulated economy for teaching real analytics.

Each **episode** is a standalone data analytics challenge built on a shared village economy simulation. Explore the data, consult the simulated business owner, and submit your structured recommendation.

## Episodes

| EP | Title | Business | Tier |
|----|-------|----------|------|
| [EP01](episodes/ep01/) | Open for Business | Village Fresh Supermarket | 1 — Reporting |

## Quick Start

```python
import sys; sys.path.insert(0, '.')
from student import Episode, Decision

ep = Episode.load('ep01', data_dir='episodes/ep01/data')
ep.brief()                     # Read the challenge
ep.db.tables()                 # See available data tables
ep.owner.questions()           # Ask the business owner questions
```

## Notebooks

Open the guided notebook for your episode:
- [EP01 — Open for Business](notebooks/ep01_open_for_business.ipynb)

## How to Submit

1. Build your decision using the `Decision` class in the notebook
2. Export to `submissions/ep01/YOUR_STUDENT_ID.json`
3. Open a **Pull Request** to this repository
4. Your submission will be validated automatically

## Episode Structure

Each episode folder contains:
```
episodes/ep01/
  data/              — SQLite database with simulation data
    village.db       — Main database (use with ep.db.query())
  brief.md           — Challenge brief
  schema.json        — Submission field requirements
  README.md          — Episode-specific instructions
```

## Student Package

The `student/` directory contains the Python package you'll use:
- `Episode` — Load and explore episode data
- `Decision` — Build, validate, and export your submission
- `Owner` — Consult the simulated business owner

No API keys or LLM required. Everything runs locally.
