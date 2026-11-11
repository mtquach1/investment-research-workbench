"""Read-only local market research, withheld unless explicitly configured."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import Field

from company_research import company_directory
from data_pipeline import Contract
from market_history import HistoryComparison, compare_history, load_history, session_dates


class CompanyMarket(Contract):
    status: Literal["available","unavailable","withheld","choose_security","integrity_error"]
    issuer_key: str
    symbols: list[str] = Field(default_factory=list)
    selected_symbol: str | None = None
    price_date: date | None = None
    raw_close: Decimal | None = None
    feed: Literal["iex"] = "iex"
    price_age_days: int | None = None
    retrieved_at: datetime | None = None
    snapshot_sha256: str | None = None
    missing_requested_sessions: int | None = None
    comparison: HistoryComparison | None = None
    issues: list[str] = Field(default_factory=list)
    live_recommendations_enabled: Literal[False] = False
    public_redistribution_allowed: Literal[False] = False
    notice: str = "Personal local research only. IEX is one exchange; SPY is an ETF proxy. Provider-adjusted history is not verified exact reinvested total return or evidence that our strategy beat the S&P 500."


def company_market(public_root,history_root,issuer_key,*,mode="withheld",symbol=None,start=None,end=None,today=None):
    base=dict(issuer_key=issuer_key)
    if mode!="local_research":return CompanyMarket(status="withheld",**base)
    today=today or datetime.now(timezone.utc).date()
    try:
        directory=company_directory(public_root,today=today)
        if directory.status=="integrity_error":return CompanyMarket(status="integrity_error",**base)
        entry=next((row for row in directory.entries if row.issuer_key==issuer_key),None)
        if entry is None:return CompanyMarket(status="unavailable",**base)
        digest,bundle=load_history(history_root)
        if bundle.completed_through>today:raise ValueError("Future history snapshot")
        matching=sorted(key for key,row in bundle.series.items() if row.role=="issuer_security" and row.cik==entry.cik)
        if not matching:return CompanyMarket(status="unavailable",**base)
        selected=symbol or (matching[0] if len(matching)==1 else None)
        if selected not in matching:return CompanyMarket(status="choose_security",symbols=matching,**base)
        series=bundle.series[selected]
        benchmark=bundle.series[bundle.benchmark]
        comparison=compare_history(series,benchmark,start=start,end=end)
        latest=series.bars[-1]
        missing=len(set(session_dates(bundle.start,bundle.completed_through))-{bar.day for bar in series.bars})
        issues=[]
        if (today-latest.day).days>7:issues.append("The latest cached price is more than seven calendar days old.")
        if missing:issues.append(f"{missing} requested trading sessions have no bar; no missing prices were filled.")
        if comparison.company.missing_sessions:issues.append("Daily volatility is withheld because the matched window has missing sessions.")
        if not comparison.company.minimum_history_gate_passed:issues.append("The inspected window does not satisfy the complete 756-return-observation requirement.")
        return CompanyMarket(status="available",symbols=matching,selected_symbol=selected,price_date=latest.day,
            raw_close=latest.raw_close,price_age_days=(today-latest.day).days,retrieved_at=series.source_retrieved_at or bundle.retrieved_at,
            snapshot_sha256=digest,missing_requested_sessions=missing,comparison=comparison,issues=issues,**base)
    except FileNotFoundError:
        return CompanyMarket(status="unavailable",**base)
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError):
        return CompanyMarket(status="integrity_error",**base)
