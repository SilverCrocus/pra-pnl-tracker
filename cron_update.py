#!/usr/bin/env python3
"""
Cron job script to update bet results from NBA API.
Run daily to fetch game results and update the database.
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.result_updater import run_result_update


def main():
    print("=" * 60)
    print("PRA PnL Tracker - Daily Result Update")
    print("=" * 60)

    # Look back 3 days to catch any missed updates
    result = run_result_update(days_back=3)

    print(f"\nResult: {result}")

    if result["status"] == "success":
        print(f"Successfully updated {result['updated']} bets")
        sys.exit(0)
    elif result["status"] == "no_data":
        print("No new data available")
        sys.exit(0)
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
