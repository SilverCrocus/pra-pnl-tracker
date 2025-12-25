# Live & Bets Pages Redesign

## Overview

Redesign the Live tracking page and Today's Bets page to match the new premium glassmorphism design system established on the homepage.

## Live Page

### Purpose
Track today's bets in real-time - both quick status check ("Are my bets hitting?") and detailed progress tracking.

### Hero Summary Section

Glassmorphism card at the top with key stats:

| Stat | Description |
|------|-------------|
| Hits / Total | e.g., "4/7" - Core success metric |
| Today's P&L | Running profit/loss, green/red colored |
| Win Rate % | Percentage hitting so far |
| Pending | Count of games not yet started |

Below stats: status line showing "● 2 games live · ○ 3 games upcoming"

### Game Cards

Cards grouped by NBA game matchup.

**Card Header:**
- Status badge: "● LIVE" (pulsing), "UPCOMING", or "FINAL"
- Game clock: Quarter + time remaining (e.g., "Q3 · 4:32")
- Score: "LAL 87 - 92 GSW"

**Player Rows:**
- Player name
- Direction: OVER/UNDER badge
- Line: The betting line (e.g., 24.5)
- Progress: Current PRA / Target (e.g., "18 / 24.5")
- On-court status: 🟢 On Court / ⚪ Bench
- Progress bar: Color-coded (green = on track/hit, yellow = warning, red = behind)

### Progress Bar Colors
- **Green (hit/on-track)**: Already hit the line, or pace suggests success
- **Yellow (warning)**: Behind pace but still possible
- **Red (danger)**: Significantly behind, unlikely to hit
- **Gold glow**: Confirmed hit (game finished)

---

## Bets Page

### Purpose
Reference for placing bets - see all picks organized by game for efficient bet placement.

### Hero Summary Section

Glassmorphism card showing:
- Date: "TODAY'S PICKS · DEC 25"
- Total bets count
- Total units
- Number of games

### Game Cards

Cards organized by game matchup, sorted by game start time (earliest first).

**Card Header:**
- Game: "🏀 LAL @ GSW"
- Time: "7:30 PM"
- Pick count: "3 picks"

**Player Rows:**
- Player name (prominent)
- Direction + Line: "OVER 24.5 PRA"
- Predicted PRA: "Pred: 28.2" (model's prediction showing the edge)
- Tier badge: ⭐ GOLDEN or 🥉 BRONZE
- Units: "1.5u"

---

## Visual Specifications

Both pages use the same design tokens as homepage:

### Colors
```css
--bg-deep: #06060b;
--glass-bg: rgba(255, 255, 255, 0.02);
--glass-border: rgba(255, 255, 255, 0.06);
--accent-primary: #6366f1;
--positive: #10b981;
--negative: #ef4444;
```

### Components
- Ambient background glows (same as homepage)
- Header with logo icon + nav tabs
- Glassmorphism cards with gradient borders
- Plus Jakarta Sans typography

### Status Badges
```css
/* Live - pulsing red */
.status-live { background: rgba(239, 68, 68, 0.15); color: #f87171; }

/* Upcoming - blue */
.status-upcoming { background: rgba(99, 102, 241, 0.15); color: #818cf8; }

/* Final - muted */
.status-final { background: rgba(113, 113, 122, 0.15); color: #a1a1aa; }
```

### Tier Badges
```css
/* Golden */
.tier-golden { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }

/* Bronze */
.tier-bronze { background: rgba(180, 83, 9, 0.2); color: #d97706; }
```

---

## Data Requirements

### Live Page API
Current `/api/live-bets` endpoint provides most data. May need to add:
- On-court status (requires NBA API check)
- Game clock details (quarter, time remaining)

### Bets Page API
Current `/api/todays-bets` groups by team. Need to modify to:
- Group by game matchup instead of team
- Include game start time
- Sort by game time (earliest first)
