#!/usr/bin/env python3
"""
Import existing goldilocks_v2 data from NBA_PRA repo for local testing.

Usage:
    uv run python scripts/import_from_nba_pra.py
"""
import shutil
from pathlib import Path

# Paths
NBA_PRA_DIR = Path.home() / "Documents" / "NBA_PRA"
LOCAL_DATA_DIR = Path(__file__).parent.parent / "data"

BETS_SOURCE = NBA_PRA_DIR / "production" / "outputs" / "bets"


def import_goldilocks_files():
    """Copy goldilocks_v2 CSV files from NBA_PRA to local data dir."""
    LOCAL_DATA_DIR.mkdir(exist_ok=True)

    # Find all goldilocks_v2 files
    source_files = list(BETS_SOURCE.glob("goldilocks_v2_*.csv"))

    if not source_files:
        print(f"No goldilocks_v2 files found in {BETS_SOURCE}")
        return

    print(f"Found {len(source_files)} goldilocks_v2 files")

    for src in sorted(source_files):
        dst = LOCAL_DATA_DIR / src.name
        shutil.copy(src, dst)
        print(f"  Copied: {src.name}")

    print(f"\nFiles copied to: {LOCAL_DATA_DIR}")


def sync_to_database():
    """Sync imported files to the local database."""
    from app.services.db_sync import sync_all_bets
    from app.models.database import init_db

    print("\nInitializing database...")
    init_db()

    print("Syncing bets to database...")
    sync_all_bets(LOCAL_DATA_DIR)

    print("Done!")


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("Importing data from NBA_PRA repo")
    print("=" * 50)

    # Check NBA_PRA exists
    if not NBA_PRA_DIR.exists():
        print(f"ERROR: NBA_PRA directory not found at {NBA_PRA_DIR}")
        sys.exit(1)

    if not BETS_SOURCE.exists():
        print(f"ERROR: Bets directory not found at {BETS_SOURCE}")
        sys.exit(1)

    # Import CSV files
    import_goldilocks_files()

    # Sync to database
    sync_to_database()
