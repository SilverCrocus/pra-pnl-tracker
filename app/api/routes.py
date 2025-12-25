"""API routes for the dashboard."""
from datetime import date, datetime, timedelta
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


@router.post("/update-results")
async def update_results(days_back: int = 3):
    """Manually trigger result update from NBA API."""
    from app.services.result_updater import run_result_update

    result = run_result_update(days_back=days_back)
    return result


@router.post("/update-results-for-date")
async def update_results_for_date(target_date: str, db: Session = Depends(get_db)):
    """
    Update results for a specific date.
    First resets any wrongly-VOIDED bets for that date, then fetches fresh results.

    Args:
        target_date: Date in YYYY-MM-DD format
    """
    from datetime import date as date_module
    from app.services.result_updater import fetch_game_results_for_date, update_bet_results, recalculate_daily_summaries

    try:
        target = date_module.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # First, reset any VOIDED bets for this date that don't have actual_pra
    voided_bets = db.query(Bet).filter(
        Bet.game_date == target,
        Bet.result == "VOIDED",
        Bet.actual_pra.is_(None)
    ).all()

    reset_count = 0
    for bet in voided_bets:
        bet.result = "PENDING"
        bet.actual_minutes = None
        reset_count += 1

    db.commit()

    # Fetch results for the specific date
    results = fetch_game_results_for_date(target)

    if not results:
        return {
            "status": "no_games",
            "date": target_date,
            "reset": reset_count,
            "updated": 0,
            "message": f"No finished games found for {target_date}"
        }

    # Build results map with date
    results_map = {(player_id, target_date): stats for player_id, stats in results.items()}

    # Update bets
    updated = update_bet_results(db, results_map)
    recalculate_daily_summaries(db)

    return {
        "status": "success",
        "date": target_date,
        "reset": reset_count,
        "updated": updated,
        "players_found": len(results)
    }


@router.post("/reset-voided")
async def reset_voided_bets(db: Session = Depends(get_db)):
    """Reset wrongly-VOIDED bets back to PENDING for re-evaluation."""
    # Find VOIDED bets that don't have actual_pra set (wrongly voided)
    voided_bets = db.query(Bet).filter(
        Bet.result == "VOIDED",
        Bet.actual_pra.is_(None)
    ).all()

    reset_count = 0
    for bet in voided_bets:
        bet.result = "PENDING"
        bet.actual_minutes = None
        reset_count += 1

    db.commit()

    return {"status": "success", "reset": reset_count}


@router.delete("/delete-bet")
async def delete_bet(
    player_id: int,
    game_date: str,
    api_key: str,
    db: Session = Depends(get_db)
):
    """Delete a specific bet by player_id and game_date (protected by API key)."""
    if api_key != SYNC_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    target_date = date.fromisoformat(game_date)
    bet = db.query(Bet).filter(
        Bet.player_id == player_id,
        Bet.game_date == target_date
    ).first()

    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")

    player_name = bet.player_name
    db.delete(bet)
    db.commit()

    # Recalculate summaries
    from app.services.result_updater import recalculate_daily_summaries
    recalculate_daily_summaries(db)

    return {"status": "success", "deleted": player_name, "game_date": game_date}


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


