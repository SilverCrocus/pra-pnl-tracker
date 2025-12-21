"""Tests for result determination and NBA API response parsing."""
import pytest
from datetime import date

from app.services.result_updater import parse_minutes, update_bet_results
from app.models.database import Bet


class TestParseMinutes:
    """Test minute parsing from various NBA API formats."""

    def test_mm_ss_format(self):
        """Parse MM:SS format (most common from stats API)."""
        assert parse_minutes("36:25") == pytest.approx(36.42, rel=0.01)
        assert parse_minutes("28:30") == pytest.approx(28.5, rel=0.01)
        assert parse_minutes("0:45") == pytest.approx(0.75, rel=0.01)

    def test_iso_duration_format(self):
        """Parse ISO 8601 duration format: PT24M30.00S."""
        assert parse_minutes("PT36M25S") == pytest.approx(36.42, rel=0.01)
        assert parse_minutes("PT24M30S") == pytest.approx(24.5, rel=0.01)
        assert parse_minutes("PT00M00S") == 0.0
        assert parse_minutes("PT00M45S") == pytest.approx(0.75, rel=0.01)

    def test_iso_duration_with_decimal_seconds(self):
        """Parse ISO duration with decimal seconds."""
        assert parse_minutes("PT36M25.00S") == pytest.approx(36.42, rel=0.01)
        assert parse_minutes("PT24M30.50S") == pytest.approx(24.51, rel=0.01)

    def test_numeric_minutes(self):
        """Parse simple numeric minutes."""
        assert parse_minutes(36.5) == 36.5
        assert parse_minutes(24) == 24
        assert parse_minutes(0) == 0.0

    def test_none_and_empty(self):
        """Handle None, empty string, DNP."""
        assert parse_minutes(None) == 0.0
        assert parse_minutes("") == 0.0
        assert parse_minutes("DNP") == 0.0

    def test_large_numeric_assumes_seconds(self):
        """Large numbers (>100) are assumed to be seconds, converted to minutes."""
        # 2190 seconds = 36.5 minutes
        assert parse_minutes(2190) == pytest.approx(36.5, rel=0.01)


class TestResultDetermination:
    """Tests for WON/LOST/VOIDED logic - prevents bugs like the Dec 18 issue."""

    def test_over_bet_wins_when_actual_exceeds_line(self, test_db):
        """OVER 34.5, actual 41.0 = WON."""
        bet = Bet(
            game_date=date(2025, 12, 19),
            player_id=1630162,
            player_name="Anthony Edwards",
            betting_line=34.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="PENDING"
        )
        test_db.add(bet)
        test_db.commit()

        results_map = {
            (1630162, "2025-12-19"): {"pra": 41.0, "minutes": 36.5}
        }

        updated = update_bet_results(test_db, results_map)

        assert updated == 1
        test_db.refresh(bet)
        assert bet.result == "WON"
        assert bet.actual_pra == 41.0
        assert bet.actual_minutes == 36.5

    def test_over_bet_loses_when_actual_below_line(self, test_db):
        """OVER 26.5, actual 19.0 = LOST."""
        bet = Bet(
            game_date=date(2025, 12, 19),
            player_id=1631096,
            player_name="Chet Holmgren",
            betting_line=26.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="PENDING"
        )
        test_db.add(bet)
        test_db.commit()

        results_map = {
            (1631096, "2025-12-19"): {"pra": 19.0, "minutes": 32.0}
        }

        updated = update_bet_results(test_db, results_map)

        assert updated == 1
        test_db.refresh(bet)
        assert bet.result == "LOST"
        assert bet.actual_pra == 19.0

    def test_under_bet_wins_when_actual_below_line(self, test_db):
        """UNDER 42.5, actual 35.0 = WON."""
        bet = Bet(
            game_date=date(2025, 12, 17),
            player_id=1628369,
            player_name="Jayson Tatum",
            betting_line=42.5,
            direction="UNDER",
            tier="HIGH_VOLATILITY",
            tier_units=1.0,
            result="PENDING"
        )
        test_db.add(bet)
        test_db.commit()

        results_map = {
            (1628369, "2025-12-17"): {"pra": 35.0, "minutes": 34.0}
        }

        updated = update_bet_results(test_db, results_map)

        assert updated == 1
        test_db.refresh(bet)
        assert bet.result == "WON"

    def test_under_bet_loses_when_actual_exceeds_line(self, test_db):
        """UNDER 30.5, actual 35.0 = LOST."""
        bet = Bet(
            game_date=date(2025, 12, 19),
            player_id=1234567,
            player_name="Test Player",
            betting_line=30.5,
            direction="UNDER",
            tier="GOLDEN",
            tier_units=1.5,
            result="PENDING"
        )
        test_db.add(bet)
        test_db.commit()

        results_map = {
            (1234567, "2025-12-19"): {"pra": 35.0, "minutes": 30.0}
        }

        updated = update_bet_results(test_db, results_map)

        assert updated == 1
        test_db.refresh(bet)
        assert bet.result == "LOST"

    def test_voided_when_player_dnp(self, test_db):
        """Player didn't play (0 minutes) = VOIDED."""
        bet = Bet(
            game_date=date(2025, 12, 18),
            player_id=1629029,
            player_name="Luka Doncic",
            betting_line=48.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="PENDING"
        )
        test_db.add(bet)
        test_db.commit()

        results_map = {
            (1629029, "2025-12-18"): {"pra": 0.0, "minutes": 0.0}
        }

        updated = update_bet_results(test_db, results_map)

        assert updated == 1
        test_db.refresh(bet)
        assert bet.result == "VOIDED"

    def test_voided_when_under_one_minute(self, test_db):
        """Played < 1 minute (injury) = VOIDED."""
        bet = Bet(
            game_date=date(2025, 12, 18),
            player_id=1629027,
            player_name="Kyrie Irving",
            betting_line=35.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="PENDING"
        )
        test_db.add(bet)
        test_db.commit()

        results_map = {
            (1629027, "2025-12-18"): {"pra": 2.0, "minutes": 0.5}
        }

        updated = update_bet_results(test_db, results_map)

        assert updated == 1
        test_db.refresh(bet)
        assert bet.result == "VOIDED"

    def test_pending_stays_pending_when_no_data(self, test_db):
        """No result data = stays PENDING (don't auto-void)."""
        bet = Bet(
            game_date=date(2025, 12, 20),
            player_id=203999,
            player_name="Nikola Jokic",
            betting_line=45.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="PENDING"
        )
        test_db.add(bet)
        test_db.commit()

        # Empty results map - player not in results
        results_map = {}

        updated = update_bet_results(test_db, results_map)

        assert updated == 0
        test_db.refresh(bet)
        assert bet.result == "PENDING"
        assert bet.actual_pra is None

    def test_exact_line_is_loss_for_over(self, test_db):
        """OVER 34.5, actual 34.5 exactly = LOST (must exceed, not equal)."""
        bet = Bet(
            game_date=date(2025, 12, 19),
            player_id=9999999,
            player_name="Edge Case Player",
            betting_line=34.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="PENDING"
        )
        test_db.add(bet)
        test_db.commit()

        results_map = {
            (9999999, "2025-12-19"): {"pra": 34.5, "minutes": 36.0}
        }

        updated = update_bet_results(test_db, results_map)

        test_db.refresh(bet)
        assert bet.result == "LOST"  # 34.5 is NOT > 34.5

    def test_exact_line_is_loss_for_under(self, test_db):
        """UNDER 34.5, actual 34.5 exactly = LOST (must be under, not equal)."""
        bet = Bet(
            game_date=date(2025, 12, 19),
            player_id=8888888,
            player_name="Edge Case Player 2",
            betting_line=34.5,
            direction="UNDER",
            tier="GOLDEN",
            tier_units=1.5,
            result="PENDING"
        )
        test_db.add(bet)
        test_db.commit()

        results_map = {
            (8888888, "2025-12-19"): {"pra": 34.5, "minutes": 36.0}
        }

        updated = update_bet_results(test_db, results_map)

        test_db.refresh(bet)
        assert bet.result == "LOST"  # 34.5 is NOT < 34.5


