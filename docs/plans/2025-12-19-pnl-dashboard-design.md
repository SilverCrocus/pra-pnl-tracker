# Goldilocks V2 PnL Dashboard Design

**Date:** 2025-12-19
**Status:** Approved

## Overview

Public showcase dashboard displaying PnL performance for the Goldilocks V2 NBA betting model. Fully automated - runs daily pipeline, tracks results, and serves a web dashboard.

## Architecture

```
pra-pnl-tracker/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── api/
│   │   └── routes.py        # API endpoints for dashboard data
│   ├── services/
│   │   ├── pipeline.py      # Runs the daily pipeline commands
│   │   ├── result_tracker.py # Syncs results to database
│   │   └── pnl_calculator.py # Calculates bankroll progression
│   ├── models/
│   │   └── database.py      # SQLAlchemy models
│   └── static/
│       ├── index.html       # Dashboard page
│       ├── chart.js         # Chart.js chart logic
│       └── styles.css       # Dark theme styles
├── ml_models/               # Trained model files (from NBA_PRA)
├── scripts/
│   └── scheduler.py         # APScheduler for daily job
├── pyproject.toml
├── render.yaml              # Render deployment config
└── README.md
```

## Daily Pipeline

Runs at 4pm AEDT via Render cron job:

```bash
1. uv run nba-pra pipeline --shadow-mode   # Fetch data, run predictions
2. uv run nba-pra goldilocks-v2            # Generate today's picks
3. uv run nba-pra v2-track                 # Update results for past bets
4. Sync to PostgreSQL                      # Dashboard reads from DB
```

## Database Schema

### bets table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| game_date | DATE | Game date |
| player_id | INTEGER | NBA player ID |
| player_name | VARCHAR | Player name |
| betting_line | FLOAT | The betting line |
| direction | VARCHAR | OVER or UNDER |
| tier | VARCHAR | GOLDEN or HIGH_VOLATILITY |
| tier_units | FLOAT | Units wagered (1.0 or 1.5) |
| twostage_prob | FLOAT | Model probability |
| prediction | FLOAT | Model's PRA prediction |
| actual_pra | FLOAT | Actual PRA (nullable) |
| actual_minutes | FLOAT | Minutes played (nullable) |
| result | VARCHAR | WON, LOST, or PENDING |
| created_at | TIMESTAMP | When bet was created |

### daily_summary table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| date | DATE | Summary date |
| total_bets | INTEGER | Bets that day |
| wins | INTEGER | Winning bets |
| losses | INTEGER | Losing bets |
| pending | INTEGER | Pending bets |
| bankroll | FLOAT | Running total from $100 |
| daily_pnl | FLOAT | Day's profit/loss |

## Dashboard UI

### Summary Cards
- Current Bankroll ($)
- Overall Win Rate (%)
- ROI (%)
- Total Bets

### Charts
1. **Bankroll Over Time** - Line chart showing cumulative growth from $100
2. **Daily P&L** - Bar chart with green (profit) / red (loss) bars per day

### Tables
- **By Tier** - Win rate breakdown for GOLDEN vs HIGH_VOLATILITY
- **By Date** - Win rate for each day

### Recent Bets List
- Last 20 bets with player, line, direction, actual result, tier
- Icons: ✅ won, ❌ lost, ⏳ pending

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** HTML + Chart.js (vanilla, no framework)
- **Database:** PostgreSQL
- **Hosting:** Render
- **Styling:** Dark theme, minimal CSS

## Deployment (Render)

| Service | Type | Cost |
|---------|------|------|
| Web Service | FastAPI app | $7/mo (always-on) |
| PostgreSQL | Database | $7/mo (starter) |
| Cron Job | Daily trigger | Free |

**Total:** ~$14/month

### Cron Setup
- Schedule: `0 5 * * *` (5am UTC = 4pm AEDT)
- Endpoint: `POST /api/run-pipeline`
- Triggers full pipeline + DB sync

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Cron Job   │────>│  Pipeline   │────>│ PostgreSQL  │
│  (4pm AEDT) │     │  Commands   │     │  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               v
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │<────│   FastAPI   │<────│  Query DB   │
│  Dashboard  │     │   + HTML    │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Source Data

Model files and pipeline logic copied from `~/Documents/NBA_PRA/`:
- `production/goldilocks_filter_v2.py`
- `production/v2_tracker.py`
- `production/pipeline.py`
- `production/cli.py`
- Trained model files from `models/`

## Success Criteria

- [ ] Dashboard loads with current bankroll and charts
- [ ] Daily pipeline runs automatically at 4pm AEDT
- [ ] Results update correctly after games finish
- [ ] Page loads fast (< 2 seconds)
- [ ] Mobile-friendly layout
