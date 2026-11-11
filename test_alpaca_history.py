"""Transport stays data-only, bounded, credential-safe and transactional."""

from copy import deepcopy
from datetime import date, datetime, timezone
import io
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs,urlparse

import pytest

from alpaca_history import (HistoryImportError,NoRedirects,import_plan,download_history,refresh_history)
from market_history import publish_history,load_history
from test_market_history import bundle
from test_company_research import research_store,DAY,NOW


KEY="FAKE_PAPER_KEY_12345"
SECRET="FAKE_PAPER_SECRET_12345"


class Response(io.BytesIO):
    status=200
    def __init__(self,payload,url):super().__init__(json.dumps(payload).encode());self.url=url
    def geturl(self):return self.url


def bar(day,close=100):
    return dict(t=f"2026-10-{day:02d}T04:00:00Z",o=close,h=close,l=close,c=close,v=10,n=2,vw=close)


def plan(tmp_path):
    return import_plan(research_store(tmp_path),["AAPL"],start=date(2026,10,26),as_of=DAY,now=NOW)


def test_completed_session_buffer_and_exact_issuer_mapping(tmp_path):
    root=research_store(tmp_path)
    p=import_plan(root,["AAPL"],start=date(2026,10,26),as_of=DAY,now=datetime(2026,10,28,20,30,tzinfo=timezone.utc))
    assert p["last"]==date(2026,10,27) and p["symbols"]==["AAPL","SPY"]
    for symbols in (["UNKNOWN"],["aapl"],["AAPL","AAPL"],["SPY"],["../../private"]):
        with pytest.raises(ValueError):import_plan(root,symbols,start=date(2026,10,26),as_of=DAY,now=NOW)


def test_current_research_release_can_bind_a_prior_price_cutoff(tmp_path):
    from datetime import timedelta
    from data_pipeline import build_release
    root=research_store(tmp_path)
    build_release(tmp_path/'raw',root,as_of=DAY+timedelta(days=1),source_ids=['sec_companyfacts_aapl'],now=NOW+timedelta(days=1))
    p=import_plan(root,['AAPL'],start=date(2026,10,26),as_of=DAY,now=NOW+timedelta(days=1))
    assert p['last']==DAY and p['bindings']=={'AAPL':320193}
    # Current identity bindings do not waive the completed-session guard.
    p=import_plan(root,['AAPL'],start=date(2026,10,26),as_of=DAY+timedelta(days=1),now=datetime(2026,10,29,20,30,tzinfo=timezone.utc))
    assert p['last']<=DAY


def test_merge_preserves_old_series_clock_and_refuses_incompatible_intervals(tmp_path,monkeypatch):
    from datetime import timedelta
    public=research_store(tmp_path);root=tmp_path/'history'
    p=import_plan(public,['AAPL'],start=date(2026,10,26),as_of=DAY,now=NOW)
    old=bundle();old.directory_sha256=p['directory_sha256'];old.adjustment='raw_all_and_split'
    for row in old.series.values():
        for item in row.bars:item.split_adjusted_close=item.raw_close
    retained=old.series['AAPL'].model_copy(deep=True,update={'symbol':'MSFT','cik':789})
    old.series['MSFT']=retained
    publish_history(root,old)
    monkeypatch.setattr('alpaca_history.credentials',lambda:{})
    monkeypatch.setattr('alpaca_history.provider_turn',lambda *a,**k:__import__('contextlib').nullcontext())
    def good(request,timeout):return Response({'bars':{'AAPL':[bar(26),bar(27),bar(28)],'SPY':[bar(26),bar(27),bar(28)]},'next_page_token':None},request.full_url)
    _,merged=refresh_history(public,root,['AAPL'],start=date(2026,10,26),as_of=DAY,now=NOW+timedelta(minutes=1),opener=good,merge=True)
    assert merged.series['MSFT'].source_retrieved_at==NOW
    assert merged.series['AAPL'].source_retrieved_at==NOW+timedelta(minutes=1)
    assert merged.series['MSFT'].bars==retained.bars
    def forbidden(*a,**k):raise AssertionError('Must refuse before transport')
    with pytest.raises(ValueError):refresh_history(public,root,['AAPL'],start=date(2026,10,25),as_of=DAY,now=NOW,opener=forbidden,merge=True)
    with pytest.raises(ValueError):publish_history(root,merged,expected_previous='0'*64)


