from datetime import date,datetime,timezone,timedelta
from decimal import Decimal as D
from copy import deepcopy
from collections import Counter
import pytest
from pydantic import ValidationError
from test_experimental_basket import research_universe
from experimental_basket import ExperimentalRequest,experimental_basket
from financial_validation import reconcile_company,validate_installed_financials
from stock_decision_review import basket_alternatives,basket_sensitivity,ExistingHolding,HoldingsReviewRequest,review_holdings
from paper_portfolio import freeze_paper_basket,track_paper_record,PaperRecord
from market_history import HistorySeries,HistoryBar


def test_independent_hand_calculated_ratios_detect_corruption_and_missing(tmp_path):
    screen=research_universe(tmp_path);row=screen.rows[0]
    # Separately hand-computed examples: NI=20, average assets=200; OI=30,
    # revenue=100; FCF=40-15=25; liabilities=90 / ending assets=300.
    values={'net_income':20,'assets_start':100,'assets_end':300,'operating_income':30,
        'revenue':100,'operating_cashflow':40,'capital_expenditures':15,'liabilities_end':90}
    raw={'facts':{key:{'value':value} for key,value in values.items()}}
    for key,value in [('return_on_assets','.1'),('operating_margin','.3'),('free_cashflow_margin','.25'),('liabilities_to_assets','.3')]:
        from stock_metrics import Metric
        row.metrics[key]=Metric(value=D(value),status='available',basis='Golden arithmetic')
    checks={item.metric:item for item in reconcile_company(row,raw)}
    assert all(checks[key].status=='pass' for key in ('return_on_assets','operating_margin','free_cashflow_margin','liabilities_to_assets'))
    row.metrics['return_on_assets'].value=D('.2')
    assert reconcile_company(row,raw)[0].status=='mismatch'
    del raw['facts']['assets_start']
    assert reconcile_company(row,raw)[0].status=='unavailable'
    raw['facts']['capital_expenditures']['value']=-15
    assert next(c for c in reconcile_company(row,raw) if c.metric=='free_cashflow_margin').status=='unavailable'


def test_validation_mode_does_not_read_private_market_store(tmp_path):
    assert validate_installed_financials(tmp_path/'absent',tmp_path/'absent').status=='withheld'


def test_independent_component_sum_catches_a_wrong_derived_liability_total(tmp_path):
    row=research_universe(tmp_path).rows[0]
    raw={'facts':{'current_liabilities_end':{'value':30},'noncurrent_liabilities_end':{'value':25},
        'liabilities_end':{'value':60,'tag':'derived:current_plus_noncurrent_liabilities'}}}
    check=next(item for item in reconcile_company(row,raw) if item.metric=='liabilities_component_sum')
    assert check.status=='mismatch' and check.expected==55 and check.actual==60


def test_official_reference_checks_require_period_identity_and_million_units():
    from financial_validation import reconcile_reference_cases
    references={'reviewed_on':'2026-10-29','cases':[{'issuer_key':'example','cik':123,'period_end':'2025-12-31',
        'values_millions':{'revenue':100,'net_income':20},'source_url':'https://example.test/annual','location':'Income statement'}]}
    raw={'cik':123,'period_end':'2025-12-31','facts':{'revenue':{'value':100000000},'net_income':{'value':20000000}}}
    assert all(row.status=='pass' for row in reconcile_reference_cases({'example':raw},references))
    raw['facts']['revenue']['value']=100
    assert reconcile_reference_cases({'example':raw},references)[0].status=='mismatch'
    raw['period_end']='2024-12-31'
    assert all(row.status=='unavailable' for row in reconcile_reference_cases({'example':raw},references))


def test_alternatives_respect_sector_constraints_and_sensitivity_preserves_inputs(tmp_path):
    screen=research_universe(tmp_path);result=experimental_basket(screen,ExperimentalRequest(acknowledge_proxy_and_estimates=True))
    choices={row.symbol:row for row in result.findings};counts=Counter(row.sector for row in result.selected)
    for alternative in basket_alternatives(result):
        if alternative['Alternative']=='None covered':continue
        removed=choices[alternative['Selected']];added=choices[alternative['Alternative']]
        assert not added.selected and counts[added.sector]-(removed.sector==added.sector)<3
        assert alternative['Score gap']>=-1e-10
    original=screen.model_dump_json();baseline=result.model_dump_json()
    scenarios=basket_sensitivity(screen,result,shock=D('.5'))
    assert len(scenarios)==40 and any(row['Changed positions'] for row in scenarios)
    assert all(0<=row['Changed positions']<=10 and row['Status']=='research_basket' for row in scenarios)
    assert screen.model_dump_json()==original and result.model_dump_json()==baseline


