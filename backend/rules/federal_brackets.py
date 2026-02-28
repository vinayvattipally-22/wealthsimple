"""
Federal tax brackets — 2024/2025 5-bracket rates (Appendix A).
"""
FEDERAL_BRACKETS_2024 = [
    (0.15, 0, 55_867),
    (0.205, 55_867, 111_733),
    (0.26, 111_733, 173_205),
    (0.29, 173_205, 246_752),
    (0.33, 246_752, None),  # no upper bound
]

FEDERAL_BRACKETS_2025 = [
    (0.15, 0, 57_375),
    (0.205, 57_375, 114_750),
    (0.26, 114_750, 177_882),
    (0.29, 177_882, 253_414),
    (0.33, 253_414, None),
]

FEDERAL_BASIC_PERSONAL_AMOUNT = {2024: 15_705, 2025: 16_129}


def get_federal_brackets(tax_year: int):
    if tax_year == 2025:
        return FEDERAL_BRACKETS_2025
    return FEDERAL_BRACKETS_2024
