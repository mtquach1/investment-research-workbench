"""Visualizations reconcile to the engines and preserve constraint failures."""

from decimal import Decimal

import pytest

from investment_visuals import (inspect_rental, rental_cashflow_curve,
    rental_funding_landscape, rental_waterfall, stock_chart_data)
from rental_feasibility import RentalFeasibilityRequest
from stock_strategy import StrategyDemoRequest, strategy_demo


def rental(**updates):
    return RentalFeasibilityRequest(available_capital=100000,monthly_rent=3000,
        minimum_purchase_price=50000,maximum_purchase_price=600000,candidate_purchase_price=300000,
        initial_repairs=5000,initial_operating_reserves=10000,annual_insurance=1800,
        annual_maintenance=2400,annual_capex_reserve=1800,**updates)


def test_chart_boundary_and_inspected_point_reconcile():
    request = rental()
    solved, rows = rental_funding_landscape(request)
    boundary = solved.maximum_feasible
    assert boundary is not None
    assert any(row['price'] == boundary.purchase_price and row['feasible'] for row in rows)
    selected = next(row for row in rows if row['price'] == 300000)
    assert selected['minimum_down'] == solved.candidate.minimum_down_payment
    result = inspect_rental(request, Decimal(str(selected['minimum_down'])))
    assert result.annual_pre_tax_cash_flow == pytest.approx(solved.candidate.annual_cash_flow_at_minimum_down, abs=.01)
    assert result.initial_cash_required == solved.candidate.initial_cash_required_at_minimum_down


def test_cashflow_curve_ends_and_waterfall_reconcile():
    request = rental()
    rows = rental_cashflow_curve(request)
    assert rows[0]['down_payment'] == 0
    assert rows[-1]['down_payment'] == 300000
    assert all(a['annual_cash_flow'] < b['annual_cash_flow'] for a,b in zip(rows,rows[1:]))
    result = inspect_rental(request,Decimal(60000))
    waterfall = rental_waterfall(result)
    assert sum(row['amount'] for row in waterfall[:-1]) == pytest.approx(result.annual_pre_tax_cash_flow,abs=.20)
    higher = inspect_rental(request.model_copy(update={'monthly_rent':Decimal(3500)}),Decimal(60000))
    assert higher.annual_pre_tax_cash_flow-result.annual_pre_tax_cash_flow == pytest.approx(500*12*.95*.92,abs=.01)
    with pytest.raises(ValueError):
        inspect_rental(request,Decimal(300001))


def test_no_match_is_missing_band_not_zero_imputed():
    _, rows = rental_funding_landscape(rental(minimum_annual_cash_flow=1000000))
    assert all(not row['feasible'] and row['minimum_down'] is None for row in rows)
    with pytest.raises(ValueError):
        rental_cashflow_curve(rental(), points=100000)


@pytest.mark.parametrize('scenario',['balanced','missing_data','sector_bottleneck'])
def test_stock_visuals_preserve_score_and_allocation_constraints(scenario):
    result = strategy_demo(StrategyDemoRequest(scenario=scenario))
    points, features, sectors, labels = stock_chart_data(result)
    assert len(labels) == 30
    for point in points:
        assert point['quality']*.6+point['valuation']*.4 == pytest.approx(point['score'])
        assert sum(row['contribution'] for row in features[point['security_id']]) == pytest.approx(point['score'])
    assert all(row['weight'] <= 30 for row in sectors)
    assert sum(row['weight'] for row in sectors) == (100 if result['selected'] else 0)
    if scenario=='missing_data':
        assert len(points) < len(labels)
