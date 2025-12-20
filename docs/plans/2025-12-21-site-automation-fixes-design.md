# PRA PnL Tracker - Site & Automation Fixes

## Overview

Fix the cron job that updates bet results, improve the live page to show results after games finish, and clean up the home page.

## Problems Identified

1. **Cron job times out**: Uses `LeagueGameLog` which fetches entire season data (~hundreds of thousands of rows) and times out after 120 seconds
2. **Live page hides bets after games end**: Shows generic "Tracking Complete" summary instead of individual bet results
3. **Recent Bets shows pending**: Shows today's pending bets instead of completed bets (decision: remove section entirely)

## Solution Design

### 1. Fix Cron Job (result_updater.py)

**Current approach (broken):**
```python
league_log = leaguegamelog.LeagueGameLog(season=season, ...)  # Times out
```

**New approach:**
Use the same fast endpoints that work in `live_tracker.py`:

```python
def fetch_game_results_by_date(target_date: str) -> Dict[int, Dict]:
    """Fetch player stats for a specific date using scoreboard + boxscore."""

    # 1. Get games for the target date
    board = scoreboard.ScoreBoard()
    games = board.get_dict()['scoreboard']['games']

    # 2. Filter to finished games only
    finished_games = [g for g in games if g['gameStatus'] == 3]

    # 3. Fetch box score for each game
    results = {}
    for game in finished_games:
        box = boxscore.BoxScore(game_id=game['gameId'])
        # Extract player stats...
        for player in players:
            results[player_id] = {'pra': pra, 'minutes': minutes}

    return results
```

**Key changes:**
- Replace `fetch_recent_game_results()` with `fetch_game_results_by_date()`
- Use `nba_api.live.nba.endpoints.scoreboard` and `boxscore`
- Add retry logic (2 retries, 5 second delay)
- Look back 3 days to catch missed updates
- Much smaller payloads (~450 records vs hundreds of thousands)

**Files changed:**
- `app/services/result_updater.py` - Complete rewrite of fetch logic

### 2. Live Page Results Table (live.js)

**Current behavior:**
When `tracking_state === 'complete'`, shows:
```
Tracking Complete
X Hits | Y Misses | Z Total
```

**New behavior:**
Show a results table grouped by outcome:

```
Today's Results: 8/12 Hits (66.7%)    Dec 21

HITS (8)
─────────────────────────────────────
LeBron James    OVER 32.5 → 38 PRA    GOLDEN
Steph Curry     OVER 28.5 → 31 PRA    GOLDEN
...

MISSES (4)
─────────────────────────────────────
Jayson Tatum    OVER 35.5 → 32 PRA    GOLDEN
...

VOIDED (2)
─────────────────────────────────────
Player DNP      OVER 25.5 → DNP       GOLDEN
```

**Key changes:**
- Add `renderResultsTable(bets, date)` function
- Replace `tracking_state === 'complete'` block to call new function
- Group bets: hits first, then misses, then voided
- Win rate excludes voided bets

**Files changed:**
- `app/static/live.js` - Add renderResultsTable(), modify complete state handling
- `app/static/styles.css` - Add styles for results table

### 3. Remove Recent Bets from Home Page

**Changes:**
- Delete Recent Bets section from `index.html`
- Delete `loadRecentBets()` from `chart.js`
- Remove from `loadDashboard()` Promise.all
- Keep `/api/recent-bets` endpoint (no harm, might be useful later)

**Files changed:**
- `app/static/index.html` - Remove Recent Bets HTML
- `app/static/chart.js` - Remove loadRecentBets function

## Error Handling

### Cron Job
- Retry up to 2 times with 5-second delay on API failure
- If single game boxscore fails, skip and continue with others
- Clear logging of which bets updated, which failed
- Look back 3 days to catch missed updates

### Live Page
- No bets today → "No bets for today" (existing)
- Games not started → "Games Starting Soon" (existing)
- Mixed state → Show game cards (existing)
- All finished → Show results table (new)

## Cron Schedule

Keep current schedule:
- `30 5 * * *` (5:30 AM UTC = 4:30 PM Sydney time)
- Right after NBA games typically finish
- Single daily run sufficient with faster approach

## Files to Modify

| File | Change |
|------|--------|
| `app/services/result_updater.py` | Rewrite to use scoreboard/boxscore |
| `app/static/live.js` | Add renderResultsTable() for completed view |
| `app/static/styles.css` | Add results table styles |
| `app/static/index.html` | Remove Recent Bets section |
| `app/static/chart.js` | Remove loadRecentBets() function |

## Testing

1. Run `python cron_update.py` locally to verify NBA API calls work
2. Check Render logs after next scheduled run (4:30 PM Sydney)
3. Visit /live page after games finish to verify results table
4. Visit home page to verify Recent Bets removed, charts still work