def test_pagination_is_per_adjustment_and_never_uses_trading_hosts(tmp_path,monkeypatch):
    p=plan(tmp_path);calls=[]
    monkeypatch.setattr("alpaca_history.provider_turn",lambda *a,**k:__import__('contextlib').nullcontext())
    def opener(request,timeout):
        query=parse_qs(urlparse(request.full_url).query);calls.append(query)
        assert request.get_method()=="GET" and urlparse(request.full_url).hostname=="data.alpaca.markets"
        assert KEY not in request.full_url and SECRET not in request.full_url
        assert query["feed"]==["iex"] and query["timeframe"]==["1Day"]
        if "page_token" not in query:return Response({"bars":{"AAPL":[bar(26),bar(27)]},"next_page_token":"next"},request.full_url)
        return Response({"bars":{"SPY":[bar(26),bar(27)]},"next_page_token":None},request.full_url)
    result=download_history(p,tmp_path/"raw",headers={"APCA-API-KEY-ID":KEY,"APCA-API-SECRET-KEY":SECRET},opener=opener)
    assert len(calls)==6 and {query["adjustment"][0] for query in calls}=={"raw","all","split"}
    assert list(result)==["AAPL","SPY"]
    assert KEY not in json.dumps({key:row.model_dump(mode="json") for key,row in result.items()})


@pytest.mark.parametrize("fault",["unknown_symbol","duplicate","repeated_token","missing_adjustment","future","intraday","nonfinite","ohlc"])
def test_bad_batches_are_rejected(tmp_path,monkeypatch,fault):
    p=plan(tmp_path)
    monkeypatch.setattr("alpaca_history.provider_turn",lambda *a,**k:__import__('contextlib').nullcontext())
    def opener(request,timeout):
        query=parse_qs(urlparse(request.full_url).query)
        payload={"bars":{"AAPL":[bar(26),bar(27)],"SPY":[bar(26),bar(27)]},"next_page_token":None}
        if fault=="unknown_symbol":payload["bars"]["EVIL"]=[bar(26)]
        if fault=="duplicate":payload["bars"]["AAPL"]=[bar(26),bar(26)]
        if fault=="repeated_token":
            payload["bars"]={};payload["next_page_token"]="same"
        if fault=="missing_adjustment" and query["adjustment"]==["all"]:payload["bars"]["AAPL"]=[bar(26)]
        if fault=="future":payload["bars"]["AAPL"]=[bar(29)]
        if fault=="intraday":payload["bars"]["AAPL"][0]["t"]="2026-10-26T15:00:00Z"
        if fault=="nonfinite":payload["bars"]["AAPL"][0]["c"]="NaN"
        if fault=="ohlc":payload["bars"]["AAPL"][0]["c"]=101
        return Response(payload,request.full_url)
    with pytest.raises(ValueError):download_history(p,tmp_path/"raw",headers={},opener=opener)


def test_auth_refusal_has_no_paid_fallback_and_preserves_good_pointer(tmp_path,monkeypatch):
    public=research_store(tmp_path);root=tmp_path/"history"
    before=publish_history(root,bundle());calls=[]
    monkeypatch.setattr("alpaca_history.credentials",lambda:{"APCA-API-KEY-ID":KEY,"APCA-API-SECRET-KEY":SECRET})
    monkeypatch.setattr("alpaca_history.provider_turn",lambda *a,**k:__import__('contextlib').nullcontext())
    def refused(request,timeout):
        calls.append(request.full_url)
        raise HTTPError(request.full_url,403,SECRET,{},io.BytesIO(SECRET.encode()))
    with pytest.raises(HistoryImportError) as error:
        refresh_history(public,root,["AAPL"],start=date(2026,10,26),as_of=DAY,now=NOW,opener=refused)
    assert SECRET not in str(error.value) and len(calls)==1
    assert load_history(root)[0]==before
    with pytest.raises(ValueError):NoRedirects().redirect_request(None,None,None,None,None,"https://evil.test")


def test_success_publication_contains_no_credentials(tmp_path,monkeypatch):
    public=research_store(tmp_path);root=tmp_path/"history"
    monkeypatch.setattr("alpaca_history.credentials",lambda:{"APCA-API-KEY-ID":KEY,"APCA-API-SECRET-KEY":SECRET})
    monkeypatch.setattr("alpaca_history.provider_turn",lambda *a,**k:__import__('contextlib').nullcontext())
    def good(request,timeout):return Response({"bars":{"AAPL":[bar(26),bar(27)],"SPY":[bar(26),bar(27)]},"next_page_token":None},request.full_url)
    digest,result=refresh_history(public,root,["AAPL"],start=date(2026,10,26),as_of=DAY,now=NOW,opener=good)
    assert load_history(root)[0]==digest
    payload=(root/"artifacts"/(digest+".json")).read_text(encoding="utf-8")
    assert KEY not in payload and SECRET not in payload and not result.public_redistribution_allowed
