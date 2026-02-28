"""
RRSP, TFSA, FHSA annual and lifetime limits by year (Appendix A).
"""
RRSP_ANNUAL_LIMIT = {2024: 31_560, 2025: 32_490}

TFSA_ANNUAL_LIMIT = {2024: 7_000, 2025: 7_000}
TFSA_CUMULATIVE = {2024: 95_000, 2025: 102_000}  # since 2009

FHSA_ANNUAL_LIMIT = {2024: 8_000, 2025: 8_000}
FHSA_LIFETIME_LIMIT = {2024: 40_000, 2025: 40_000}

HBP_WITHDRAWAL_LIMIT = {2024: 60_000, 2025: 60_000}


def get_rrsp_limit(tax_year: int) -> int:
    return RRSP_ANNUAL_LIMIT.get(tax_year, RRSP_ANNUAL_LIMIT[2024])


def get_tfsa_annual(tax_year: int) -> int:
    return TFSA_ANNUAL_LIMIT.get(tax_year, 7_000)


def get_tfsa_cumulative(tax_year: int) -> int:
    return TFSA_CUMULATIVE.get(tax_year, 95_000)


def get_fhsa_annual(tax_year: int) -> int:
    return FHSA_ANNUAL_LIMIT.get(tax_year, 8_000)


def get_fhsa_lifetime(tax_year: int) -> int:
    return FHSA_LIFETIME_LIMIT.get(tax_year, 40_000)
