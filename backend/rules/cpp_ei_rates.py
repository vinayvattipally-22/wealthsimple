"""
CPP and EI rates — YMPE, YAMPE, max contributions (Appendix A).
"""
# Year's Maximum Pensionable Earnings
YMPE = {2024: 68_500, 2025: 71_300}
# Year's Additional Maximum Pensionable Earnings (CPP2 ceiling)
YAMPE = {2024: 73_200, 2025: 81_200}

MAX_CPP_EMPLOYEE = {2024: 3_867.50, 2025: 4_034.10}
MAX_CPP2_EMPLOYEE = {2024: 188.00, 2025: 396.00}

MAX_EI_EMPLOYEE = {2024: 1_049.12, 2025: 1_077.48}
EI_MAX_ANNUAL_INSURABLE = {2024: 63_200, 2025: 65_700}


def get_ympe(tax_year: int) -> float:
    return YMPE.get(tax_year, 68_500)


def get_yampe(tax_year: int) -> float:
    return YAMPE.get(tax_year, 73_200)


def get_max_cpp(tax_year: int) -> float:
    return MAX_CPP_EMPLOYEE.get(tax_year, 3_867.50)


def get_max_cpp2(tax_year: int) -> float:
    return MAX_CPP2_EMPLOYEE.get(tax_year, 188.00)


def get_max_ei(tax_year: int) -> float:
    return MAX_EI_EMPLOYEE.get(tax_year, 1_049.12)
