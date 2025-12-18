# PnL Dashboard Implementation Plan

**Date:** 2025-12-19
**Design Doc:** [2025-12-19-pnl-dashboard-design.md](./2025-12-19-pnl-dashboard-design.md)

---

## Task 1: Project Setup

**Files to create:**
- `pyproject.toml` - Project dependencies
- `.gitignore` - Standard Python ignores
- `.python-version` - Python 3.11
- `README.md` - Basic project description

**Dependencies:**
```toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "pandas>=2.0.0",
    "python-dotenv>=1.0.0",
    "apscheduler>=3.10.0",
    "httpx>=0.25.0",
    "nba-api>=1.4.0",
]
```

---

## Task 2: Copy Files from NBA_PRA

**Files to copy from `~/Documents/NBA_PRA/`:**

```
production/goldilocks_filter_v2.py  → app/services/goldilocks_filter.py
production/v2_tracker.py           → app/services/v2_tracker.py
production/config.py               → app/config.py (modify paths)
```

**Model files to copy:**
```
models/                            → ml_models/ (trained model files)
data/nba_api/player_games.parquet  → data/player_games.parquet (initial data)
```

**Note:** Will need to modify import paths and hardcoded paths in copied files.

---

## Task 3: Database Models

**File:** `app/models/database.py`

```python
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

class Bet(Base):
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True)
    game_date = Column(Date, nullable=False)
    player_id = Column(Integer, nullable=False)
    player_name = Column(String, nullable=False)
    betting_line = Column(Float, nullable=False)
    direction = Column(String, nullable=False)  # OVER/UNDER
    tier = Column(String, nullable=False)  # GOLDEN/HIGH_VOLATILITY
    tier_units = Column(Float, nullable=False)
    twostage_prob = Column(Float)
    prediction = Column(Float)
    actual_pra = Column(Float, nullable=True)
    actual_minutes = Column(Float, nullable=True)
    result = Column(String, default="PENDING")  # WON/LOST/PENDING
    created_at = Column(DateTime)

class DailySummary(Base):
    __tablename__ = "daily_summary"

    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    total_bets = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    bankroll = Column(Float, default=100.0)
    daily_pnl = Column(Float, default=0.0)
```

---

## Task 4: FastAPI Backend

**File:** `app/main.py`

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import routes

app = FastAPI(title="Goldilocks V2 PnL Tracker")

app.include_router(routes.router, prefix="/api")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def root():
    return FileResponse("app/static/index.html")
```

**File:** `app/api/routes.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db, Bet, DailySummary

router = APIRouter()

@router.get("/summary")
async def get_summary(db: Session = Depends(get_db)):
    """Get overall stats for summary cards."""
    # Return bankroll, win_rate, roi, total_bets

@router.get("/bankroll-history")
async def get_bankroll_history(db: Session = Depends(get_db)):
    """Get daily bankroll values for line chart."""
    # Return list of {date, bankroll}

@router.get("/daily-pnl")
async def get_daily_pnl(db: Session = Depends(get_db)):
    """Get daily P&L for bar chart."""
    # Return list of {date, pnl}

@router.get("/by-tier")
async def get_by_tier(db: Session = Depends(get_db)):
    """Get win rate breakdown by tier."""

@router.get("/by-date")
async def get_by_date(db: Session = Depends(get_db)):
    """Get win rate breakdown by date."""

@router.get("/recent-bets")
async def get_recent_bets(limit: int = 20, db: Session = Depends(get_db)):
    """Get most recent bets with outcomes."""

@router.post("/run-pipeline")
async def run_pipeline():
    """Triggered by cron job - runs daily pipeline."""
    # 1. Run pipeline --shadow-mode
    # 2. Run goldilocks-v2
    # 3. Run v2-track
    # 4. Sync results to database
