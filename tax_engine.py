"""Pure deterministic US single-filer tax and contribution calculations.

Only the Python standard library is used here. The model is a planning estimate,
not tax-return preparation: see README for covered and excluded tax provisions.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from math import isfinite
from typing import Protocol


class FinancialProfile(Protocol):
    gross_income: float
    traditional_401k_contribution: float
    other_pretax_adjustments: float
    roth_magi_adjustments: float
    itemized_deductions: float | None
    age: int
    annual_ira_contributions_already_made: float
    annual_traditional_ira_contributions_already_made: float
    other_ira_assets: float
    state_tax_rate: float


@dataclass(frozen=True)
class TaxParameters:
    """Plain Python tax table so the calculation module has no package dependencies."""
    tax_year: int = 2026
    standard_deduction_single: float = 16_100
    traditional_401k_limit: float = 24_500
    ira_limit: float = 7_500
    ira_catch_up_age: int = 50
    ira_catch_up_limit: float = 1_100
    roth_phaseout_start_single: float = 153_000
    roth_phaseout_end_single: float = 168_000
    social_security_wage_base: float = 184_500
    state_tax_rate_baseline: float = 0.08
    social_security_rate: float = 0.062
    medicare_rate: float = 0.0145
    additional_medicare_rate: float = 0.009
    additional_medicare_threshold_single: float = 200_000
    federal_brackets_single: tuple[tuple[float | None, float], ...] = (
        (12_400, .10), (50_400, .12), (105_700, .22), (201_775, .24),
        (256_225, .32), (640_600, .35), (None, .37),
    )


TAX_YEAR = TaxParameters()


@dataclass(frozen=True)
class TaxResult:
    tax_year: int
    gross_income: float
    traditional_401k_contribution: float
    agi_estimate: float
    roth_ira_magi_estimate: float
    standard_deduction: float
    itemized_deduction: float
    deduction_used: float
    federal_taxable_income: float
    federal_income_tax: float
    federal_marginal_rate: float
    federal_effective_rate_on_gross: float
    state_tax_estimate: float
    social_security_tax: float
    medicare_tax: float
    additional_medicare_tax: float
    total_estimated_tax: float
    estimated_take_home: float
    tax_savings_from_401k: float
    roth_ira_direct_contribution_cap: float
    roth_ira_phaseout_status: str
    recommended_401k_contribution: float
    recommended_ira_contribution: float
    backdoor_roth_pro_rata_note: str
    strategic_pivot: str
    assumptions: tuple[str, ...]


def _validate_amount(name: str, value: float) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


def federal_income_tax(taxable_income: float, config: TaxParameters = TAX_YEAR) -> float:
    """Compute progressive federal income tax using the supplied brackets."""
    _validate_amount("taxable_income", taxable_income)
    tax = 0.0
    lower = 0.0
    for upper, rate in config.federal_brackets_single:
        amount = taxable_income - lower if upper is None else min(taxable_income, upper) - lower
        if amount > 0:
            tax += amount * rate
        if upper is None or taxable_income <= upper:
            break
        lower = upper
    return round(tax, 2)


def marginal_rate(taxable_income: float, config: TaxParameters = TAX_YEAR) -> float:
    """Return the rate on the next dollar of taxable income."""
    _validate_amount("taxable_income", taxable_income)
    for upper, rate in config.federal_brackets_single:
        if upper is None or taxable_income < upper:
            return rate
    return config.federal_brackets_single[-1][1]


def agi_estimate(gross_income: float, pretax_401k: float, other_adjustments: float) -> float:
    """Estimate AGI for the modeled W-2 case; does not model all Form 1040 lines."""
    for label, value in (("gross_income", gross_income), ("pretax_401k", pretax_401k), ("other_adjustments", other_adjustments)):
        _validate_amount(label, value)
    return max(0.0, gross_income - pretax_401k - other_adjustments)


def roth_direct_contribution_cap(magi: float, age: int, already_contributed: float = 0.0,
                                 config: TaxParameters = TAX_YEAR, *, compensation: float | None = None,
                                 prior_traditional: float = 0.0) -> tuple[float, str]:
    """Return remaining direct Roth IRA limit after the 2026 MAGI phase-out."""
    for label, value in (("magi", magi), ("already_contributed", already_contributed),
                         ("prior_traditional", prior_traditional)):
        _validate_amount(label, value)
    if prior_traditional > already_contributed:
        raise ValueError("Prior traditional contributions cannot exceed total prior IRA contributions")
    annual_limit = config.ira_limit + (config.ira_catch_up_limit if age >= config.ira_catch_up_age else 0.0)
    if compensation is not None:
        _validate_amount("compensation", compensation)
    base = Decimal(str(min(annual_limit, annual_limit if compensation is None else compensation)))
    if magi < config.roth_phaseout_start_single:
        allowed, status = base, "Full direct Roth IRA contribution generally available"
    elif magi >= config.roth_phaseout_end_single:
        allowed, status = Decimal(0), "Direct Roth IRA contribution phased out"
    else:
        fraction = ((Decimal(str(config.roth_phaseout_end_single)) - Decimal(str(magi))) /
                    Decimal(str(config.roth_phaseout_end_single - config.roth_phaseout_start_single)))
        reduced = (base * fraction / 10).to_integral_value(rounding=ROUND_CEILING) * 10
        allowed = max(Decimal(200), reduced)
        status = "Direct Roth IRA contribution partially phased out"
    # Worksheet 2-2: traditional contributions reduce aggregate capacity, not the
    # MAGI-reduced cap directly. Prior Roth contributions reduce the remaining cap.
    capacity = max(Decimal(0), base - Decimal(str(prior_traditional)))
    prior_roth = Decimal(str(already_contributed)) - Decimal(str(prior_traditional))
    return float(max(Decimal(0), min(allowed, capacity) - prior_roth).quantize(Decimal("0.01"))), status


def calculate_tax(profile: FinancialProfile, config: TaxParameters = TAX_YEAR) -> TaxResult:
    """Calculate the modeled tax estimate and simple contribution priorities."""
    gross = profile.gross_income
    actual_401k = min(profile.traditional_401k_contribution, config.traditional_401k_limit, gross)
    agi = agi_estimate(gross, actual_401k, profile.other_pretax_adjustments)
    standard = config.standard_deduction_single
    itemized = profile.itemized_deductions or 0.0
    deduction_used = max(standard, itemized)
    taxable = max(0.0, agi - deduction_used)
    federal = federal_income_tax(taxable, config)
    marginal = marginal_rate(taxable, config) if taxable > 0 else 0.0
    state = round(max(0.0, gross - actual_401k - profile.other_pretax_adjustments - deduction_used) * profile.state_tax_rate, 2)
    social_security = round(min(gross, config.social_security_wage_base) * config.social_security_rate, 2)
    medicare = round(gross * config.medicare_rate, 2)
    additional_medicare = round(max(0.0, gross - config.additional_medicare_threshold_single) * config.additional_medicare_rate, 2)
    total = round(federal + state + social_security + medicare + additional_medicare, 2)
    tax_at_no_401k = federal_income_tax(max(0.0, agi + actual_401k - deduction_used), config)
    tax_savings = round(max(0.0, tax_at_no_401k - federal), 2)
    roth_magi = agi + profile.roth_magi_adjustments
    roth_cap, phaseout_status = roth_direct_contribution_cap(
        roth_magi, profile.age, profile.annual_ira_contributions_already_made, config,
        compensation=max(0.0, gross - actual_401k),
        prior_traditional=profile.annual_traditional_ira_contributions_already_made,
    )
    recommended_401k = min(max(0.0, config.traditional_401k_limit - actual_401k), max(0.0, gross - actual_401k))
    recommended_ira = roth_cap
    if agi < config.roth_phaseout_start_single:
        pivot = "Prioritize capturing any employer match, then consider completing the pre-tax 401(k), followed by an eligible IRA contribution."
    elif agi < config.roth_phaseout_end_single:
        pivot = "Prioritize the employer match and 401(k). Direct Roth IRA eligibility is reduced; compare remaining direct Roth capacity with a backdoor Roth only after reviewing pre-tax IRA balances and tax consequences."
    else:
        pivot = "Prioritize the employer match and 401(k). Direct Roth IRA contributions are phased out; a backdoor Roth may be considered only after assessing the pro-rata rule and other IRA balances."
    prorata_note = (
        "Pre-tax IRA assets were reported. A Roth conversion may be partly taxable under the pro-rata rule; get individualized tax advice before converting."
        if profile.other_ira_assets > 0 else
        "No pre-tax IRA balance was reported. Confirm all traditional, SEP, and SIMPLE IRA balances at year-end before considering a backdoor Roth; the pro-rata rule can make a conversion taxable."
    )
    assumptions = (
        "2026 single-filer federal ordinary income tax brackets and $16,100 standard deduction.",
        "W-2 wages only; traditional employee 401(k) deferrals reduce modeled federal AGI but not FICA wages. The model uses the $24,500 base limit and excludes age-based catch-up contributions and their Roth treatment rules.",
        "State income tax is a configurable flat-rate estimate applied to income after modeled pre-tax adjustments and the deduction used.",
        "Includes employee Social Security and Medicare taxes, including Additional Medicare Tax; assumes no other employer wages.",
        "Roth IRA MAGI is estimated as modeled AGI plus user-entered MAGI adjustments; confirm actual MAGI before contributing.",
        "IRA compensation is approximated as modeled gross W-2 wages less traditional 401(k) deferrals. Prior IRA totals are treated as Roth unless their traditional portion is specified. Eligibility capacity is not a household affordability recommendation.",
        "Excludes tax credits, capital gains, qualified dividends, AMT, NIIT, itemized-deduction limits, special 2026 deductions, local taxes, and withholding/refund calculations.",
    )
    return TaxResult(
        tax_year=config.tax_year,
        gross_income=gross,
        traditional_401k_contribution=actual_401k,
        agi_estimate=round(agi, 2),
        roth_ira_magi_estimate=round(roth_magi, 2),
        standard_deduction=standard,
        itemized_deduction=itemized,
        deduction_used=deduction_used,
        federal_taxable_income=round(taxable, 2),
        federal_income_tax=federal,
        federal_marginal_rate=marginal,
        federal_effective_rate_on_gross=round(federal / gross, 4) if gross else 0.0,
        state_tax_estimate=state,
        social_security_tax=social_security,
        medicare_tax=medicare,
        additional_medicare_tax=additional_medicare,
        total_estimated_tax=total,
        estimated_take_home=round(gross - actual_401k - total, 2),
        tax_savings_from_401k=tax_savings,
        roth_ira_direct_contribution_cap=roth_cap,
        roth_ira_phaseout_status=phaseout_status,
        recommended_401k_contribution=round(recommended_401k, 2),
        recommended_ira_contribution=recommended_ira,
        backdoor_roth_pro_rata_note=prorata_note,
        strategic_pivot=pivot,
        assumptions=assumptions,
    )
