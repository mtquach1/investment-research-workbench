from copy import deepcopy
from datetime import date
from decimal import Decimal as D
import pytest
from pydantic import ValidationError
from company_research import _year
from stock_financials import normalize_annual_financials
from test_stock_financials import company
from test_stock_screen import screen_store
from stock_screen import stock_screen
from stock_metrics import Metric,ScreenFilters,filter_screen,screen_metrics


DAY=date(2026,10,28)


def test_metrics_growth_reference_missing_loss_baseline_and_period_gap():
    raw=normalize_annual_financials(company(),as_of=DAY).to_dict()
    year=_year(raw)
    previous=deepcopy(raw);previous['period_end']='2024-12-31'
    previous['facts']['revenue']['value']=D(800)
    previous['facts']['net_income']['value']=D(50)
    metrics=screen_metrics(year,[previous],None,today=DAY)
    assert metrics['return_on_assets'].value==D('.1')
    assert metrics['revenue_growth'].value==D('.25')
    assert metrics['net_income_growth'].value==1
    assert metrics['annualized_volatility'].status=='missing_inputs'
    previous['facts']['net_income']['value']=D(-50)
    assert screen_metrics(year,[previous],None,today=DAY)['net_income_growth'].status=='nonpositive_baseline'
    previous['period_end']='2023-12-31'
    assert screen_metrics(year,[previous],None,today=DAY)['revenue_growth'].status=='unaligned_periods'
    assert screen_metrics(year,[],None,today=date(2028,1,1))['operating_margin'].status=='stale'


def test_thresholds_are_exact_fail_closed_and_never_enable_scores(tmp_path):
    public,history=screen_store(tmp_path)
    screen=stock_screen(public,history,mode='local_research',today=DAY)
    row=screen.rows[0]
    row.metrics['return_on_assets']=Metric(value=D('.1'),status='available',basis='fixture')
    assert filter_screen(screen,ScreenFilters(minimum_roa='.1')).included_issuer_keys==[row.issuer_key]
    failed=filter_screen(screen,ScreenFilters(minimum_roa='.10001'))
    assert not failed.included_issuer_keys and 'minimum_roa' in failed.exclusions[0].reasons[0]
    row.metrics['return_on_assets'].status='stale'
    assert not filter_screen(screen,ScreenFilters(minimum_roa='-.1')).included_issuer_keys
    assert filter_screen(screen,ScreenFilters()).included_issuer_keys
    assert row.score is None and not row.selected and not failed.live_recommendations_enabled


def test_drawdown_loss_sign_and_explicit_estimate_consent(tmp_path):
    public,history=screen_store(tmp_path)
    screen=stock_screen(public,history,mode='local_research',today=DAY)
    screen.rows[0].metrics['maximum_drawdown']=Metric(value=D('-.25'),status='available',basis='fixture')
    assert filter_screen(screen,ScreenFilters(maximum_drawdown_loss='.25')).included_issuer_keys
    assert not filter_screen(screen,ScreenFilters(maximum_drawdown_loss='.249')).included_issuer_keys
    with pytest.raises(ValidationError):ScreenFilters(minimum_estimated_earnings_yield='.01')
    with pytest.raises(ValidationError):ScreenFilters(minimum_roa='NaN')
    with pytest.raises(ValidationError):ScreenFilters(sectors=['Unknown'])
    assert filter_screen(screen,ScreenFilters(allow_valuation_estimates=True,minimum_estimated_earnings_yield=-1)).included_issuer_keys


def test_coverage_retains_unresolved_and_unanalysed_securities(tmp_path):
    public,history=screen_store(tmp_path)
    screen=stock_screen(public,history,mode='local_research',today=DAY)
    assert len(screen.security_coverage)==2
    unknown=next(row for row in screen.security_coverage if row.symbol=='UNKNOWN')
    assert unknown.mapping_status=='unresolved' and unknown.cik is None
    assert not unknown.financials_installed and not unknown.exact_symbol_history_installed
    assert not any(row.official_membership_verified or row.current_valuation_verified for row in screen.security_coverage)
