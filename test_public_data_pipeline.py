"""Adversarial fixtures for public-data transactions; no external network."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

import data_pipeline
from data_pipeline import build_release, load_release, read_table
from market_catalog import load_catalog
from market_data import SourceConfigurationError, SourceDownloadError, fetch_source, load_snapshot
from market_sources import SOURCES, source_for_id
from public_data_store import DataIntegrityError, file_lock, provider_turn, strict_json
from source_adapters import normalize_source


DAY=date(2026,10,28)
CLOCK=datetime(2026,10,28,23,tzinfo=timezone.utc)
PRICE="alphavantage_ibm_daily_demo"
VALUE="zillow_sfr_value_zip"
GEO="census_zcta_county_2020"


def daily():
    return {"Meta Data":{"2. Symbol":"IBM","3. Last Refreshed":"2026-10-27","5. Time Zone":"US/Eastern"},
        "Time Series (Daily)":{day:{"1. open":"10","2. high":"12","3. low":"8","4. close":"11",
            "5. adjusted close":"5.5","6. volume":"100","7. dividend amount":".2","8. split coefficient":"2"}
            for day in ("2026-10-26","2026-10-27")}}


def seed(cache,source_id,payload):
    source=source_for_id(source_id)
    payload=payload.encode() if isinstance(payload,str) else payload
    digest=hashlib.sha256(payload).hexdigest()
    directory=Path(cache)/source_id
    directory.mkdir(parents=True,exist_ok=True)
    (directory/(digest+".raw")).write_bytes(payload)
    metadata={"source_id":source_id,"source_url":source.url,"sha256":digest,"bytes":len(payload),
              "retrieved_at":"2026-10-28T01:00:00+00:00","rights_status":"public_display_not_cleared"}
    (directory/"latest.json").write_text(json.dumps(metadata))
    return directory/(digest+".raw")


def seed_price(cache):
    return seed(cache,PRICE,json.dumps(daily()))


def test_verified_reads_use_file_size_without_weakening_checks(tmp_path,monkeypatch):
    from public_data_store import read_verified
    path=tmp_path/'small.json';payload=b'{"value":42}'
    path.write_bytes(payload);digest=hashlib.sha256(payload).hexdigest()
    assert read_verified(path,digest)=={'value':42}
    with pytest.raises(DataIntegrityError):read_verified(path,digest,maximum_bytes=len(payload)-1)
    path.write_bytes(b'{"value":43}')
    with pytest.raises(DataIntegrityError):read_verified(path,digest)
    path.write_bytes(b'{"x":1,"x":2}')
    with pytest.raises(DataIntegrityError):read_verified(path,hashlib.sha256(path.read_bytes()).hexdigest())
    # Simulate growth between fstat and read: the sentinel refuses the artifact.
    monkeypatch.setattr('public_data_store.os.fstat',lambda fd:type('Stat',(),{'st_size':1})())
    with pytest.raises(DataIntegrityError,match='changed size'):read_verified(path,hashlib.sha256(path.read_bytes()).hexdigest())


def seed_rentals(cache):
    seed(cache,GEO,"GEOID_ZCTA5_20|GEOID_COUNTY_20|AREALAND_PART\n01234|06059|25\n01234|06037|75\n01235|06059|100\n")
    seed(cache,VALUE,"RegionID,RegionName,RegionType,State,CountyName,2025-01-31,2026-09-30,2026-11-30\n1,01234,zip,CA,Orange County,100,120,130\n2,01235,zip,CA,Orange County,200,,\n3,09999,zip,CA,Orange County,200,220,\n")


def test_release_idempotence_and_provenance(tmp_path):
    cache,store=tmp_path/"raw",tmp_path/"published"
    seed_price(cache)
    first,manifest=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK)
    stamp=(store/"CURRENT.json").stat().st_mtime_ns
    second,_=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK+timedelta(minutes=1))
    assert first==second
    assert (store/"CURRENT.json").stat().st_mtime_ns==stamp
    assert load_release(store)[0]==first
    table=read_table(store,manifest.tables[PRICE])
    assert table["source_sha256"]==load_snapshot(PRICE,cache).metadata["sha256"]
    assert table["records"][0]["adjusted_close"]=="5.5"
    assert "do_not_add_dividends_again" in table["records"][0]["adjustment_basis"]
    assert not table["summary"]["three_year_history_verified"]
    assert not manifest.stock_recommendations_ready and not manifest.rental_discovery_ready


def test_corrupt_raw_snapshot_retains_verified_normalized_table(tmp_path):
    cache,store=tmp_path/"raw",tmp_path/"published"
    raw=seed_price(cache)
    _,first=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK)
    raw.write_bytes(b"corrupt")
    _,second=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK)
    assert second.tables[PRICE].artifact_sha256==first.tables[PRICE].artifact_sha256
    assert second.tables[PRICE].state=="retained_previous_release"
    assert second.failures[PRICE].code=="cache_unavailable"
    assert len(read_table(store,second.tables[PRICE])["records"])==2


def test_http_failure_preserved_across_offline_rebuild_then_cleared_on_success(tmp_path):
    cache,store=tmp_path/"raw",tmp_path/"published"
    seed_price(cache)
    def fail(*args,**kwargs):
        raise SourceDownloadError("PRIVATE PROVIDER BODY",status_code=503)
    _,first=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK,
        download=True,force_refresh=True,fetch=fail)
    assert first.tables[PRICE].state=="cached_after_refresh_failure"
    _,offline=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK)
    assert offline.failures[PRICE].http_status==503
    assert offline.failures[PRICE].observed_at==CLOCK
    assert "PRIVATE" not in (store/"last_attempt.json").read_text()
    def good(source,root,**kwargs):
        snapshot=load_snapshot(source.source_id,root)
        kwargs["validator"](snapshot.path)
        return snapshot
    _,recovered=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK,
        download=True,force_refresh=True,fetch=good)
    assert not recovered.failures
    assert recovered.tables[PRICE].state=="normalized"


def test_failed_pointer_publication_keeps_previous_release(tmp_path,monkeypatch):
    cache,store=tmp_path/"raw",tmp_path/"published"
    seed_price(cache)
    first,_=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK)
    changed=daily();changed["Time Series (Daily)"]["2026-10-26"]["5. adjusted close"]="5.4"
    seed(cache,PRICE,json.dumps(changed))
    real=data_pipeline.atomic_json
    def interrupted(path,value):
        if Path(path).name=="CURRENT.json":
            raise OSError("simulated interrupted publication")
        real(path,value)
    monkeypatch.setattr(data_pipeline,"atomic_json",interrupted)
    with pytest.raises(OSError):
        build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK)
    assert load_release(store)[0]==first


def test_readers_fail_closed_on_tampered_artifact_and_traversal(tmp_path):
    cache,store=tmp_path/"raw",tmp_path/"published"
    seed_price(cache)
    _,manifest=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK)
    reference=manifest.tables[PRICE]
    (store/"artifacts"/(reference.artifact_sha256+".json")).write_bytes(b"{}")
    assert load_catalog(store,today=DAY).status=="integrity_error"
    (store/"CURRENT.json").write_text('{"manifest_sha256":"../../private"}')
    with pytest.raises(DataIntegrityError):
        load_release(store)


def test_empty_install_and_no_success_cannot_publish(tmp_path):
    assert load_catalog(tmp_path/"store",today=DAY).status=="unavailable"
    with pytest.raises(DataIntegrityError):
        build_release(tmp_path/"raw",tmp_path/"store",as_of=DAY,source_ids=[PRICE],now=CLOCK)
    assert not (tmp_path/"store"/"CURRENT.json").exists()
    assert json.loads((tmp_path/"store"/"last_attempt.json").read_text())["status"]=="no_release_published"


def test_geography_categories_future_dates_and_age_are_explicit(tmp_path):
    cache,store=tmp_path/"raw",tmp_path/"published"
    seed_rentals(cache)
    _,manifest=build_release(cache,store,as_of=DAY,source_ids=[GEO,VALUE],now=CLOCK)
    table=read_table(store,manifest.tables[VALUE])
    assert table["summary"]["future_observations_excluded"]==1
    assert all(row["category"]=="single_family" and not row["property_underwriting_rent_supported"] for row in table["records"])
    summary=load_catalog(store,today=DAY)
    assert summary.rentals.items[0].count==2
    # An additional provider-county-labelled area cannot inflate Census overlap coverage.
    assert summary.rentals.items[1].count==1
    assert summary.rentals.items[1].denominator==2
    assert load_catalog(store,today=date(2027,1,15)).rentals.items[1].count==0
    geo=read_table(store,manifest.tables[GEO])
    assert geo["records"][0]["zcta"]=="01234"
    assert geo["summary"]["dominant_county_count"]==1
    from coverage_report import coverage_report
    report=coverage_report(store)
    assert [row["zcta"] for row in report["rental_candidates"]]==["01234","01235"]
    assert report["provider_county_labels_outside_census_candidate_set"]==["09999"]
    assert all(not row["property_cashflow_screening_supported"] for row in report["rental_candidates"])


@pytest.mark.parametrize("mutation",["wrong_symbol","negative_dividend","zero_split","bad_ohlc","noninteger_volume","future_refresh"])
def test_daily_adapter_rejects_financially_invalid_rows(tmp_path,mutation):
    data=daily();bar=data["Time Series (Daily)"]["2026-10-27"]
    if mutation=="wrong_symbol":data["Meta Data"]["2. Symbol"]="OTHER"
    if mutation=="negative_dividend":bar["7. dividend amount"]="-.1"
    if mutation=="zero_split":bar["8. split coefficient"]="0"
    if mutation=="bad_ohlc":bar["2. high"]="9"
    if mutation=="noninteger_volume":bar["6. volume"]=".5"
    if mutation=="future_refresh":data["Meta Data"]["3. Last Refreshed"]="2026-10-26"
    path=tmp_path/"daily.json";path.write_text(json.dumps(data))
    with pytest.raises(ValueError):normalize_source(PRICE,path,as_of=DAY)


def test_duplicate_json_fields_are_not_silently_overwritten():
    with pytest.raises(DataIntegrityError):strict_json('{"price":10,"price":11}')
    with pytest.raises(DataIntegrityError):strict_json('{"price":NaN}')


def test_semantic_refresh_failure_never_promotes_header_valid_raw_file(tmp_path):
    source=SOURCES[PRICE]
    class Response(io.BytesIO):
        status=200
        headers={}
        def geturl(self):return source.url
    valid=json.dumps(daily()).encode()
    validator=lambda path:normalize_source(PRICE,path,as_of=DAY)
    first=fetch_source(source,tmp_path,opener=lambda *a,**k:Response(valid),validator=validator)
    invalid=daily();invalid["Time Series (Daily)"]["2026-10-27"]["8. split coefficient"]="0"
    with pytest.raises(ValueError):
        fetch_source(source,tmp_path,refresh=True,opener=lambda *a,**k:Response(json.dumps(invalid).encode()),validator=validator)
    assert load_snapshot(PRICE,tmp_path).metadata==first.metadata
    assert not list(first.path.parent.glob("*.part"))


def test_refresh_cadence_avoids_unnecessary_requests(tmp_path):
    seed_price(tmp_path/"raw")
    def forbidden(*args,**kwargs):raise AssertionError("Unexpected download")
    build_release(tmp_path/"raw",tmp_path/"store",as_of=DAY,source_ids=[PRICE],now=CLOCK,download=True,fetch=forbidden)
    calls=[]
    def fetch(source,root,**kwargs):
        calls.append(source.source_id)
        return load_snapshot(source.source_id,root)
    build_release(tmp_path/"raw",tmp_path/"store",as_of=DAY,source_ids=[PRICE],now=CLOCK+timedelta(days=1),download=True,fetch=fetch)
    assert calls==[PRICE]


def test_selective_refresh_preserves_other_domain_tables(tmp_path):
    cache,store=tmp_path/"raw",tmp_path/"store"
    seed_price(cache)
    seed_rentals(cache)
    _,first=build_release(cache,store,as_of=DAY,source_ids=[PRICE,GEO,VALUE],now=CLOCK)
    _,second=build_release(cache,store,as_of=DAY,source_ids=[PRICE],now=CLOCK)
    assert set(second.tables)=={PRICE,GEO,VALUE}
    assert second.tables[GEO].artifact_sha256==first.tables[GEO].artifact_sha256
    assert second.tables[GEO].observation_date is None


def test_provider_spacing_and_os_lock_contention(tmp_path):
    clock=[100.0];delays=[]
    def sleep(seconds):delays.append(seconds);clock[0]+=seconds
    for _ in range(2):
        with provider_turn(tmp_path,"test.provider",1,clock=lambda:clock[0],sleep=sleep):pass
    assert delays==[1]
    with file_lock(tmp_path/"single.lock"):
        with pytest.raises(TimeoutError):
            with file_lock(tmp_path/"single.lock",timeout=0):pass


def test_concurrent_cache_misses_fetch_once(tmp_path):
    calls=[]
    class Response(io.BytesIO):
        status=200;headers={}
        def geturl(self):return SOURCES[PRICE].url
    def opener(*args,**kwargs):
        calls.append(1)
        return Response(json.dumps(daily()).encode())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:fetch_source(SOURCES[PRICE],tmp_path,opener=opener),range(2)))
    assert calls==[1]
    assert results[0].path==results[1].path


def test_sec_refresh_requires_operator_contact_without_network(tmp_path,monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT",raising=False)
    from types import SimpleNamespace
    monkeypatch.setattr("source_policy.SourceAccessSettings",lambda:SimpleNamespace(sec_user_agent=None))
    def forbidden(*a,**k):raise AssertionError("Network must not run")
    with pytest.raises(SourceConfigurationError):
        fetch_source(SOURCES['sec_companyfacts_aapl'],tmp_path,opener=forbidden)


def test_retry_after_is_bounded_and_provider_bodies_are_not_exposed(tmp_path):
    delays=[];calls=[]
    def opener(*a,**k):
        calls.append(1)
        raise HTTPError(SOURCES[PRICE].url,429,"PRIVATE",{"Retry-After":"9999"},None)
    with pytest.raises(SourceDownloadError) as error:
        fetch_source(SOURCES[PRICE],tmp_path,opener=opener,sleep=delays.append)
    assert delays==[] and calls==[1]
    assert error.value.status_code==429 and "PRIVATE" not in str(error.value)


def test_short_retry_after_is_respected(tmp_path):
    delays=[]
    def opener(*a,**k):raise HTTPError(SOURCES[PRICE].url,429,"PRIVATE",{"Retry-After":"3"},None)
    with pytest.raises(SourceDownloadError):
        fetch_source(SOURCES[PRICE],tmp_path,opener=opener,sleep=delays.append)
    assert delays==[3]
