"""Mock NBA API responses for testing without hitting real API."""

# ScoreboardV3 response format
MOCK_SCOREBOARD_FINISHED = {
    "scoreboard": {
        "games": [
            {
                "gameId": "0022400400",
                "gameStatus": 3,  # Final
                "gameStatusText": "Final",
                "homeTeam": {
                    "teamTricode": "MIN",
                    "score": 112
                },
                "awayTeam": {
                    "teamTricode": "OKC",
                    "score": 105
                }
            },
            {
                "gameId": "0022400401",
                "gameStatus": 3,  # Final
                "gameStatusText": "Final",
                "homeTeam": {
                    "teamTricode": "BOS",
                    "score": 118
                },
                "awayTeam": {
                    "teamTricode": "PHI",
                    "score": 110
                }
            }
        ]
    }
}

MOCK_SCOREBOARD_LIVE = {
    "scoreboard": {
        "games": [
            {
                "gameId": "0022400402",
                "gameStatus": 2,  # In Progress
                "gameStatusText": "Q3 5:30",
                "period": 3,
                "gameClock": "PT05M30S",
                "homeTeam": {
                    "teamTricode": "LAL",
                    "score": 85
                },
                "awayTeam": {
                    "teamTricode": "GSW",
                    "score": 78
                }
            }
        ]
    }
}

MOCK_SCOREBOARD_EMPTY = {
    "scoreboard": {
        "games": []
    }
}

# BoxScoreTraditionalV3 response format
MOCK_BOXSCORE_GAME_400 = {
    "boxScoreTraditional": {
        "homeTeam": {
            "teamTricode": "MIN",
            "players": [
                {
                    "personId": 1630162,
                    "name": "Anthony Edwards",
                    "statistics": {
                        "points": 28,
                        "reboundsTotal": 8,
                        "assists": 5,
                        "minutes": "PT36M25S"  # 36.4 minutes
                    }
                },
                {
                    "personId": 1628978,
                    "name": "Donte DiVincenzo",
                    "statistics": {
                        "points": 12,
                        "reboundsTotal": 4,
                        "assists": 4,
                        "minutes": "PT28M30S"  # 28.5 minutes
                    }
                }
            ]
        },
        "awayTeam": {
            "teamTricode": "OKC",
            "players": [
                {
                    "personId": 1631096,
                    "name": "Chet Holmgren",
                    "statistics": {
                        "points": 12,
                        "reboundsTotal": 5,
                        "assists": 2,
                        "minutes": "PT32M10S"  # 32.2 minutes
                    }
                },
                {
                    "personId": 1631114,
                    "name": "Jalen Williams",
                    "statistics": {
                        "points": 18,
                        "reboundsTotal": 5,
                        "assists": 3,
                        "minutes": "PT34M00S"  # 34.0 minutes
                    }
                }
            ]
        }
    }
}

MOCK_BOXSCORE_GAME_401 = {
    "boxScoreTraditional": {
        "homeTeam": {
            "teamTricode": "BOS",
            "players": [
                {
                    "personId": 1627759,
                    "name": "Jaylen Brown",
                    "statistics": {
                        "points": 32,
                        "reboundsTotal": 8,
                        "assists": 6,
                        "minutes": "PT35M45S"
                    }
                },
                {
                    "personId": 1628369,
                    "name": "Jayson Tatum",
                    "statistics": {
                        "points": 25,
                        "reboundsTotal": 6,
                        "assists": 4,
                        "minutes": "PT34M00S"
                    }
                }
            ]
        },
        "awayTeam": {
            "teamTricode": "PHI",
            "players": [
                {
                    "personId": 1630178,
                    "name": "Tyrese Maxey",
                    "statistics": {
                        "points": 28,
                        "reboundsTotal": 4,
                        "assists": 9,
                        "minutes": "PT37M15S"
                    }
                }
            ]
        }
    }
}

# DNP / Injury case
MOCK_BOXSCORE_WITH_DNP = {
    "boxScoreTraditional": {
        "homeTeam": {
            "teamTricode": "DAL",
            "players": [
                {
                    "personId": 1629029,
                    "name": "Luka Doncic",
                    "statistics": {
                        "points": 0,
                        "reboundsTotal": 0,
                        "assists": 0,
                        "minutes": "PT00M00S"  # DNP
                    }
                },
                {
                    "personId": 1629027,
                    "name": "Kyrie Irving",
                    "statistics": {
                        "points": 0,
                        "reboundsTotal": 1,
                        "assists": 0,
                        "minutes": "PT00M45S"  # Played < 1 minute (injury exit)
                    }
                }
            ]
        },
        "awayTeam": {
            "teamTricode": "LAC",
            "players": []
        }
    }
}

# Live game boxscore (in progress)
MOCK_BOXSCORE_LIVE = {
    "boxScoreTraditional": {
        "homeTeam": {
            "teamTricode": "LAL",
            "players": [
                {
                    "personId": 2544,
                    "name": "LeBron James",
                    "statistics": {
                        "points": 18,
                        "reboundsTotal": 6,
                        "assists": 5,
                        "minutes": "PT24M30S"
                    }
                }
            ]
        },
        "awayTeam": {
            "teamTricode": "GSW",
            "players": [
                {
                    "personId": 201939,
                    "name": "Stephen Curry",
                    "statistics": {
                        "points": 22,
                        "reboundsTotal": 3,
                        "assists": 4,
                        "minutes": "PT26M00S"
                    }
                }
            ]
        }
    }
}


# Helper function to get expected PRA values from mock data
def get_expected_player_stats():
    """Return dict of player_id -> expected stats from mock boxscores."""
    return {
        # From MOCK_BOXSCORE_GAME_400
        1630162: {"pra": 41, "minutes": 36.4},   # Anthony Edwards: 28+8+5
        1628978: {"pra": 20, "minutes": 28.5},   # Donte DiVincenzo: 12+4+4
        1631096: {"pra": 19, "minutes": 32.2},   # Chet Holmgren: 12+5+2
        1631114: {"pra": 26, "minutes": 34.0},   # Jalen Williams: 18+5+3

        # From MOCK_BOXSCORE_GAME_401
        1627759: {"pra": 46, "minutes": 35.75},  # Jaylen Brown: 32+8+6
        1628369: {"pra": 35, "minutes": 34.0},   # Jayson Tatum: 25+6+4
        1630178: {"pra": 41, "minutes": 37.25},  # Tyrese Maxey: 28+4+9

        # From MOCK_BOXSCORE_WITH_DNP
        1629029: {"pra": 0, "minutes": 0.0},     # Luka Doncic: DNP
        1629027: {"pra": 1, "minutes": 0.75},    # Kyrie Irving: 0+1+0, injury exit
    }
