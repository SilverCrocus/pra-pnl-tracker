#!/bin/bash
# Push new goldilocks bets to production
# Run this after: uv run nba-pra pipeline --shadow-mode

set -e

NBA_PRA_DIR="$HOME/Documents/NBA_PRA"
TRACKER_DIR="$HOME/Documents/pra-pnl-tracker"

echo "=== Pushing Goldilocks Bets to Production ==="

# Copy all goldilocks CSVs from NBA_PRA to tracker
echo "Copying CSVs..."
cp "$NBA_PRA_DIR/production/outputs/bets/goldilocks_v3_"*.csv "$TRACKER_DIR/data/"

# Count files
COUNT=$(ls -1 "$TRACKER_DIR/data/goldilocks_v3_"*.csv 2>/dev/null | wc -l | tr -d ' ')
echo "Copied $COUNT CSV files"

# Git add, commit, push
cd "$TRACKER_DIR"
git add -f data/goldilocks_v3_*.csv

if git diff --staged --quiet; then
    echo "No changes to commit"
else
    DATE=$(date +%Y-%m-%d)
    git commit -m "Update goldilocks bets for $DATE"
    git push origin main
    echo "Pushed to production!"
fi

echo "=== Done ==="