@router.get("/live-bets")
async def get_live_bets(db: Session = Depends(get_db)):
    """Get today's bets with live tracking status."""
    from datetime import date as date_module
    from zoneinfo import ZoneInfo
    from app.services.live_tracker import live_tracker

    # Get today's date in Eastern time (NBA schedule timezone)
    eastern = ZoneInfo('America/New_York')
    today = datetime.now(eastern).date()

    # Get today's bets from database
    todays_bets = db.query(Bet).filter(
        Bet.game_date == today
    ).all()

    if not todays_bets:
        return {"bets": [], "games": [], "summary": {"total": 0, "live": 0, "hits": 0, "pending": 0}, "tracking_state": "no_bets", "date": today.isoformat()}

    # Get live stats from NBA API - filter to only today's games
    try:
        live_stats, games = live_tracker.get_all_live_stats(filter_date=today.isoformat())
    except Exception as e:
        live_stats = {}
        games = []

    # Merge bets with live stats
    result = []
    hits = 0
    live_count = 0
    pending = 0

    for bet in todays_bets:
        player_stats = live_stats.get(bet.player_id, {})

        current_pra = player_stats.get('current_pra')
        minutes_raw = player_stats.get('minutes', 0)
        minutes_played = live_tracker.parse_minutes(minutes_raw)
        game_status = player_stats.get('game_status', 'Not Started')

        # Calculate tracking status
        status_info = live_tracker.calculate_tracking_status(
            current_pra=current_pra,
            line=bet.betting_line,
            direction=bet.direction,
            minutes_played=minutes_played,
            game_status=game_status
        )

        # Count stats
        if status_info['status'] == 'hit':
            hits += 1
        if game_status == 'Live':
            live_count += 1
        if game_status == 'Not Started':
            pending += 1

        # Format period display
        period = player_stats.get('period', 0)
        if period == 0:
            period_text = "-"
        elif period <= 4:
            period_text = f"Q{period}"
        elif period == 5:
            period_text = "OT"
        else:
            period_text = f"{period - 4}OT"

        result.append({
            "player_name": bet.player_name,
            "player_id": bet.player_id,
            "betting_line": bet.betting_line,
            "direction": bet.direction,
            "tier": bet.tier,
            "prediction": round(bet.prediction, 1) if bet.prediction else None,
            "current_pra": current_pra,
            "minutes_played": f"{minutes_played:.1f}" if minutes_played else "0:00",
            "projected_pra": round(status_info['projected'], 1) if status_info['projected'] else None,
            "game": player_stats.get('game', '-'),
            "period": period_text,
            "game_time": player_stats.get('game_time', '-'),
            "game_status": game_status,
            "status": status_info['status'],
            "status_text": status_info['status_text'],
            "status_color": status_info['status_color'],
            "distance": round(status_info['distance'], 1) if status_info['distance'] is not None else None,
        })

    # Format games for display
    games_summary = [
        {
            "game": f"{g['away_team']} @ {g['home_team']}",
            "score": f"{g['away_score']} - {g['home_score']}",
            "status": g['status_text'],
            "period": g['period'],
        }
        for g in games
    ]

    # Determine tracking state
    finished_count = sum(1 for b in result if b['game_status'] == 'Finished')
    all_finished = finished_count == len(result) and finished_count > 0
    all_pending = pending == len(result)

    if all_finished:
        tracking_state = "complete"
    elif all_pending:
        tracking_state = "upcoming"
    elif live_count > 0:
        tracking_state = "live"
    else:
        tracking_state = "mixed"

    return {
        "bets": result,
        "games": games_summary,
        "summary": {
            "total": len(todays_bets),
            "live": live_count,
            "hits": hits,
            "pending": pending,
            "finished": finished_count,
        },
        "tracking_state": tracking_state,
        "date": today.isoformat(),
    }


