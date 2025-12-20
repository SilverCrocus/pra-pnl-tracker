"""Fetch NBA game results and update bet outcomes."""
import logging
import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import time

from sqlalchemy.orm import Session
from nba_api.live.nba.endpoints import scoreboard, boxscore

from app.models.database import SessionLocal, Bet, DailySummary
from app.config import STARTING_BANKROLL, calculate_pnl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 2
RETRY_DELAY = 5  # seconds


def parse_minutes(minutes_raw) -> float:
    """Parse player minutes from various formats."""
    if minutes_raw is None or minutes_raw == '' or minutes_raw == 'DNP':
        return 0.0

    # ISO 8601 duration: "PT24M30.00S"
    if isinstance(minutes_raw, str) and minutes_raw.startswith('PT'):
        match = re.match(r'PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', minutes_raw)
        if match:
            mins = int(match.group(1)) if match.group(1) else 0
            secs = float(match.group(2)) if match.group(2) else 0.0
            return mins + secs / 60
        return 0.0

    # MM:SS format
    if isinstance(minutes_raw, str) and ':' in minutes_raw:
        try:
            mins, secs = minutes_raw.split(':')
            return int(mins) + int(secs) / 60
        except (ValueError, AttributeError):
            return 0.0

    # Numeric
    try:
        val = float(minutes_raw)
        return val / 60 if val > 100 else val
    except (ValueError, TypeError):
        return 0.0


def fetch_boxscore_with_retry(game_id: str) -> Optional[Dict]:
    """Fetch boxscore with retry logic."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            box = boxscore.BoxScore(game_id=game_id)
            return box.get_dict()
        except Exception as e:
            if attempt < MAX_RETRIES:
                logger.warning(f"Boxscore fetch failed for {game_id}, attempt {attempt + 1}/{MAX_RETRIES + 1}: {e}")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"Boxscore fetch failed for {game_id} after {MAX_RETRIES + 1} attempts: {e}")
                return None


def fetch_game_results_for_date(target_date: date) -> Dict[int, Dict]:
    """
    Fetch player stats for all finished games on a specific date.

    Uses the fast scoreboard + boxscore endpoints instead of bulk LeagueGameLog.

    Args:
        target_date: The date to fetch results for

    Returns:
        Dict mapping player_id to {pra, minutes}
    """
    logger.info(f"Fetching results for {target_date.isoformat()}")
    results = {}

    try:
        # Get scoreboard (shows all games for today/most recent)
        board = scoreboard.ScoreBoard()
        scoreboard_data = board.get_dict()['scoreboard']
        games = scoreboard_data.get('games', [])

        # Check if scoreboard date matches target date
        api_date = scoreboard_data.get('gameDate', '')
        if api_date != target_date.isoformat():
            logger.info(f"Scoreboard date {api_date} doesn't match target {target_date.isoformat()}")
            # The live API only returns today's games, so we can only process today
            # For historical dates, we'll rely on the CSV sync
            return results

        # Filter to finished games only
        finished_games = [g for g in games if g.get('gameStatus') == 3]
        logger.info(f"Found {len(finished_games)} finished games out of {len(games)} total")

        if not finished_games:
            return results

        # Fetch boxscore for each finished game
        for game in finished_games:
            game_id = game['gameId']
            home_team = game.get('homeTeam', {}).get('teamTricode', '???')
            away_team = game.get('awayTeam', {}).get('teamTricode', '???')
            logger.info(f"Fetching boxscore for {away_team} @ {home_team} (game {game_id})")

            time.sleep(0.5)  # Small delay between requests

            box_data = fetch_boxscore_with_retry(game_id)
            if not box_data:
                logger.warning(f"Skipping game {game_id} due to fetch failure")
                continue

            game_data = box_data.get('game', {})

            # Extract player stats from both teams
            for team_key in ['homeTeam', 'awayTeam']:
                team = game_data.get(team_key, {})
                players = team.get('players', [])

                for player in players:
                    player_id = int(player.get('personId', 0))
                    if player_id == 0:
                        continue

                    stats = player.get('statistics', {})
                    if not stats:
                        # Player DNP - no stats
                        results[player_id] = {
                            'pra': 0,
                            'minutes': 0
                        }
                        continue

                    points = stats.get('points', 0)
                    rebounds = stats.get('reboundsTotal', 0)
                    assists = stats.get('assists', 0)
                    pra = points + rebounds + assists

                    minutes_raw = stats.get('minutesCalculated', stats.get('minutes', '0'))
                    minutes = parse_minutes(minutes_raw)

                    results[player_id] = {
                        'pra': pra,
                        'minutes': minutes
                    }

        logger.info(f"Fetched stats for {len(results)} players")
        return results

    except Exception as e:
        logger.error(f"Error fetching game results for {target_date}: {e}")
        return results


def fetch_recent_game_results(days_back: int = 3) -> Dict[tuple, Dict]:
    """
    Fetch game results for recent days.

    Args:
        days_back: Number of days to look back (default 3)

    Returns:
        Dict mapping (player_id, date_str) -> {pra, minutes}
    """
    logger.info(f"Fetching results for last {days_back} days")
    all_results = {}

    today = date.today()

    for day_offset in range(days_back):
        target_date = today - timedelta(days=day_offset)
        date_str = target_date.isoformat()

        day_results = fetch_game_results_for_date(target_date)

        # Add date to the key
        for player_id, stats in day_results.items():
            all_results[(player_id, date_str)] = stats

        # Small delay between days
        if day_offset < days_back - 1:
            time.sleep(1)

    logger.info(f"Total: {len(all_results)} player-game results fetched")
    return all_results


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
    today = date.today()

    for bet in pending_bets:
        key = (bet.player_id, bet.game_date.isoformat())
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


def run_result_update(days_back: int = 3) -> Dict:
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

    # Fetch recent game results using fast endpoints
    results_map = fetch_recent_game_results(days_back)

    if not results_map:
        logger.warning("No game data to process")
        return {"status": "no_data", "updated": 0}

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
