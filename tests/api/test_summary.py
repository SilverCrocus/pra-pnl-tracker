"""Tests for /api/summary endpoint - main dashboard stats."""
import pytest


class TestSummaryEndpoint:
    """Tests for the summary endpoint."""

    def test_summary_with_settled_bets(self, client, sample_bets, sample_summaries):
        """Summary returns correct stats with settled bets."""
        response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()

        # Check all expected fields are present
        assert "bankroll" in data
        assert "win_rate" in data
        assert "roi" in data
        assert "total_bets" in data
        assert "pending_bets" in data
        assert "voided_bets" in data
        assert "wins" in data
        assert "losses" in data

        # Verify counts from sample_bets fixture
        # 2 wins (Edwards WON, Tatum WON), 1 loss (Holmgren LOST)
        assert data["wins"] == 2
        assert data["losses"] == 1
        assert data["total_bets"] == 3  # Only settled bets counted
        assert data["pending_bets"] == 1  # Jokic
        assert data["voided_bets"] == 1  # Doncic

    def test_summary_win_rate_calculation(self, client, sample_bets, sample_summaries):
        """Win rate is calculated correctly (wins / settled bets)."""
        response = client.get("/api/summary")
        data = response.json()

        # 2 wins out of 3 settled = 66.7%
        assert data["win_rate"] == pytest.approx(66.7, rel=0.1)

    def test_summary_empty_database(self, client, empty_db):
        """Summary handles empty database gracefully."""
        response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["total_bets"] == 0
        assert data["win_rate"] == 0
        assert data["bankroll"] == 100  # Starting bankroll
        assert data["wins"] == 0
        assert data["losses"] == 0

    def test_summary_bankroll_from_latest_summary(self, client, sample_bets, sample_summaries):
        """Bankroll comes from latest daily summary."""
        response = client.get("/api/summary")
        data = response.json()

        # Latest summary is Dec 20 with bankroll ~100.77
        assert data["bankroll"] == pytest.approx(100.77, rel=0.01)


class TestBankrollHistoryEndpoint:
    """Tests for /api/bankroll-history endpoint."""

    def test_bankroll_history_format(self, client, sample_bets, sample_summaries):
        """Bankroll history returns correct format."""
        response = client.get("/api/bankroll-history")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # First entry should be starting bankroll
        assert data[0]["date"] is None
        assert data[0]["bankroll"] == 100

        # Subsequent entries should have dates
        for entry in data[1:]:
            assert "date" in entry
            assert "bankroll" in entry
            assert entry["date"] is not None

    def test_bankroll_history_empty_db(self, client, empty_db):
        """Bankroll history with no data returns just starting point."""
        response = client.get("/api/bankroll-history")

        assert response.status_code == 200
        data = response.json()

        # Should have at least the starting bankroll entry
        assert len(data) >= 1
        assert data[0]["bankroll"] == 100


class TestDailyPnLEndpoint:
    """Tests for /api/daily-pnl endpoint."""

    def test_daily_pnl_format(self, client, sample_bets, sample_summaries):
        """Daily P&L returns correct format."""
        response = client.get("/api/daily-pnl")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        for entry in data:
            assert "date" in entry
            assert "pnl" in entry
            assert "wins" in entry
            assert "losses" in entry

    def test_daily_pnl_empty_db(self, client, empty_db):
        """Daily P&L with no data returns empty list."""
        response = client.get("/api/daily-pnl")

        assert response.status_code == 200
        data = response.json()

        assert data == []
