# Goldilocks V2 PnL Tracker

Public dashboard showing PnL performance of the Goldilocks V2 NBA PRA betting model.

## Features

- Live bankroll tracking from $100 starting point
- Daily P&L visualization
- Win rate breakdown by tier (GOLDEN / HIGH_VOLATILITY)
- Recent bets with outcomes
- Fully automated daily updates

## Tech Stack

- **Backend:** FastAPI
- **Frontend:** HTML + Chart.js
- **Database:** PostgreSQL
- **Hosting:** Render

## Local Development

```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your database URL

# Run locally
uv run uvicorn app.main:app --reload
```

## Deployment

Deployed on Render with:
- Web service (FastAPI)
- PostgreSQL database
- Daily cron job at 4pm AEDT

See `render.yaml` for configuration.
