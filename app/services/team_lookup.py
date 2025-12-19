"""Team lookup service using NBA API."""

import logging
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

from nba_api.stats.endpoints import commonallplayers

logger = logging.getLogger(__name__)

# Cache for player-to-team mapping
_player_team_cache: Dict[int, str] = {}
_cache_timestamp: Optional[datetime] = None
_cache_ttl = timedelta(hours=6)  # Refresh every 6 hours


def get_player_team_map(force_refresh: bool = False) -> Dict[int, str]:
    """
    Get a mapping of player_id -> team_abbreviation.

    Uses caching to avoid hitting the NBA API repeatedly.
    """
    global _player_team_cache, _cache_timestamp

    # Check if cache is valid
    if not force_refresh and _cache_timestamp and _player_team_cache:
        if datetime.now() - _cache_timestamp < _cache_ttl:
            return _player_team_cache

    # Fetch fresh data
    try:
        logger.info("Fetching player-team mapping from NBA API...")
        time.sleep(1)  # Rate limiting

        players = commonallplayers.CommonAllPlayers(
            is_only_current_season=1,
            timeout=60
        )
        df = players.get_data_frames()[0]

        # Build the mapping
        _player_team_cache = {}
        for _, row in df.iterrows():
            player_id = int(row['PERSON_ID'])
            team = row['TEAM_ABBREVIATION']
            if team:  # Skip players without a team
                _player_team_cache[player_id] = team

        _cache_timestamp = datetime.now()
        logger.info(f"Cached {len(_player_team_cache)} player-team mappings")

        return _player_team_cache

    except Exception as e:
        logger.error(f"Error fetching player-team mapping: {e}")
        # Return existing cache if available, otherwise empty dict
        return _player_team_cache if _player_team_cache else {}


def get_player_team(player_id: int) -> Optional[str]:
    """Get the team abbreviation for a specific player."""
    team_map = get_player_team_map()
    return team_map.get(player_id)
