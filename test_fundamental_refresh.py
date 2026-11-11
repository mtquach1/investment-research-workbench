"""Financial-source refresh preserves meaning, identity and last-good evidence."""
from datetime import date, timedelta
import json
from pathlib import Path
import pytest
from data_pipeline import load_release,build_release,read_table
from fundamental_refresh import plan_fundamental_refresh,refresh_fundamentals
from market_data import SourceDownloadError,load_snapshot
from test_company_research import research_store,DAY,NOW
from test_stock_screen import shares_company
from test_public_data_pipeline import seed


def installed(tmp_path):
    store=research_store(tmp_path)
    seed(tmp_path/'raw','sec_companyfacts_aapl',json.dumps(shares_company()))
    build_release(tmp_path/'raw',store,as_of=DAY,source_ids=['sec_companyfacts_aapl'],now=NOW)
    return store


def fetcher(tmp_path,*,now,quantity=None,date_change=False):
    def fetch(source,cache_root,refresh,validator):
        assert source.source_id=='sec_companyfacts_aapl' and refresh
        data=shares_company()
        share=data['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0]
        if quantity is not None:share['val']=quantity
        if date_change:share.update(end='2026-10-27',filed='2026-10-28',accn='new-point')
        path=seed(cache_root,source.source_id,json.dumps(data))
        validator(path)
        metadata_path=Path(cache_root)/source.source_id/'latest.json'
        metadata=json.loads(metadata_path.read_text(encoding='utf-8'));metadata['retrieved_at']=now.isoformat()
        metadata_path.write_text(json.dumps(metadata),encoding='utf-8')
        return load_snapshot(source.source_id,cache_root)
    return fetch


def test_offline_plan_targets_installed_issuers_only_and_preserves_dates(tmp_path):
    store=installed(tmp_path)
    plan=plan_fundamental_refresh(store,as_of=DAY,now=NOW)
    assert len(plan.observations)==1 and plan.observations[0].cik==320193
    assert plan.observations[0].share_measured_on==date(2026,10,26)
    assert plan.observations[0].reported_shares==100
    assert plan.observations[0].annual_period_end==date(2025,12,31)
    with pytest.raises(ValueError):plan_fundamental_refresh(store,as_of=DAY,now=NOW+timedelta(days=8))


def test_redownload_does_not_relabel_old_share_observations_as_fresh(tmp_path):
    store=installed(tmp_path);now=NOW+timedelta(hours=1)
    result=refresh_fundamentals(tmp_path/'raw',store,as_of=DAY,now=now,fetch=fetcher(tmp_path,now=now))
    change=result.changes[0]
    assert result.status=='refreshed' and result.refetched_sources==1
    assert change.after.retrieved_at==now and change.after.share_measured_on==date(2026,10,26)
    assert not change.source_bytes_changed and not change.share_evidence_changed
    assert not result.strict_recommendations_enabled and not result.automatic_schedule_enabled


def test_share_amount_changes_are_detected_even_if_dates_do_not_change(tmp_path):
    store=installed(tmp_path);now=NOW+timedelta(hours=1)
    result=refresh_fundamentals(tmp_path/'raw',store,as_of=DAY,now=now,fetch=fetcher(tmp_path,now=now,quantity=105))
    change=result.changes[0]
    assert change.share_evidence_changed and change.source_bytes_changed
    assert change.before.reported_shares==100 and change.after.reported_shares==105


def test_reported_share_dates_can_advance_with_exact_filing_provenance(tmp_path):
    store=installed(tmp_path);now=NOW+timedelta(hours=1)
    result=refresh_fundamentals(tmp_path/'raw',store,as_of=DAY,now=now,fetch=fetcher(tmp_path,now=now,date_change=True))
    change=result.changes[0]
    assert change.share_evidence_changed and change.after.share_accession=='new-point'
    assert change.after.share_measured_on==date(2026,10,27)


def test_failed_source_retains_previous_values_and_visible_failure(tmp_path):
    store=installed(tmp_path);now=NOW+timedelta(hours=1)
    def refused(*args,**kwargs):raise SourceDownloadError('SENSITIVE_ERROR_BODY',status_code=403)
    result=refresh_fundamentals(tmp_path/'raw',store,as_of=DAY,now=now,fetch=refused)
    change=result.changes[0]
    assert result.status=='degraded' and result.refetched_sources==0
    assert change.retained_after_failure and change.before==change.after
    assert 'SENSITIVE_ERROR_BODY' not in result.model_dump_json()
    _,manifest=load_release(store)
    assert manifest.failures['sec_companyfacts_aapl'].http_status==403


def test_budget_exhaustion_makes_no_network_request_and_retains_evidence(tmp_path):
    store=installed(tmp_path);times=iter([0,2])
    def forbidden(*args,**kwargs):pytest.fail('Transport budget was exhausted')
    result=refresh_fundamentals(tmp_path/'raw',store,as_of=DAY,now=NOW,fetch=forbidden,clock=lambda:next(times),budget_seconds=1)
    assert result.status=='degraded' and result.budget_exhausted and result.refetched_sources==0


def test_changed_release_guard_precedes_any_download(tmp_path):
    store=installed(tmp_path);before=load_release(store)[0]
    build_release(tmp_path/'raw',store,as_of=DAY+timedelta(days=1),source_ids=['sec_companyfacts_aapl'],now=NOW+timedelta(days=1))
    def forbidden(*args,**kwargs):pytest.fail('Stale plan cannot download')
    with pytest.raises(ValueError,match='release changed'):
        build_release(tmp_path/'raw',store,as_of=DAY+timedelta(days=1),download=True,
            source_ids=['sec_companyfacts_aapl'],now=NOW+timedelta(days=1),fetch=forbidden,expected_release_id=before)


def test_long_refresh_receipts_use_advanced_clock_instead_of_becoming_falsely_future_dated(tmp_path):
    store=installed(tmp_path)
    values=iter([0,0,420])
    result=refresh_fundamentals(tmp_path/'raw',store,as_of=DAY,now=NOW,
        fetch=fetcher(tmp_path,now=NOW+timedelta(minutes=7)),clock=lambda:next(values),budget_seconds=600)
    assert result.status=='refreshed' and result.refetched_sources==1


def test_observation_fields_reject_duration_shares_instead_of_using_weighted_averages():
    from equity_reference import reported_share_reference
    data=shares_company()
    data['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0]['start']='2026-01-01'
    assert reported_share_reference(data,as_of=DAY)['status']=='unavailable'
