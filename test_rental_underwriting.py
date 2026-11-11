"""Independent cash-accounting and financing references for rental model v2."""

from decimal import Decimal, getcontext

import pytest

from scenario_engine import underwrite_rental


def inputs(**updates):
    values = dict(purchase_price=200_000, down_payment=40_000, closing_costs=5_000,
                  monthly_rent_per_unit=2_000, rented_units=1, total_units=1, vacancy_rate=.1,
                  annual_property_tax=2_400, annual_insurance=1_200, annual_maintenance=1_200,
                  annual_capex_reserve=1_200, annual_management_rate=.1, annual_interest_rate=0,
                  loan_term_years=20, initial_repairs=3_000, initial_operating_reserves=12_000)
    return dict(values, **updates)


def test_operating_noi_reserve_cashflow_and_capital_reconcile():
    result = underwrite_rental(**inputs())
    # 2,000 * .9 = 1,800 received; management180 and fixed costs400/month.
    assert result.monthly_operating_expenses == 580
    assert result.annual_noi == 14_640
    assert result.cap_rate == .0732
    assert result.annual_cash_flow_before_capex_reserve == 6_640
    assert result.annual_pre_tax_cash_flow == 5_440
    assert result.cash_invested_estimate == 48_000
    assert result.initial_cash_required == 60_000
    assert result.cash_on_cash_return == .0907
    assert result.first_year_interest == 0
    assert result.first_year_principal == 8_000
    assert result.loan_balance_after_one_year == 152_000


def test_capex_and_initial_reserve_have_separate_accounting_effects():
    base = underwrite_rental(**inputs())
    extra_capex = underwrite_rental(**inputs(annual_capex_reserve=2_400))
    extra_cash = underwrite_rental(**inputs(initial_operating_reserves=24_000))
    assert extra_capex.annual_noi == base.annual_noi
    assert extra_capex.cap_rate == base.cap_rate and extra_capex.dscr == base.dscr
    assert extra_capex.annual_pre_tax_cash_flow == base.annual_pre_tax_cash_flow-1200
    assert extra_cash.annual_pre_tax_cash_flow == base.annual_pre_tax_cash_flow
    assert extra_cash.initial_cash_required == base.initial_cash_required+12_000
    assert extra_cash.cash_on_cash_return < base.cash_on_cash_return


def test_break_even_rent_funds_all_costs_and_reserves_within_cent_rounding():
    result = underwrite_rental(**inputs())
    assert result.break_even_monthly_rent_per_unit == 1440.33
    solved = underwrite_rental(**inputs(monthly_rent_per_unit=result.break_even_monthly_rent_per_unit))
    assert abs(solved.annual_pre_tax_cash_flow) <= .1


def test_interest_and_principal_match_independent_decimal_amortization():
    getcontext().prec = 40
    balance, rate = Decimal(160000), Decimal(".065")/12
    months = 360
    payment = balance * rate * (1+rate)**months / ((1+rate)**months-1)
    interest_total = Decimal(0)
    for _ in range(12):
        interest = balance*rate
        interest_total += interest
        balance -= payment-interest
    result = underwrite_rental(**inputs(annual_interest_rate=.065, loan_term_years=30))
    assert result.first_year_interest == float(interest_total.quantize(Decimal(".01")))
    assert result.loan_balance_after_one_year == float(balance.quantize(Decimal(".01")))
    assert result.first_year_principal == float((Decimal(160000)-balance).quantize(Decimal(".01")))


def test_cash_purchase_and_zero_capital_do_not_report_fabricated_ratios():
    cash = underwrite_rental(**inputs(down_payment=200_000))
    assert cash.dscr is None and cash.monthly_debt_service == 0
    assert cash.first_year_interest == cash.first_year_principal == 0
    leveraged = underwrite_rental(**inputs(down_payment=0, closing_costs=0, initial_repairs=0, initial_operating_reserves=0))
    assert leveraged.cash_on_cash_return is None


@pytest.mark.parametrize("changes", [{"vacancy_rate": 1}, {"annual_management_rate": 1}, {"rented_units": 0}])
def test_no_rent_capacity_is_explicit_not_infinity(changes):
    result = underwrite_rental(**inputs(**changes))
    assert result.break_even_monthly_rent_per_unit is None
    assert result.break_even_status == "no_rent_capacity"
    assert result.annual_pre_tax_cash_flow < 0


def test_hoa_utilities_and_fully_vacant_scenarios_are_supported():
    result = underwrite_rental(**inputs(annual_hoa=1200, annual_owner_paid_utilities=600))
    assert result.annual_noi == 12_840
    with pytest.raises(ValueError):
        underwrite_rental(**inputs(rented_units=1.5))
