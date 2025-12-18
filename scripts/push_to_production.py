#!/usr/bin/env python3
"""Push local bet data to production API."""

import json
import glob
import pandas as pd
import httpx
from pathlib import Path

# Configuration
PRODUCTION_URL = "https://pra-pnl-tracker.onrender.com"
API_KEY = "5mFbYUegphFYJKpPGFXwCh6EeRXrR0v10ZcoBAnXj44"

# Path to NBA_PRA bets directory
NBA_PRA_BETS = Path.home() / "Documents" / "NBA_PRA" / "bets"


def load_bets() -> list[dict]:
    """Load all V2 bets from CSV files."""
    pattern = str(NBA_PRA_BETS / "goldilocks_v2_*.csv")
    files = glob.glob(pattern)

    if not files:
        print(f"No bet files found at {pattern}")
        return []

    all_bets = []
    for filepath in files:
        df = pd.read_csv(filepath)

        for _, row in df.iterrows():
            # Determine result
            result = "PENDING"
            if pd.notna(row.get("actual_pra")):
                actual_minutes = row.get("actual_minutes", 0) or 0
                if actual_minutes < 1:
                    result = "VOIDED"
                elif row["direction"] == "OVER":
                    result = "WON" if row["actual_pra"] > row["betting_line"] else "LOST"
                else:
                    result = "WON" if row["actual_pra"] < row["betting_line"] else "LOST"

            bet = {
                "player_id": int(row["player_id"]),
                "player_name": row["player_name"],
                "game_date": row["game_date"],
                "betting_line": float(row["betting_line"]),
                "direction": row["direction"],
                "prediction": float(row["prediction"]) if pd.notna(row.get("prediction")) else None,
                "tier": row["tier"],
                "tier_units": float(row.get("tier_units", 1.0)),
                "actual_pra": float(row["actual_pra"]) if pd.notna(row.get("actual_pra")) else None,
                "actual_minutes": float(row["actual_minutes"]) if pd.notna(row.get("actual_minutes")) else None,
                "result": result,
            }
            all_bets.append(bet)

    print(f"Loaded {len(all_bets)} bets from {len(files)} files")
    return all_bets


def push_to_production(bets: list[dict]):
    """Push bets to production API."""
    url = f"{PRODUCTION_URL}/api/sync-bets"

    response = httpx.post(
        url,
        params={"api_key": API_KEY},
        json=bets,
        timeout=60.0
    )

    if response.status_code == 200:
        result = response.json()
        print(f"Success! Synced {result['synced']} bets to production")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def main():
    print("Loading bets from NBA_PRA...")
    bets = load_bets()

    if not bets:
        print("No bets to sync")
        return

    print(f"\nPushing {len(bets)} bets to production...")
    push_to_production(bets)

    print(f"\nDashboard: {PRODUCTION_URL}")


if __name__ == "__main__":
    main()
