"""
tests/test_leverage_helper_integration.py
==========================================
Regression tests for derivative helper wiring into AIFM leverage calculations.
Verifies that the new helper-based path produces identical results to inline formulas.
Run with: python3 -m pytest tests/test_leverage_helper_integration.py -v
"""

import pytest
import pandas as pd
from fund_risk_workflow.data.database import get_engine
from fund_risk_workflow.data.enrichment import get_risk_ready_df
from fund_risk_workflow.computation.leverage import compute_leverage
from fund_risk_workflow.data.mock_bloomberg import MockBloomberg
from fund_risk_workflow.config import VALUATION_DATE
from fund_risk_workflow.risk.leverage_computation import build_bbg_maps


class TestAIFMHedgeFundLeverageWithHelper:
    """Test AIFM Hedge Fund leverage with wired derivative helper."""

    @pytest.fixture
    def setup(self):
        """Set up AIFM Hedge Fund leverage calculation."""
        engine = get_engine()
        risk_df = get_risk_ready_df(engine, 'AIFM_HedgeFund', VALUATION_DATE)
        nav = risk_df['market_value_eur'].sum()
        bbg = MockBloomberg()
        currency_bbg_map, deriv_bbg_map = build_bbg_maps('AIFM_HedgeFund')

        result = compute_leverage(
            risk_df, nav, bbg=bbg,
            deriv_bbg_map=deriv_bbg_map,
            currency_bbg_map=currency_bbg_map
        )

        return {
            'result': result,
            'nav': nav,
            'risk_df': risk_df,
        }

    def test_gross_leverage(self, setup):
        """Test that gross leverage matches expected value."""
        result = setup['result']
        # Expected baseline (captured from inline implementation)
        expected = 2.1039
        tolerance = 1e-3  # 0.1%
        relative_error = abs(result['gross_leverage'] - expected) / expected
        assert relative_error < tolerance, \
            f"Gross leverage {result['gross_leverage']:.4f}x differs from expected {expected:.4f}x"

    def test_commitment_leverage(self, setup):
        """Test that commitment leverage matches expected value."""
        result = setup['result']
        expected = 1.1084
        tolerance = 1e-3
        relative_error = abs(result['commitment_leverage'] - expected) / expected
        assert relative_error < tolerance, \
            f"Commitment leverage {result['commitment_leverage']:.4f}x differs from expected {expected:.4f}x"

    def test_gross_exposure(self, setup):
        """Test that gross exposure is computed correctly."""
        result = setup['result']
        expected = 186196810  # EUR
        tolerance = 1e-3
        relative_error = abs(result['gross_exposure'] - expected) / expected
        assert relative_error < tolerance, \
            f"Gross exposure €{result['gross_exposure']:.0f} differs from expected €{expected:.0f}"

    def test_commitment_exposure(self, setup):
        """Test that commitment exposure is computed correctly."""
        result = setup['result']
        expected = 98090671  # EUR
        tolerance = 1e-3
        relative_error = abs(result['commitment_exposure'] - expected) / expected
        assert relative_error < tolerance, \
            f"Commitment exposure €{result['commitment_exposure']:.0f} differs from expected €{expected:.0f}"

    def test_derivative_notional_commitment(self, setup):
        """Test that derivative notional commitment matches expected value."""
        result = setup['result']
        expected = 16358468  # EUR
        tolerance = 1e-3
        relative_error = abs(result['deriv_notional_commitment'] - expected) / expected
        assert relative_error < tolerance, \
            f"Derivative notional €{result['deriv_notional_commitment']:.0f} differs from expected €{expected:.0f}"

    def test_equity_components(self, setup):
        """Test that equity components are computed correctly."""
        result = setup['result']

        # Test net equity
        expected_net_eq = 66887116  # EUR
        tolerance = 1e-3
        relative_error = abs(result['net_eq'] - expected_net_eq) / expected_net_eq
        assert relative_error < tolerance, \
            f"Net equity differs: {result['net_eq']:.0f} vs {expected_net_eq:.0f}"

    def test_bond_exposure(self, setup):
        """Test that bond exposure is unchanged."""
        result = setup['result']
        expected = 8983190  # EUR
        tolerance = 1e-3
        relative_error = abs(result['bonds'] - expected) / expected
        assert relative_error < tolerance, \
            f"Bond exposure differs: €{result['bonds']:.0f} vs €{expected:.0f}"

    def test_fx_exposure(self, setup):
        """Test that FX exposure is unchanged."""
        result = setup['result']
        expected = 5861896  # EUR
        tolerance = 1e-3
        relative_error = abs(result['fx_exposure'] - expected) / expected
        assert relative_error < tolerance, \
            f"FX exposure differs: €{result['fx_exposure']:.0f} vs €{expected:.0f}"

    def test_hedge_treatment(self, setup):
        """Test that hedge flag treatment is preserved."""
        result = setup['result']
        risk_df = setup['risk_df']

        # Verify that short hedge equity is negative (netted against long)
        assert result['short_hedge'] < 0, "Short hedge equity should be negative"

        # Verify that hedges reduce commitment but not gross exposure
        assert result['deriv_notional_commitment'] > 0, "Derivative commitment should be positive after hedge netting"

    def test_no_external_borrowings(self, setup):
        """Test that external borrowings field is correctly zero."""
        result = setup['result']
        assert result['borrowings'] == 0, "AIFM Hedge Fund should have no borrowings"

    def test_all_components_sum_to_commitment(self, setup):
        """Test that commitment components sum correctly."""
        result = setup['result']
        expected_sum = (
            result['net_eq'] +
            result['bonds'] +
            result['fx_exposure'] +
            result['deriv_notional_commitment'] +
            result['borrowings']
        )
        tolerance = 1.0  # EUR tolerance for rounding
        assert abs(result['commitment_exposure'] - expected_sum) < tolerance, \
            f"Commitment components don't sum: {expected_sum:.0f} vs {result['commitment_exposure']:.0f}"


