"""Bounded second-source diagnostics. Never replaces primary prices or authorizes trades."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from typing import Literal
from data_pipeline import Contract
from market_history import load_history, session_dates, calendar_for
from public_data_store import atomic_json, strict_json


class PriceCheck(Contract):
    symbol: str = Field(pattern=r"^[A-Z][A-Z0-9.-]{0,14}$")
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    price_date: date
    checked_at: datetime
    provider: Literal["Yahoo Finance"] = "Yahoo Finance"
    status: Literal["within_tolerance", "discrepancy", "unavailable"]
    primary_close: Decimal = Field(gt=0,le=Decimal("1e9"))
    reference_close: Decimal | None = Field(default=None,gt=0,le=Decimal("1e9"))
    difference_percent: Decimal | None = None
    source_url: str
    full_history_verified: Literal[False] = False
    public_redistribution_allowed: Literal[False] = False

    @model_validator(mode="after")
    def coherent(self):
        if self.checked_at.tzinfo is None or self.price_date>self.checked_at.astimezone(ZoneInfo("America/New_York")).date():
            raise ValueError("Invalid check clock")
        if self.source_url!=f"https://finance.yahoo.com/quote/{self.symbol}/history/":
            raise ValueError("Unexpected evidence URL")
        if self.reference_close is None:
            if self.status!="unavailable" or self.difference_percent is not None:raise ValueError("Missing check evidence")
        else:
            difference=abs(self.primary_close-self.reference_close)
            expected="within_tolerance" if difference<=max(Decimal('.05'),self.reference_close*Decimal('.005')) else "discrepancy"
            if self.status!=expected or self.difference_percent!=100*difference/self.reference_close:
                raise ValueError("Check calculation mismatch")
        return self


def freshness_label(price_date,now):
    if now.tzinfo is None:raise ValueError("Timezone-aware clock required")
    today=now.astimezone(ZoneInfo("America/New_York")).date()
    if price_date>today:return "Price date is in the future; investigate this snapshot."
    start=today-timedelta(days=14)
    calendar=calendar_for(start,today)
    complete=[day for day in session_dates(start,today)
              if calendar.session_close(day.isoformat()).to_pydatetime()+timedelta(hours=1)<=now]
    if not complete:return f"Daily data through {price_date}; completed-session freshness unavailable."
    last=complete[-1]
    if price_date==last:return f"Through {price_date} · Latest completed trading session (one-hour finalization buffer)."
    if price_date>last:return f"Through {price_date} · Newer than the finalized-session cutoff; investigate."
    return f"Through {price_date} · Behind the latest finalized session ({last}); refresh needed."


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError("Redirect refused")


def fetch_reference(symbol,day,*,opener=None):
    """Experimental public endpoint, no credentials, one bounded request, no retries."""
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}",symbol):raise ValueError("Invalid symbol")
    request=Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=1d",
                    headers={"User-Agent":"InvestmentResearch/1.0"})
    opener=opener or build_opener(_NoRedirects())
    with opener.open(request,timeout=15) as response:
        if response.status!=200:raise ValueError("Reference unavailable")
        payload=response.read(512*1024+1)
    if len(payload)>512*1024:raise ValueError("Reference too large")
    result=strict_json(payload)["chart"]
    if result.get("error") is not None or len(result["result"])!=1:raise ValueError("Reference unavailable")
    result=result["result"][0];meta=result["meta"]
    if meta["symbol"]!=symbol or meta["currency"]!="USD" or meta["exchangeTimezoneName"]!="America/New_York":
        raise ValueError("Reference identity/currency mismatch")
    timestamps=result["timestamp"];quotes=result["indicators"]["quote"]
    if len(quotes)!=1:raise ValueError("Unexpected quote series")
    values=quotes[0]["close"]
    if not 1<=len(timestamps)<=40 or len(values)!=len(timestamps):raise ValueError("Unexpected daily history")
    matches=[];seen=set()
    for stamp,value in zip(timestamps,values):
        if type(stamp) is not int:raise ValueError("Invalid date")
        observed=datetime.fromtimestamp(stamp,ZoneInfo("America/New_York")).date()
        if observed in seen:raise ValueError("Duplicate reference date")
        seen.add(observed)
        if observed==day:
            if isinstance(value,bool) or value is None:raise ValueError("Missing reference close")
            close=Decimal(str(value))
            if not close.is_finite() or not Decimal('1e-8')<=close<=Decimal('1e9'):raise ValueError("Invalid reference price")
            matches.append(close)
    if len(matches)!=1:raise ValueError("Requested date unavailable")
    return matches[0]


def check_price(root,symbol,*,now=None,fetch=fetch_reference):
    now=now or datetime.now(timezone.utc)
    digest,bundle=load_history(root)
    series=bundle.series[symbol];bar=series.bars[-1]
    if bundle.retrieved_at>now+timedelta(minutes=5):raise ValueError("Future snapshot")
    base=dict(symbol=symbol,snapshot_sha256=digest,price_date=bar.day,checked_at=now,
              primary_close=bar.raw_close,source_url=f"https://finance.yahoo.com/quote/{symbol}/history/")
    try:
        reference=fetch(symbol,bar.day)
        difference=abs(reference-bar.raw_close)
        status="within_tolerance" if difference<=max(Decimal('.05'),reference*Decimal('.005')) else "discrepancy"
        report=PriceCheck(**base,status=status,reference_close=reference,difference_percent=100*difference/reference)
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError):
        report=PriceCheck(**base,status="unavailable")
    atomic_json(Path(root)/"price_checks"/(symbol+".json"),report.model_dump(mode="json"))
    return report


def load_price_check(root,symbol,digest,day):
    if not isinstance(symbol,str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}",symbol):return None
    try:
        with (Path(root)/"price_checks"/(symbol+".json")).open("rb") as stream:payload=stream.read(16385)
        if len(payload)>16384:return None
        report=PriceCheck.model_validate(strict_json(payload))
        if report.symbol!=symbol or report.snapshot_sha256!=digest or report.price_date!=day:return None
        if report.checked_at>datetime.now(timezone.utc)+timedelta(minutes=5):return None
        return report
    except (OSError,ValueError,KeyError,TypeError):return None
