"""Typed local-research history and deterministic, gap-aware risk calculations."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from functools import lru_cache
import hashlib
from math import sqrt
from pathlib import Path
import statistics
from typing import Literal

import exchange_calendars as xc
from pydantic import Field, model_validator

from data_pipeline import Contract
from public_data_store import atomic_json, canonical_bytes, file_lock, read_verified, strict_json


@lru_cache(maxsize=16)
def calendar_for(start,end):
    return xc.get_calendar("XNYS",start=(start-timedelta(days=7)).isoformat(),end=(end+timedelta(days=7)).isoformat())


def session_dates(start,end):
    return [stamp.date() for stamp in calendar_for(start,end).sessions_in_range(start.isoformat(),end.isoformat())]


class HistoryBar(Contract):
    day: date
    raw_close: Decimal = Field(ge=Decimal("1e-8"),le=Decimal("1e9"))
    adjusted_close: Decimal = Field(ge=Decimal("1e-8"),le=Decimal("1e9"))
    split_adjusted_close: Decimal | None = Field(default=None,ge=Decimal("1e-8"),le=Decimal("1e9"))


class HistorySeries(Contract):
    symbol: str = Field(pattern=r"^[A-Z][A-Z0-9.-]{0,14}$")
    cik: int | None = Field(default=None,gt=0,strict=True)
    role: Literal["issuer_security","benchmark_proxy"]
    bars: list[HistoryBar] = Field(min_length=1,max_length=3000)
    source_retrieved_at: datetime | None = None

    @model_validator(mode="after")
    def ordered(self):
        days=[bar.day for bar in self.bars]
        if days!=sorted(set(days)):raise ValueError("History dates must be unique and ordered")
        if self.role=="issuer_security" and self.cik is None:raise ValueError("Issuer CIK required")
        if self.source_retrieved_at is not None and self.source_retrieved_at.tzinfo is None:raise ValueError("Series retrieval clock requires timezone")
        return self


class HistoryBundle(Contract):
    schema_version: Literal["local-market-history-v1"] = "local-market-history-v1"
    provider: Literal["Alpaca"] = "Alpaca"
    feed: Literal["iex"] = "iex"
    adjustment: Literal["raw_and_all","raw_all_and_split"] = "raw_and_all"
    usage: Literal["local_research_only"] = "local_research_only"
    start: date
    completed_through: date
    retrieved_at: datetime
    directory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    calendar_version: str
    benchmark: Literal["SPY"] = "SPY"
    series: dict[str,HistorySeries]
    security_identity_verified: Literal[False] = False
    exact_total_return_verified: Literal[False] = False
    public_redistribution_allowed: Literal[False] = False

    @model_validator(mode="after")
    def coherent(self):
        if self.retrieved_at.tzinfo is None or self.start>self.completed_through or (self.completed_through-self.start).days>3660:
            raise ValueError("Invalid history interval/clock")
        if not 1<=len(self.series)<=100 or self.benchmark not in self.series:
            raise ValueError("Bounded history requires its benchmark proxy")
        sessions=set(session_dates(self.start,self.completed_through))
        if not sessions or calendar_for(self.start,self.completed_through).session_close(self.completed_through.isoformat()).to_pydatetime()+timedelta(hours=1)>self.retrieved_at:
            raise ValueError("History must end after a completed session plus finalization buffer")
        for symbol,series in self.series.items():
            if series.source_retrieved_at is not None and series.source_retrieved_at>self.retrieved_at:raise ValueError('Series clock exceeds bundle clock')
            if symbol!=series.symbol or any(bar.day not in sessions for bar in series.bars):
                raise ValueError("History identity or session mismatch")
            if (symbol==self.benchmark)!=(series.role=="benchmark_proxy"):
                raise ValueError("Benchmark role mismatch")
            if self.adjustment=="raw_all_and_split" and any(bar.split_adjusted_close is None for bar in series.bars):
                raise ValueError("Split adjustment evidence missing")
        return self


def publish_history(root,bundle,*,expected_previous='unchecked'):
    bundle=HistoryBundle.model_validate(bundle.model_dump())
    root=Path(root)
    payload=bundle.model_dump(mode="json")
    encoded=canonical_bytes(payload)
    if len(encoded)>64*1024*1024:raise ValueError('History artifact exceeds 64 MiB')
    digest=hashlib.sha256(encoded).hexdigest()
    with file_lock(root/"writer.lock"):
        if expected_previous!='unchecked':
            try:current,_=load_history(root)
            except FileNotFoundError:current=None
            if current!=expected_previous:raise ValueError('History changed during merge; retry from the current snapshot')
        atomic_json(root/"artifacts"/(digest+".json"),payload)
        atomic_json(root/"CURRENT.json",{"sha256":digest})
    return digest


def load_history(root):
    root=Path(root)
    with (root/"CURRENT.json").open("rb") as stream:payload=stream.read(1025)
    if len(payload)>1024:raise ValueError("Invalid history pointer")
    pointer=strict_json(payload)
    digest=pointer["sha256"]
    # read_verified validates a checksum but also validate before constructing a path.
    import re
    if not isinstance(digest,str) or not re.fullmatch(r"[0-9a-f]{64}",digest):raise ValueError("Invalid history pointer")
    return digest,HistoryBundle.model_validate(read_verified(root/"artifacts"/(digest+".json"),digest,maximum_bytes=64*1024*1024))


class SeriesRisk(Contract):
    first: date
    last: date
    observations: int
    return_observations: int
    missing_sessions: list[date]
    cumulative_change: float
    annualized_change: float | None
    maximum_drawdown: float
    annualized_volatility: float | None
    minimum_history_gate_passed: bool


def series_risk(series):
    """All-adjusted provider close changes; never add dividends a second time."""
    series=HistorySeries.model_validate(series.model_dump())
    bars=series.bars
    if len(bars)<2:raise ValueError("At least two observations required")
    days={bar.day for bar in bars}
    missing=[day for day in session_dates(bars[0].day,bars[-1].day) if day not in days]
    values=[bar.adjusted_close for bar in bars]
    returns=[float(b/a-1) for a,b in zip(values,values[1:])]
    peak=values[0]; drawdown=Decimal(0)
    for value in values:
        peak=max(peak,value);drawdown=min(drawdown,value/peak-1)
    elapsed=(bars[-1].day-bars[0].day).days
    growth=float(values[-1]/values[0])
    return SeriesRisk(first=bars[0].day,last=bars[-1].day,observations=len(bars),return_observations=len(returns),
        missing_sessions=missing,cumulative_change=growth-1,annualized_change=growth**(365.25/elapsed)-1 if elapsed>=365 else None,
        maximum_drawdown=float(drawdown),annualized_volatility=statistics.stdev(returns)*sqrt(252)
        if not missing and len(returns)>=2 else None,
        minimum_history_gate_passed=not missing and len(returns)>=756)


class ComparisonPoint(Contract):
    day: date
    company_adjusted_close: Decimal
    benchmark_adjusted_close: Decimal
    company_split_adjusted_close: Decimal | None = None
    benchmark_split_adjusted_close: Decimal | None = None
    company_raw_close: Decimal | None = None
    benchmark_raw_close: Decimal | None = None
    company_index: float
    benchmark_index: float
    company_drawdown: float
    benchmark_drawdown: float


class HistoryComparison(Contract):
    company: SeriesRisk
    benchmark: SeriesRisk
    points: list[ComparisonPoint]
    excluded_company_dates: int
    excluded_benchmark_dates: int
    endpoint_difference: float
    basis: str = "Alpaca all-adjusted IEX close changes; SPY ETF proxy, not the S&P 500 index. Exact reinvested total return is not verified."
    strategy_performance_evidence: Literal[False] = False


def compare_history(company,benchmark,*,start=None,end=None):
    if company.symbol==benchmark.symbol:raise ValueError("Choose a company distinct from benchmark")
    left={bar.day:bar for bar in company.bars if (start is None or bar.day>=start) and (end is None or bar.day<=end)}
    right={bar.day:bar for bar in benchmark.bars if (start is None or bar.day>=start) and (end is None or bar.day<=end)}
    common=sorted(set(left)&set(right))
    if len(common)<2:raise ValueError("Two shared dates required; missing dates are never filled")
    # Both statistics and curves use exactly the same dates, including the first and last.
    a=company.model_copy(update={"bars":[left[day] for day in common]})
    b=benchmark.model_copy(update={"bars":[right[day] for day in common]})
    sa,sb=series_risk(a),series_risk(b)
    a0,b0=a.bars[0].adjusted_close,b.bars[0].adjusted_close
    pa=pb=Decimal(100); points=[]
    for aa,bb in zip(a.bars,b.bars):
        av,bv=100*aa.adjusted_close/a0,100*bb.adjusted_close/b0
        pa,pb=max(pa,av),max(pb,bv)
        points.append(ComparisonPoint(day=aa.day,company_adjusted_close=aa.adjusted_close,benchmark_adjusted_close=bb.adjusted_close,company_split_adjusted_close=aa.split_adjusted_close,benchmark_split_adjusted_close=bb.split_adjusted_close,company_raw_close=aa.raw_close,benchmark_raw_close=bb.raw_close,company_index=float(av),benchmark_index=float(bv),
                      company_drawdown=float(av/pa-1),benchmark_drawdown=float(bv/pb-1)))
    return HistoryComparison(company=sa,benchmark=sb,points=points,
        excluded_company_dates=len(left)-len(common),excluded_benchmark_dates=len(right)-len(common),
        endpoint_difference=sa.cumulative_change-sb.cumulative_change)
