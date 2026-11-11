"""Assumption-driven retirement, portfolio, rental, and flip calculators.

No market returns or property outcomes are predicted. Every output is a math
projection from values supplied by the user.
"""

from dataclasses import dataclass
from math import expm1, isfinite, log1p


def time_budget_metrics(estimated_monthly_hours: float | None,
                        available_monthly_hours: float | None) -> dict[str, float | bool | None]:
    """Compare a user's time estimate with their stated monthly time budget.

    A fit result is omitted until both values are supplied. Utilization is undefined
    for a zero-hour budget, but fit remains a direct comparison.
    """
    for name, value in (("estimated_monthly_hours", estimated_monthly_hours),
                        ("available_monthly_hours", available_monthly_hours)):
        if value is not None and (not isfinite(value) or value < 0 or value > 1000):
            raise ValueError(f"{name} must be between 0 and 1000 hours")
    fit = None if estimated_monthly_hours is None or available_monthly_hours is None else estimated_monthly_hours <= available_monthly_hours
    utilization = None
    if fit is not None and available_monthly_hours:
        utilization = round(estimated_monthly_hours / available_monthly_hours, 4)
    return {
        "estimated_monthly_hours": estimated_monthly_hours,
        "available_monthly_hours": available_monthly_hours,
        "time_budget_utilization": utilization,
        "fits_time_budget": fit,
    }


def _nonnegative(name: str, value: float) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


def _rate(name: str, value: float, *, upper: float = 1.0) -> None:
    if not isfinite(value) or value < 0 or value > upper:
        raise ValueError(f"{name} must be between 0 and {upper}")


def future_value(monthly_contribution: float, years: int, annual_return: float, annual_fee: float = 0.0) -> float:
    """Future value with monthly end-of-month deposits and monthly net return."""
    _nonnegative("monthly_contribution", monthly_contribution)
    if not isfinite(annual_return) or annual_return < -0.95 or annual_return > 1:
        raise ValueError("annual_return must be between -0.95 and 1.0")
    _rate("annual_fee", annual_fee, upper=0.1)
    if annual_return - annual_fee <= -1:
        raise ValueError("annual return less fees must be greater than -100%")
    if not 1 <= years <= 60:
        raise ValueError("years must be between 1 and 60")
    monthly_rate = (1.0 + annual_return - annual_fee) ** (1.0 / 12.0) - 1.0
    months = years * 12
    if monthly_rate == 0:
        return round(monthly_contribution * months, 2)
    return round(monthly_contribution * (((1 + monthly_rate) ** months - 1) / monthly_rate), 2)


@dataclass(frozen=True)
class PortfolioProjection:
    years: int
    monthly_contribution: float
    annual_return_assumption: float
    annual_fee_assumption: float
    total_contributions: float
    projected_balance: float
    projected_growth: float
    disclaimer: str = "Illustrative projection from user-entered assumptions; not an expected or guaranteed return."


def project_portfolio(monthly_contribution: float, years: int, annual_return: float, annual_fee: float = 0.0) -> PortfolioProjection:
    balance = future_value(monthly_contribution, years, annual_return, annual_fee)
    contributions = round(monthly_contribution * years * 12, 2)
    return PortfolioProjection(years, monthly_contribution, annual_return, annual_fee, contributions, balance,
                               round(balance - contributions, 2))


@dataclass(frozen=True)
class GoalProjection:
    annual_return_assumption: float
    total_contributions: float
    projected_balance_nominal: float
    projected_balance_in_today_dollars: float
    projected_growth: float
    target_amount_future_dollars: float | None
    goal_surplus_or_shortfall: float | None
    required_monthly_contribution: float | None
    goal_status: str
    disclaimer: str = "Scenario estimate from user-entered assumptions; investment returns are not guaranteed."


@dataclass(frozen=True)
class GoalSensitivityFactor:
    assumption: str
    low_input: float
    base_input: float
    high_input: float
    balance_at_low_input_today_dollars: float
    balance_at_base_today_dollars: float
    balance_at_high_input_today_dollars: float
    balance_span_today_dollars: float
    impact_rank: int


