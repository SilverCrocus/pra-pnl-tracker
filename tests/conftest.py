"""Shared test fixtures for PRA PNL Tracker."""
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.models.database import Base, Bet, DailySummary, get_db
from app.main import app

# In-memory SQLite for fast tests - use StaticPool to share connection
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_engine():
    """Create test database engine with shared connection pool."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Share same connection for all requests
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db(test_engine):
    """Create fresh test database session for each test."""
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSession()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def client(test_db):
    """FastAPI test client with injected test database."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_bets(test_db):
    """Pre-populated database with realistic test bets."""
    bets = [
        # Dec 19 - Settled bets (1 win, 1 loss)
        Bet(
            game_date=date(2025, 12, 19),
            player_id=1630162,
            player_name="Anthony Edwards",
            betting_line=34.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            twostage_prob=0.65,
            prediction=39.7,
            actual_pra=41.0,
            actual_minutes=36.5,
            result="WON",
            created_at=datetime(2025, 12, 19, 10, 0, 0)
        ),
        Bet(
            game_date=date(2025, 12, 19),
            player_id=1631096,
            player_name="Chet Holmgren",
            betting_line=26.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            twostage_prob=0.73,
            prediction=33.7,
            actual_pra=19.0,
            actual_minutes=32.0,
            result="LOST",
            created_at=datetime(2025, 12, 19, 10, 0, 0)
        ),
        # Dec 20 - Pending bet
        Bet(
            game_date=date(2025, 12, 20),
            player_id=203999,
            player_name="Nikola Jokic",
            betting_line=45.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            twostage_prob=0.68,
            prediction=50.2,
            actual_pra=None,
            actual_minutes=None,
            result="PENDING",
            created_at=datetime(2025, 12, 20, 10, 0, 0)
        ),
        # Voided bet (DNP)
        Bet(
            game_date=date(2025, 12, 18),
            player_id=1629029,
            player_name="Luka Doncic",
            betting_line=48.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            twostage_prob=0.70,
            prediction=52.0,
            actual_pra=0.0,
            actual_minutes=0.0,
            result="VOIDED",
            created_at=datetime(2025, 12, 18, 10, 0, 0)
        ),
        # Under bet that won
        Bet(
            game_date=date(2025, 12, 17),
            player_id=1628369,
            player_name="Jayson Tatum",
            betting_line=42.5,
            direction="UNDER",
            tier="HIGH_VOLATILITY",
            tier_units=1.0,
            twostage_prob=0.62,
            prediction=38.5,
            actual_pra=35.0,
            actual_minutes=34.0,
            result="WON",
            created_at=datetime(2025, 12, 17, 10, 0, 0)
        ),
    ]
    test_db.add_all(bets)
    test_db.commit()

    # Refresh to get IDs
    for bet in bets:
        test_db.refresh(bet)

    return bets


@pytest.fixture
def sample_summaries(test_db, sample_bets):
    """Pre-populated daily summaries matching sample bets."""
    summaries = [
        DailySummary(
            date=date(2025, 12, 17),
            total_bets=1,
            wins=1,
            losses=0,
            pending=0,
            daily_pnl=0.909,  # 1 unit * 0.909 win multiplier
            bankroll=100.909
        ),
        DailySummary(
            date=date(2025, 12, 18),
            total_bets=1,
            wins=0,
            losses=0,
            pending=0,
            daily_pnl=0.0,  # Voided, no P&L impact
            bankroll=100.909
        ),
        DailySummary(
            date=date(2025, 12, 19),
            total_bets=2,
            wins=1,
            losses=1,
            pending=0,
            daily_pnl=1.5 * 0.909 - 1.5,  # Win 1.364, lose 1.5 = -0.136
            bankroll=100.773
        ),
        DailySummary(
            date=date(2025, 12, 20),
            total_bets=1,
            wins=0,
            losses=0,
            pending=1,
            daily_pnl=0.0,
            bankroll=100.773
        ),
    ]
    test_db.add_all(summaries)
    test_db.commit()
    return summaries


@pytest.fixture
def empty_db(test_db):
    """Empty database for testing zero-state scenarios."""
    return test_db
