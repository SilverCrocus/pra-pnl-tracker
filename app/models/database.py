"""Database models and connection setup."""
import os
from datetime import datetime, date
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pra_pnl.db")

# Handle Render's postgres:// URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Bet(Base):
    """Individual bet record."""
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    game_date = Column(Date, nullable=False, index=True)
    player_id = Column(Integer, nullable=False)
    player_name = Column(String, nullable=False)
    betting_line = Column(Float, nullable=False)
    direction = Column(String, nullable=False)  # OVER or UNDER
    tier = Column(String, nullable=False)  # GOLDEN or HIGH_VOLATILITY
    tier_units = Column(Float, nullable=False)
    twostage_prob = Column(Float, nullable=True)
    prediction = Column(Float, nullable=True)
    actual_pra = Column(Float, nullable=True)
    actual_minutes = Column(Float, nullable=True)
    result = Column(String, default="PENDING")  # WON, LOST, or PENDING
    created_at = Column(DateTime, default=datetime.utcnow)


class DailySummary(Base):
    """Daily aggregated stats for fast dashboard queries."""
    __tablename__ = "daily_summary"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    total_bets = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    bankroll = Column(Float, default=100.0)
    daily_pnl = Column(Float, default=0.0)


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
