"""Live NBA game tracking service."""

import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from nba_api.live.nba.endpoints import scoreboard, boxscore

logger = logging.getLogger(__name__)


class LiveTracker:
    """Tracks live PRA stats for NBA players."""

    def get_live_games(self) -> List[Dict]:
        """Get all games happening today."""
        try:
            board = scoreboard.ScoreBoard()
            games_data = board.get_dict()['scoreboard']['games']

            games = []
            for g in games_data:
                status_code = g['gameStatus']
                if status_code == 1:
                    status_text = "Not Started"
                elif status_code == 2:
                    status_text = "Live"
                elif status_code == 3:
                    status_text = "Finished"
                else:
                    status_text = g.get('gameStatusText', 'Unknown')

                games.append({
                    'game_id': g['gameId'],
                    'status': status_code,
                    'status_text': status_text,
                    'home_team': g['homeTeam']['teamTricode'],
                    'away_team': g['awayTeam']['teamTricode'],
                    'home_score': g['homeTeam'].get('score', 0),
                    'away_score': g['awayTeam'].get('score', 0),
                    'period': g.get('period', 0),
                    'game_time': g.get('gameClock', ''),
                })

            return games

        except Exception as e:
            logger.error(f"Error fetching games: {e}")
            return []

    def get_player_stats(self, game_id: str) -> pd.DataFrame:
        """Get PRA stats for all players in a game."""
        try:
            box = boxscore.BoxScore(game_id=game_id)
            game_data = box.get_dict()['game']

            players = []
            for team_key in ['homeTeam', 'awayTeam']:
                team = game_data[team_key]
                team_code = team['teamTricode']

                for player in team['players']:
                    if player.get('statistics'):
                        stats = player['statistics']
                        players.append({
                            'player_id': int(player.get('personId', 0)),
                            'player': f"{player['firstName']} {player['familyName']}",
                            'team': team_code,
                            'points': stats.get('points', 0),
                            'rebounds': stats.get('reboundsTotal', 0),
                            'assists': stats.get('assists', 0),
                            'pra': (
                                stats.get('points', 0) +
                                stats.get('reboundsTotal', 0) +
                                stats.get('assists', 0)
                            ),
                            'minutes': stats.get('minutesCalculated', 'DNP'),
                        })

            return pd.DataFrame(players)

        except Exception as e:
            logger.error(f"Error fetching player stats for game {game_id}: {e}")
            return pd.DataFrame()

    def get_all_live_stats(self) -> Dict[str, Dict]:
        """Get live stats for all players keyed by player_id."""
        games = self.get_live_games()
        active_games = [g for g in games if g['status'] in [2, 3]]

        all_stats = {}
        for game in active_games:
            game_stats = self.get_player_stats(game['game_id'])
            if not game_stats.empty:
                for _, row in game_stats.iterrows():
                    all_stats[row['player_id']] = {
                        'current_pra': row['pra'],
                        'minutes': row['minutes'],
                        'game': f"{game['away_team']} @ {game['home_team']}",
                        'period': game['period'],
                        'game_time': game['game_time'],
                        'game_status': game['status_text'],
                    }

        return all_stats, games

    def parse_minutes(self, minutes_raw) -> float:
        """Parse player minutes from various formats."""
        if minutes_raw is None or minutes_raw == '' or minutes_raw == 'DNP':
            return 0.0

        if not isinstance(minutes_raw, (str, int, float)):
            return 0.0

        try:
            if pd.isna(minutes_raw):
                return 0.0
        except (ValueError, TypeError):
            return 0.0

        # ISO 8601 duration: "PT24M30.00S"
        if isinstance(minutes_raw, str) and minutes_raw.startswith('PT'):
            match = re.match(r'PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', minutes_raw)
            if match:
                mins = int(match.group(1)) if match.group(1) else 0
                secs = float(match.group(2)) if match.group(2) else 0.0
                return mins + secs / 60

        # MM:SS format
        if isinstance(minutes_raw, str) and ':' in minutes_raw:
            try:
                mins, secs = minutes_raw.split(':')
                return int(mins) + int(secs) / 60
            except (ValueError, AttributeError):
                pass

        # Numeric
        try:
            val = float(minutes_raw)
            return val / 60 if val > 100 else val
        except (ValueError, TypeError):
            return 0.0

    def calculate_tracking_status(
        self,
        current_pra: Optional[float],
        line: float,
        direction: str,
        minutes_played: float,
        game_status: str
    ) -> Dict:
        """Calculate tracking status for a bet."""

        # Not started
        if game_status == 'Not Started' or current_pra is None:
            return {
                'status': 'not_started',
                'status_text': 'NOT STARTED',
                'status_color': 'gray',
                'distance': None,
                'projected': None,
            }

        # Calculate projection
        if minutes_played > 0:
            rate = current_pra / minutes_played
            avg_minutes = 34.0
            remaining = max(0, avg_minutes - minutes_played)
            projected = current_pra + (rate * remaining)
        else:
            projected = 0

        # Finished game
        if game_status == 'Finished':
            if direction == 'OVER':
                if current_pra >= line:
                    return {
                        'status': 'hit',
                        'status_text': 'HIT',
                        'status_color': 'green',
                        'distance': current_pra - line,
                        'projected': current_pra,
                    }
                else:
                    return {
                        'status': 'miss',
                        'status_text': 'MISS',
                        'status_color': 'red',
                        'distance': current_pra - line,
                        'projected': current_pra,
                    }
            else:  # UNDER
                if current_pra <= line:
                    return {
                        'status': 'hit',
                        'status_text': 'HIT',
                        'status_color': 'green',
                        'distance': line - current_pra,
                        'projected': current_pra,
                    }
                else:
                    return {
                        'status': 'miss',
                        'status_text': 'MISS',
                        'status_color': 'red',
                        'distance': line - current_pra,
                        'projected': current_pra,
                    }

        # Live game - OVER bets
        if direction == 'OVER':
            distance = line - current_pra

            if current_pra >= line:
                return {
                    'status': 'hit',
                    'status_text': 'HIT',
                    'status_color': 'green',
                    'distance': current_pra - line,
                    'projected': projected,
                }
            elif projected >= line * 1.05:
                return {
                    'status': 'on_track',
                    'status_text': 'ON TRACK',
                    'status_color': 'green',
                    'distance': distance,
                    'projected': projected,
                }
            elif projected >= line * 0.85:
                return {
                    'status': 'needs_more',
                    'status_text': 'NEEDS MORE',
                    'status_color': 'yellow',
                    'distance': distance,
                    'projected': projected,
                }
            else:
                return {
                    'status': 'unlikely',
                    'status_text': 'UNLIKELY',
                    'status_color': 'red',
                    'distance': distance,
                    'projected': projected,
                }

        # Live game - UNDER bets
        else:
            margin = line - current_pra

            if current_pra > line:
                return {
                    'status': 'busted',
                    'status_text': 'BUSTED',
                    'status_color': 'red',
                    'distance': current_pra - line,
                    'projected': projected,
                }
            elif projected <= line * 0.95:
                return {
                    'status': 'safe',
                    'status_text': 'SAFE',
                    'status_color': 'green',
                    'distance': margin,
                    'projected': projected,
                }
            elif projected <= line:
                return {
                    'status': 'close',
                    'status_text': 'CLOSE',
                    'status_color': 'yellow',
                    'distance': margin,
                    'projected': projected,
                }
            else:
                return {
                    'status': 'danger',
                    'status_text': 'DANGER',
                    'status_color': 'red',
                    'distance': margin,
                    'projected': projected,
                }


# Singleton instance
live_tracker = LiveTracker()