@router.get("/todays-bets")
async def get_todays_bets(db: Session = Depends(get_db)):
    """Get today's bet recommendations organized by game matchup."""
    from zoneinfo import ZoneInfo
    from app.services.team_lookup import get_player_team_map
    from app.services.live_tracker import live_tracker

    # Get today's date in Eastern time (NBA schedule timezone)
    eastern = ZoneInfo('America/New_York')
    today = datetime.now(eastern).date()

    # Get today's bets from database
    todays_bets = db.query(Bet).filter(
        Bet.game_date == today
    ).order_by(Bet.tier, Bet.player_name).all()

    if not todays_bets:
        return {
            "date": today.isoformat(),
            "games": [],
            "summary": {"total_bets": 0, "total_units": 0, "games_count": 0}
        }

    # Get player-to-team mapping from NBA API
    player_team_map = {}
    try:
        player_team_map = get_player_team_map()
    except Exception as e:
        pass  # Continue without team data if API fails

    # Get today's games from NBA API to build team-to-game mapping
    team_to_game = {}
    try:
        # Try live scoreboard first
        games = live_tracker.get_live_games(filter_date=today.isoformat())
        if not games:
            games = live_tracker.get_live_games()

        # If still no games, use ScoreboardV2 which has schedule data
        if not games:
            from nba_api.stats.endpoints import scoreboardv2
            from nba_api.stats.static import teams as nba_teams

            # Build team ID to tricode map
            team_id_to_tricode = {t['id']: t['abbreviation'] for t in nba_teams.get_teams()}

            scoreboard = scoreboardv2.ScoreboardV2(game_date=today.strftime('%m/%d/%Y'))
            games_df = scoreboard.get_data_frames()[0]

            for _, row in games_df.iterrows():
                home_code = team_id_to_tricode.get(row['HOME_TEAM_ID'], 'UNK')
                away_code = team_id_to_tricode.get(row['VISITOR_TEAM_ID'], 'UNK')
                matchup = f"{away_code} @ {home_code}"
                team_to_game[home_code] = matchup
                team_to_game[away_code] = matchup
        else:
            for game in games:
                matchup = f"{game['away_team']} @ {game['home_team']}"
                team_to_game[game['home_team']] = matchup
                team_to_game[game['away_team']] = matchup
    except Exception as e:
        pass  # Continue without game data if API fails

    # Build bets grouped by game matchup
    games_dict = {}
    total_units = 0

    # Define tier order for sorting (GOLDEN/GOLD first)
    tier_order = {'GOLDEN': 0, 'GOLD': 0, 'BRONZE': 1}

    for bet in todays_bets:
        team = player_team_map.get(bet.player_id, "UNK")
        game_matchup = team_to_game.get(team, f"{team} Game")

        bet_data = {
            "player_name": bet.player_name,
            "player_id": bet.player_id,
            "team": team,
            "betting_line": bet.betting_line,
            "direction": bet.direction,
            "tier": bet.tier,
            "tier_units": bet.tier_units,
            "prediction": round(bet.prediction, 1) if bet.prediction else None,
            "probability": round(bet.twostage_prob * 100, 1) if bet.twostage_prob else None,
            "result": bet.result,
            "actual_pra": bet.actual_pra,
        }

        if game_matchup not in games_dict:
            games_dict[game_matchup] = {
                "matchup": game_matchup,
                "bets": []
            }

        games_dict[game_matchup]["bets"].append(bet_data)
        total_units += bet.tier_units

    # Sort bets within each game by tier (Golden first, then Bronze)
    for game in games_dict.values():
        game["bets"].sort(key=lambda b: (tier_order.get(b["tier"], 2), b["player_name"]))

    # Sort games by number of bets (most first), then alphabetically
    sorted_games = sorted(
        games_dict.values(),
        key=lambda x: (-len(x["bets"]), x["matchup"])
    )

    return {
        "date": today.isoformat(),
        "games": sorted_games,
        "summary": {
            "total_bets": len(todays_bets),
            "total_units": round(total_units, 1),
            "games_count": len(sorted_games)
        }
    }


@router.get("/recent-results")
async def get_recent_results(days: int = 3, db: Session = Depends(get_db)):
    """Get recent settled bet results for display."""
    from zoneinfo import ZoneInfo

    # Get today's date in Eastern time
    eastern = ZoneInfo('America/New_York')
    today = datetime.now(eastern).date()

    # Get bets from recent days (excluding today)
    recent_bets = db.query(Bet).filter(
        Bet.game_date < today,
        Bet.game_date >= today - timedelta(days=days),
        Bet.result.in_(["WON", "LOST", "VOIDED"])
    ).order_by(desc(Bet.game_date), Bet.player_name).all()

    # Group by date
    by_date = {}
    for bet in recent_bets:
        date_str = bet.game_date.isoformat()
        if date_str not in by_date:
            by_date[date_str] = {
                "date": date_str,
                "bets": [],
                "wins": 0,
                "losses": 0,
                "voided": 0
            }

        by_date[date_str]["bets"].append({
            "player_name": bet.player_name,
            "betting_line": bet.betting_line,
            "direction": bet.direction,
            "tier": bet.tier,
            "actual_pra": round(bet.actual_pra, 1) if bet.actual_pra else None,
            "result": bet.result,
        })

        if bet.result == "WON":
            by_date[date_str]["wins"] += 1
        elif bet.result == "LOST":
            by_date[date_str]["losses"] += 1
        else:
            by_date[date_str]["voided"] += 1

    # Convert to list sorted by date descending
    results = sorted(by_date.values(), key=lambda x: x["date"], reverse=True)

    # Calculate win rate for each day
    for day in results:
        settled = day["wins"] + day["losses"]
        day["win_rate"] = round((day["wins"] / settled * 100), 1) if settled > 0 else 0
        day["total"] = len(day["bets"])

    return {
        "days": results,
        "total_days": len(results)
    }


@router.get("/health")
async def health_check():
    """Health check endpoint for Render."""
    return {"status": "healthy"}


# Need to import Integer for the cast
from sqlalchemy import Integer
