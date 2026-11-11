"""Operator import boundaries, directory races and dynamic issuer publication."""

from datetime import timedelta
import json

import pytest

from company_research import company_directory, company_research
from data_pipeline import build_release, load_release
from market_sources import source_for_id, companyfacts_cik
from sec_import import plan_sec_import
from source_adapters import normalize_source
from test_company_research import research_store, DAY, NOW
from test_public_data_pipeline import seed
from test_stock_financials import company


SOURCE="sec_companyfacts_cik0000000999"


@pytest.mark.parametrize("key",["sec_companyfacts_cik0000000000", "sec_companyfacts_cik999",
    "sec_companyfacts_cik0000000999/../x", "sec_companyfacts_cik0000000999?url=x",
    "sec_companyfacts_cik０００００００９９９", "https://example.com/", None])
def test_source_namespace_refuses_urls_paths_and_noncanonical_ciks(key):
    with pytest.raises(ValueError):source_for_id(key)


def test_plan_reuses_existing_source_and_validates_every_symbol(tmp_path):
    store=research_store(tmp_path)
    plan=plan_sec_import(store,["aapl","AAPL","OTHER"],now=NOW)
    assert plan.new_issuer_count==1
    assert {row.source_id for row in plan.issuers}=={"sec_companyfacts_aapl",SOURCE}
    assert source_for_id(SOURCE).url=="https://data.sec.gov/api/xbrl/companyfacts/CIK0000000999.json"
    assert companyfacts_cik(SOURCE)==999
    before=load_release(store)[0]
    for tickers in (["AAPL","UNKNOWN"],["../../private"],[],[False]):
        with pytest.raises(ValueError):plan_sec_import(store,tickers,now=NOW)
    assert load_release(store)[0]==before
    for clock in (NOW+timedelta(days=8),NOW-timedelta(days=2),NOW.replace(tzinfo=None)):
        with pytest.raises(ValueError):plan_sec_import(store,["OTHER"],now=clock)
    for maximum in (0,26,True):
        with pytest.raises(ValueError):plan_sec_import(store,["OTHER"],now=NOW,maximum_new_issuers=maximum)


def test_share_classes_deduplicate_and_ambiguous_mapping_rejects(tmp_path):
    store=research_store(tmp_path); cache=tmp_path/"raw"
    rows=[[999,"Other issuer","OTHER","NYSE"],[999,"Other issuer","OTHER.A","NYSE"],
          [1,"One","AMBIG","NYSE"],[2,"Two","AMBIG","NYSE"],
          [3,"Third","THIRD","NYSE"]]
    seed(cache,"sec_ticker_exchange",json.dumps({"fields":["cik","name","ticker","exchange"],"data":rows}))
    build_release(cache,store,as_of=DAY,source_ids=["sec_ticker_exchange"],now=NOW)
    plan=plan_sec_import(store,["OTHER","OTHER.A"],now=NOW)
    assert plan.new_issuer_count==1 and plan.issuers[0].requested_tickers==["OTHER","OTHER.A"]
    with pytest.raises(ValueError,match="multiple issuers"):
        plan_sec_import(store,["OTHER","AMBIG"],now=NOW)
    with pytest.raises(ValueError,match="batch limit"):
        plan_sec_import(store,["OTHER","THIRD"],now=NOW,maximum_new_issuers=1)


def test_dynamic_snapshot_identity_reading_and_default_rebuild(tmp_path):
    store=research_store(tmp_path); cache=tmp_path/"raw"
    data=company(); data.update(cik=999,entityName="Other issuer")
    raw=seed(cache,SOURCE,json.dumps(data))
    build_release(cache,store,as_of=DAY,source_ids=[SOURCE],now=NOW)
    detail=company_research(store,"cik0000000999",today=DAY)
    assert detail.status=="available" and detail.company.tickers==["OTHER"]
    assert detail.latest.facts["revenue"].value==1000
    assert not detail.live_recommendations_enabled
    build_release(cache,store,as_of=DAY,now=NOW)
    assert len(company_directory(store,today=DAY).entries)==2
    data["cik"]=998; raw.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError,match="Issuer does not match"):
        normalize_source(SOURCE,raw,as_of=DAY)


def test_directory_change_guard_precedes_transport_and_publication(tmp_path):
    store=research_store(tmp_path); cache=tmp_path/"raw"
    before=load_release(store)[0]; calls=[]
    def fetch(*args,**kwargs):calls.append(args);raise AssertionError("network must not run")
    with pytest.raises(ValueError,match="directory changed"):
        build_release(cache,store,as_of=DAY,source_ids=[SOURCE],now=NOW,download=True,
                      expected_directory_sha="0"*64,fetch=fetch)
    assert calls==[] and load_release(store)[0]==before
