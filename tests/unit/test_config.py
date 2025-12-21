"""Tests for P&L calculations and configuration - CRITICAL for money accuracy."""
import pytest
from app.config import calculate_pnl, STARTING_BANKROLL, WIN_MULTIPLIER, STANDARD_ODDS


class TestPnLCalculations:
    """These tests protect the money math - most critical tests in the suite."""

    def test_winning_bet_single_unit(self):
        """Win 1 unit at -110 odds = profit of ~0.909 units."""
        result = calculate_pnl(won=True, units=1.0)
        assert result == pytest.approx(0.909, rel=0.01)

    def test_losing_bet_single_unit(self):
        """Lose 1 unit = -1.0 units."""
        result = calculate_pnl(won=False, units=1.0)
        assert result == -1.0

    def test_winning_bet_golden_tier(self):
        """GOLDEN tier bets are 1.5 units - win = 1.5 * 0.909 = ~1.364."""
        result = calculate_pnl(won=True, units=1.5)
        assert result == pytest.approx(1.364, rel=0.01)

    def test_losing_bet_golden_tier(self):
        """GOLDEN tier loss = -1.5 units."""
        result = calculate_pnl(won=False, units=1.5)
        assert result == -1.5

    def test_winning_bet_high_volatility_tier(self):
        """HIGH_VOLATILITY tier bets are 1.0 units."""
        result = calculate_pnl(won=True, units=1.0)
        assert result == pytest.approx(0.909, rel=0.01)

    def test_losing_bet_high_volatility_tier(self):
        """HIGH_VOLATILITY tier loss = -1.0 units."""
        result = calculate_pnl(won=False, units=1.0)
        assert result == -1.0

    def test_zero_units_returns_zero(self):
        """Edge case: 0 units should return 0."""
        assert calculate_pnl(won=True, units=0.0) == 0.0
        assert calculate_pnl(won=False, units=0.0) == 0.0

    def test_fractional_units(self):
        """Verify fractional unit calculations work correctly."""
        result = calculate_pnl(won=True, units=0.5)
        assert result == pytest.approx(0.4545, rel=0.01)

        result = calculate_pnl(won=False, units=0.5)
        assert result == -0.5

    def test_large_units(self):
        """Verify large unit calculations don't have floating point issues."""
        result = calculate_pnl(won=True, units=100.0)
        assert result == pytest.approx(90.909, rel=0.01)

        result = calculate_pnl(won=False, units=100.0)
        assert result == -100.0


class TestConfigConstants:
    """Verify configuration constants are set correctly."""

    def test_starting_bankroll(self):
        """Starting bankroll should be 100 units."""
        assert STARTING_BANKROLL == 100.0

    def test_win_multiplier(self):
        """Win multiplier for -110 odds should be ~0.909."""
        assert WIN_MULTIPLIER == pytest.approx(0.909, rel=0.01)

    def test_standard_odds(self):
        """Standard odds should be -110."""
        assert STANDARD_ODDS == -110


class TestPnLScenarios:
    """Test realistic betting scenarios."""

    def test_breakeven_win_rate(self):
        """At -110 odds, ~52.4% win rate is breakeven."""
        # 100 bets, 52 wins, 48 losses at 1 unit each
        wins_pnl = calculate_pnl(won=True, units=1.0) * 52
        losses_pnl = calculate_pnl(won=False, units=1.0) * 48
        total_pnl = wins_pnl + losses_pnl

        # Should be close to breakeven (slight loss at exactly 52%)
        assert total_pnl == pytest.approx(-0.73, rel=0.1)

    def test_profitable_session(self):
        """Calculate P&L for a profitable day."""
        # 10 bets: 6 wins (1.5u each), 4 losses (1.5u each)
        wins_pnl = calculate_pnl(won=True, units=1.5) * 6
        losses_pnl = calculate_pnl(won=False, units=1.5) * 4

        total_pnl = wins_pnl + losses_pnl
        # 6 * 1.364 - 4 * 1.5 = 8.18 - 6.0 = 2.18
        assert total_pnl == pytest.approx(2.18, rel=0.01)

    def test_losing_session(self):
        """Calculate P&L for a losing day."""
        # 10 bets: 3 wins (1.5u each), 7 losses (1.5u each)
        wins_pnl = calculate_pnl(won=True, units=1.5) * 3
        losses_pnl = calculate_pnl(won=False, units=1.5) * 7

        total_pnl = wins_pnl + losses_pnl
        # 3 * 1.364 - 7 * 1.5 = 4.09 - 10.5 = -6.41
        assert total_pnl == pytest.approx(-6.41, rel=0.01)