@dataclass(frozen=True)
class GoalSensitivityAnalysis:
    goal_name: str
    factors: list[GoalSensitivityFactor]
    method: str = "One-variable-at-a-time deterministic sensitivity; each factor changes independently while other assumptions stay at base values."
    disclaimer: str = "Sensitivity shows model response to the supplied ranges. It does not assign likelihood to any input or outcome."


def analyze_goal_sensitivity(*, goal_name: str, current_balance: float, monthly_contribution: float,
                             years: int, annual_return: float, annual_fee: float,
                             annual_inflation: float, target_amount_today: float | None,
                             ranges: dict[str, tuple[float, float]]) -> GoalSensitivityAnalysis:
    """Rank one-at-a-time assumption ranges by change in real projected balance."""
    base = project_goal(current_balance=current_balance, monthly_contribution=monthly_contribution,
                        years=years, annual_return=annual_return, annual_fee=annual_fee,
                        annual_inflation=annual_inflation, target_amount_today=target_amount_today)
    base_values = {
        "annual_return": annual_return,
        "monthly_contribution": monthly_contribution,
        "annual_fee": annual_fee,
        "annual_inflation": annual_inflation,
    }
    allowed = set(base_values)
    if set(ranges) != allowed:
        raise ValueError("ranges must include annual_return, monthly_contribution, annual_fee, and annual_inflation")

    measured: list[tuple[str, float, float, float, float, float, float]] = []
    for key in ("annual_return", "monthly_contribution", "annual_fee", "annual_inflation"):
        low, high = ranges[key]
        base_value = base_values[key]
        if low > high or not low <= base_value <= high:
            raise ValueError(f"{key} sensitivity range must be ordered and contain its base assumption")
        outputs: list[float] = []
        for value in (low, base_value, high):
            assumptions = dict(base_values)
            assumptions[key] = value
            projected = project_goal(
                current_balance=current_balance,
                monthly_contribution=assumptions["monthly_contribution"],
                years=years,
                annual_return=assumptions["annual_return"],
                annual_fee=assumptions["annual_fee"],
                annual_inflation=assumptions["annual_inflation"],
                target_amount_today=target_amount_today,
            )
            outputs.append(projected.projected_balance_in_today_dollars)
        measured.append((key, low, base_value, high, outputs[0], outputs[1], outputs[2]))

    ranked = sorted(measured, key=lambda item: max(item[4], item[6]) - min(item[4], item[6]), reverse=True)
    factors = [
        GoalSensitivityFactor(
            assumption=key,
            low_input=round(low, 6),
            base_input=round(base_value, 6),
            high_input=round(high, 6),
            balance_at_low_input_today_dollars=low_balance,
            balance_at_base_today_dollars=base_balance,
            balance_at_high_input_today_dollars=high_balance,
            balance_span_today_dollars=round(max(low_balance, high_balance) - min(low_balance, high_balance), 2),
            impact_rank=index,
        )
        for index, (key, low, base_value, high, low_balance, base_balance, high_balance) in enumerate(ranked, start=1)
    ]
    return GoalSensitivityAnalysis(goal_name=goal_name, factors=factors)


def project_goal(*, current_balance: float, monthly_contribution: float, years: int,
                 annual_return: float, annual_fee: float, annual_inflation: float,
                 target_amount_today: float | None = None) -> GoalProjection:
    """Project a goal account, its current-dollar value, and target funding pace."""
    _nonnegative("current_balance", current_balance)
    _nonnegative("monthly_contribution", monthly_contribution)
    if not isfinite(annual_return) or not -0.95 <= annual_return <= 1.0:
        raise ValueError("annual_return must be between -0.95 and 1.0")
    _rate("annual_fee", annual_fee, upper=0.1)
    _rate("annual_inflation", annual_inflation, upper=0.2)
    if annual_return - annual_fee <= -1:
        raise ValueError("annual return less fees must be greater than -100%")
    if not 1 <= years <= 60:
        raise ValueError("years must be between 1 and 60")
    if target_amount_today is not None:
        _nonnegative("target_amount_today", target_amount_today)

    monthly_rate = (1.0 + annual_return - annual_fee) ** (1.0 / 12.0) - 1.0
    months = years * 12
    growth_factor = (1.0 + monthly_rate) ** months
    annuity_factor = months if monthly_rate == 0 else (growth_factor - 1.0) / monthly_rate
    future_balance = current_balance * growth_factor + monthly_contribution * annuity_factor
    total_contributions = current_balance + monthly_contribution * months
    inflation_factor = (1.0 + annual_inflation) ** years
    target_future = None if target_amount_today is None else target_amount_today * inflation_factor
    surplus = None if target_future is None else future_balance - target_future
    required_monthly = None
    if target_future is not None:
        required_monthly = max(0.0, (target_future - current_balance * growth_factor) / annuity_factor)
    status = "target not provided" if target_future is None else ("on track under this scenario" if surplus >= 0 else "below target under this scenario")
    return GoalProjection(
        annual_return_assumption=annual_return,
        total_contributions=round(total_contributions, 2),
        projected_balance_nominal=round(future_balance, 2),
        projected_balance_in_today_dollars=round(future_balance / inflation_factor, 2),
        projected_growth=round(future_balance - total_contributions, 2),
        target_amount_future_dollars=None if target_future is None else round(target_future, 2),
        goal_surplus_or_shortfall=None if surplus is None else round(surplus, 2),
        required_monthly_contribution=None if required_monthly is None else round(required_monthly, 2),
        goal_status=status,
    )


