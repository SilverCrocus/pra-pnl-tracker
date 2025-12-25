# Homepage Redesign

## Overview

Redesign the Goldilocks V2 PnL Tracker homepage from a basic/blocky dashboard to a premium, modern interface inspired by Uniswap and Phantom wallet aesthetics.

## Design Goals

- **Premium + Futuristic vibe** - Sleek, expensive feel with subtle tech flair
- **Clear visual hierarchy** - Bankroll as hero, supporting metrics secondary
- **Moderate glassmorphism** - Frosted glass cards, gradient borders, subtle glows
- **Focused content** - Remove clutter, keep what matters

## Layout Structure

### 1. Hero Section

Large frosted glass card at the top containing:

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│            $247.83                                  │
│         ↑ +$147.83 (147.8%)                        │
│                                                     │
│   [All Time]  [This Week]  [This Month]            │
│                                                     │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│   │ Win Rate │  │   ROI    │  │  Today   │        │
│   │  61.2%   │  │  +24.3%  │  │ 4-1 +$12 │        │
│   │  32W-20L │  │  52 bets │  │          │        │
│   └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────┘
```

**Elements:**
- Bankroll: Large (3-4rem), bold, centered, with subtle glow (green when positive, red when negative)
- Profit/loss indicator: Shows change from starting bankroll with percentage
- Time period toggles: Pill buttons to switch between All Time / This Week / This Month
- Supporting metric pills: Win Rate, ROI, Today's Record in smaller frosted cards

### 2. Charts Section

Two charts side-by-side in frosted glass containers:

```
┌─────────────────────────────┐  ┌─────────────────────────────┐
│  Bankroll Over Time         │  │  Daily P&L                  │
│  (line chart)               │  │  (bar chart)                │
└─────────────────────────────┘  └─────────────────────────────┘
```

**Bankroll Over Time:**
- Line chart showing cumulative bankroll
- Gradient fill underneath the line (green when above starting point)
- Subtle glow on the line

**Daily P&L:**
- Bar chart showing profit/loss per day
- Green bars for winning days, red bars for losing days
- Subtle glow effects on bars

**Responsive:** Charts stack vertically on mobile

### 3. Removed Elements

- Tier breakdown table (removed)
- Date breakdown table (removed)
- Pending bets card (removed)

## Visual Specifications

### Colors

```css
/* Background */
--bg-gradient-start: #0a0a12;
--bg-gradient-end: #12121f;

/* Accent gradient (borders, glows) */
--accent-start: #3b82f6;  /* blue */
--accent-end: #8b5cf6;    /* purple */

/* Semantic colors */
--positive: #22c55e;      /* green - profits */
--negative: #ef4444;      /* red - losses */
--text-primary: #e4e4e7;
--text-secondary: #a1a1aa;
--text-muted: #71717a;
```

### Glassmorphism Cards

```css
.glass-card {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* Gradient border effect (using pseudo-element or border-image) */
.glass-card-accent {
  position: relative;
}
.glass-card-accent::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 16px;
  padding: 1px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.5;
}
```

### Typography

```css
/* Hero bankroll number */
.bankroll-value {
  font-size: 3.5rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 40px rgba(34, 197, 94, 0.3); /* green glow when positive */
}

/* Labels */
.stat-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

/* Metric values */
.stat-value {
  font-size: 1.25rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
```

### Micro-interactions

- **Time period toggle:** Stats fade and shift slightly when switching periods
- **Card hover:** Subtle increase in glow/border opacity
- **Number updates:** Smooth number transition animation when values change
- **Positive/negative glow:** Numbers have soft colored shadow based on value

## Background

Subtle gradient background instead of flat color:

```css
body {
  background: linear-gradient(135deg, #0a0a12 0%, #12121f 50%, #0a0a12 100%);
  min-height: 100vh;
}
```

Optional: Add a subtle noise texture or aurora mesh effect for extra depth.

## Responsive Behavior

**Desktop (>768px):**
- Hero section full width
- Charts side-by-side

**Mobile (<=768px):**
- Hero section stacks vertically
- Supporting pills may wrap to 2 rows
- Charts stack vertically
- Touch-friendly toggle buttons

## Reference Designs

- [Uniswap](https://app.uniswap.org) - Glassmorphism, gradient accents
- [Phantom Wallet](https://phantom.app) - Premium dark theme, glowing elements
