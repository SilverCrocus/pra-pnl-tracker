"""Tests for bet-related API endpoints."""
import pytest
from datetime import date


class TestRecentBetsEndpoint:
    """Tests for /api/recent-bets endpoint."""

    def test_recent_bets_returns_list(self, client, sample_bets):
        """Recent bets returns a list of bets."""
        response = client.get("/api/recent-bets")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    def test_recent_bets_structure(self, client, sample_bets):
        """Each bet has required fields."""
        response = client.get("/api/recent-bets?limit=10")

        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0

        bet = data[0]
        required_fields = [
            "id", "game_date", "player_name", "betting_line",
            "direction", "tier", "tier_units", "result"
        ]
        for field in required_fields:
            assert field in bet, f"Missing field: {field}"

    def test_recent_bets_limit(self, client, sample_bets):
        """Limit parameter controls number of results."""
        response = client.get("/api/recent-bets?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data) <= 2

    def test_recent_bets_ordered_by_date(self, client, sample_bets):
        """Bets are ordered by date descending (most recent first)."""
        response = client.get("/api/recent-bets?limit=10")
        data = response.json()

        dates = [bet["game_date"] for bet in data]
        assert dates == sorted(dates, reverse=True)

    def test_recent_bets_empty_db(self, client, empty_db):
        """Empty database returns empty list."""
        response = client.get("/api/recent-bets")

        assert response.status_code == 200
        assert response.json() == []


class TestByTierEndpoint:
    """Tests for /api/by-tier endpoint."""

    def test_by_tier_format(self, client, sample_bets):
        """By-tier returns correct format."""
        response = client.get("/api/by-tier")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        for tier_data in data:
            assert "tier" in tier_data
            assert "wins" in tier_data
            assert "total" in tier_data
            assert "win_rate" in tier_data

    def test_by_tier_win_rate_calculation(self, client, sample_bets):
        """Win rate is calculated correctly per tier."""
        response = client.get("/api/by-tier")
        data = response.json()

        for tier_data in data:
            if tier_data["total"] > 0:
                expected_rate = (tier_data["wins"] / tier_data["total"]) * 100
                assert tier_data["win_rate"] == pytest.approx(expected_rate, rel=0.1)


class TestByDateEndpoint:
    """Tests for /api/by-date endpoint."""

    def test_by_date_format(self, client, sample_bets):
        """By-date returns correct format."""
        response = client.get("/api/by-date")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        for date_data in data:
            assert "date" in date_data
            assert "wins" in date_data
            assert "total" in date_data
            assert "win_rate" in date_data

    def test_by_date_limit(self, client, sample_bets):
        """Limit parameter controls number of dates returned."""
        response = client.get("/api/by-date?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data) <= 2

    def test_by_date_ordered_descending(self, client, sample_bets):
        """Dates are ordered most recent first."""
        response = client.get("/api/by-date?limit=10")
        data = response.json()

        dates = [d["date"] for d in data]
        assert dates == sorted(dates, reverse=True)


class TestRecentResultsEndpoint:
    """Tests for /api/recent-results endpoint."""

    def test_recent_results_format(self, client, sample_bets):
        """Recent results returns correct format."""
        response = client.get("/api/recent-results?days=5")

        assert response.status_code == 200
        data = response.json()

        assert "days" in data
        assert "total_days" in data
        assert isinstance(data["days"], list)

    def test_recent_results_day_structure(self, client, sample_bets):
        """Each day has required fields."""
        response = client.get("/api/recent-results?days=5")
        data = response.json()

        if data["days"]:
            day = data["days"][0]
            assert "date" in day
            assert "bets" in day
            assert "wins" in day
            assert "losses" in day
            assert "win_rate" in day

    def test_recent_results_excludes_pending(self, client, sample_bets):
        """Recent results only includes settled bets."""
        response = client.get("/api/recent-results?days=10")
        data = response.json()

        for day in data["days"]:
            for bet in day["bets"]:
                assert bet["result"] in ["WON", "LOST", "VOIDED"]
                assert bet["result"] != "PENDING"


class TestLiveBetsEndpoint:
    """Tests for /api/live-bets endpoint."""

    def test_live_bets_structure(self, client, sample_bets):
        """Live bets returns correct structure."""
        response = client.get("/api/live-bets")

        assert response.status_code == 200
        data = response.json()

        assert "bets" in data
        assert "games" in data
        assert "summary" in data
        assert "tracking_state" in data
        assert "date" in data

    def test_live_bets_summary_fields(self, client, sample_bets):
        """Summary has required fields."""
        response = client.get("/api/live-bets")
        data = response.json()

        summary = data["summary"]
        assert "total" in summary
        assert "live" in summary
        assert "hits" in summary
        assert "pending" in summary
        assert "voided" in summary

    def test_live_bets_tracking_states(self, client, sample_bets):
        """Tracking state is a valid value."""
        response = client.get("/api/live-bets")
        data = response.json()

        valid_states = ["no_bets", "upcoming", "live", "mixed", "complete"]
        assert data["tracking_state"] in valid_states


class TestTodaysBetsEndpoint:
    """Tests for /api/todays-bets endpoint."""

    def test_todays_bets_structure(self, client, sample_bets):
        """Today's bets returns correct structure."""
        response = client.get("/api/todays-bets")

        assert response.status_code == 200
        data = response.json()

        assert "date" in data
        assert "teams" in data
        assert "summary" in data

    def test_todays_bets_summary_fields(self, client, sample_bets):
        """Summary has required fields."""
        response = client.get("/api/todays-bets")
        data = response.json()

        summary = data["summary"]
        assert "total_bets" in summary
        assert "total_units" in summary
        assert "teams_count" in summary
