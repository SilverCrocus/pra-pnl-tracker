"""API routes for the dashboard."""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.database import get_db, Bet, DailySummary
from app.config import STARTING_BANKROLL, SYNC_API_KEY, calculate_pnl

router = APIRouter()


@router.get("/summary")
async def get_summary(db: Session = Depends(get_db)):
    """Get overall stats for summary cards."""
    # Get all settled bets (exclude VOIDED from win rate calc)
    settled = db.query(Bet).filter(Bet.result.in_(["WON", "LOST"])).all()
    pending = db.query(Bet).filter(Bet.result == "PENDING").count()
    voided = db.query(Bet).filter(Bet.result == "VOIDED").count()

    if not settled:
        return {
            "bankroll": STARTING_BANKROLL,
            "win_rate": 0,
            "roi": 0,
            "total_bets": 0,
            "pending_bets": pending,
            "voided_bets": voided,
            "wins": 0,
            "losses": 0,
        }

    wins = sum(1 for b in settled if b.result == "WON")
    losses = len(settled) - wins
    total_bets = len(settled)
    win_rate = wins / total_bets if total_bets > 0 else 0

    # Calculate current bankroll from daily_summary
    latest = db.query(DailySummary).order_by(desc(DailySummary.date)).first()
    bankroll = latest.bankroll if latest else STARTING_BANKROLL

    # ROI calculation
    total_wagered = sum(b.tier_units for b in settled)
    profit = bankroll - STARTING_BANKROLL
    roi = (profit / total_wagered * 100) if total_wagered > 0 else 0

    return {
        "bankroll": round(bankroll, 2),
        "win_rate": round(win_rate * 100, 1),
        "roi": round(roi, 1),
        "total_bets": total_bets,
        "pending_bets": pending,
        "voided_bets": voided,
        "wins": wins,
        "losses": losses,
    }


@router.get("/bankroll-history")
async def get_bankroll_history(db: Session = Depends(get_db)):
    """Get daily bankroll values for line chart."""
    summaries = db.query(DailySummary).order_by(DailySummary.date).all()

    # Always start with the initial bankroll
    history = [{"date": None, "bankroll": STARTING_BANKROLL}]

    for s in summaries:
        history.append({
            "date": s.date.isoformat(),
            "bankroll": round(s.bankroll, 2)
        })

    return history


@router.get("/daily-pnl")
async def get_daily_pnl(db: Session = Depends(get_db)):
    """Get daily P&L for bar chart."""
    summaries = db.query(DailySummary).order_by(DailySummary.date).all()

    return [
        {
            "date": s.date.isoformat(),
            "pnl": round(s.daily_pnl, 2),
            "wins": s.wins,
            "losses": s.losses,
        }
        for s in summaries
    ]


@router.get("/by-tier")
async def get_by_tier(db: Session = Depends(get_db)):
    """Get win rate breakdown by tier."""
    tiers = db.query(
        Bet.tier,
        func.count(Bet.id).label("total"),
        func.sum(func.cast(Bet.result == "WON", Integer)).label("wins")
    ).filter(
        Bet.result.in_(["WON", "LOST"])
    ).group_by(Bet.tier).all()

    result = []
    for tier, total, wins in tiers:
        wins = wins or 0
        win_rate = (wins / total * 100) if total > 0 else 0
        result.append({
            "tier": tier,
            "wins": wins,
            "total": total,
            "win_rate": round(win_rate, 1),
        })

    return result


@router.get("/by-date")
async def get_by_date(limit: int = 14, db: Session = Depends(get_db)):
    """Get win rate breakdown by date (most recent first)."""
    dates = db.query(
        Bet.game_date,
        func.count(Bet.id).label("total"),
        func.sum(func.cast(Bet.result == "WON", Integer)).label("wins")
    ).filter(
        Bet.result.in_(["WON", "LOST"])
    ).group_by(Bet.game_date).order_by(desc(Bet.game_date)).limit(limit).all()

    result = []
    for game_date, total, wins in dates:
        wins = wins or 0
        win_rate = (wins / total * 100) if total > 0 else 0
        result.append({
            "date": game_date.isoformat(),
            "wins": wins,
            "total": total,
            "win_rate": round(win_rate, 1),
        })

    return result


