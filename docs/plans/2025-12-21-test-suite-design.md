# Test Suite Design for PRA PNL Tracker

**Date:** 2025-12-21
**Status:** Approved

## Goals

- Prevent regressions (catch bugs when code changes)
- Validate core logic (P&L calculations, win rate math, result determination)
- API reliability (endpoints return expected data formats)
- ~90% coverage - comprehensive testing

## Decisions

- **Mock all external dependencies** - NBA API mocked for fast, reliable tests
- **GitHub Actions CI** - Tests run automatically on every push/PR, blocks deploys if tests fail
- **pytest ecosystem** - pytest + pytest-cov + pytest-mock + pytest-asyncio

## Project Structure

```
pra-pnl-tracker/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures (test DB, mock data, test client)
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py       # P&L calculations, constants
│   │   ├── test_db_sync.py      # CSV parsing, bet syncing logic
│   │   ├── test_result_updater.py   # Result determination, API response parsing
│   │   ├── test_live_tracker.py     # Status calculations, minute parsing
│   │   └── test_models.py       # Database model validation
│   ├── api/
│   │   ├── __init__.py
│   │   ├── test_summary.py      # /summary endpoint
│   │   ├── test_bets.py         # /recent-bets, /live-bets, /todays-bets
│   │   ├── test_history.py      # /bankroll-history, /daily-pnl, /by-tier, /by-date
│   │   └── test_actions.py      # /update-results, /sync-bets, /reset-voided
│   └── fixtures/
│       ├── sample_bets.csv      # Test CSV data
│       └── nba_responses.py     # Mock NBA API responses
├── .github/
│   └── workflows/
│       └── tests.yml            # GitHub Actions CI config
└── pyproject.toml               # Updated with pytest dependencies
```

## Core Fixtures

```python
# tests/conftest.py

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.models.database import Base, Bet, DailySummary
from app.main import app
from app.models.database import get_db

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def test_db():
    """Create fresh test database for each test."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    db = TestSession()
    yield db
    db.close()

@pytest.fixture
def client(test_db):
    """FastAPI test client with injected test database."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def sample_bets(test_db):
    """Pre-populated database with realistic test bets."""
    bets = [
        Bet(game_date=date(2025, 12, 19), player_id=1630162, player_name="Anthony Edwards",
            betting_line=34.5, direction="OVER", tier="GOLDEN", tier_units=1.5,
            actual_pra=41.0, actual_minutes=36.5, result="WON"),
        Bet(game_date=date(2025, 12, 19), player_id=1631096, player_name="Chet Holmgren",
            betting_line=26.5, direction="OVER", tier="GOLDEN", tier_units=1.5,
            actual_pra=19.0, actual_minutes=32.0, result="LOST"),
        Bet(game_date=date(2025, 12, 20), player_id=203999, player_name="Nikola Jokic",
            betting_line=45.5, direction="OVER", tier="GOLDEN", tier_units=1.5,
            actual_pra=None, actual_minutes=None, result="PENDING"),
    ]
    test_db.add_all(bets)
    test_db.commit()
    return bets
```

## Critical Unit Tests

### P&L Calculations
```python
class TestPnLCalculations:
    def test_winning_bet_pnl(self):
        result = calculate_pnl(won=True, units=1.0)
        assert result == pytest.approx(0.909, rel=0.01)

    def test_losing_bet_pnl(self):
        result = calculate_pnl(won=False, units=1.0)
        assert result == -1.0

    def test_golden_tier_units(self):
        win_pnl = calculate_pnl(won=True, units=1.5)
        lose_pnl = calculate_pnl(won=False, units=1.5)
        assert win_pnl == pytest.approx(1.364, rel=0.01)
        assert lose_pnl == -1.5
```

### Result Determination
```python
class TestResultDetermination:
    def test_over_bet_wins_when_actual_exceeds_line(self):
        assert determine_result("OVER", 34.5, 41.0, minutes=36.0) == "WON"

    def test_over_bet_loses_when_actual_below_line(self):
        assert determine_result("OVER", 26.5, 19.0, minutes=32.0) == "LOST"

    def test_voided_when_player_dnp(self):
        assert determine_result("OVER", 25.5, 0.0, minutes=0.0) == "VOIDED"

    def test_voided_when_under_one_minute(self):
        assert determine_result("OVER", 25.5, 2.0, minutes=0.5) == "VOIDED"

    def test_pending_when_no_actual_pra(self):
        assert determine_result("OVER", 25.5, None, minutes=None) == "PENDING"
```

## GitHub Actions CI

```yaml
# .github/workflows/tests.yml

name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[test]"

      - name: Run tests with coverage
        run: |
          pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=85
```

## pyproject.toml Additions

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["app"]
omit = ["app/__init__.py", "app/*/__init__.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
]
```

## Test Coverage Target

| Component | Coverage Target |
|-----------|-----------------|
| config.py (P&L calc) | 100% |
| result_updater.py | 95% |
| db_sync.py | 90% |
| live_tracker.py | 90% |
| routes.py | 85% |
| models/database.py | 80% |
| **Overall** | **85%+** |

## Implementation Order

1. Set up test infrastructure (conftest.py, pyproject.toml updates)
2. Write critical unit tests (P&L, result determination)
3. Write API endpoint tests
4. Write service layer tests (db_sync, live_tracker)
5. Add GitHub Actions CI
6. Achieve 85% coverage threshold
