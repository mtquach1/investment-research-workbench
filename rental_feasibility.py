"""Cent-level price/down-payment feasibility under explicit fixed rent assumptions.

At each price, cash, down-payment and return constraints define an integer-cent
interval for down payment. Feasibility is monotone as price decreases: keeping
the same down payment (capped at price) reduces debt, price-related costs and
capital. Binary search therefore finds the highest feasible cent in the bounds.
"""

from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import Field, model_validator

from schemas import StrictModel


Money = Annotated[Decimal, Field(ge=0, le=100_000_000, decimal_places=2, allow_inf_nan=False)]
Price = Annotated[Decimal, Field(gt=0, le=100_000_000, decimal_places=2, allow_inf_nan=False)]
Rate = Annotated[Decimal, Field(ge=0, le=1, decimal_places=6, allow_inf_nan=False)]


class RentalFeasibilityRequest(StrictModel):
    available_capital: Money
    monthly_rent: Money
    minimum_purchase_price: Price = Decimal("1.00")
    maximum_purchase_price: Price = Decimal("1000000.00")
    candidate_purchase_price: Price | None = None
    minimum_down_payment_rate: Rate = Decimal("0.20")
    annual_interest_rate: Annotated[Decimal, Field(ge=0, le=.5, decimal_places=6, allow_inf_nan=False)] = Decimal("0.065")
    loan_term_years: int = Field(default=30, ge=1, le=50, strict=True)
    fixed_closing_costs: Money = Decimal(0)
    closing_cost_rate: Rate = Decimal("0.02")
    initial_repairs: Money = Decimal(0)
    initial_operating_reserves: Money = Decimal(0)
    annual_property_tax_rate: Rate = Decimal("0.0125")
    annual_special_assessments: Money = Decimal(0)
    annual_insurance: Money = Decimal(0)
    annual_maintenance: Money = Decimal(0)
    annual_hoa: Money = Decimal(0)
    annual_owner_paid_utilities: Money = Decimal(0)
    annual_capex_reserve: Money = Decimal(0)
    vacancy_rate: Rate = Decimal("0.05")
    management_rate: Rate = Decimal("0.08")
    minimum_annual_cash_flow: Annotated[Decimal, Field(ge=-1_000_000, le=1_000_000, decimal_places=2, allow_inf_nan=False)] = Decimal(0)
    minimum_cash_on_cash_return: Rate | None = None

    @model_validator(mode="after")
    def coherent_search(self):
        if self.minimum_purchase_price > self.maximum_purchase_price:
            raise ValueError("Search price bounds are reversed")
        if self.candidate_purchase_price is not None and not self.minimum_purchase_price <= self.candidate_purchase_price <= self.maximum_purchase_price:
            raise ValueError("Candidate price must be within search bounds")
        return self


class FeasiblePrice(StrictModel):
    purchase_price: float
    minimum_down_payment: float
    maximum_down_payment: float
    initial_cash_required_at_minimum_down: float
    remaining_capital_at_minimum_down: float
    annual_cash_flow_at_minimum_down: float
    cash_on_cash_at_minimum_down: float | None
    details: dict[str, str]


class RentalFeasibilityResponse(StrictModel):
    model_version: Literal["rental-feasibility-v1"] = "rental-feasibility-v1"
    status: Literal["feasible", "infeasible"]
    explanation: str
    maximum_feasible: FeasiblePrice | None
    candidate: FeasiblePrice | None
    candidate_status: Literal["not_requested", "feasible", "infeasible"]
    search_bound_reached: bool
    prices_evaluated: int
    limitations: list[str] = Field(default_factory=lambda: [
        "One fully rented property. Rent and non-price-related expenses stay fixed across candidate prices.",
        "Price-related tax and closing costs round upward to cents; loan math uses unrounded payments.",
        "Cash-on-cash denominator includes held operating reserves. No sales, appreciation, depreciation or income tax.",
        "No mortgage insurance, loan fees beyond entered closing costs, or lender qualification is inferred.",
        "The maximum is conditional on these assumptions and bounded search, not a valuation or rent forecast.",
        "A permitted negative annual cash-flow target does not prove that future deficits can be funded.",
    ])


def solve_rental_feasibility(request: RentalFeasibilityRequest) -> RentalFeasibilityResponse:
    request = RentalFeasibilityRequest.model_validate(request.model_dump())
    with localcontext() as context:
        context.prec = 40
        return _solve(request)


