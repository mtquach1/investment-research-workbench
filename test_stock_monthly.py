from decimal import Decimal as D
from types import SimpleNamespace
import pytest
from stock_monthly import plan_monthly_contribution
from stock_decisions import DecisionContext,DecisionHolding
from experimental_basket import experimental_basket,ExperimentalRequest
from test_experimental_basket import research_universe


def context(**changes):
    return DecisionContext(acknowledge_experimental=True,monthly_contribution_cents=100003,**changes)


def targets(screen):
    return [item.symbol for item in experimental_basket(screen,ExperimentalRequest(
        acknowledge_proxy_and_estimates=True,budget_cents=100003)).selected]


def test_monthly_cash_is_separate_from_initial_cash_and_reconciles_exactly(tmp_path):
    screen=research_universe(tmp_path);before=screen.model_dump_json()
    result=plan_monthly_contribution(screen,context())
    assert result.status=='allocated' and result.monthly_amount_cents==100003
    assert result.to_stocks_cents==100000 and result.cash_unassigned_cents==3
    assert {row.symbol for row in result.positions if row.target_weight}==set(targets(screen))
    assert result.to_stocks_cents+result.cash_unassigned_cents==result.monthly_amount_cents
    assert not result.live_recommendations_enabled and not result.automatic_schedule_enabled
    assert result.context == context()
    assert screen.model_dump_json()==before


def test_excluded_target_is_not_replaced_or_renormalized(tmp_path):
    screen=research_universe(tmp_path);symbol=targets(screen)[0]
    result=plan_monthly_contribution(screen,context(excluded_symbols=[symbol]))
    assert result.status=='allocated' and result.cash_unassigned_cents==10003
    assert next(row for row in result.positions if row.symbol==symbol).purchase_cents==0
    assert 'exclusion' in next(row for row in result.positions if row.symbol==symbol).explanation
    assert all(row.purchase_cents<=10000 for row in result.positions)


def test_cap_can_require_partial_cash_without_relaxing_the_cap(tmp_path):
    screen=research_universe(tmp_path)
    result=plan_monthly_contribution(screen,context(maximum_direct_weight=D('.05')))
    assert result.status=='allocated' and result.to_stocks_cents==50000 and result.cash_unassigned_cents==50003
    assert all(row.after_cents<=5000 for row in result.positions)


def test_existing_target_over_its_target_gets_no_extra_purchase(tmp_path):
    screen=research_universe(tmp_path);symbol=targets(screen)[0]
    result=plan_monthly_contribution(screen,context(maximum_direct_weight=1,
        holdings=[DecisionHolding(symbol=symbol,value_cents=100000)]))
    row=next(row for row in result.positions if row.symbol==symbol)
    assert result.status=='allocated' and row.before_cents==row.after_cents==100000 and row.purchase_cents==0
    assert result.to_stocks_cents+result.cash_unassigned_cents==100003


def test_overweight_position_that_cannot_be_diluted_withholds_the_plan(tmp_path):
    screen=research_universe(tmp_path);symbol=targets(screen)[0]
    result=plan_monthly_contribution(screen,context(holdings=[DecisionHolding(symbol=symbol,value_cents=100000)]))
    assert result.status=='infeasible' and not result.positions
    assert result.to_stocks_cents==0 and result.cash_unassigned_cents==100003


def test_unknown_holdings_stay_in_the_denominator_without_becoming_purchase_targets(tmp_path):
    screen=research_universe(tmp_path)
    result=plan_monthly_contribution(screen,context(holdings=[DecisionHolding(symbol='UNKNOWN',value_cents=10000)]))
    row=next(row for row in result.positions if row.symbol=='UNKNOWN')
    assert row.before_cents==row.after_cents==10000 and row.purchase_cents==0 and row.target_weight==0
    assert result.entered_holdings_cents==10000


def test_consent_freshness_zero_and_short_horizon_are_explicit(tmp_path):
    screen=research_universe(tmp_path);c=context();c.acknowledge_experimental=False
    assert plan_monthly_contribution(screen,c).status=='acknowledgement_required'
    c=context();c.monthly_contribution_cents=0
    assert plan_monthly_contribution(screen,c).status=='nothing_to_allocate'
    result=plan_monthly_contribution(screen,context(horizon_years=1))
    assert result.status=='cash_only' and result.cash_unassigned_cents==100003
    screen.universe.fresh=False
    assert plan_monthly_contribution(screen,context()).status=='unavailable'


def test_input_limits_never_silently_drop_holdings_or_round_caps(tmp_path):
    screen=research_universe(tmp_path)
    c=context(holdings=[DecisionHolding(symbol=f'X{i}',value_cents=1) for i in range(25)])
    assert plan_monthly_contribution(screen,c).status=='input_limit'
    assert plan_monthly_contribution(screen,context(maximum_direct_weight=D('.123456789'))).status=='input_limit'


def test_solver_failure_or_invalid_cents_never_leak_a_partial_purchase(tmp_path,monkeypatch):
    import stock_monthly
    screen=research_universe(tmp_path)
    monkeypatch.setattr(stock_monthly,'allocate_contributions',lambda request:SimpleNamespace(status='limit'))
    result=plan_monthly_contribution(screen,context())
    assert result.status=='solver_unavailable' and result.cash_unassigned_cents==100003
    monkeypatch.setattr(stock_monthly,'allocate_contributions',lambda request:SimpleNamespace(status='optimal',
        trades=[SimpleNamespace(account_id='monthly',asset_id='_CASH',amount_cents=1)],absolute_weight_drift=0))
    result=plan_monthly_contribution(screen,context())
    assert result.status=='solver_unavailable' and not result.positions