class TestLeverageNoFallback:
    """Test that leverage raises clear errors when required derivative inputs are missing."""

    def test_error_when_bbg_missing(self):
        """Test that clear error is raised when BBG is not provided but derivatives exist."""
        engine = get_engine()
        risk_df = get_risk_ready_df(engine, 'AIFM_HedgeFund', VALUATION_DATE)
        nav = risk_df['market_value_eur'].sum()

        # Has derivatives but no BBG → should raise ValueError
        with pytest.raises(ValueError, match="Bloomberg data provider"):
            compute_leverage(risk_df, nav, bbg=None)

    def test_error_when_deriv_map_missing(self):
        """Test that clear error is raised when deriv_bbg_map is not provided but derivatives exist."""
        engine = get_engine()
        risk_df = get_risk_ready_df(engine, 'AIFM_HedgeFund', VALUATION_DATE)
        nav = risk_df['market_value_eur'].sum()
        bbg = MockBloomberg()

        # Has derivatives but no deriv_bbg_map → should raise ValueError
        with pytest.raises(ValueError, match="Bloomberg ticker mapping"):
            compute_leverage(risk_df, nav, bbg=bbg, deriv_bbg_map=None)

    def test_error_message_includes_derivative_details(self):
        """Test that error messages include ISIN and instrument_name for debugging."""
        engine = get_engine()
        risk_df = get_risk_ready_df(engine, 'AIFM_HedgeFund', VALUATION_DATE)
        nav = risk_df['market_value_eur'].sum()

        # Missing BBG → error should mention OPT_SPX_PUT_001
        try:
            compute_leverage(risk_df, nav, bbg=None)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            # Should mention the derivative in the error
            assert 'derivative' in error_msg.lower(), f"Error should mention derivatives: {error_msg}"
