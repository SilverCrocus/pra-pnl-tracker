"""Sync bet data from CSV files to PostgreSQL database."""
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import pandas as pd
from sqlalchemy.orm import Session

from app.models.database import SessionLocal, Bet, DailySummary
from app.config import STARTING_BANKROLL, calculate_pnl


def get_goldilocks_csv_files(data_dir: Path) -> List[Path]:
    """Find all goldilocks_v4_*.csv files."""
    pattern = str(data_dir / "goldilocks_v4_*.csv")
    return sorted(glob.glob(pattern))


def sync_bets_from_csv(csv_path: Path, db: Session) -> int:
    """
    Sync bets from a single CSV file to the database.

    This does a FULL SYNC for the date - removes any bets not in the CSV.

    Returns number of new/updated bets.
    """
    df = pd.read_csv(csv_path)

    if df.empty:
        return 0

    # Get the game date from the CSV
    game_date = datetime.strptime(df.iloc[0]['game_date'], '%Y-%m-%d').date()

    # Get all player_ids in this CSV
    csv_player_ids = set(int(row['player_id']) for _, row in df.iterrows())

    # Delete any existing bets for this date that are NOT in the CSV
    # (This handles when CSV is updated with different players)
    existing_bets = db.query(Bet).filter(Bet.game_date == game_date).all()
    for bet in existing_bets:
        if bet.player_id not in csv_player_ids:
            db.delete(bet)

    count = 0

    for _, row in df.iterrows():
        # Check if bet already exists
        existing = db.query(Bet).filter(
            Bet.game_date == row['game_date'],
            Bet.player_id == row['player_id']
        ).first()

        # Determine result
        result = "PENDING"
        actual_minutes = row.get('actual_minutes')

        if pd.notna(row.get('actual_pra')):
            # Check for DNP/injury - player didn't play or played < 1 minute
            # These bets are typically voided by sportsbooks
            if pd.notna(actual_minutes) and actual_minutes < 1:
                result = "VOIDED"
            elif row['direction'] == 'OVER':
                result = "WON" if row['actual_pra'] > row['betting_line'] else "LOST"
            else:
                result = "WON" if row['actual_pra'] < row['betting_line'] else "LOST"
        # NOTE: Don't auto-void bets without results - leave them PENDING
        # for result_updater to fetch from NBA API

        if existing:
            # Update existing bet (but preserve result if already settled)
            if existing.result == "PENDING":
                existing.actual_pra = row.get('actual_pra') if pd.notna(row.get('actual_pra')) else None
                existing.actual_minutes = row.get('actual_minutes') if pd.notna(row.get('actual_minutes')) else None
                existing.result = result
            elif pd.notna(row.get('actual_pra')):
                # Update actual values if CSV has them
                existing.actual_pra = float(row['actual_pra'])
                existing.actual_minutes = float(row['actual_minutes']) if pd.notna(row.get('actual_minutes')) else None
        else:
            # Create new bet
            bet = Bet(
                game_date=game_date,
                player_id=int(row['player_id']),
                player_name=row['player_name'],
                betting_line=float(row['betting_line']),
                direction=row['direction'],
                tier=row['tier'],
                tier_units=float(row['tier_units']),
                twostage_prob=float(row.get('twostage_prob', 0)) if pd.notna(row.get('twostage_prob')) else None,
                prediction=float(row.get('mean_pred', row.get('twostage_pred', 0))) if pd.notna(row.get('mean_pred', row.get('twostage_pred'))) else None,
                actual_pra=float(row['actual_pra']) if pd.notna(row.get('actual_pra')) else None,
                actual_minutes=float(row['actual_minutes']) if pd.notna(row.get('actual_minutes')) else None,
                result=result,
                created_at=datetime.utcnow()
            )
            db.add(bet)
            count += 1

    db.commit()
    return count


def recalculate_daily_summaries(db: Session):
    """Recalculate all daily summaries from bets."""
    # Get all unique dates with bets
    dates = db.query(Bet.game_date).distinct().order_by(Bet.game_date).all()
    dates = [d[0] for d in dates]

    running_bankroll = STARTING_BANKROLL

    for game_date in dates:
        bets = db.query(Bet).filter(Bet.game_date == game_date).all()

        wins = sum(1 for b in bets if b.result == "WON")
        losses = sum(1 for b in bets if b.result == "LOST")
        pending = sum(1 for b in bets if b.result == "PENDING")
        voided = sum(1 for b in bets if b.result == "VOIDED")

        # Calculate daily P&L (VOIDED bets don't affect P&L - money returned)
        daily_pnl = 0.0
        for bet in bets:
            if bet.result == "WON":
                daily_pnl += calculate_pnl(True, bet.tier_units)
            elif bet.result == "LOST":
                daily_pnl += calculate_pnl(False, bet.tier_units)
            # VOIDED bets: no P&L impact (stake returned)

        running_bankroll += daily_pnl

        # Update or create summary
        summary = db.query(DailySummary).filter(DailySummary.date == game_date).first()

        if summary:
            summary.total_bets = len(bets)
            summary.wins = wins
            summary.losses = losses
            summary.pending = pending
            summary.daily_pnl = daily_pnl
            summary.bankroll = running_bankroll
        else:
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


def sync_all_bets(data_dir: Path = None):
    """
    Sync all goldilocks CSV files to the database.

    Args:
        data_dir: Directory containing CSV files. Defaults to project's data dir.
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent.parent / "data"

    db = SessionLocal()
    try:
        csv_files = get_goldilocks_csv_files(data_dir)
        total_new = 0

        for csv_path in csv_files:
            new_count = sync_bets_from_csv(Path(csv_path), db)
            total_new += new_count
            print(f"Synced {csv_path}: {new_count} new bets")

        # Recalculate summaries after all bets are synced
        recalculate_daily_summaries(db)

        print(f"Total: {total_new} new bets synced, summaries recalculated")
        return total_new

    finally:
        db.close()


if __name__ == "__main__":
    sync_all_bets()
