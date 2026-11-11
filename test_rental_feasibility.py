"""Independent brute-force cent-grid oracle and economic boundary references."""

from decimal import Decimal, ROUND_CEILING, localcontext
from fractions import Fraction
from random import Random

from rental_feasibility import RentalFeasibilityRequest, solve_rental_feasibility


def test_exact_cash_purchase_budget_boundary_and_one_cent_failure():
    request = RentalFeasibilityRequest(available_capital="100", monthly_rent="100", minimum_down_payment_rate=1,
        maximum_purchase_price="200", closing_cost_rate=".02", fixed_closing_costs="1",
        annual_property_tax_rate=0, annual_interest_rate=0)
    result = solve_rental_feasibility(request)
    assert result.maximum_feasible.purchase_price == 97.05
    assert result.maximum_feasible.minimum_down_payment == 97.05
    assert result.maximum_feasible.initial_cash_required_at_minimum_down == 100
    assert not result.search_bound_reached
    above = request.model_copy(update={"minimum_purchase_price": Decimal("97.06")})
    assert solve_rental_feasibility(above).status == "infeasible"


def test_joint_price_and_down_payment_intervals_match_brute_force():
    rng = Random(280026)
    for _ in range(35):
        budget = rng.randrange(1, 31)
        # Costs/rent are cents; zero-interest 20-year loan -> exact annual factor .05.
        rent = rng.randrange(0, 3)
        fee = rng.randrange(0, 3)
        min_down = Fraction(rng.choice([0, 2, 5, 10]), 10)
        tax = Fraction(rng.choice([0, 1]), 10)
        close = Fraction(rng.choice([0, 1]), 10)
        coc = rng.choice([None, Fraction(0), Fraction(1, 20), Fraction(1, 10)])
        request = RentalFeasibilityRequest(available_capital=Decimal(budget)/100, monthly_rent=Decimal(rent)/100,
            minimum_purchase_price=".01", maximum_purchase_price=".30", minimum_down_payment_rate=str(float(min_down)),
            annual_interest_rate=0, loan_term_years=20, fixed_closing_costs=Decimal(fee)/100,
            closing_cost_rate=str(float(close)), annual_property_tax_rate=str(float(tax)), vacancy_rate=0,
            management_rate=0, minimum_cash_on_cash_return=None if coc is None else str(float(coc)))
        feasible = {}
        for price in range(1, 31):
            capital_cost = fee-(-(close*price).numerator//(close*price).denominator)
            property_tax = -(-(tax*price).numerator//(tax*price).denominator)
            downs = []
            for down in range(price+1):
                cf = rent*12-property_tax-Fraction(price-down, 20)
                initial = down+capital_cost
                if (down >= min_down*price and initial <= budget and cf >= 0 and
                        (coc is None or (initial > 0 and cf >= coc*initial))):
                    downs.append(down)
            if downs:
                feasible[price] = downs
        result = solve_rental_feasibility(request)
        if not feasible:
            assert result.status == "infeasible"
        else:
            price = max(feasible)
            assert result.maximum_feasible.purchase_price == price/100
            assert result.maximum_feasible.minimum_down_payment == min(feasible[price])/100
            assert result.maximum_feasible.maximum_down_payment == max(feasible[price])/100
        assert result.prices_evaluated <= 9


def test_realistic_case_candidate_range_and_bound_reporting():
    result = solve_rental_feasibility(RentalFeasibilityRequest(available_capital="100000", monthly_rent="3000",
        candidate_purchase_price="300000", annual_insurance="1500", annual_maintenance="3000",
        annual_capex_reserve="2000", initial_repairs="5000", initial_operating_reserves="10000"))
    assert result.maximum_feasible.purchase_price == 349535.96
    assert result.candidate_status == "feasible"
    assert result.candidate.minimum_down_payment >= 60000
    assert result.prices_evaluated <= 38
    # Independent high-precision financing reference: even the largest affordable
    # down payment at one cent higher leaves negative annual distributable cash.
    with localcontext() as context:
        context.prec = 70
        rate = Decimal(".065")/12
        factor = 12*rate*(1+rate)**360/((1+rate)**360-1)
        def reference_cashflow(price):
            closing = (price*Decimal(".02")).quantize(Decimal(".01"), rounding=ROUND_CEILING)
            maximum_down = min(price, Decimal(100000)-15000-closing)
            tax = (price*Decimal(".0125")).quantize(Decimal(".01"), rounding=ROUND_CEILING)
            return Decimal(3000)*12*Decimal(".95")*Decimal(".92")-1500-3000-2000-tax-factor*(price-maximum_down)
        assert reference_cashflow(Decimal("349535.96")) >= 0
        assert reference_cashflow(Decimal("349535.97")) < 0
    clipped = solve_rental_feasibility(RentalFeasibilityRequest(available_capital="1000000", monthly_rent="10000",
        maximum_purchase_price="100000"))
    assert clipped.search_bound_reached and clipped.maximum_feasible.purchase_price == 100000


def test_return_target_can_impose_upper_down_payment_bound():
    # With annual loan factor .05 below a 10% return target, extra equity can
    # reduce cash-on-cash. A solver assuming "more down always helps" is wrong.
    result = solve_rental_feasibility(RentalFeasibilityRequest(available_capital="1000", monthly_rent=".75",
        minimum_purchase_price="100", maximum_purchase_price="100", annual_interest_rate=0, loan_term_years=20,
        closing_cost_rate=0, annual_property_tax_rate=0, vacancy_rate=0, management_rate=0,
        minimum_cash_on_cash_return=".1"))
    assert result.maximum_feasible.minimum_down_payment == 20
    assert result.maximum_feasible.maximum_down_payment == 80


def test_zero_income_zero_cost_all_cash_is_not_lost_to_roundoff():
    result = solve_rental_feasibility(RentalFeasibilityRequest(available_capital="10000", monthly_rent=0,
        maximum_purchase_price="10000", closing_cost_rate=0, annual_property_tax_rate=0, annual_interest_rate=".000001",
        minimum_down_payment_rate=1, loan_term_years=50))
    assert result.maximum_feasible.purchase_price == 10000
    assert result.maximum_feasible.minimum_down_payment == 10000
