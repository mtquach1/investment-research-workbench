from collections import Counter
from decimal import Decimal as D
import pytest
from stock_screen import stock_screen
from stock_metrics import Metric
from stock_portfolio import stock_proposal,ProposalRequest
from experimental_basket import ExperimentalRequest,experimental_basket
from test_stock_screen import screen_store
from test_company_research import DAY


def research_universe(tmp_path):
    public,history=screen_store(tmp_path)
    screen=stock_screen(public,history,mode='local_research',today=DAY)
    template=screen.rows[0];rows=[]
    for sector_index,sector in enumerate(['Information Technology','Consumer Staples','Health Care','Industrials']):
        for rank in range(5):
            index=sector_index*5+rank
            row=template.model_copy(deep=True,update={'issuer_key':f'cik{index+1000:010d}','cik':index+1000,
                'company':f'Fictional test company {index}','tickers':[f'T{index:02d}'],'sector':sector,
                'financial_status':'pass','financial_reasons':[],'sector_status':'pass','price_status':'pass',
                'history_count_status':'pass','proxy_member':True})
            row.metrics={key:Metric(value=D('.1')+D(rank)/100,status='available',basis='Independent synthetic test inputs') for key in ('return_on_assets','operating_margin','free_cashflow_margin')}
            row.metrics['annualized_volatility']=Metric(value=D('.25'),status='available',basis='Synthetic')
            row.valuation.annual_earnings_yield_estimate=D('.05')+D(rank)/100
            row.valuation.annual_fcf_yield_estimate=D('.05')+D(rank)/100
            rows.append(row)
    screen.rows=rows
    return screen


def test_opt_in_deterministic_ranks_sector_caps_and_cent_accounting(tmp_path):
    screen=research_universe(tmp_path)
    assert experimental_basket(screen,ExperimentalRequest()).status=='acknowledgement_required'
    request=ExperimentalRequest(acknowledge_proxy_and_estimates=True,budget_cents=100003)
    result=experimental_basket(screen,request)
    assert result.status=='research_basket' and len(result.selected)==10
    assert len({row.issuer_key for row in result.selected})==10
    assert max(Counter(row.sector for row in result.selected).values())<=3
    assert sum(row.purchase_cents for row in result.selected)+result.cash_unallocated_cents==100003
    assert result.cash_unallocated_cents==3 and sum(row.weight for row in result.selected)==1
    # Identical monotonic features independently imply percentiles 0,.25,.5,.75,1.
    assert sorted(row.score for row in result.findings)==sorted([0,.25,.5,.75,1]*4)
    assert sorted(row.score for row in result.selected)==[.5,.5,.75,.75,.75,.75,1,1,1,1]
    assert not result.live_recommendations_enabled and not result.verified_current_valuations
    screen.rows.reverse()
    assert [r.symbol for r in experimental_basket(screen,request).selected]==[r.symbol for r in result.selected]
    assert not stock_proposal(screen,ProposalRequest()).selected


def test_no_relaxation_for_sector_peer_risk_or_budget_failures(tmp_path):
    screen=research_universe(tmp_path)
    common=dict(acknowledge_proxy_and_estimates=True)
    assert experimental_basket(screen,ExperimentalRequest(**common,maximum_stocks_per_sector=2)).status=='infeasible'
    assert experimental_basket(screen,ExperimentalRequest(**common,excluded_symbols=['T00'])).status=='infeasible'
    assert experimental_basket(screen,ExperimentalRequest(**common,maximum_volatility='.1')).status=='infeasible'
    assert experimental_basket(screen,ExperimentalRequest(**common,budget_cents=9)).status=='infeasible'
    screen.universe.fresh=False
    assert experimental_basket(screen,ExperimentalRequest(**common)).status=='unavailable'


def test_missing_feature_and_duplicate_issuer_cannot_receive_a_score(tmp_path):
    screen=research_universe(tmp_path)
    screen.rows[0].metrics['return_on_assets'].status='missing_inputs'
    screen.rows[6].cik=screen.rows[5].cik
    result=experimental_basket(screen,ExperimentalRequest(acknowledge_proxy_and_estimates=True))
    assert result.status=='infeasible'
    assert all(row.score is None for row in result.findings if row.issuer_key in {screen.rows[i].issuer_key for i in (0,5,6)})
    assert not result.selected and result.cash_unallocated_cents==result.inputs.budget_cents


def test_invalid_request_cannot_certify_inputs():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):ExperimentalRequest(verified_membership=True)
    with pytest.raises(ValidationError):ExperimentalRequest(maximum_volatility='NaN')
    with pytest.raises(ValidationError):ExperimentalRequest(excluded_symbols=['../AAPL'])


def test_observed_filing_class_conflict_excludes_research_selection(tmp_path):
    from security_identity import FilingClassEvidence
    screen=research_universe(tmp_path)
    row=screen.rows[-1]
    row.filing_class_evidence[row.tickers[0]]=FilingClassEvidence(status='conflict',symbol=row.tickers[0])
    result=experimental_basket(screen,ExperimentalRequest(acknowledge_proxy_and_estimates=True))
    finding=next(item for item in result.findings if item.issuer_key==row.issuer_key)
    assert finding.score is None and any('Filing-class' in reason for reason in finding.reasons)
