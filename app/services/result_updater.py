"""Fetch NBA game results and update bet outcomes."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

import pandas as pd
from sqlalchemy.orm import Session
from nba_api.stats.endpoints import leaguegamelog

from app.models.database import SessionLocal, Bet, DailySummary
from app.config import STARTING_BANKROLL, calculate_pnl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom headers to avoid NBA API rate limiting
CUSTOM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://www.nba.com',
    'Referer': 'https://www.nba.com/',
}


def get_current_season() -> str:
    """Get current NBA season string (e.g., '2025-26')."""
    now = datetime.now()
    year = now.year
    month = now.month
    # NBA season starts in October
    if month >= 10:
        return f"{year}-{str(year + 1)[2:]}"
    else:
        return f"{year - 1}-{str(year)[2:]}"


def fetch_recent_game_results(days_back: int = 7) -> pd.DataFrame:
    """
    Fetch NBA game results for recent days.

    Args:
        days_back: Number of days to look back

    Returns:
        DataFrame with player game results
    """
    season = get_current_season()
    logger.info(f"Fetching NBA results for season {season}")

    try:
        time.sleep(2)  # Rate limiting
        league_log = leaguegamelog.LeagueGameLog(
            season=season,
            season_type_all_star='Regular Season',
            player_or_team_abbreviation='P',
            headers=CUSTOM_HEADERS,
            timeout=120
        )
        df = league_log.get_data_frames()[0]

        if df.empty:
            logger.warning("No game data returned from NBA API")
            return pd.DataFrame()

        # Convert game date and filter to recent days
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        cutoff_date = datetime.now() - timedelta(days=days_back)
        df = df[df['GAME_DATE'] >= cutoff_date]

        # Calculate PRA
        df['PRA'] = df['PTS'] + df['REB'] + df['AST']

        logger.info(f"Fetched {len(df)} game results from last {days_back} days")
        return df

    except Exception as e:
        logger.error(f"Error fetching NBA results: {e}")
        return pd.DataFrame()


def build_player_results_map(df: pd.DataFrame) -> Dict[tuple, Dict]:
    """
    Build a lookup map of (player_id, game_date) -> results.

    Args:
        df: DataFrame from NBA API with game results

    Returns:
        Dict mapping (player_id, date_str) to {pra, minutes}
    """
    results = {}

    for _, row in df.iterrows():
        player_id = int(row['PLAYER_ID'])
        game_date = row['GAME_DATE'].strftime('%Y-%m-%d')

        results[(player_id, game_date)] = {
            'pra': float(row['PRA']),
            'minutes': float(row['MIN']) if pd.notna(row['MIN']) else 0
        }

    return results


def update_bet_results(db: Session, results_map: Dict[tuple, Dict]) -> int:
    """
    Update pending bets with actual results.

    Args:
        db: Database session
        results_map: Map of (player_id, date) -> results

    Returns:
        Number of bets updated
    """
    # Get all pending bets
    pending_bets = db.query(Bet).filter(Bet.result == "PENDING").all()
    logger.info(f"Found {len(pending_bets)} pending bets to check")

    updated = 0

    from datetime import date
    today = date.today()

    for bet in pending_bets:
        key = (bet.player_id, bet.game_date.strftime('%Y-%m-%d'))
        days_since_game = (today - bet.game_date).days

        if key in results_map:
            result_data = results_map[key]
            actual_pra = result_data['pra']
            actual_minutes = result_data['minutes']

            bet.actual_pra = actual_pra
            bet.actual_minutes = actual_minutes

            # Determine result
            if actual_minutes < 1:
                bet.result = "VOIDED"
            elif bet.direction == 'OVER':
                bet.result = "WON" if actual_pra > bet.betting_line else "LOST"
            else:
                bet.result = "WON" if actual_pra < bet.betting_line else "LOST"

            updated += 1
            logger.info(f"Updated {bet.player_name}: {actual_pra} PRA, {bet.result}")

        elif days_since_game >= 1:
            # Game has passed but player not in results - they didn't play (DNP)
            bet.result = "VOIDED"
            bet.actual_pra = None
            bet.actual_minutes = 0
            updated += 1
            logger.info(f"VOIDED {bet.player_name}: DNP (not in game results)")

    db.commit()
    return updated


def recalculate_daily_summaries(db: Session):
    """Recalculate all daily summaries from bets."""
    # Clear existing summaries
    db.query(DailySummary).delete()

    # Get all dates with bets
    dates = db.query(Bet.game_date).distinct().order_by(Bet.game_date).all()
    dates = [d[0] for d in dates]

    running_bankroll = STARTING_BANKROLL

    for game_date in dates:
        bets = db.query(Bet).filter(Bet.game_date == game_date).all()

        wins = sum(1 for b in bets if b.result == "WON")
        losses = sum(1 for b in bets if b.result == "LOST")
        pending = sum(1 for b in bets if b.result == "PENDING")

        # Calculate daily P&L
        daily_pnl = 0.0
        for bet in bets:
            if bet.result == "WON":
                daily_pnl += calculate_pnl(True, bet.tier_units)
            elif bet.result == "LOST":
                daily_pnl += calculate_pnl(False, bet.tier_units)

        running_bankroll += daily_pnl

        summary = DailySummary(
            date=game_date,
            total_bets=len(bets),
            wins=wins,
            losses=losses,
            pending=pending,
            daily_pnl=daily_pnl,
            bankroll=running_bankroll
        )
        db.add(summary)

    db.commit()
    logger.info(f"Recalculated summaries for {len(dates)} days")


def run_result_update(days_back: int = 7) -> Dict:
    """
    Main function to update bet results from NBA API.

    Args:
        days_back: Number of days to look back for results

    Returns:
        Dict with update summary
    """
    logger.info("=" * 50)
    logger.info("Starting NBA result update")
    logger.info("=" * 50)

    # Fetch recent game results
    game_data = fetch_recent_game_results(days_back)

    if game_data.empty:
        logger.warning("No game data to process")
        return {"status": "no_data", "updated": 0}

    # Build lookup map
    results_map = build_player_results_map(game_data)
    logger.info(f"Built results map with {len(results_map)} player-games")

    # Update database
    db = SessionLocal()
    try:
        updated = update_bet_results(db, results_map)
        recalculate_daily_summaries(db)

        logger.info("=" * 50)
        logger.info(f"Update complete: {updated} bets updated")
        logger.info("=" * 50)

        return {"status": "success", "updated": updated}

    except Exception as e:
        logger.error(f"Error updating results: {e}")
        db.rollback()
        return {"status": "error", "error": str(e)}

    finally:
        db.close()


if __name__ == "__main__":
    run_result_update()