@dataclass(frozen=True)
class RetirementAccountComparison:
    annual_gross_contribution: float
    current_marginal_tax_rate: float
    retirement_tax_rate_assumption: float
    years: int
    annual_return_assumption: float
    traditional_current_tax_reduction_estimate: float
    traditional_future_balance_before_tax: float
    traditional_future_spendable_balance: float
    roth_contribution_at_equal_current_cash_cost: float
    roth_future_spendable_balance: float
    traditional_advantage_at_assumptions: float
    note: str


def compare_retirement_accounts(annual_gross_contribution: float, current_marginal_tax_rate: float,
                                retirement_tax_rate: float, years: int, annual_return: float,
                                annual_fee: float = 0.0) -> RetirementAccountComparison:
    _nonnegative("annual_gross_contribution", annual_gross_contribution)
    _rate("current_marginal_tax_rate", current_marginal_tax_rate, upper=0.6)
    _rate("retirement_tax_rate", retirement_tax_rate, upper=0.6)
    if not 1 <= years <= 60:
        raise ValueError("years must be between 1 and 60")
    if not isfinite(annual_return) or annual_return < -0.95 or annual_return > 1:
        raise ValueError("annual_return must be between -0.95 and 1.0")
    _rate("annual_fee", annual_fee, upper=0.1)
    if annual_return - annual_fee <= -1:
        raise ValueError("annual return less fees must be greater than -100%")
    monthly_traditional = annual_gross_contribution / 12
    # Same paycheck cost: Roth dollars are after-tax, while traditional contributions
    # reduce current tax by approximately the marginal rate.
    monthly_roth = monthly_traditional * (1 - current_marginal_tax_rate)
    trad_pre_tax = future_value(monthly_traditional, years, annual_return, annual_fee)
    trad_spendable = round(trad_pre_tax * (1 - retirement_tax_rate), 2)
    roth_spendable = future_value(monthly_roth, years, annual_return, annual_fee)
    tax_cut = round(annual_gross_contribution * current_marginal_tax_rate, 2)
    return RetirementAccountComparison(
        annual_gross_contribution, current_marginal_tax_rate, retirement_tax_rate, years, annual_return,
        tax_cut, trad_pre_tax, trad_spendable, round(monthly_roth * 12, 2), roth_spendable,
        round(trad_spendable - roth_spendable, 2),
        "Equal-current-cash-cost comparison. Simplifies tax brackets, contribution limits, employer match, withdrawals, and future law; tax-rate and return assumptions change the result.",
    )


def _mortgage_payment(principal: float, annual_rate: float, years: int) -> float:
    if principal == 0:
        return 0.0
    monthly_rate = annual_rate / 12
    months = years * 12
    if monthly_rate == 0:
        return principal / months
    return principal * monthly_rate / -expm1(-months * log1p(monthly_rate))


