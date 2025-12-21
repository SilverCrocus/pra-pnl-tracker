"""Tests for live tracking service."""
import pytest
from app.services.live_tracker import LiveTracker


@pytest.fixture
def tracker():
    """Fresh LiveTracker instance for each test."""
    return LiveTracker()


class TestParseMinutes:
    """Test minute parsing from various NBA API formats."""

    def test_iso_duration_format(self, tracker):
        """Parse ISO 8601 duration: PT24M30.00S."""
        assert tracker.parse_minutes("PT36M25S") == pytest.approx(36.42, rel=0.01)
        assert tracker.parse_minutes("PT24M30S") == pytest.approx(24.5, rel=0.01)
        assert tracker.parse_minutes("PT00M00S") == 0.0
        assert tracker.parse_minutes("PT00M45S") == pytest.approx(0.75, rel=0.01)

    def test_iso_duration_with_decimal_seconds(self, tracker):
        """Parse ISO duration with decimal seconds."""
        assert tracker.parse_minutes("PT36M25.00S") == pytest.approx(36.42, rel=0.01)
        assert tracker.parse_minutes("PT24M30.50S") == pytest.approx(24.51, rel=0.01)

    def test_mm_ss_format(self, tracker):
        """Parse MM:SS format."""
        assert tracker.parse_minutes("36:25") == pytest.approx(36.42, rel=0.01)
        assert tracker.parse_minutes("28:30") == pytest.approx(28.5, rel=0.01)
        assert tracker.parse_minutes("0:45") == pytest.approx(0.75, rel=0.01)

    def test_numeric_minutes(self, tracker):
        """Parse simple numeric minutes."""
        assert tracker.parse_minutes(36.5) == 36.5
        assert tracker.parse_minutes(24) == 24.0
        assert tracker.parse_minutes(0) == 0.0

    def test_none_and_empty(self, tracker):
        """Handle None, empty string, DNP."""
        assert tracker.parse_minutes(None) == 0.0
        assert tracker.parse_minutes("") == 0.0
        assert tracker.parse_minutes("DNP") == 0.0

    def test_large_numeric_assumes_seconds(self, tracker):
        """Large numbers (>100) are assumed to be seconds."""
        assert tracker.parse_minutes(2190) == pytest.approx(36.5, rel=0.01)


