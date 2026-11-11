from decimal import Decimal as D
import pytest
from experimental_basket import ExperimentalRequest
from ranking_cost_evaluation import evaluate_ranking_costs
from test_experimental_basket import research_universe


def request(cents=100003):
    return ExperimentalRequest(acknowledge_proxy_and_estimates=True,budget_cents=cents)


def test_known_rank_reference_and_scenarios_preserve_input(tmp_path):
    screen=research_universe(tmp_path);before=screen.model_dump_json()
    report=evaluate_ranking_costs(screen,request())
    assert report.status=='evaluated'
    # Four groups of five have scores 0, .25, .5, .75, 1.
    assert report.strategy_score_total==D('8')
    assert report.alphabetical_score_total==D('2.25')
    assert report.row_order_invariant and report.uniform_yield_scale_invariant
    assert len(report.sensitivity)==40
    assert report.scenarios_with_changes==sum(row['Changed positions']>0 for row in report.sensitivity)
    assert 0<=report.minimum_retained<=10
    assert not report.investment_performance_verified and not report.live_recommendations_enabled
    assert screen.model_dump_json()==before


def test_entry_costs_use_equal_policies_and_explicit_trade_counts(tmp_path):
    report=evaluate_ranking_costs(research_universe(tmp_path),request())
    rows={row.scenario_id:row for row in report.costs}
    assert rows['zero'].basket_cost_cents==rows['zero'].benchmark_cost_cents==0
    assert rows['ten_bps'].basket_cost_cents==rows['ten_bps'].benchmark_cost_cents==100
    flat=rows['one_dollar_per_trade']
    assert flat.basket_trades==10 and flat.benchmark_trades==1
    assert flat.basket_cost_cents==1000 and flat.benchmark_cost_cents==100
    assert flat.basket_capital_cents==99003 and flat.benchmark_capital_cents==99903
    assert flat.extra_basket_cost_cents==900
    assert all(row.basket_capital_cents+row.basket_cost_cents==100003 for row in rows.values())


def test_unaffordable_cost_cases_never_create_negative_capital(tmp_path):
    report=evaluate_ranking_costs(research_universe(tmp_path),request(10))
    flat=next(row for row in report.costs if row.scenario_id=='one_dollar_per_trade')
    assert flat.status=='unaffordable' and flat.basket_capital_cents is None


@pytest.mark.parametrize('budget,expected',[(500,1),(1500,2)])
def test_percentage_costs_round_half_up_to_cents(tmp_path,budget,expected):
    report=evaluate_ranking_costs(research_universe(tmp_path),request(budget))
    row=next(row for row in report.costs if row.scenario_id=='ten_bps')
    assert row.basket_cost_cents==row.benchmark_cost_cents==expected


def test_consent_staleness_and_infeasible_baseline_withhold_evaluation(tmp_path):
    screen=research_universe(tmp_path)
    result=evaluate_ranking_costs(screen,ExperimentalRequest())
    assert result.status=='acknowledgement_required' and not result.costs and not result.sensitivity
    screen.universe.fresh=False
    assert evaluate_ranking_costs(screen,request()).status=='unavailable'
    screen.universe.fresh=True
    screen.rows=screen.rows[:5]
    assert evaluate_ranking_costs(screen,request()).status=='infeasible'