class TestBulkResultUpdate:
    """Test updating multiple bets at once."""

    def test_update_multiple_bets(self, test_db):
        """Update multiple pending bets in one call."""
        bets = [
            Bet(game_date=date(2025, 12, 19), player_id=1, player_name="P1",
                betting_line=30.5, direction="OVER", tier="GOLDEN",
                tier_units=1.5, result="PENDING"),
            Bet(game_date=date(2025, 12, 19), player_id=2, player_name="P2",
                betting_line=25.5, direction="OVER", tier="GOLDEN",
                tier_units=1.5, result="PENDING"),
            Bet(game_date=date(2025, 12, 19), player_id=3, player_name="P3",
                betting_line=35.5, direction="UNDER", tier="GOLDEN",
                tier_units=1.5, result="PENDING"),
        ]
        test_db.add_all(bets)
        test_db.commit()

        results_map = {
            (1, "2025-12-19"): {"pra": 35.0, "minutes": 32.0},  # WON
            (2, "2025-12-19"): {"pra": 20.0, "minutes": 28.0},  # LOST
            (3, "2025-12-19"): {"pra": 30.0, "minutes": 30.0},  # WON (under)
        }

        updated = update_bet_results(test_db, results_map)

        assert updated == 3

        for bet in bets:
            test_db.refresh(bet)

        assert bets[0].result == "WON"
        assert bets[1].result == "LOST"
        assert bets[2].result == "WON"

    def test_only_updates_pending_bets(self, test_db):
        """Already settled bets should not be updated."""
        bet = Bet(
            game_date=date(2025, 12, 19),
            player_id=1630162,
            player_name="Anthony Edwards",
            betting_line=34.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            actual_pra=41.0,
            actual_minutes=36.5,
            result="WON"  # Already settled
        )
        test_db.add(bet)
        test_db.commit()

        # Try to update with different result
        results_map = {
            (1630162, "2025-12-19"): {"pra": 20.0, "minutes": 30.0}  # Would be LOST
        }

        updated = update_bet_results(test_db, results_map)

        assert updated == 0  # No updates because bet was already settled
        test_db.refresh(bet)
        assert bet.result == "WON"  # Still WON
        assert bet.actual_pra == 41.0  # Original value preserved
