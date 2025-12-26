# Live Page: On-Court Status & Game Clock

## Overview

Add two features to the live bet tracking page:
1. Show which players are currently on the court
2. Show minutes remaining in the quarter

## Data Changes

### `app/services/live_tracker.py`

Add `oncourt` field to player stats in `get_player_stats()`:

```python
'oncourt': player.get('oncourt', 0) == '1' or player.get('oncourt', 0) == 1
```

### `app/api/routes.py`

In `/api/live-bets` endpoint:
- Add `oncourt` boolean to each bet in response
- Add `game_clock` (formatted like "5:32") to each game in games array

## UI Changes

### Game Card Header

Add time remaining next to quarter display:

```
┌─────────────────────────────────────────────────────────┐
│ ● LIVE   Q4 · 5:32                   DAL 104 - 115 GSW  │
└─────────────────────────────────────────────────────────┘
```

Currently shows just "Q4", will show "Q4 · 5:32"

### Player Row

Add "ON COURT" badge next to status chip:

```
Brandin Podziemski   [HIT] [ON COURT]              25/17.5
  OVER  17.5 PRA  28.0 min                         ═══════
```

Badge styling:
- Small pill badge, similar to status chip
- Bright cyan/teal color (#22d3ee) to stand out
- Only shown when `oncourt === true` and game is live
- Hidden for finished games or players on bench

## Files to Change

1. `app/services/live_tracker.py` - Add oncourt field to player stats
2. `app/api/routes.py` - Pass oncourt and game_clock through API
3. `app/static/live.js` - Update UI rendering
4. `app/static/live.html` - Add CSS for oncourt badge (if needed)

## API Response Changes

### Bet object additions:
```json
{
  "oncourt": true
}
```

### Game object additions:
```json
{
  "game_clock": "5:32"
}
```