class TestCalculateTrackingStatus:
    """Test tracking status calculation."""

    def test_not_started_game(self, tracker):
        """Game not started returns not_started status."""
        result = tracker.calculate_tracking_status(
            current_pra=None,
            line=30.5,
            direction="OVER",
            minutes_played=0,
            game_status="Not Started"
        )

        assert result["status"] == "not_started"
        assert result["status_color"] == "gray"

    # --- FINISHED GAME TESTS ---

    def test_finished_over_bet_hit(self, tracker):
        """Finished game: OVER bet that hit."""
        result = tracker.calculate_tracking_status(
            current_pra=35.0,
            line=30.5,
            direction="OVER",
            minutes_played=34.0,
            game_status="Finished"
        )

        assert result["status"] == "hit"
        assert result["status_color"] == "green"
        assert result["distance"] == 4.5  # 35 - 30.5

    def test_finished_over_bet_miss(self, tracker):
        """Finished game: OVER bet that missed."""
        result = tracker.calculate_tracking_status(
            current_pra=25.0,
            line=30.5,
            direction="OVER",
            minutes_played=34.0,
            game_status="Finished"
        )

        assert result["status"] == "miss"
        assert result["status_color"] == "red"
        assert result["distance"] == -5.5  # 25 - 30.5

    def test_finished_under_bet_hit(self, tracker):
        """Finished game: UNDER bet that hit."""
        result = tracker.calculate_tracking_status(
            current_pra=28.0,
            line=32.5,
            direction="UNDER",
            minutes_played=34.0,
            game_status="Finished"
        )

        assert result["status"] == "hit"
        assert result["status_color"] == "green"
        assert result["distance"] == 4.5  # 32.5 - 28

    def test_finished_under_bet_miss(self, tracker):
        """Finished game: UNDER bet that missed."""
        result = tracker.calculate_tracking_status(
            current_pra=38.0,
            line=32.5,
            direction="UNDER",
            minutes_played=34.0,
            game_status="Finished"
        )

        assert result["status"] == "miss"
        assert result["status_color"] == "red"

    # --- LIVE GAME OVER BET TESTS ---

    def test_live_over_already_hit(self, tracker):
        """Live game: OVER bet already exceeded line."""
        result = tracker.calculate_tracking_status(
            current_pra=35.0,
            line=30.5,
            direction="OVER",
            minutes_played=28.0,
            game_status="Live"
        )

        assert result["status"] == "hit"
        assert result["status_color"] == "green"

    def test_live_over_on_track(self, tracker):
        """Live game: OVER bet on pace to exceed line."""
        # At 20 minutes, has 20 PRA, rate = 1.0 PRA/min
        # Projected = 20 + (1.0 * 14) = 34 PRA (>30.5 * 1.05 = 32.025)
        result = tracker.calculate_tracking_status(
            current_pra=20.0,
            line=30.5,
            direction="OVER",
            minutes_played=20.0,
            game_status="Live"
        )

        assert result["status"] == "on_track"
        assert result["status_color"] == "green"

    def test_live_over_needs_more(self, tracker):
        """Live game: OVER bet behind pace but still possible."""
        # At 28 minutes, has 22 PRA, rate = 0.786 PRA/min
        # Projected = 22 + (0.786 * 6) = 26.7 PRA (in warning range)
        result = tracker.calculate_tracking_status(
            current_pra=22.0,
            line=30.5,
            direction="OVER",
            minutes_played=28.0,
            game_status="Live"
        )

        assert result["status"] == "needs_more"
        assert result["status_color"] == "yellow"

    def test_live_over_unlikely(self, tracker):
        """Live game: OVER bet very unlikely to hit."""
        # At 32 minutes, has 15 PRA, rate = 0.47 PRA/min
        # Projected = 15 + (0.47 * 2) = 15.9 PRA (way below line)
        result = tracker.calculate_tracking_status(
            current_pra=15.0,
            line=30.5,
            direction="OVER",
            minutes_played=32.0,
            game_status="Live"
        )

        assert result["status"] == "unlikely"
        assert result["status_color"] == "red"

    # --- LIVE GAME UNDER BET TESTS ---

    def test_live_under_busted(self, tracker):
        """Live game: UNDER bet already exceeded line."""
        result = tracker.calculate_tracking_status(
            current_pra=35.0,
            line=30.5,
            direction="UNDER",
            minutes_played=20.0,
            game_status="Live"
        )

        assert result["status"] == "busted"
        assert result["status_color"] == "red"

    def test_live_under_safe(self, tracker):
        """Live game: UNDER bet on pace to stay under."""
        # At 28 minutes, has 15 PRA, rate = 0.536 PRA/min
        # Projected = 15 + (0.536 * 6) = 18.2 PRA (<30.5 * 0.95 = 28.975)
        result = tracker.calculate_tracking_status(
            current_pra=15.0,
            line=30.5,
            direction="UNDER",
            minutes_played=28.0,
            game_status="Live"
        )

        assert result["status"] == "safe"
        assert result["status_color"] == "green"

    def test_live_under_close(self, tracker):
        """Live game: UNDER bet projected close to line."""
        # At 25 minutes, has 22 PRA, rate = 0.88 PRA/min
        # Projected = 22 + (0.88 * 9) = 29.9 PRA (close to 30.5)
        result = tracker.calculate_tracking_status(
            current_pra=22.0,
            line=30.5,
            direction="UNDER",
            minutes_played=25.0,
            game_status="Live"
        )

        assert result["status"] == "close"
        assert result["status_color"] == "yellow"

    def test_live_under_danger(self, tracker):
        """Live game: UNDER bet projected to exceed line."""
        # At 20 minutes, has 22 PRA, rate = 1.1 PRA/min
        # Projected = 22 + (1.1 * 14) = 37.4 PRA (>30.5)
        result = tracker.calculate_tracking_status(
            current_pra=22.0,
            line=30.5,
            direction="UNDER",
            minutes_played=20.0,
            game_status="Live"
        )

        assert result["status"] == "danger"
        assert result["status_color"] == "red"


class TestTrackingStatusEdgeCases:
    """Edge cases for tracking status."""

    def test_zero_minutes_played(self, tracker):
        """Player in game but 0 minutes (just checked in)."""
        result = tracker.calculate_tracking_status(
            current_pra=0.0,
            line=30.5,
            direction="OVER",
            minutes_played=0.0,
            game_status="Live"
        )

        # With 0 minutes, projection is 0, should be unlikely
        assert result["status"] == "unlikely"

    def test_exact_line_over_finished(self, tracker):
        """Finished game: OVER at exactly the line."""
        result = tracker.calculate_tracking_status(
            current_pra=30.5,
            line=30.5,
            direction="OVER",
            minutes_played=34.0,
            game_status="Finished"
        )

        # 30.5 >= 30.5 is True, so it's a hit
        assert result["status"] == "hit"

    def test_exact_line_under_finished(self, tracker):
        """Finished game: UNDER at exactly the line."""
        result = tracker.calculate_tracking_status(
            current_pra=30.5,
            line=30.5,
            direction="UNDER",
            minutes_played=34.0,
            game_status="Finished"
        )

        # 30.5 <= 30.5 is True, so it's a hit
        assert result["status"] == "hit"
