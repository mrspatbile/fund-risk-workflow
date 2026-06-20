"""
tests/test_daily_workflow.py
============================
Unit tests for daily_workflow.py
Run with: python3 -m pytest tests/test_daily_workflow.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.data.daily_workflow import (
    business_day_offset,
    summarise_position_snapshot,
    summarise_risk_ready_dataset,
)


class TestBusinessDayOffset:
    """Tests for business_day_offset function."""

    def test_positive_offset(self):
        """Test forward business day offset."""
        result = business_day_offset("2026-03-31", 1)
        assert result == "2026-04-01"

    def test_negative_offset(self):
        """Test backward business day offset."""
        result = business_day_offset("2026-04-01", -1)
        assert result == "2026-03-31"

    def test_zero_offset(self):
        """Test zero offset returns same date."""
        result = business_day_offset("2026-03-31", 0)
        assert result == "2026-03-31"

    def test_weekend_handling(self):
        """Test that offsets skip weekends correctly."""
        # 2026-04-04 is a Saturday
        # +1 business day should give Monday 2026-04-06
        result = business_day_offset("2026-04-03", 1)
        assert result == "2026-04-06"

    def test_output_format(self):
        """Test that output is ISO date string."""
        result = business_day_offset("2026-03-31", 1)
        assert isinstance(result, str)
        assert len(result) == 10
        assert result.count("-") == 2


class TestSummarisePositionSnapshot:
    """Tests for summarise_position_snapshot function."""

    @pytest.fixture
    def sample_positions(self):
        """Create sample position data."""
        return pd.DataFrame(
            {
                "isin": ["US0001", "US0002", "US0003"],
                "instrument_name": ["Apple", "Microsoft", "Google"],
                "asset_class": ["Equity", "Equity", "Equity"],
                "bloomberg_ticker": ["AAPL US", "MSFT US", "GOOGL US"],
                "market_value_eur": [100.0, 200.0, 150.0],
            }
        )

    @pytest.fixture
    def sample_prior_positions(self):
        """Create sample prior position data."""
        return pd.DataFrame(
            {
                "isin": ["US0001", "US0002", "US0004"],
                "instrument_name": ["Apple", "Microsoft", "Intel"],
                "asset_class": ["Equity", "Equity", "Equity"],
                "bloomberg_ticker": ["AAPL US", "MSFT US", "INTC US"],
                "market_value_eur": [95.0, 195.0, 100.0],
            }
        )

    def test_identifies_new_isins(self, sample_positions, sample_prior_positions):
        """Test that new ISINs are correctly identified."""
        result = summarise_position_snapshot(sample_positions, sample_prior_positions)
        assert "US0003" in result["new_isins"]
        assert "US0001" not in result["new_isins"]

    def test_identifies_removed_isins(self, sample_positions, sample_prior_positions):
        """Test that removed ISINs are correctly identified."""
        result = summarise_position_snapshot(sample_positions, sample_prior_positions)
        assert "US0004" in result["removed_isins"]
        assert "US0001" not in result["removed_isins"]

    def test_calculates_nav(self, sample_positions, sample_prior_positions):
        """Test NAV calculation."""
        result = summarise_position_snapshot(sample_positions, sample_prior_positions)
        expected_nav = 100.0 + 200.0 + 150.0
        assert result["nav"] == expected_nav

    def test_position_summary_structure(self, sample_positions, sample_prior_positions):
        """Test position_summary DataFrame structure."""
        result = summarise_position_snapshot(sample_positions, sample_prior_positions)
        ps = result["position_summary"]
        assert "metric" in ps.columns
        assert "value" in ps.columns
        assert len(ps) == 8

    def test_asset_class_breakdown_structure(
        self, sample_positions, sample_prior_positions
    ):
        """Test asset_class_breakdown DataFrame structure."""
        result = summarise_position_snapshot(sample_positions, sample_prior_positions)
        acb = result["asset_class_breakdown"]
        assert "asset_class" in acb.columns
        assert "market_value_eur" in acb.columns
        assert "weight_pct" in acb.columns

    def test_new_instruments_dataframe(self, sample_positions, sample_prior_positions):
        """Test new_instruments DataFrame."""
        result = summarise_position_snapshot(sample_positions, sample_prior_positions)
        ni = result["new_instruments"]
        assert len(ni) == 1
        assert ni.iloc[0]["isin"] == "US0003"

    def test_removed_instruments_dataframe(self, sample_positions, sample_prior_positions):
        """Test removed_instruments DataFrame."""
        result = summarise_position_snapshot(sample_positions, sample_prior_positions)
        ri = result["removed_instruments"]
        assert len(ri) == 1
        assert ri.iloc[0]["isin"] == "US0004"

    def test_return_dictionary_keys(self, sample_positions, sample_prior_positions):
        """Test that return dictionary has all required keys."""
        result = summarise_position_snapshot(sample_positions, sample_prior_positions)
        required_keys = {
            "new_isins",
            "removed_isins",
            "nav",
            "position_summary",
            "asset_class_breakdown",
            "new_instruments",
            "removed_instruments",
        }
        assert set(result.keys()) == required_keys

    def test_no_changes(self):
        """Test when there are no position changes."""
        positions = pd.DataFrame(
            {
                "isin": ["US0001"],
                "instrument_name": ["Apple"],
                "asset_class": ["Equity"],
                "bloomberg_ticker": ["AAPL US"],
                "market_value_eur": [100.0],
            }
        )
        result = summarise_position_snapshot(positions, positions)
        assert len(result["new_isins"]) == 0
        assert len(result["removed_isins"]) == 0
        assert len(result["new_instruments"]) == 0
        assert len(result["removed_instruments"]) == 0


class TestSummariseRiskReadyDataset:
    """Tests for summarise_risk_ready_dataset function."""

    @pytest.fixture
    def sample_risk_df(self):
        """Create sample risk-ready dataset."""
        return pd.DataFrame(
            {
                "instrument_name": ["Apple", "Microsoft", "Google", "Intel"],
                "asset_class": ["Equity", "Equity", "Equity", "Equity"],
                "market_value_eur": [100.0, 200.0, 150.0, 50.0],
                "weight_pct": [20.0, 40.0, 30.0, 10.0],
                "beta": [1.2, 1.0, 1.3, 0.9],
                "dur_adj_mid": [np.nan, np.nan, np.nan, np.nan],
                "convexity": [np.nan, np.nan, np.nan, np.nan],
                "adv_eur": [500.0, 1000.0, 750.0, 200.0],
                "enrichment_source": ["bbg", "bbg", "bbg", "fund_admin"],
            }
        )

    def test_enrichment_summary_structure(self, sample_risk_df):
        """Test enrichment_summary DataFrame structure."""
        result = summarise_risk_ready_dataset(sample_risk_df)
        es = result["enrichment_summary"]
        assert "enrichment_source" in es.columns
        assert "positions" in es.columns

    def test_sensitivity_coverage_structure(self, sample_risk_df):
        """Test sensitivity_coverage DataFrame structure."""
        result = summarise_risk_ready_dataset(sample_risk_df)
        sc = result["sensitivity_coverage"]
        assert "field" in sc.columns
        assert "available_positions" in sc.columns
        assert "total_positions" in sc.columns
        assert len(sc) == 4

    def test_top_positions_structure(self, sample_risk_df):
        """Test top_positions DataFrame structure."""
        result = summarise_risk_ready_dataset(sample_risk_df)
        tp = result["top_positions"]
        expected_columns = [
            "instrument_name",
            "asset_class",
            "market_value_eur",
            "weight_pct",
            "beta",
            "dur_adj_mid",
            "enrichment_source",
        ]
        assert all(col in tp.columns for col in expected_columns)

    def test_top_positions_sorted_by_absolute_value(self, sample_risk_df):
        """Test that top_positions is sorted by absolute market value."""
        result = summarise_risk_ready_dataset(sample_risk_df)
        tp = result["top_positions"]
        mv = tp["market_value_eur"].abs().values
        assert all(mv[i] >= mv[i + 1] for i in range(len(mv) - 1))

    def test_return_dictionary_keys(self, sample_risk_df):
        """Test that return dictionary has all required keys."""
        result = summarise_risk_ready_dataset(sample_risk_df)
        required_keys = {
            "enrichment_summary",
            "sensitivity_coverage",
            "top_positions",
        }
        assert set(result.keys()) == required_keys

    def test_beta_coverage(self, sample_risk_df):
        """Test beta coverage calculation."""
        result = summarise_risk_ready_dataset(sample_risk_df)
        sc = result["sensitivity_coverage"]
        beta_row = sc[sc["field"] == "beta"]
        assert beta_row.iloc[0]["available_positions"] == 4
        assert beta_row.iloc[0]["total_positions"] == 4

    def test_duration_coverage(self, sample_risk_df):
        """Test duration coverage calculation."""
        result = summarise_risk_ready_dataset(sample_risk_df)
        sc = result["sensitivity_coverage"]
        dur_row = sc[sc["field"] == "dur_adj_mid"]
        assert dur_row.iloc[0]["available_positions"] == 0
        assert dur_row.iloc[0]["total_positions"] == 4

    def test_adv_coverage(self, sample_risk_df):
        """Test ADV coverage calculation."""
        result = summarise_risk_ready_dataset(sample_risk_df)
        sc = result["sensitivity_coverage"]
        adv_row = sc[sc["field"] == "adv_eur"]
        assert adv_row.iloc[0]["available_positions"] == 4
