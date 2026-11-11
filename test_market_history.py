"""Independent arithmetic, calendar gaps and local-only history transactions."""

from datetime import date, timedelta
from decimal import Decimal
import math

import pytest

from market_history import (HistoryBar,HistorySeries,HistoryBundle,series_risk,compare_history,
                            load_history,publish_history,calendar_for)
from company_market import company_market
from test_company_research import research_store, DAY, NOW


def series(values,symbol="AAPL",days=None):
    days=days or [date(2026,10,26)+timedelta(days=index) for index in range(len(values))]
    return HistorySeries(symbol=symbol,cik=None if symbol=="SPY" else 320193,
        role="benchmark_proxy" if symbol=="SPY" else "issuer_security",
        bars=[HistoryBar(day=day,raw_close=Decimal(str(value)),adjusted_close=Decimal(str(value))) for day,value in zip(days,values)])


def bundle():
    return HistoryBundle(start=date(2026,10,26),completed_through=DAY,retrieved_at=NOW,
        directory_sha256="a"*64,calendar_version="fixture",series={"AAPL":series([100,120,90]),"SPY":series([100,101,102],"SPY")})


def test_risk_math_uses_sample_variance_peak_drawdown_and_endpoint_change():
    result=series_risk(series([100,120,90,108]))
    assert result.cumulative_change==pytest.approx(.08)
    assert result.maximum_drawdown==pytest.approx(-.25)
    # Returns .20, -.25, .20 have sample variance .0675.
    assert result.annualized_volatility==pytest.approx(math.sqrt(.0675*252))
    assert result.return_observations==3 and not result.minimum_history_gate_passed
    assert result.annualized_change is None


def test_comparison_aligns_exact_dates_without_forward_fill():
    days=[date(2026,10,26),date(2026,10,28),date(2026,10,29)]
    left=series([100,90,108],days=days)
    right=series([100,101,102,103],"SPY")
    result=compare_history(left,right)
    assert result.excluded_company_dates==0 and result.excluded_benchmark_dates==1
    assert [point.day for point in result.points]==days
    assert result.company.missing_sessions==[date(2026,10,27)]
    assert result.company.annualized_volatility is None
    assert result.benchmark.annualized_volatility is None
    assert result.endpoint_difference==pytest.approx(.05)
    assert not result.strategy_performance_evidence
    assert result.points[0].company_index==result.points[0].benchmark_index==100


def test_holidays_early_close_and_split_adjustment_basis():
    calendar=calendar_for(date(2026,11,23),date(2026,11,30))
    assert not calendar.is_session("2026-11-26")
    assert calendar.session_close("2026-11-27").hour==18
    data=series([50,50,51])
    data.bars[0].raw_close=Decimal(100)
    assert series_risk(data).cumulative_change==pytest.approx(.02)
    assert series_risk(data).maximum_drawdown==0


def test_bad_series_and_incomplete_sessions_cannot_pass_history_gate():
    with pytest.raises(ValueError):series([0,1])
    with pytest.raises(ValueError):HistoryBar(day=DAY,raw_close=True,adjusted_close=1)
    with pytest.raises(ValueError):series([100,101],days=[DAY,DAY])
    with pytest.raises(ValueError):series_risk(series([100]))
    candidate=bundle().model_dump();candidate["completed_through"]=date(2026,10,29)
    with pytest.raises(ValueError):HistoryBundle.model_validate(candidate)


def test_local_snapshot_integrity_and_display_gate(tmp_path,monkeypatch):
    public=research_store(tmp_path);root=tmp_path/"history"
    digest=publish_history(root,bundle())
    assert load_history(root)[0]==digest
    result=company_market(public,root,"aapl",mode="local_research",today=DAY)
    assert result.status=="available" and result.raw_close==90 and result.price_date==DAY
    assert not result.live_recommendations_enabled and not result.public_redistribution_allowed
    def forbidden(*a,**k):raise AssertionError("Withheld data must not be loaded")
    monkeypatch.setattr("company_market.load_history",forbidden)
    assert company_market(public,root,"aapl",mode="withheld",today=DAY).status=="withheld"
    monkeypatch.undo()
    (root/"artifacts"/(digest+".json")).write_bytes(b"{}")
    assert company_market(public,root,"aapl",mode="local_research",today=DAY).status=="integrity_error"
    (root/"CURRENT.json").write_text('{"sha256":"../../private"}',encoding="utf-8")
    with pytest.raises(ValueError):load_history(root)
