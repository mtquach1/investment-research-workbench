from datetime import date
from decimal import Decimal as D
import pytest
from market_history import compare_history,session_dates
from test_market_history import series
from stock_replay import ReplayRequest,calculate_replay,replay_stock
from stock_portfolio import ProposalRequest,stock_proposal
from stock_screen import stock_screen
from test_stock_screen import screen_store


def split_points():
    a=series([100,100,110]);b=series([100,100,100],'SPY')
    for index,bar in enumerate(a.bars):
        bar.split_adjusted_close=bar.adjusted_close
        bar.raw_close=[D(1000),D(100),D(110)][index]
    for bar in b.bars:bar.split_adjusted_close=bar.adjusted_close
    return compare_history(a,b).points


def test_ten_for_one_split_is_not_a_ninety_percent_loss():
    points=split_points()
    request=ReplayRequest(issuer_key='aapl',start=points[0].day,end=points[-1].day,initial_cents=100000,monthly_cents=0)
    rows=calculate_replay(request,points)
    assert rows[0].company_value==1000 and rows[1].company_value==1000
    assert rows[-1].company_value==1100 and rows[-1].benchmark_value==1000
    from history_chart import comparison_chart
    spec=comparison_chart(points,share_price=True).to_dict()
    values=next(rows for rows in spec['datasets'].values() if rows and 'Primary' in rows[0])
    assert [row['Primary'] for row in values]==[100,100,110]


def test_monthly_cash_rolls_to_shared_trading_close_and_is_not_profit():
    days=session_dates(date(2026,1,30),date(2026,3,2))
    a=series([100 if day.month!=2 else 200 for day in days],days=days)
    b=series([100]*len(days),'SPY',days=days)
    for item in (a,b):
        for bar in item.bars:bar.split_adjusted_close=bar.adjusted_close
    request=ReplayRequest(issuer_key='aapl',start=days[0],end=days[-1],initial_cents=10000,monthly_cents=10000)
    rows=calculate_replay(request,compare_history(a,b).points)
    assert [(r.day,r.deposit_cents) for r in rows if r.deposit_cents]==[(date(2026,1,30),10000),(date(2026,2,2),10000),(date(2026,3,2),10000)]
    assert rows[-1].company_value==250 and rows[-1].benchmark_value==300
    assert rows[-1].cumulative_deposits_cents==30000
    charged=calculate_replay(request.model_copy(update={'purchase_fee_rate':D('.01')}),compare_history(a,b).points)
    assert charged[-1].company_value==D('247.50') and charged[-1].benchmark_value==297
    assert charged[-1].company_fees==3


def test_missing_split_or_trading_date_never_falls_back_to_raw():
    points=split_points();r=ReplayRequest(issuer_key='aapl',start=points[0].day,end=points[-1].day)
    with pytest.raises(ValueError):calculate_replay(r,points[1:])
    points[0].company_split_adjusted_close=None
    with pytest.raises(ValueError):calculate_replay(r,points)
    assert calculate_replay(r.model_copy(update={'basis':'provider_all_adjusted_proxy'}),points)


def test_account_fees_reduce_both_balances_and_are_separate_from_deposits():
    points=split_points();r=ReplayRequest(issuer_key='aapl',start=points[0].day,end=points[-1].day,initial_cents=100000,monthly_cents=0,annual_account_fee_rate='.1')
    rows=calculate_replay(r,points)
    assert rows[-1].company_value<1100 and rows[-1].benchmark_value<1000
    assert rows[-1].company_fees>0 and rows[-1].cumulative_deposits_cents==100000


def test_server_replay_and_proposal_keep_source_gates(tmp_path):
    public,history=screen_store(tmp_path)
    r=ReplayRequest(issuer_key='aapl',start=date(2026,10,26),end=date(2026,10,28),initial_cents=10000,monthly_cents=0)
    result=replay_stock(public,history,r,mode='local_research',today=date(2026,10,29))
    assert result.status=='available' and result.snapshot_sha256 and not result.strategy_performance_evidence
    assert replay_stock(public,history,r).status=='withheld'
    assert replay_stock(public,history,r.model_copy(update={'end':date(2027,1,1)}),mode='local_research').status=='unavailable'
    screen=stock_screen(public,history,mode='local_research',today=date(2026,10,29))
    proposal=stock_proposal(screen,ProposalRequest(budget_cents=100000))
    assert not proposal.selected and proposal.cash_unallocated_cents==100000
    assert proposal.findings and proposal.global_blockers and not proposal.live_recommendations_enabled
    from pydantic import ValidationError
    with pytest.raises(ValidationError):ProposalRequest(budget_cents=1000,membership_verified=True)
