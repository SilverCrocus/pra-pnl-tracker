"""Application configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "ml_models"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pra_pnl.db")

# API Key for sync endpoint (set in environment)
SYNC_API_KEY = os.getenv("SYNC_API_KEY", "dev-key-change-me")

# Betting config
STARTING_BANKROLL = 100.0
STANDARD_ODDS = -110  # American odds

# Calculated values
# At -110 odds: bet $110 to win $100, so profit on win = stake * (100/110) = 0.909
WIN_MULTIPLIER = 100 / 110  # ~0.909


def calculate_pnl(won: bool, units: float) -> float:
    """Calculate P&L for a bet at -110 odds.

    Args:
        won: Whether the bet won
        units: Units wagered

    Returns:
        Profit (positive) or loss (negative) in units
    """
    if won:
        return units * WIN_MULTIPLIER
    else:
        return -units
