"""Bounded IEX-only data client. No trading, account or paid-feed endpoints."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zoneinfo import ZoneInfo

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from company_research import company_directory
from data_pipeline import load_release, read_table
from issuer_mapping import ticker_issuer_index
from market_history import HistoryBar, HistoryBundle, HistorySeries, calendar_for, session_dates, publish_history
from public_data_store import provider_turn, strict_json
from source_policy import policy_for


BASE="https://data.alpaca.markets/v2/stocks/bars"
NY=ZoneInfo("America/New_York")


class HistoryImportError(ValueError):pass


class AlpacaAccess(BaseSettings):
    model_config=SettingsConfigDict(env_file=".env",env_file_encoding="utf-8",extra="ignore")
    alpaca_api_key: SecretStr | None = None
    alpaca_secret_key: SecretStr | None = None


def credentials():
    try:settings=AlpacaAccess()
    except ValidationError:raise HistoryImportError("Invalid local market-data configuration") from None
    values=[field.get_secret_value() if field else "" for field in (settings.alpaca_api_key,settings.alpaca_secret_key)]
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{10,200}",value) for value in values):
        raise HistoryImportError("Configure ALPACA_API_KEY and ALPACA_SECRET_KEY locally; never paste keys into chat")
    return dict(zip(("APCA-API-KEY-ID","APCA-API-SECRET-KEY"),values))


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise HistoryImportError("Market-data redirects are refused")


def import_plan(public_root,symbols,*,start,as_of,now):
    if now.tzinfo is None or type(start) is not date or type(as_of) is not date:
        raise HistoryImportError("Dates and timezone-aware import clock required")
    if start<date(2016,1,4) or start>as_of or as_of>now.astimezone(NY).date() or (as_of-start).days>3660:
        raise HistoryImportError("Choose a past interval since 2016, bounded to ten years")
    if not isinstance(symbols,(tuple,list)) or not 1<=len(symbols)<=24:
        raise HistoryImportError("Choose one through 24 issuer tickers; SPY is added as a proxy")
    if any(not isinstance(symbol,str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}",symbol) for symbol in symbols) or len(set(symbols))!=len(symbols):
        raise HistoryImportError("Use unique canonical uppercase symbols")
    _,manifest=load_release(public_root)
    directory=manifest.tables.get("sec_ticker_exchange")
    if (directory is None or not directory.policy["public_display_allowed"] or not policy_for("sec_ticker_exchange").public_display_allowed
            or now-directory.retrieved_at>timedelta(days=7) or directory.retrieved_at>now+timedelta(minutes=5)):
        raise HistoryImportError("A fresh verified SEC directory is required")
    mapping=ticker_issuer_index(read_table(public_root,directory)["records"])
    # Bind current installed issuer identities using the current assessment clock.
    # The requested price end is not a request for a historical SEC directory.
    # This does not establish point-in-time membership or historical tradability.
    supported={row.cik for row in company_directory(public_root,today=now.astimezone(NY).date()).entries}
    bindings={}
    for symbol in symbols:
        if symbol=="SPY":continue
        matches=mapping.get(symbol,set())
        if len(matches)!=1 or next(iter(matches)) not in supported:
            raise HistoryImportError("Ticker must uniquely match an installed research issuer")
        bindings[symbol]=next(iter(matches))
    if not bindings:raise HistoryImportError("At least one issuer ticker is required")
    calendar=calendar_for(start,as_of)
    completed=[day for day in session_dates(start,as_of) if calendar.session_close(day.isoformat()).to_pydatetime()+timedelta(hours=1)<=now]
    if not completed:raise HistoryImportError("No fully completed sessions in the interval")
    last=completed[-1]
    end=min(datetime.combine(last+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc),now-timedelta(minutes=20))
    return dict(symbols=sorted(set(bindings)|{"SPY"}),bindings=bindings,start=start,last=last,end=end,
                directory_sha256=directory.source_sha256)


def _bar(payload,*,start,last):
    if not isinstance(payload,dict) or not {"t","o","h","l","c"}.issubset(payload) or set(payload)-{"t","o","h","l","c","v","n","vw"}:
        raise HistoryImportError("Unexpected daily bar schema")
    if not isinstance(payload["t"],str):raise HistoryImportError("Invalid bar timestamp")
    stamp=datetime.fromisoformat(payload["t"].replace("Z","+00:00"))
    if stamp.tzinfo is None:raise HistoryImportError("Bar timestamp requires a timezone")
    local=stamp.astimezone(NY)
    if local.time().isoformat()!="00:00:00" or not start<=local.date()<=last:
        raise HistoryImportError("Bar lies outside the completed daily interval")
    numbers=[]
    for field in ("o","h","l","c"):
        raw=payload[field]
        if isinstance(raw,bool):raise HistoryImportError("Boolean price refused")
        try:value=Decimal(str(raw))
        except InvalidOperation:raise HistoryImportError("Invalid price value") from None
        if not value.is_finite() or not Decimal("1e-8")<=value<=Decimal("1e9"):
            raise HistoryImportError("Invalid price range")
        numbers.append(value)
    opened,high,low,close=numbers
    if not low<=min(opened,close)<=max(opened,close)<=high:
        raise HistoryImportError("Incoherent OHLC bar")
    return local.date(),close


def download_history(plan,cache_root,*,headers,opener=None,sleep=time.sleep,clock=time.monotonic):
    opener=opener or build_opener(NoRedirects()).open
    started=clock();total_bytes=0; all_modes={}
    for adjustment in ("raw","all","split"):
        values={symbol:{} for symbol in plan["symbols"]};token=None;seen_tokens=set()
        for page in range(10):
            if clock()-started>120:raise HistoryImportError("Market-data request budget exceeded")
            params=dict(symbols=",".join(plan["symbols"]),timeframe="1Day",start=plan["start"].isoformat(),
                        end=plan["end"].isoformat(),asof=plan["last"].isoformat(),adjustment=adjustment,
                        feed="iex",currency="USD",sort="asc",limit="10000")
            if token:params["page_token"]=token
            request=Request(BASE+"?"+urlencode(params),headers={**headers,"Accept":"application/json"})
            payload=None
            for attempt in range(3):
                try:
                    with provider_turn(cache_root,"data.alpaca.markets",.4),opener(request,timeout=20) as response:
                        if response.status!=200 or urlparse(response.geturl()).hostname!="data.alpaca.markets":
                            raise HistoryImportError("Unexpected market-data response")
                        body=response.read(10*1024*1024+1)
                        if clock()-started>120:raise HistoryImportError("Market-data request budget exceeded")
                        if len(body)>10*1024*1024:raise HistoryImportError("Oversized market-data page")
                        total_bytes+=len(body)
                        if total_bytes>50*1024*1024:raise HistoryImportError("Market-data batch exceeds byte budget")
                        payload=strict_json(body)
                    break
                except HTTPError as error:
                    error.close()  # Never read or persist a provider's error body.
                    if error.code in (401,403):raise HistoryImportError("Market-data authentication or entitlement refused; no paid fallback was attempted") from None
                    if error.code not in (429,500,502,503,504) or attempt==2:
                        raise HistoryImportError("Market-data service unavailable; prior history preserved") from None
                    delay=2**attempt
                    retry=(error.headers or {}).get("Retry-After")
                    if retry:
                        from email.utils import parsedate_to_datetime
                        try:wait=float(retry)
                        except ValueError:
                            try:wait=(parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds()
                            except (ValueError,TypeError,OverflowError):wait=0
                        if wait>30 or not float("-inf")<wait<float("inf"):
                            raise HistoryImportError("Provider retry delay exceeds batch budget") from None
                        delay=max(delay,wait)
                    sleep(delay)
                except (URLError,OSError,TimeoutError):
                    if attempt==2:raise HistoryImportError("Market-data request failed; prior history preserved") from None
                    sleep(2**attempt)
            if not isinstance(payload,dict) or set(payload)-{"bars","next_page_token"} or not isinstance(payload.get("bars"),dict):
                raise HistoryImportError("Unexpected market-data response schema")
            if set(payload["bars"])-set(values):raise HistoryImportError("Unrequested ticker in market-data response")
            count=0
            for symbol,bars in payload["bars"].items():
                if not isinstance(bars,list):raise HistoryImportError("Invalid bar list")
                count+=len(bars)
                if count>10000:raise HistoryImportError("Provider exceeded requested page limit")
                for bar in bars:
                    day,close=_bar(bar,start=plan["start"],last=plan["last"])
                    if day in values[symbol]:raise HistoryImportError("Duplicate market-data date across pages")
                    values[symbol][day]=close
            token=payload.get("next_page_token")
            if token is None:break
            if not isinstance(token,str) or not 1<=len(token)<=2048 or token in seen_tokens:
                raise HistoryImportError("Invalid or repeated market-data page token")
            seen_tokens.add(token)
        else:raise HistoryImportError("Market-data pagination exceeds ten pages per adjustment")
        all_modes[adjustment]=values
    series={}
    for symbol in plan["symbols"]:
        raw,adjusted=all_modes["raw"][symbol],all_modes["all"][symbol]
        split=all_modes["split"][symbol]
        if not raw or set(raw)!=set(adjusted) or set(raw)!=set(split):raise HistoryImportError("Missing symbol or unmatched adjustment dates; prior history preserved")
        series[symbol]=HistorySeries(symbol=symbol,cik=plan["bindings"].get(symbol),role="benchmark_proxy" if symbol=="SPY" else "issuer_security",
            bars=[HistoryBar(day=day,raw_close=raw[day],adjusted_close=adjusted[day],split_adjusted_close=split[day]) for day in sorted(raw)])
    return series


def refresh_history(public_root,history_root,symbols,*,start,as_of,now=None,opener=None,merge=False):
    now=now or datetime.now(timezone.utc)
    plan=import_plan(public_root,symbols,start=start,as_of=as_of,now=now)
    previous=None;previous_id=None
    if merge:
        from market_history import load_history
        try:previous_id,previous=load_history(history_root)
        except FileNotFoundError:pass
        if previous is not None and (previous.start!=start or previous.completed_through!=plan['last'] or previous.directory_sha256!=plan['directory_sha256'] or previous.adjustment!='raw_all_and_split'):
            raise HistoryImportError('Merge requires the same completed interval, directory and adjustment basis')
        if previous is not None and len(set(previous.series)|set(plan['symbols']))>100:
            raise HistoryImportError('Merged research store is bounded to 100 securities')
    headers=credentials()  # Validate locally before opening any network connection.
    series=download_history(plan,Path(history_root)/"transport",headers=headers,opener=opener)
    for row in series.values():row.source_retrieved_at=now
    if previous is not None:
        retained={symbol:row.model_copy(update={'source_retrieved_at':row.source_retrieved_at or previous.retrieved_at}) for symbol,row in previous.series.items()}
        retained.update(series);series=retained
    import exchange_calendars
    bundle=HistoryBundle(start=start,completed_through=plan["last"],retrieved_at=now,adjustment="raw_all_and_split",
        directory_sha256=plan["directory_sha256"],calendar_version=exchange_calendars.__version__,series=series)
    return publish_history(history_root,bundle,expected_previous=previous_id if merge else 'unchecked'),bundle
