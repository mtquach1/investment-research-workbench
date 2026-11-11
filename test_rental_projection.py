from decimal import Decimal as D
import pytest
from pydantic import ValidationError
from rental_feasibility import RentalFeasibilityRequest
from rental_projection import RentalProjectionRequest,project_rental


def request(**changes):
    p=RentalFeasibilityRequest(available_capital=200000,monthly_rent=1000,candidate_purchase_price=120000,
        closing_cost_rate=0,annual_property_tax_rate=0,annual_interest_rate=0,
        initial_operating_reserves=1200,annual_capex_reserve=1200,vacancy_rate=0,management_rate=0)
    values=dict(property=p,down_payment=120000,years=1,annual_rent_growth=0,annual_expense_growth=0,
                annual_appreciation=0,selling_cost_rate=0)
    values.update(changes)
    return RentalProjectionRequest(**values)


def test_cash_purchase_and_retained_reserves_reconcile_without_double_counting():
    result=project_rental(request())
    assert result.status=='funded' and result.completed_months==12
    assert result.initial_cash_required==121200
    assert result.total_distributions==10800
    assert result.months[-1].capex_reserves==1200
    assert result.exit_net_cash==122400 and result.net_profit==12000
    assert all(row.loan_balance==0 and row.interest==0 for row in result.months)
    repaired=project_rental(request(repair_shock_amount=600,repair_shock_month=12))
    assert repaired.net_profit==11400 and repaired.months[-1].capex_reserves==600


def test_zero_rate_amortization_clears_last_cent_and_stops_after_payoff():
    r=request(down_payment=0,years=2)
    r.property.loan_term_years=1
    r.property.monthly_rent=D(12000)
    result=project_rental(r)
    assert result.status=='funded'
    assert sum(row.principal for row in result.months)==120000
    assert result.months[11].loan_balance==0
    assert all(row.debt_payment==0 for row in result.months[12:])
    assert result.net_profit==288000


def test_interest_matches_independent_loan_reference_and_ledger_invariants():
    r=request(down_payment=20000,years=2)
    r.property.annual_interest_rate=D('.06');r.property.loan_term_years=30
    r.property.monthly_rent=D(5000)
    result=project_rental(r)
    # Independent standard mortgage reference: 100k, 6%, 360 payments.
    assert result.scheduled_monthly_payment==D('599.55')
    assert result.months[0].interest==500 and result.months[0].principal==D('99.55')
    previous=D(100000)
    for row in result.months:
        assert previous-row.principal==row.loan_balance
        assert row.debt_payment==row.principal+row.interest
        assert row.equity==row.property_value-row.loan_balance
        assert row.operating_cash_flow+row.reserve_draw+row.external_cash==row.distribution
        previous=row.loan_balance
    end=result.months[-1]
    assert result.net_profit==result.exit_net_cash+result.total_distributions-result.total_cash_invested
    assert result.exit_net_cash==end.property_value-result.selling_costs-end.loan_balance+end.operating_reserves+end.capex_reserves


def test_funding_failure_stops_before_unpaid_month_without_an_invented_sale():
    r=request();r.property.monthly_rent=D(0);r.property.annual_capex_reserve=D(0)
    r.property.annual_insurance=D(1200);r.property.initial_operating_reserves=D(200)
    result=project_rental(r)
    assert result.status=='funding_shortfall' and result.completed_months==2
    assert result.first_unfunded_month==3 and result.unfunded_amount==100
    assert result.net_profit is None and result.exit_net_cash is None
    r.additional_capital_limit=D(100)
    extended=project_rental(r)
    assert extended.completed_months==3 and extended.first_unfunded_month==4
    assert extended.months[-1].cumulative_external_cash==100


def test_initial_shortfall_no_timeline_and_invalid_inputs():
    r=request();r.property.available_capital=D(1)
    result=project_rental(r)
    assert result.status=='initial_capital_shortfall' and not result.months
    assert result.initial_capital_shortfall==121199 and result.net_profit is None
    with pytest.raises(ValidationError):request(down_payment=120001)
    with pytest.raises(ValidationError):request(repair_shock_month=13,repair_shock_amount=1)
    with pytest.raises(ValidationError):request(annual_appreciation='NaN')


def test_growth_starts_in_second_year_and_tax_does_not_follow_appreciation():
    r=request(years=2,annual_rent_growth='.1',annual_expense_growth='.1',annual_appreciation='.2')
    r.property.annual_property_tax_rate=D('.01')
    result=project_rental(r)
    assert result.months[0].collected_rent==1000 and result.months[11].collected_rent==1000
    assert result.months[12].collected_rent==1100
    assert result.months[0].operating_costs==100 and result.months[12].operating_costs==110
    assert result.months[11].property_value==144000 and result.months[23].property_value==172800


def test_underwater_sale_requires_budgeted_cash_without_double_counting():
    r=request(down_payment=0,annual_appreciation='-.5')
    r.property.annual_capex_reserve=D(0);r.property.initial_operating_reserves=D(0)
    r.property.monthly_rent=D(12000)
    result=project_rental(r)
    assert result.status=='exit_funding_shortfall' and result.completed_months==12
    assert result.exit_cash_before_funding==D('-56000.04')
    assert result.unfunded_amount==D('56000.04') and result.net_profit is None and result.exit_net_cash is None
    r.additional_capital_limit=D('56000.04')
    funded=project_rental(r)
    assert funded.status=='funded' and funded.exit_external_cash==D('56000.04')
    assert funded.exit_net_cash==0 and funded.total_cash_invested==D('56000.04')
    assert funded.net_profit==funded.total_distributions-funded.total_cash_invested
