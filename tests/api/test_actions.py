"""Tests for action endpoints (update-results, sync-bets, reset-voided)."""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from app.models.database import Bet


class TestUpdateResultsEndpoint:
    """Tests for /api/update-results endpoint."""

    def test_update_results_success(self, client, mocker):
        """Update results endpoint triggers result update."""
        mock_result = {"status": "success", "updated": 5}
        mocker.patch(
            "app.services.result_updater.run_result_update",
            return_value=mock_result
        )

        response = client.post("/api/update-results?days_back=3")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_update_results_default_days(self, client, mocker):
        """Default days_back is 3."""
        mock_run = mocker.patch(
            "app.services.result_updater.run_result_update",
            return_value={"status": "success", "updated": 0}
        )

        client.post("/api/update-results")

        mock_run.assert_called_once_with(days_back=3)


class TestUpdateResultsForDateEndpoint:
    """Tests for /api/update-results-for-date endpoint."""

    def test_invalid_date_format(self, client):
        """Invalid date format returns 400."""
        response = client.post("/api/update-results-for-date?target_date=invalid")

        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    def test_valid_date_format(self, client, test_db, mocker):
        """Valid date triggers update."""
        mocker.patch(
            "app.services.result_updater.fetch_game_results_for_date",
            return_value={}
        )
        mocker.patch(
            "app.services.result_updater.update_bet_results",
            return_value=0
        )
        mocker.patch(
            "app.services.result_updater.recalculate_daily_summaries"
        )

        response = client.post("/api/update-results-for-date?target_date=2025-12-19")

        assert response.status_code == 200

    def test_resets_wrongly_voided_bets(self, client, test_db, mocker):
        """Endpoint resets wrongly-voided bets before updating."""
        # Create a wrongly voided bet (no actual_pra)
        voided_bet = Bet(
            game_date=date(2025, 12, 19),
            player_id=12345,
            player_name="Wrongly Voided",
            betting_line=30.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="VOIDED",
            actual_pra=None  # Wrongly voided - no actual data
        )
        test_db.add(voided_bet)
        test_db.commit()

        mocker.patch(
            "app.services.result_updater.fetch_game_results_for_date",
            return_value={12345: {"pra": 35.0, "minutes": 32.0}}
        )
        mocker.patch(
            "app.services.result_updater.update_bet_results",
            return_value=1
        )
        mocker.patch(
            "app.services.result_updater.recalculate_daily_summaries"
        )

        response = client.post("/api/update-results-for-date?target_date=2025-12-19")

        assert response.status_code == 200
        data = response.json()
        assert data["reset"] == 1  # One bet was reset


class TestResetVoidedEndpoint:
    """Tests for /api/reset-voided endpoint."""

    def test_reset_voided_bets(self, client, test_db):
        """Reset wrongly-voided bets back to PENDING."""
        # Create wrongly voided bets (no actual_pra)
        bet1 = Bet(
            game_date=date(2025, 12, 18),
            player_id=111,
            player_name="Wrongly Voided 1",
            betting_line=30.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="VOIDED",
            actual_pra=None
        )
        bet2 = Bet(
            game_date=date(2025, 12, 18),
            player_id=222,
            player_name="Wrongly Voided 2",
            betting_line=25.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="VOIDED",
            actual_pra=None
        )
        # Correctly voided bet (has actual_pra)
        bet3 = Bet(
            game_date=date(2025, 12, 18),
            player_id=333,
            player_name="Correctly Voided",
            betting_line=40.5,
            direction="OVER",
            tier="GOLDEN",
            tier_units=1.5,
            result="VOIDED",
            actual_pra=0.0,  # DNP - correctly voided
            actual_minutes=0.0
        )
        test_db.add_all([bet1, bet2, bet3])
        test_db.commit()

        response = client.post("/api/reset-voided")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["reset"] == 2  # Only wrongly voided bets reset

        # Verify bets were reset
        test_db.refresh(bet1)
        test_db.refresh(bet2)
        test_db.refresh(bet3)

        assert bet1.result == "PENDING"
        assert bet2.result == "PENDING"
        assert bet3.result == "VOIDED"  # Correctly voided stays voided

    def test_reset_voided_no_bets(self, client, empty_db):
        """No wrongly-voided bets returns 0 reset."""
        response = client.post("/api/reset-voided")

        assert response.status_code == 200
        data = response.json()
        assert data["reset"] == 0


class TestSyncBetsEndpoint:
    """Tests for /api/sync-bets endpoint."""

    def test_sync_bets_invalid_api_key(self, client):
        """Invalid API key returns 401."""
        response = client.post(
            "/api/sync-bets?api_key=wrong-key",
            json=[{"player_id": 123, "player_name": "Test"}]
        )

        assert response.status_code == 401


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_check(self, client):
        """Health check returns healthy status."""
        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