@router.get("/recent-bets")
async def get_recent_bets(limit: int = 20, db: Session = Depends(get_db)):
    """Get most recent bets with outcomes."""
    bets = db.query(Bet).order_by(
        desc(Bet.game_date),
        desc(Bet.created_at)
    ).limit(limit).all()

    return [
        {
            "id": b.id,
            "game_date": b.game_date.isoformat(),
            "player_name": b.player_name,
            "betting_line": b.betting_line,
            "direction": b.direction,
            "tier": b.tier,
            "tier_units": b.tier_units,
            "prediction": round(b.prediction, 1) if b.prediction else None,
            "actual_pra": round(b.actual_pra, 1) if b.actual_pra else None,
            "result": b.result,
        }
        for b in bets
    ]


@router.post("/run-pipeline")
async def run_pipeline(background_tasks: BackgroundTasks):
    """Triggered by cron job - runs daily pipeline in background."""
    from app.services.pipeline_runner import run_daily_pipeline

    background_tasks.add_task(run_daily_pipeline)

    return {"status": "Pipeline started", "message": "Running in background"}


@router.post("/sync-bets")
async def sync_bets(
    bets: List[dict],
    api_key: str,
    db: Session = Depends(get_db)
):
    """Sync bets from external source (protected by API key)."""
    if api_key != SYNC_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    synced = 0
    for bet_data in bets:
        # Check if bet exists
        existing = db.query(Bet).filter(
            Bet.player_id == bet_data["player_id"],
            Bet.game_date == date.fromisoformat(bet_data["game_date"])
        ).first()

        if existing:
            # Update existing bet
            for key, value in bet_data.items():
                if key == "game_date":
                    value = date.fromisoformat(value)
                if hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            # Create new bet
            bet = Bet(
                player_id=bet_data["player_id"],
                player_name=bet_data["player_name"],
                game_date=date.fromisoformat(bet_data["game_date"]),
                betting_line=bet_data["betting_line"],
                direction=bet_data["direction"],
                prediction=bet_data.get("prediction"),
                tier=bet_data["tier"],
                tier_units=bet_data.get("tier_units", 1.0),
                actual_pra=bet_data.get("actual_pra"),
                actual_minutes=bet_data.get("actual_minutes"),
                result=bet_data.get("result", "PENDING"),
            )
            db.add(bet)
        synced += 1

    db.commit()

    # Recalculate daily summaries
    await recalculate_summaries(db)

    return {"status": "success", "synced": synced}


async def recalculate_summaries(db: Session):
    """Recalculate all daily summaries from bets."""
    # Clear existing summaries
    db.query(DailySummary).delete()

    # Get all settled bets grouped by date
    settled_bets = db.query(Bet).filter(
        Bet.result.in_(["WON", "LOST"])
    ).order_by(Bet.game_date).all()

    if not settled_bets:
        db.commit()
        return

    # Group by date
    by_date = {}
    for bet in settled_bets:
        d = bet.game_date
        if d not in by_date:
            by_date[d] = []
        by_date[d].append(bet)

    # Calculate running bankroll
    bankroll = STARTING_BANKROLL

    for game_date in sorted(by_date.keys()):
        day_bets = by_date[game_date]
        wins = sum(1 for b in day_bets if b.result == "WON")
        losses = len(day_bets) - wins

        # Calculate P&L for the day
        daily_pnl = sum(
            calculate_pnl(b.result == "WON", b.tier_units)
            for b in day_bets
        )
        bankroll += daily_pnl

        summary = DailySummary(
            date=game_date,
            wins=wins,
            losses=losses,
            daily_pnl=daily_pnl,
            bankroll=bankroll,
        )
        db.add(summary)

    db.commit()


@router.get("/health")
async def health_check():
    """Health check endpoint for Render."""
    return {"status": "healthy"}


# Need to import Integer for the cast
from sqlalchemy import Integer
