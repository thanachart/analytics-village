# Analytics Village

A simulated economy for teaching real analytics.

One instructor runs a village economy simulation. The simulation generates realistic datasets across multiple businesses. Challenges are packaged as episodes and released to students. Students analyse data, consult a simulated business owner, and submit structured decisions.

## Episodes

| EP | Title | Business | Tier | Status |
|----|-------|----------|------|--------|
| 01 | Open for Business | Village Fresh Supermarket | 1 — Reporting | Active |

## For Students

### Quick Start (Google Colab or Local)

```python
import sys; sys.path.insert(0, '.')
from student import Episode, Decision

ep = Episode.load('ep01', data_dir='data/ep01')
ep.brief()                     # Read the challenge
ep.owner.questions()           # See what you can ask the owner
ep.db.tables()                 # Explore the database
```

### Notebooks

Open `notebooks/ep01_open_for_business.ipynb` to get started with a guided template.

### Submit

1. Build your decision using the `Decision` class
2. Export to `submissions/ep01/YOUR_ID.json`
3. Open a Pull Request

## For Instructors

### Generate a New Episode

```bash
python -m simulation.generate --households 150 --days 90 --no-llm --output data/ep01 --episode-id ep01
```

### Run the Facilitator App

```bash
python -m uvicorn server.main:app --port 8000
# Open http://localhost:8000
```

### With LLM (Ollama)

```bash
# Start Ollama first: ollama serve
# Pull model: ollama pull gemma4:e2b
python -m simulation.generate --households 150 --days 90 --live-days 30 --episode-id ep01 --output data/ep01
```

## Architecture

```
analytics-village/
  simulation/    — Simulation engine (generates village.db)
  student/       — Student Python package (Episode, Decision)
  server/        — FastAPI facilitator backend
  frontend/      — React SPA facilitator UI
  data/          — Generated episode databases
  episodes/      — Episode briefs and schemas
  submissions/   — Student submission JSONs (via PR)
  notebooks/     — Guided analysis notebooks
```

## Tech Stack

- **Simulation:** Python, SQLite, Ollama (gemma4:e2b)
- **Student Package:** pandas, sqlite3, tabulate
- **Facilitator:** FastAPI + React (Vite) with masonry card UI