def _solve(request):
    ceil = lambda value: -(-value.numerator//value.denominator)
    floor = lambda value: value.numerator//value.denominator
    decimal_value = lambda value: Decimal(value.numerator)/Decimal(value.denominator)
    cents = lambda amount: int(amount*100)
    budget = cents(request.available_capital)
    fixed_capital = cents(request.fixed_closing_costs+request.initial_repairs+request.initial_operating_reserves)
    fixed_annual_cost = cents(request.annual_special_assessments+request.annual_insurance+request.annual_maintenance+
                              request.annual_hoa+request.annual_owner_paid_utilities+request.annual_capex_reserve)
    annual_income = Fraction(cents(request.monthly_rent))*12*(1-Fraction(request.vacancy_rate))*(1-Fraction(request.management_rate))
    months, monthly_rate = request.loan_term_years*12, Fraction(request.annual_interest_rate)/12
    if monthly_rate == 0:
        annual_debt_factor = Fraction(12, months)
    else:
        growth = (1+monthly_rate)**months
        annual_debt_factor = 12*monthly_rate*growth/(growth-1)
    target = cents(request.minimum_annual_cash_flow)
    coc = Fraction(request.minimum_cash_on_cash_return) if request.minimum_cash_on_cash_return is not None else None
    evaluated = 0

    def interval(price):
        nonlocal evaluated
        evaluated += 1
        capital_cost = fixed_capital+ceil(Fraction(request.closing_cost_rate)*price)
        available_before_debt = annual_income-fixed_annual_cost-ceil(Fraction(request.annual_property_tax_rate)*price)
        base_cf = available_before_debt-annual_debt_factor*price
        low = max(0, ceil(Fraction(request.minimum_down_payment_rate)*price), ceil((target-base_cf)/annual_debt_factor))
        high = min(price, budget-capital_cost)
        if coc is not None:
            if capital_cost == 0:
                low = max(low, 1)  # Undefined zero-capital ratio cannot meet a return target.
            coefficient = annual_debt_factor-coc
            rhs = coc*capital_cost-base_cf
            if coefficient > 0:
                low = max(low, ceil(rhs/coefficient))
            elif coefficient < 0:
                high = min(high, floor(rhs/coefficient))
            elif rhs > 0:
                return None
        return (low, high, capital_cost, base_cf) if low <= high else None

    def output(price, bounds):
        low, high, capital_cost, base_cf = bounds
        required = low+capital_cost
        cashflow = base_cf+annual_debt_factor*low
        # Independent original-constraint checks on each end of the interval.
        for down in (low, high):
            cf, initial = base_cf+annual_debt_factor*down, down+capital_cost
            if not (0 <= down <= price and Fraction(down) >= Fraction(request.minimum_down_payment_rate)*price and initial <= budget and cf >= target):
                raise ArithmeticError("Feasibility output failed original constraints")
            if coc is not None and (initial <= 0 or cf < coc*initial):
                raise ArithmeticError("Feasibility output failed return constraint")
        return FeasiblePrice(purchase_price=price/100, minimum_down_payment=low/100, maximum_down_payment=high/100,
                             initial_cash_required_at_minimum_down=required/100,
                             remaining_capital_at_minimum_down=(budget-required)/100,
                             annual_cash_flow_at_minimum_down=floor(cashflow)/100,
                             cash_on_cash_at_minimum_down=float(cashflow/required) if required else None,
                             details={"annual_debt_factor_decimal": str(decimal_value(annual_debt_factor)),
                                      "annual_cash_flow_cents_decimal": str(decimal_value(cashflow)),
                                      "constraint_arithmetic": "exact_rational_internal; decimal details rounded to 40 significant digits",
                                      "price_related_tax_cents": str(ceil(Fraction(request.annual_property_tax_rate)*price)),
                                      "capital_cost_excluding_down_cents": str(capital_cost)})

    left, right = cents(request.minimum_purchase_price), cents(request.maximum_purchase_price)
    maximum = None
    if interval(left) is not None:
        while left < right:
            middle = (left+right+1)//2
            if interval(middle) is None:
                right = middle-1
            else:
                left = middle
        maximum = output(left, interval(left))
    candidate, candidate_status = None, "not_requested"
    if request.candidate_purchase_price is not None:
        price = cents(request.candidate_purchase_price)
        bounds = interval(price)
        candidate_status = "feasible" if bounds is not None else "infeasible"
        candidate = output(price, bounds) if bounds else None
    bound_reached = maximum is not None and maximum.purchase_price == float(request.maximum_purchase_price)
    return RentalFeasibilityResponse(status="feasible" if maximum else "infeasible",
        explanation="Highest feasible price within the entered search bounds; the down-payment range satisfies all modeled constraints." if maximum else
                    "No price in the entered range satisfies the cash, financing and cash-flow/return constraints.",
        maximum_feasible=maximum, candidate=candidate, candidate_status=candidate_status,
        search_bound_reached=bound_reached, prices_evaluated=evaluated)
