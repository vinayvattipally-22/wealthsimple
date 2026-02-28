"""Tests for deterministic tax engine calculations."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.tax_engine import (
    federal_tax,
    provincial_tax,
    combined_marginal_rate,
    estimated_liability,
    over_withholding_estimate,
    cpp_overpayment,
    ei_overpayment,
    bracket_analysis,
)


class TestFederalTax:
    """Test federal tax calculations."""

    def test_zero_income(self):
        assert federal_tax(0, 2024) == 0.0

    def test_below_bpa(self):
        tax = federal_tax(10000, 2024)
        assert tax == 0.0

    def test_moderate_income(self):
        tax = federal_tax(55000, 2024)
        assert 4000 <= tax <= 8000

    def test_high_income(self):
        tax = federal_tax(250000, 2024)
        assert tax > 40000

    def test_tax_increases_with_income(self):
        t1 = federal_tax(50000, 2024)
        t2 = federal_tax(100000, 2024)
        t3 = federal_tax(200000, 2024)
        assert t1 < t2 < t3


class TestProvincialTax:
    """Test provincial tax calculations."""

    def test_ontario_moderate_income(self):
        tax = provincial_tax(55000, "ON", 2024)
        assert tax > 0

    def test_different_provinces_vary(self):
        on_tax = provincial_tax(80000, "ON", 2024)
        ab_tax = provincial_tax(80000, "AB", 2024)
        assert on_tax != ab_tax


class TestCombinedMarginalRate:
    """Test combined marginal rate calculation."""

    def test_ontario_85k(self):
        fed_m, prov_m, combined = combined_marginal_rate(85000, "ON", 2024)
        assert 0.25 <= combined <= 0.35
        assert fed_m > 0
        assert prov_m > 0

    def test_marginal_increases_with_income(self):
        _, _, low = combined_marginal_rate(40000, "ON", 2024)
        _, _, high = combined_marginal_rate(200000, "ON", 2024)
        assert high > low

    def test_all_components_positive(self):
        fed, prov, comb = combined_marginal_rate(75000, "ON", 2024)
        assert fed > 0
        assert prov > 0
        assert abs(comb - (fed + prov)) < 0.001


class TestEstimatedLiability:
    """Test total estimated tax liability."""

    def test_ontario_85k(self):
        liability = estimated_liability(85000, "ON", 2024)
        assert 17000 <= liability <= 20000

    def test_zero_income(self):
        liability = estimated_liability(0, "ON", 2024)
        assert liability == 0.0

    def test_with_deductions(self):
        no_ded = estimated_liability(85000, "ON", 2024)
        with_ded = estimated_liability(85000, "ON", 2024, other_deductions=10000)
        assert with_ded < no_ded


class TestOverWithholding:
    """Test over-withholding calculation."""

    def test_over_withheld(self):
        assert over_withholding_estimate(20832, 18432) == 2400.0

    def test_exact_match(self):
        assert over_withholding_estimate(18432, 18432) == 0.0

    def test_under_withheld(self):
        assert over_withholding_estimate(15000, 18432) == 0.0


class TestCPPEIOverpayment:
    """Test CPP and EI overpayment detection."""

    def test_cpp_overpayment(self):
        result = cpp_overpayment(4000, 2024)
        assert result > 0

    def test_cpp_no_overpayment(self):
        result = cpp_overpayment(3000, 2024)
        assert result == 0.0

    def test_ei_overpayment(self):
        result = ei_overpayment(1100, 2024)
        assert result > 0

    def test_ei_no_overpayment(self):
        result = ei_overpayment(800, 2024)
        assert result == 0.0


class TestBracketAnalysis:
    """Test bracket distance analysis."""

    def test_returns_distance(self):
        result = bracket_analysis(85000, "ON", 2024)
        assert "distance_to_next_bracket_down" in result
        assert result["distance_to_next_bracket_down"] > 0

    def test_distance_reasonable(self):
        result = bracket_analysis(60000, "ON", 2024)
        assert result["distance_to_next_bracket_down"] <= 60000