def test_existing_holdings_add_cash_without_implicit_etf_lookthrough(tmp_path):
    result=experimental_basket(research_universe(tmp_path),ExperimentalRequest(acknowledge_proxy_and_estimates=True,budget_cents=100003))
    symbol=result.selected[0].symbol
    review=review_holdings(result,HoldingsReviewRequest(holdings=[ExistingHolding(symbol=symbol,amount_cents=900000),ExistingHolding(symbol='VOO',amount_cents=100000)]))
    assert review['combined_cents']==1100003 and review['cash_cents']==3
    row=next(row for row in review['rows'] if row['Symbol']==symbol)
    assert row['Already held'] and row['Paper addition ($)']==100 and review['largest_direct_weight']>80
    assert 'unresolved' in review['notice']
    with pytest.raises(ValidationError):HoldingsReviewRequest(holdings=[ExistingHolding(symbol='VOO',amount_cents=1)]*2)


def paper_fixture(tmp_path):
    from test_market_history import bundle
    screen=research_universe(tmp_path);result=experimental_basket(screen,ExperimentalRequest(acknowledge_proxy_and_estimates=True,budget_cents=100000))
    now=datetime.combine(result.checked_on,datetime.min.time(),tzinfo=timezone.utc)+timedelta(hours=19)
    ciks={row.symbol:next(item.cik for item in screen.rows if item.issuer_key==row.issuer_key) for row in result.selected}
    record=freeze_paper_basket(result,now=now,security_ciks=ciks,entry_cost_bps=100)
    first=record.earliest_entry_date
    from market_history import session_dates
    days=session_dates(first,first+timedelta(days=6))[:3]
    history=bundle();history.start=first;history.completed_through=days[-1];history.series={}
    for symbol,cik in {**ciks,'SPY':None}.items():
        prices=[D(100),D(110),D(90)] if symbol!='SPY' else [D(100)]*3
        history.series[symbol]=HistorySeries(symbol=symbol,cik=cik,role='benchmark_proxy' if symbol=='SPY' else 'issuer_security',bars=[HistoryBar(day=day,raw_close=price,adjusted_close=price,split_adjusted_close=price) for day,price in zip(days,prices)])
    return record,history


def test_prospective_tracking_timing_fees_losses_and_reproducibility(tmp_path):
    record,bundle=paper_fixture(tmp_path)
    assert record.earliest_entry_date>record.created_at.date()
    waiting=bundle.model_copy(deep=True);waiting.completed_through=record.earliest_entry_date-timedelta(days=1)
    assert track_paper_record(record,waiting,today=bundle.completed_through)['status']=='pending'
    result=track_paper_record(record,bundle,today=bundle.completed_through)
    assert result['status']=='available' and D(result['entry_cost'])==10
    assert D(result['points'][0]['basket_net'])==990
    assert D(result['points'][-1]['basket_net'])==891
    assert D(result['basket_gain'])==-109 and D(result['benchmark_gain'])==-10
    assert D(result['difference_dollars'])==-99
    assert result==track_paper_record(PaperRecord.model_validate_json(record.model_dump_json()),bundle,today=bundle.completed_through)
    assert not result['historical_strategy_performance_verified']


def test_tracking_rejects_missing_dates_wrong_issuer_and_mutated_record(tmp_path):
    record,bundle=paper_fixture(tmp_path)
    symbol=record.basket.selected[0].symbol
    original=bundle.model_copy(deep=True)
    bundle.series[symbol].bars.pop(1)
    assert track_paper_record(record,bundle,today=bundle.completed_through)['status']=='unavailable'
    original.series[symbol].cik+=1
    assert track_paper_record(record,original,today=bundle.completed_through)['status']=='unavailable'
    data=record.model_dump();data['entry_cost_bps']=0
    with pytest.raises(ValidationError,match='checksum'):PaperRecord.model_validate(data)
    with pytest.raises(ValueError):freeze_paper_basket(record.basket,now=record.created_at.replace(tzinfo=None),security_ciks=record.security_ciks)


def test_restore_is_bounded_deduplicated_and_never_accepts_future_clock(tmp_path):
    from paper_portfolio import restore_paper_record
    record,_=paper_fixture(tmp_path);payload=record.model_dump_json().encode()
    assert restore_paper_record(payload,now=record.created_at).fingerprint==record.fingerprint
    with pytest.raises(ValueError):restore_paper_record(payload,now=record.created_at,known_fingerprints=[record.fingerprint])
    with pytest.raises(ValueError):restore_paper_record(payload,now=record.created_at-timedelta(seconds=1))
    with pytest.raises(ValueError):restore_paper_record(b' '*524289,now=record.created_at)
    with pytest.raises(ValueError):restore_paper_record(b'{"version":"one","version":"two"}',now=record.created_at)
