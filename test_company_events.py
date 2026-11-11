"""News context stays sourced, time-aware, offline and separate from selection."""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json

import pytest

from company_events import company_events, load_reviewed_events, ReviewedEvent, FilingEvent
from company_research import company_directory
from data_pipeline import build_release, load_release
from filing_events import normalize_submissions
from market_data import SourceDownloadError
from market_sources import source_for_id
from test_public_data_pipeline import seed, DAY, CLOCK


SOURCE="sec_submissions_cik0000002488"


def submissions(cik=2488):
    return {"cik":f"{cik:010d}","name":"Reference issuer","filings":{"recent":{
        "accessionNumber":[f"{cik:010d}-26-000001",f"{cik:010d}-26-000002"],
        "filingDate":["2026-10-27","2026-11-02"],"form":["8-K","10-Q"],
        "primaryDocument":["release.htm","report.htm"],"items":["2.02,9.01",""]}}}


def event_store(tmp_path,cik=2488):
    cache,store=tmp_path/"raw",tmp_path/"store"
    key=f"sec_submissions_cik{cik:010d}"
    seed(cache,key,json.dumps(submissions(cik)))
    seed(cache,"sec_ticker_exchange",json.dumps({"fields":["cik","name","ticker","exchange"],
        "data":[[cik,"Reference issuer","AMD" if cik==2488 else "SNDK","Nasdaq"]]}))
    build_release(cache,store,as_of=DAY,source_ids=[key,"sec_ticker_exchange"],now=CLOCK)
    return cache,store


def test_normalization_keeps_filing_date_and_no_inferred_earnings_schedule():
    result=normalize_submissions(SOURCE,submissions(),as_of=DAY)
    assert result["summary"]["future_filings_excluded"]==1
    rows=result["records"][0]["filings"]
    assert len(rows)==1 and rows[0]["filed_on"]=="2026-10-27"
    assert rows[0]["topics"]==["Results of operations disclosed"]
    assert "scheduled_at" not in rows[0]
    assert rows[0]["source_url"]=="https://www.sec.gov/Archives/edgar/data/2488/000000248826000001/release.htm"
    empty=normalize_submissions(SOURCE,submissions(),as_of=date(2026,1,1))
    assert empty["records"][0]["filings"]==[] and empty["observation_date"] is None


@pytest.mark.parametrize("mutation",["cik","columns","accession","path","items","duplicate"])
def test_metadata_rejects_wrong_identity_misalignment_and_unsafe_links(mutation):
    data=submissions(); recent=data["filings"]["recent"]
    if mutation=="cik":data["cik"]="0000000999"
    if mutation=="columns":recent["form"].pop()
    if mutation=="accession":recent["accessionNumber"][0]="../../private"
    if mutation=="path":recent["primaryDocument"][0]="../../evil.htm"
    if mutation=="items":recent["items"][0]="<script>"
    if mutation=="duplicate":
        recent["accessionNumber"][1]=recent["accessionNumber"][0]
        recent["filingDate"][1]="2026-10-27"
    with pytest.raises(ValueError):normalize_submissions(SOURCE,data,as_of=DAY)


def test_busy_issuer_bounds_are_explicit():
    data=submissions(); recent=data["filings"]["recent"]
    for key,value in recent.items():recent[key]=[value[0]]*26551
    recent["form"]=["424B2"]*26551  # Busy note issuer; unsupported forms are not news events.
    assert normalize_submissions(SOURCE,data,as_of=DAY)["records"][0]["filings"]==[]
    for key,value in recent.items():recent[key]=[value[0]]*50001
    with pytest.raises(ValueError):normalize_submissions(SOURCE,data,as_of=DAY)


def test_offline_events_support_news_only_issuer_without_financial_claims(tmp_path,monkeypatch):
    _,store=event_store(tmp_path)
    def forbidden(*a,**k):raise AssertionError("Serving must not download")
    monkeypatch.setattr("market_data.fetch_source",forbidden)
    entry=company_directory(store,today=DAY).entries[0]
    assert not entry.financials_available and entry.tickers==["AMD"]
    result=company_events(store,entry.issuer_key,now=CLOCK)
    assert result.status=="available" and len(result.filings)==1 and len(result.events)==1
    assert not result.complete_news_coverage and not result.affects_strategy_score
    assert result.events[0].schedule_status=="announced"
    assert result.filing_source_sha256 and result.context_catalog_sha256
    assert company_events(store,"../../private",now=CLOCK).status=="unavailable"


def test_confirmed_schedule_transitions_without_claiming_results(tmp_path):
    _,store=event_store(tmp_path,2023554)
    before=datetime(2026,10,29,20,29,tzinfo=timezone.utc)
    key="cik0002023554"
    event=company_events(store,key,now=before).events[0]
    assert event.schedule_status=="upcoming" and event.scheduled_at.utcoffset()==timedelta(hours=-7)
    after=company_events(store,key,now=before+timedelta(minutes=2)).events[0]
    assert after.schedule_status=="scheduled_time_passed_outcome_unverified"
    assert company_events(store,key,now=CLOCK+timedelta(days=8)).events[0].review_stale
    with pytest.raises(ValueError):company_events(store,key,now=CLOCK.replace(tzinfo=None))


def test_catalog_validation_and_corruption_do_not_erase_filings(tmp_path):
    _,store=event_store(tmp_path)
    events,_=load_reviewed_events()
    row=events[0].model_dump(mode="json")
    for url in ("javascript:alert(1)","https://ir.amd.com.evil.test/story","https://ir.amd.com:443/story"):
        with pytest.raises(ValueError):ReviewedEvent.model_validate(dict(row,source_url=url))
    bad=tmp_path/"bad.json";bad.write_text("{}",encoding="utf-8")
    result=company_events(store,"cik0000002488",now=CLOCK,catalog_path=bad)
    assert result.status=="available" and result.filings and not result.events
    assert result.context_catalog_status=="unavailable"
    with pytest.raises(ValueError):ReviewedEvent.model_validate(dict(row,kind="earnings_call",scheduled_at="2026-10-29T13:30:00"))


def test_stale_or_failed_refresh_and_current_policy_are_visible(tmp_path,monkeypatch):
    from dataclasses import replace
    from source_policy import policy_for
    cache,store=event_store(tmp_path)
    def fail(*a,**k):raise SourceDownloadError("provider body",status_code=503)
    build_release(cache,store,as_of=DAY,source_ids=[SOURCE],download=True,force_refresh=True,fetch=fail,now=CLOCK)
    result=company_events(store,"cik0000002488",now=CLOCK+timedelta(days=2))
    assert result.filings_refresh_failed and result.filings_refresh_due and result.filings
    monkeypatch.setattr("company_events.policy_for",lambda key:replace(policy_for(key),public_display_allowed=False))
    assert not company_events(store,"cik0000002488",now=CLOCK).filings
    (store/"CURRENT.json").write_text('{"manifest_sha256":"invalid"}',encoding="utf-8")
    assert company_events(store,"cik0000002488",now=CLOCK).status=="integrity_error"


def test_new_source_namespace_and_filing_links_fail_closed():
    assert source_for_id(SOURCE).url=="https://data.sec.gov/submissions/CIK0000002488.json"
    for key in (SOURCE+"/../x","sec_submissions_cik0000000000","sec_submissions_cik１２３４５６７８９０"):
        with pytest.raises(ValueError):source_for_id(key)
    row=normalize_submissions(SOURCE,submissions(),as_of=DAY)["records"][0]["filings"][0]
    with pytest.raises(ValueError):FilingEvent.model_validate(dict(row,source_url="https://evil.test"))