@dataclass(frozen=True)
class RentalUnderwriting:
    purchase_price: float
    monthly_gross_rent: float
    monthly_effective_rent: float
    monthly_operating_expenses: float
    monthly_debt_service: float
    annual_noi: float
    cap_rate: float
    annual_pre_tax_cash_flow: float
    cash_invested_estimate: float
    cash_on_cash_return: float | None
    dscr: float | None
    monthly_owner_occupied_rent_comparable: float
    initial_repairs: float
    initial_operating_reserves: float
    initial_cash_required: float
    annual_capex_reserve: float
    annual_cash_flow_before_capex_reserve: float
    break_even_monthly_rent_per_unit: float | None
    break_even_status: str
    first_year_interest: float
    first_year_principal: float
    loan_balance_after_one_year: float
    model_version: str = "rental-underwriting-v2"
    disclaimer: str = "Underwriting estimate from user assumptions, not an appraisal, loan approval, tax calculation, or rent guarantee."


def underwrite_rental(*, purchase_price: float, down_payment: float, closing_costs: float,
                      monthly_rent_per_unit: float, rented_units: int, vacancy_rate: float,
                      annual_property_tax: float, annual_insurance: float, annual_maintenance: float,
                      annual_capex_reserve: float, annual_management_rate: float,
                      annual_interest_rate: float, loan_term_years: int, monthly_owner_costs: float = 0.0,
                      owner_occupied_units: int = 0, total_units: int = 1,
                      initial_repairs: float = 0.0, initial_operating_reserves: float = 0.0,
                      annual_hoa: float = 0.0, annual_owner_paid_utilities: float = 0.0) -> RentalUnderwriting:
    for key, value in {"purchase_price": purchase_price, "down_payment": down_payment, "closing_costs": closing_costs,
                       "monthly_rent_per_unit": monthly_rent_per_unit, "annual_property_tax": annual_property_tax,
                       "annual_insurance": annual_insurance, "annual_maintenance": annual_maintenance,
                       "annual_capex_reserve": annual_capex_reserve, "monthly_owner_costs": monthly_owner_costs,
                       "initial_repairs": initial_repairs, "initial_operating_reserves": initial_operating_reserves,
                       "annual_hoa": annual_hoa, "annual_owner_paid_utilities": annual_owner_paid_utilities}.items():
        _nonnegative(key, value)
        if value > 100_000_000:
            raise ValueError(f"{key} exceeds the supported rental amount")
    _rate("vacancy_rate", vacancy_rate, upper=1)
    _rate("annual_management_rate", annual_management_rate, upper=1)
    _rate("annual_interest_rate", annual_interest_rate, upper=.5)
    if any(not isinstance(value, int) or isinstance(value, bool)
           for value in (rented_units, owner_occupied_units, total_units, loan_term_years)):
        raise ValueError("Unit counts and loan term must be integers")
    if max(rented_units, owner_occupied_units, total_units) > 100:
        raise ValueError("Unit counts cannot exceed 100")
    if purchase_price <= 0 or down_payment > purchase_price or rented_units < 0 or owner_occupied_units < 0 or total_units < 1:
        raise ValueError("Price must be positive; down payment cannot exceed price; total units must be positive")
    if rented_units + owner_occupied_units > total_units:
        raise ValueError("Rented and owner-occupied units cannot exceed total_units")
    if not 1 <= loan_term_years <= 50:
        raise ValueError("loan_term_years must be between 1 and 50")
    gross_monthly = monthly_rent_per_unit * rented_units
    effective_monthly = gross_monthly * (1 - vacancy_rate)
    management_monthly = effective_monthly * annual_management_rate
    fixed_operating_monthly = (annual_property_tax + annual_insurance + annual_maintenance + annual_hoa + annual_owner_paid_utilities) / 12 + monthly_owner_costs
    operating_monthly = fixed_operating_monthly + management_monthly
    monthly_noi = effective_monthly - operating_monthly
    loan = purchase_price - down_payment
    monthly_debt = _mortgage_payment(loan, annual_interest_rate, loan_term_years)
    annual_noi = monthly_noi * 12
    before_reserves = (monthly_noi - monthly_debt) * 12
    annual_cf = before_reserves - annual_capex_reserve
    invested = down_payment + closing_costs + initial_repairs
    capital_required = invested + initial_operating_reserves
    retention = rented_units * (1-vacancy_rate) * (1-annual_management_rate)
    needed = fixed_operating_monthly + monthly_debt + annual_capex_reserve/12
    break_even = needed/retention if retention > 0 else 0.0 if rented_units and needed == 0 else None
    balance, principal_paid, interest_paid = loan, 0.0, 0.0
    for _ in range(12):
        interest = balance * annual_interest_rate/12
        principal = min(balance, max(0.0, monthly_debt-interest))
        balance = max(0.0, balance-principal)
        principal_paid += principal
        interest_paid += interest
    return RentalUnderwriting(
        purchase_price=purchase_price, monthly_gross_rent=gross_monthly,
        monthly_effective_rent=round(effective_monthly, 2), monthly_operating_expenses=round(operating_monthly, 2),
        monthly_debt_service=round(monthly_debt, 2), annual_noi=round(annual_noi, 2),
        cap_rate=round(annual_noi/purchase_price, 4), annual_pre_tax_cash_flow=round(annual_cf, 2),
        cash_invested_estimate=round(invested, 2),
        cash_on_cash_return=round(annual_cf/capital_required, 4) if capital_required else None,
        dscr=round(annual_noi/(monthly_debt*12), 4) if monthly_debt else None,
        monthly_owner_occupied_rent_comparable=0.0 if owner_occupied_units == 0 else round(monthly_rent_per_unit*owner_occupied_units, 2),
        initial_repairs=round(initial_repairs, 2), initial_operating_reserves=round(initial_operating_reserves, 2),
        initial_cash_required=round(capital_required, 2), annual_capex_reserve=round(annual_capex_reserve, 2),
        annual_cash_flow_before_capex_reserve=round(before_reserves, 2),
        break_even_monthly_rent_per_unit=None if break_even is None else round(break_even, 2),
        break_even_status="available" if break_even is not None else "no_rent_capacity",
        first_year_interest=round(interest_paid, 2), first_year_principal=round(principal_paid, 2),
        loan_balance_after_one_year=round(balance, 2),
        disclaimer="Illustrative pre-tax property model. NOI excludes debt service and capex reserves; cash flow deducts both. Cash-on-cash uses initial capital including held operating reserves. Excludes depreciation, appreciation, sale taxes and lender qualification; owner-occupied rent comparable is not cash income.",
    )