```

---

## Task 5: Frontend Dashboard

**File:** `app/static/index.html`

Structure:
- Summary cards section (4 cards)
- Bankroll chart (Chart.js line)
- Daily P&L chart (Chart.js bar)
- Two-column: By Tier / By Date tables
- Recent bets table

**File:** `app/static/chart.js`

- Fetch data from `/api/bankroll-history` and `/api/daily-pnl`
- Render two Chart.js charts
- Dark theme colors

**File:** `app/static/styles.css`

- Dark theme (bg: #1a1a2e, cards: #16213e)
- Responsive grid layout
- Table styling

---

## Task 6: Pipeline Runner Service

**File:** `app/services/pipeline_runner.py`

```python
import subprocess
from pathlib import Path
from app.services.db_sync import sync_bets_to_database

def run_daily_pipeline():
    """Run the full daily pipeline."""
    project_root = Path(__file__).parent.parent.parent

    # Step 1: Run pipeline --shadow-mode
    subprocess.run(
        ["uv", "run", "nba-pra", "pipeline", "--shadow-mode"],
        cwd=project_root,
        check=True
    )

    # Step 2: Run goldilocks-v2
    subprocess.run(
        ["uv", "run", "nba-pra", "goldilocks-v2"],
        cwd=project_root,
        check=True
    )

    # Step 3: Run v2-track
    subprocess.run(
        ["uv", "run", "nba-pra", "v2-track"],
        cwd=project_root,
        check=True
    )

    # Step 4: Sync to database
    sync_bets_to_database()
```

**File:** `app/services/db_sync.py`

- Read goldilocks_v2_*.csv files
- Upsert bets to database
- Recalculate daily_summary table
- Update bankroll running total

---

## Task 7: Render Deployment Config

**File:** `render.yaml`

```yaml
services:
  - type: web
    name: pra-pnl-tracker
    env: python
    buildCommand: pip install -e .
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: pra-pnl-db
          property: connectionString
      - key: PYTHON_VERSION
        value: "3.11"

databases:
  - name: pra-pnl-db
    plan: starter

cron:
  - name: daily-pipeline
    schedule: "0 5 * * *"  # 5am UTC = 4pm AEDT
    command: curl -X POST https://pra-pnl-tracker.onrender.com/api/run-pipeline
```

**File:** `.env.example`

```
DATABASE_URL=postgresql://user:pass@localhost:5432/pra_pnl
```

---

## Task 8: Testing & Deployment

1. **Local testing:**
   - Set up local PostgreSQL or use SQLite for dev
   - Run `uvicorn app.main:app --reload`
   - Test all API endpoints
   - Verify charts render correctly

2. **Deploy to Render:**
   - Push to GitHub
   - Connect repo to Render
   - Create PostgreSQL database
   - Deploy web service
   - Set up cron job

3. **Verify:**
   - Manually trigger `/api/run-pipeline`
   - Check database has data
   - Verify dashboard displays correctly

---

## File Structure (Final)

```
pra-pnl-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pipeline_runner.py
│   │   ├── db_sync.py
│   │   ├── pnl_calculator.py
│   │   ├── goldilocks_filter.py  (copied from NBA_PRA)
│   │   └── v2_tracker.py         (copied from NBA_PRA)
│   └── static/
│       ├── index.html
│       ├── chart.js
│       └── styles.css
├── data/
│   └── .gitkeep
├── ml_models/
│   └── .gitkeep
├── docs/
│   └── plans/
│       ├── 2025-12-19-pnl-dashboard-design.md
│       └── 2025-12-19-implementation-plan.md
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── render.yaml
└── README.md
```

---

## Execution Order

1. [ ] Task 1: Project setup (pyproject.toml, .gitignore, etc.)
2. [ ] Task 2: Copy files from NBA_PRA, adjust imports
3. [ ] Task 3: Database models
4. [ ] Task 4: FastAPI backend + routes
5. [ ] Task 5: Frontend dashboard (HTML, CSS, JS)
6. [ ] Task 6: Pipeline runner + DB sync
7. [ ] Task 7: Render config
8. [ ] Task 8: Test locally, deploy, verify
