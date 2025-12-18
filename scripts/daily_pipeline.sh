#!/bin/bash
# Daily pipeline script - Run at 4pm AEDT (5am UTC)
# This runs the NBA_PRA model and pushes results to production

set -e

cd ~/Documents/NBA_PRA

echo "$(date): Starting daily pipeline..."

# Run the prediction pipeline in shadow mode
echo "Running pipeline..."
uv run nba-pra pipeline --shadow-mode

# Generate V2 bets
echo "Generating goldilocks-v2 bets..."
uv run nba-pra goldilocks-v2

# Update bet results from NBA data
echo "Updating bet results..."
uv run nba-pra v2-track

# Push to production dashboard
echo "Pushing to production..."
cd ~/Documents/pra-pnl-tracker
python scripts/push_to_production.py

echo "$(date): Pipeline complete!"
