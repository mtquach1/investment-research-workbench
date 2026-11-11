"""Share evidence, split-safe estimates and the strict real-selection barrier."""

from copy import deepcopy
from datetime import date
from decimal import Decimal
import json

import pytest

from data_pipeline import build_release
from equity_reference import reported_share_reference
from stock_screen import estimate_valuation,stock_screen,ValuationEstimate
from market_history import publish_history
from test_company_research import research_store,two_year_company,DAY,NOW
from test_market_history import series,bundle
from test_public_data_pipeline import seed


def shares_company():
    data=two_year_company()
    data["facts"]["dei"]={"EntityCommonStockSharesOutstanding":{"units":{"shares":[
        {"end":"2026-10-26","filed":"2026-10-27","val":100,"accn":"shares-one","form":"10-Q"},
        {"end":"2026-11-01","filed":"2026-11-02","val":200,"accn":"future","form":"10-Q"}]}}}
    return data


def test_only_point_shares_are_used_and_future_conflicts_fail_closed():
    data=shares_company();point=reported_share_reference(data,as_of=DAY)
    assert point["status"]=="reported_point" and point["evidence"]["shares"]=="100"
    assert point["evidence"]["unit"]=="shares"
    values=data["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"]
    values.append(dict(values[0],val=101,accn="conflict"))
    assert reported_share_reference(data,as_of=DAY)["status"]=="ambiguous"
    data["facts"].pop("dei")
    data["facts"]["us-gaap"]["WeightedAverageNumberOfDilutedSharesOutstanding"]={"units":{"shares":[{"val":100}]}}
    assert reported_share_reference(data,as_of=DAY)["status"]=="unavailable"


def valuation_inputs():
    row={"share_reference":reported_share_reference(shares_company(),as_of=DAY),
         "facts":{"net_income":{"value":"100"},"free_cashflow":{"value":"120"}}}
    history=series([100,50,50])
    for bar in history.bars:bar.split_adjusted_close=Decimal(50)
    return row,history


def test_two_for_one_split_does_not_halve_estimated_equity_value():
    row,history=valuation_inputs()
    result=estimate_valuation(row,history,{"AAPL"},today=DAY)
    assert result.status=="estimated" and result.split_factor==2
    assert result.shares_at_price_date_estimate==200 and result.market_cap_estimate==10000
    assert result.annual_earnings_yield_estimate==Decimal(".01")
    assert result.annual_fcf_yield_estimate==Decimal(".012") and result.annual_pe_estimate==100
    assert result.split_reference_on==date(2026,10,26)
    assert not result.verified_current_market_cap
    row["facts"]["net_income"]["value"]="-100"
    loss=estimate_valuation(row,history,{"AAPL"},today=DAY)
    assert loss.annual_earnings_yield_estimate==Decimal("-.01") and loss.annual_pe_estimate is None


def test_estimates_refuse_multiple_classes_stale_unknown_splits_and_late_filings():
    row,history=valuation_inputs()
    assert estimate_valuation(row,history,{"AAPL","OTHER"},today=DAY).status=="multiple_securities"
    history.bars[0].split_adjusted_close=None
    assert estimate_valuation(row,history,{"AAPL"},today=DAY).status=="split_evidence_missing"
    history.bars[0].split_adjusted_close=Decimal(50)
    row["share_reference"]["evidence"]["filed_on"]="2026-10-29"
    assert estimate_valuation(row,history,{"AAPL"},today=DAY).status=="unavailable"
    row["share_reference"]["evidence"].update(measured_on="2026-01-01",filed_on="2026-02-01")
    assert estimate_valuation(row,history,{"AAPL"},today=DAY).status=="stale"
    with pytest.raises(ValueError):ValuationEstimate(status="estimated",reason="invalid",verified_current_market_cap=True)


def screen_store(tmp_path):
    public=research_store(tmp_path);cache=tmp_path/"raw";history=tmp_path/"history"
    seed(cache,"sec_companyfacts_aapl",json.dumps(shares_company()))
    seed(cache,"ivv_holdings_proxy",'Fund Holdings as of,"Oct 26, 2026"\nTicker,Sector,Asset Class,Market Value,Price\nAAPL,Information Technology,Equity,"1,000",100\nUNKNOWN,Industrials,Equity,100,10\n')
    build_release(cache,public,as_of=DAY,source_ids=["sec_companyfacts_aapl","ivv_holdings_proxy"],now=NOW)
    b=bundle();b.adjustment="raw_all_and_split"
    for item in b.series.values():
        for bar in item.bars:bar.split_adjusted_close=bar.raw_close
    publish_history(history,b)
    return public,history


def test_screen_joins_dated_sectors_and_keeps_estimates_out_of_selection(tmp_path):
    public,history=screen_store(tmp_path)
    result=stock_screen(public,history,mode="local_research",today=DAY)
    assert result.status=="available" and result.universe.securities==2
    assert result.universe.uniquely_mapped_securities==1
    row=result.rows[0]
    assert row.sector=="Information Technology" and row.sector_status=="pass"
    assert row.financial_status=="pass" and row.valuation.status=="estimated"
    assert row.eligible_financial_sector_peers==1 and row.score is None and not row.selected
    assert not result.live_recommendations_enabled and not result.universe.official_index_membership_verified
    assert result.public_release_id and result.market_snapshot_sha256


def test_stale_sector_reference_and_local_display_gate_do_not_pass(tmp_path,monkeypatch):
    public,history=screen_store(tmp_path)
    result=stock_screen(public,history,mode="local_research",today=date(2026,11,5))
    assert not result.universe.fresh and result.rows[0].sector_status=="unavailable"
    monkeypatch.setattr("stock_screen.load_release",lambda *a,**k:(_ for _ in ()).throw(AssertionError("must not read")))
    assert stock_screen(public,history,mode="withheld",today=DAY).status=="withheld"


def test_unknown_provider_sector_is_not_treated_as_an_eligible_sector(tmp_path):
    public,history=screen_store(tmp_path)
    seed(tmp_path/"raw","ivv_holdings_proxy",'Fund Holdings as of,"Oct 26, 2026"\nTicker,Sector,Asset Class,Market Value,Price\nAAPL,Unrecognized category,Equity,1000,100\n')
    build_release(tmp_path/"raw",public,as_of=DAY,source_ids=["ivv_holdings_proxy"],now=NOW)
    result=stock_screen(public,history,mode="local_research",today=DAY)
    assert result.rows[0].provider_sector=="Unrecognized category"
    assert result.rows[0].sector is None and result.rows[0].sector_status=="unavailable"
