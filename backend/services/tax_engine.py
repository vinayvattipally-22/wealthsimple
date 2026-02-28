"""
Deterministic Canadian tax calculations: marginal rate, estimated liability,
bracket analysis, over-withholding, CPP/EI overpayment.
"""
from typing import Optional
from rules.federal_brackets import get_federal_brackets, FEDERAL_BASIC_PERSONAL_AMOUNT
from rules.provincial_brackets import get_provincial_brackets
from rules.cpp_ei_rates import get_max_cpp, get_max_ei


def _tax_in_brackets(income: float, brackets: list[tuple[float, float, Optional[float]]]) -> float:
    """Compute tax given (rate, low, high) brackets. None = no upper bound."""
    tax = 0.0
    for rate, low, high in brackets:
        if income <= low:
            break
        bracket_income = income - low
        if high is not None:
            bracket_income = min(bracket_income, high - low)
        tax += bracket_income * rate
    return round(tax, 2)


def federal_tax(taxable_income: float, tax_year: int) -> float:
    """Federal tax before credits (simplified: no credits other than BPA)."""
    brackets = get_federal_brackets(tax_year)
    tax = _tax_in_brackets(taxable_income, brackets)
    bpa = FEDERAL_BASIC_PERSONAL_AMOUNT.get(tax_year, 15_705)
    # Basic personal amount credit (15% on BPA)
    credit = min(bpa * 0.15, tax)
    return round(tax - credit, 2)


def provincial_tax(taxable_income: float, province_code: str, tax_year: int) -> float:
    """Provincial tax (simplified; no provincial credits)."""
    brackets = get_provincial_brackets(province_code, tax_year)
    return _tax_in_brackets(taxable_income, brackets)


def combined_marginal_rate(
    taxable_income: float,
    province_code: str,
    tax_year: int,
    delta: float = 100.0,
) -> tuple[float, float, float]:
    """
    Return (federal_marginal, provincial_marginal, combined_marginal) as decimals.
    Uses a small delta to approximate marginal rate.
    """
    f1 = federal_tax(taxable_income, tax_year)
    f2 = federal_tax(taxable_income + delta, tax_year)
    federal_marginal = (f2 - f1) / delta

    p1 = provincial_tax(taxable_income, province_code, tax_year)
    p2 = provincial_tax(taxable_income + delta, province_code, tax_year)
    provincial_marginal = (p2 - p1) / delta

    return (federal_marginal, provincial_marginal, federal_marginal + provincial_marginal)


def estimated_liability(
    employment_income: float,
    province_code: str,
    tax_year: int,
    other_deductions: float = 0.0,
) -> float:
    """Estimated total income tax (federal + provincial) on employment income."""
    taxable = max(0, employment_income - other_deductions)
    fed = federal_tax(taxable, tax_year)
    prov = provincial_tax(taxable, province_code, tax_year)
    return round(fed + prov, 2)


def over_withholding_estimate(
    box_22_total: float,
    estimated_liability: float,
) -> float:
    """Amount over-withheld (Box 22 minus estimated liability)."""
    return max(0.0, round(box_22_total - estimated_liability, 2))


def cpp_overpayment(
    total_cpp_deducted: float,
    tax_year: int,
) -> float:
    """CPP overpayment when total deducted across T4s exceeds annual max."""
    max_cpp = get_max_cpp(tax_year)
    return max(0.0, round(total_cpp_deducted - max_cpp, 2))


def ei_overpayment(
    total_ei_deducted: float,
    tax_year: int,
) -> float:
    """EI overpayment when total deducted exceeds annual max."""
    max_ei = get_max_ei(tax_year)
    return max(0.0, round(total_ei_deducted - max_ei, 2))


def bracket_analysis(
    taxable_income: float,
    province_code: str,
    tax_year: int,
) -> dict:
    """
    Distance to next bracket threshold (for bracket-straddling insight).
    Returns e.g. distance_to_next_bracket_down (savings if income dropped to next threshold).
    """
    fed_brackets = get_federal_brackets(tax_year)
    # Find current bracket and distance to lower boundary
    distance_down = taxable_income
    for rate, low, high in fed_brackets:
        if high and taxable_income < high:
            distance_down = taxable_income - low
            break
        if high is None:
            distance_down = taxable_income - low
            break
    return {
        "distance_to_next_bracket_down": round(distance_down, 2),
        "marginal_federal": get_federal_brackets(tax_year)[-1][0] if fed_brackets else 0,
    }
