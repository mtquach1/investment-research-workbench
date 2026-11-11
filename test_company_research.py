"""Real-data research contracts exercised using independent synthetic fixtures."""

from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
import json

import pytest

from company_research import company_directory, company_research
from data_pipeline import build_release
from issuer_mapping import exact_issuer_matches
from stock_financials import annual_financial_history, normalize_annual_financials
from test_public_data_pipeline import seed
from test_stock_financials import company


DAY=date(2026,10,28)
NOW=datetime(2026,10,28,23,tzinfo=timezone.utc)


def two_year_company():
    data=company()
    older=deepcopy(data)
    for tag in older["facts"]["us-gaap"].values():
        for item in tag["units"]["USD"]:
            for key in ("start","end","filed"):
                if key in item:
                    value=date.fromisoformat(item[key])
                    item[key]=value.replace(year=value.year-1).isoformat()
            item["accn"]="older"
    for tag,item in older["facts"]["us-gaap"].items():
        data["facts"]["us-gaap"][tag]["units"]["USD"]+=item["units"]["USD"]
    data["cik"]=320193
    data["entityName"]="Synthetic Apple reference issuer"
    return data


def research_store(tmp_path):
    cache,store=tmp_path/"raw",tmp_path/"store"
    seed(cache,"sec_companyfacts_aapl",json.dumps(two_year_company()))
    seed(cache,"sec_ticker_exchange",json.dumps({"fields":["cik","name","ticker","exchange"],"data":[
        [320193,"Reference issuer","AAPL","Nasdaq"],
        [999,"Reference other","OTHER","NYSE"]]}))
    build_release(cache,store,as_of=DAY,source_ids=["sec_companyfacts_aapl","sec_ticker_exchange"],now=NOW)
    return store


def test_each_fiscal_year_keeps_one_filing_and_independent_arithmetic():
    history=annual_financial_history(two_year_company(),as_of=DAY)
    assert [item.period_end for item in history]==["2024-12-31","2025-12-31"]
    assert [item.accession for item in history]==["older","one"]
    for item in history:
        assert item.metrics["return_on_assets"]==Decimal('.1')
        assert item.metrics["free_cashflow_margin"]==Decimal('.12')
        assert item.facts["free_cashflow"].value==120
        assert {fact.accession for fact in item.facts.values()}=={item.accession}
    chosen=normalize_annual_financials(two_year_company(),as_of=DAY,period_end=date(2024,12,31))
    assert chosen.accession=="older"
    assert len(annual_financial_history(two_year_company(),as_of=DAY,years=1))==1
    with pytest.raises(ValueError):annual_financial_history(two_year_company(),as_of=DAY,years=100)


def test_history_does_not_fill_partial_amendments_or_future_periods():
    data=two_year_company()
    revenue=data["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"]
    revenue.append(dict(revenue[0],filed="2026-10-01",form="10-K/A",accn="partial",val=1200))
    revenue.append(dict(revenue[0],end="2027-12-31",filed="2028-02-01",accn="future"))
    history=annual_financial_history(data,as_of=DAY)
    assert len(history)==2
    assert history[-1].accession=="partial"
    assert history[-1].metrics["free_cashflow_margin"] is None
    assert history[-1].facts["revenue"].value==1200


def test_exact_mapping_refuses_alias_guesses_and_multiple_issuers():
    securities=[{"security_id":key,"ticker":key} for key in ("AAPL","BRKB","AMBIG")]
    result=exact_issuer_matches(securities,[{"ticker":"AAPL","cik":320193},
        {"ticker":"BRK-B","cik":1067983},{"ticker":"AMBIG","cik":1},{"ticker":"AMBIG","cik":2}])
    assert result[0]["issuer_id"]=="sec:0000320193"
    assert result[1]["status"]=="unmatched"
    assert result[2]["status"]=="ambiguous"
    assert all(not item["index_membership_verified"] for item in result)


def test_research_directory_and_detail_retain_evidence_without_recommendation(tmp_path):
    store=research_store(tmp_path)
    directory=company_directory(store,today=DAY)
    assert directory.status=="available"
    assert directory.entries[0].tickers==["AAPL"]
    detail=company_research(store,"aapl",today=DAY)
    assert detail.status=="available" and len(detail.history)==2
    assert detail.latest.facts["revenue"].value==1000
    assert detail.latest.metrics["earnings_yield"] is None
    assert detail.latest.facts["free_cashflow"].inputs==["operating_cashflow","capital_expenditures"]
    assert len(detail.source_sha256)==64
    assert not detail.live_recommendations_enabled
    assert company_research(store,"../../private",today=DAY).status=="unavailable"
    stale=company_research(store,"aapl",today=date(2028,1,1))
    assert stale.status=="available" and not stale.current_strategy_period_gate_passed


def test_missing_and_corrupt_research_fail_closed(tmp_path):
    assert company_directory(tmp_path,today=DAY).status=="unavailable"
    store=research_store(tmp_path)
    (store/"CURRENT.json").write_text('{"manifest_sha256":"invalid"}')
    assert company_research(store,"aapl",today=DAY).status=="integrity_error"


def test_company_detail_verifies_consumed_artifacts_not_unrelated_datasets(tmp_path):
    from data_pipeline import load_release,build_release
    from test_public_data_pipeline import seed
    store=research_store(tmp_path);cache=tmp_path/'raw'
    # Add another issuer source; a detail read does not consume its facts.
    import json
    other=two_year_company();other['cik']=789019;other['entityName']='Other issuer'
    seed(cache,'sec_companyfacts_msft',json.dumps(other))
    _,manifest=build_release(cache,store,as_of=DAY,source_ids=['sec_companyfacts_msft'],now=NOW)
    unrelated=store/'artifacts'/(manifest.tables['sec_companyfacts_msft'].artifact_sha256+'.json')
    unrelated.write_bytes(b'{}')
    assert company_research(store,'aapl',today=DAY).status=='available'
    assert company_research(store,'msft',today=DAY).status=='integrity_error'
    # Both the requested facts and the SEC association are independently verified.
    target=store/'artifacts'/(manifest.tables['sec_ticker_exchange'].artifact_sha256+'.json')
    target.write_bytes(b'{}')
    assert company_research(store,'aapl',today=DAY).status=='integrity_error'


def test_current_policy_can_withhold_an_older_approved_release(tmp_path,monkeypatch):
    from dataclasses import replace
    from source_policy import policy_for
    store=research_store(tmp_path)
    monkeypatch.setattr("company_research.policy_for",lambda key:replace(policy_for(key),public_display_allowed=False))
    assert company_directory(store,today=DAY).entries==[]
    response=company_research(store,"aapl",today=DAY)
    assert response.status=="display_not_cleared" and response.latest is None
