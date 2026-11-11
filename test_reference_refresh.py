from datetime import timedelta
import json
from pathlib import Path
import pytest
from data_pipeline import build_release,load_release
from market_data import load_snapshot,SourceDownloadError
from reference_refresh import REFERENCE_SOURCES,plan_reference_refresh,refresh_references,read_reference_report
from test_stock_screen import screen_store
from test_public_data_pipeline import seed
from test_security_listing import NASDAQ,OTHER,FOOTER
from test_company_research import DAY,NOW


def installed(tmp_path):
    root,_=screen_store(tmp_path)
    seed(tmp_path/'raw','nasdaq_listed_directory',NASDAQ+FOOTER)
    seed(tmp_path/'raw','nasdaq_other_directory',OTHER+FOOTER)
    build_release(tmp_path/'raw',root,as_of=DAY,source_ids=list(REFERENCE_SOURCES),now=NOW)
    return root


def fetcher(*,now,failed=None,stale=False,callback=None):
    def fetch(source,cache,refresh,validator):
        if callback:callback(source)
        if source.source_id==failed:raise SourceDownloadError('secret provider response must not appear')
        snapshot=load_snapshot(source.source_id,cache)
        if stale and source.source_id=='ivv_holdings_proxy':
            body=snapshot.path.read_text().replace('Oct 26, 2026','Oct 01, 2026')
            seed(cache,source.source_id,body)
            snapshot=load_snapshot(source.source_id,cache)
        validator(snapshot.path)
        path=Path(cache)/source.source_id/'latest.json'
        metadata=json.loads(path.read_text());metadata['retrieved_at']=now.isoformat()
        path.write_text(json.dumps(metadata))
        return load_snapshot(source.source_id,cache)
    return fetch


def test_plan_is_offline_and_complete_cohort_only(tmp_path):
    root=installed(tmp_path)
    plan=plan_reference_refresh(root,as_of=DAY,now=NOW)
    assert {item.source_id for item in plan.sources}==set(REFERENCE_SOURCES)
    assert len(plan.previous_release_id)==64


def test_success_preserves_unrelated_tables_and_explains_unchanged_observations(tmp_path):
    root=installed(tmp_path);before,manifest=load_release(root);now=NOW+timedelta(hours=1)
    result=refresh_references(tmp_path/'raw',root,as_of=DAY,now=now,fetch=fetcher(now=now))
    after,new=load_release(root)
    assert result.status=='published' and after!=before and after==result.installed_release_id
    assert new.tables['sec_companyfacts_aapl']==manifest.tables['sec_companyfacts_aapl']
    assert all(item.retrieved_at==now for item in result.candidate)
    assert [item.observed_on for item in result.candidate]==[item.observed_on for item in result.before]
    assert not result.official_membership_verified and not result.automatic_schedule_enabled
    assert read_reference_report(root)==result


@pytest.mark.parametrize('failed',REFERENCE_SOURCES)
def test_any_required_source_failure_preserves_exact_published_pointer(tmp_path,failed):
    root=installed(tmp_path);pointer=(root/'CURRENT.json').read_bytes();now=NOW+timedelta(hours=1)
    result=refresh_references(tmp_path/'raw',root,as_of=DAY,now=now,fetch=fetcher(now=now,failed=failed))
    assert result.status=='not_published' and failed in result.failed_sources
    assert (root/'CURRENT.json').read_bytes()==pointer
    assert 'secret' not in result.model_dump_json()
    assert json.loads((root/'last_attempt.json').read_text())['status']=='rejected_before_publication'


def test_fresh_download_of_stale_reference_cannot_publish(tmp_path):
    root=installed(tmp_path);before,_=load_release(root);now=NOW+timedelta(hours=1)
    result=refresh_references(tmp_path/'raw',root,as_of=DAY,now=now,fetch=fetcher(now=now,stale=True))
    assert result.status=='not_published' and 'ivv_holdings_proxy' in result.failed_sources
    assert load_release(root)[0]==before


def test_changed_release_is_refused_before_transport(tmp_path,monkeypatch):
    import reference_refresh
    root=installed(tmp_path);original=reference_refresh.plan_reference_refresh
    def changed(*args,**kwargs):
        plan=original(*args,**kwargs)
        snapshot=load_snapshot('ivv_holdings_proxy',tmp_path/'raw')
        seed(tmp_path/'raw','ivv_holdings_proxy',snapshot.path.read_text().replace('UNKNOWN','CHANGED'))
        build_release(tmp_path/'raw',root,as_of=DAY,source_ids=['ivv_holdings_proxy'],now=NOW+timedelta(seconds=1))
        return plan
    monkeypatch.setattr(reference_refresh,'plan_reference_refresh',changed)
    result=refresh_references(tmp_path/'raw',root,as_of=DAY,now=NOW,fetch=lambda *a,**k:pytest.fail('transport must not run'))
    assert result.status=='not_published' and result.reason=='release_changed_or_invalid'
    assert result.installed_release_id!=result.previous_release_id


def test_budget_exhaustion_and_malformed_reports_fail_closed(tmp_path):
    root=installed(tmp_path);pointer=(root/'CURRENT.json').read_bytes()
    ticks=iter([0,301,302,303,304,305,306,307,308,309])
    result=refresh_references(tmp_path/'raw',root,as_of=DAY,now=NOW,clock=lambda:next(ticks),fetch=lambda *a,**k:pytest.fail('exhausted'))
    assert result.status=='not_published' and (root/'CURRENT.json').read_bytes()==pointer
    (root/'reference_refresh.json').write_text('{"status":"secret"}')
    assert read_reference_report(root) is None