@dataclass(frozen=True)
class FlipUnderwriting:
    purchase_price: float
    rehab_budget: float
    contingency: float
    holding_costs: float
    selling_costs: float
    financing_costs: float
    all_in_cost: float
    estimated_resale_value: float
    estimated_profit_before_tax: float
    estimated_return_on_cost: float
    break_even_resale_price: float
    disclaimer: str = "Illustrative project math from entered assumptions; excludes tax, permitting delays, hidden defects, and market uncertainty."


def underwrite_flip(*, purchase_price: float, rehab_budget: float, contingency_rate: float,
                    holding_months: int, monthly_holding_cost: float, selling_cost_rate: float,
                    financing_costs: float, estimated_resale_value: float, closing_costs: float = 0.0) -> FlipUnderwriting:
    for key, value in {"purchase_price": purchase_price, "rehab_budget": rehab_budget,
                       "monthly_holding_cost": monthly_holding_cost, "financing_costs": financing_costs,
                       "estimated_resale_value": estimated_resale_value, "closing_costs": closing_costs}.items():
        _nonnegative(key, value)
    _rate("contingency_rate", contingency_rate, upper=1)
    _rate("selling_cost_rate", selling_cost_rate, upper=.25)
    if purchase_price <= 0 or not 0 <= holding_months <= 60:
        raise ValueError("purchase_price must be positive and holding_months between 0 and 60")
    contingency = rehab_budget * contingency_rate
    holding = monthly_holding_cost * holding_months
    selling = estimated_resale_value * selling_cost_rate
    all_in = purchase_price + rehab_budget + contingency + holding + financing_costs + closing_costs
    profit = estimated_resale_value - selling - all_in
    return FlipUnderwriting(purchase_price, rehab_budget, round(contingency, 2), round(holding, 2), round(selling, 2),
                            financing_costs, round(all_in, 2), estimated_resale_value, round(profit, 2),
                            round(profit / all_in, 4) if all_in else 0.0,
                            round(all_in / (1 - selling_cost_rate), 2))
