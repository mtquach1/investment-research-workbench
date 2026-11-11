"""Failure injection checks for full-cohort staging, recovery and publication."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import io
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
import pytest
from daily_stock_refresh import plan_daily_refresh, refresh_installed_history, rollback_history
from market_history import load_history, publish_history
from test_market_history import bundle
from test_company_research import research_store, DAY
from test_alpaca_history import Response, bar

NOW = datetime(2026,10,29,23,tzinfo=timezone.utc)


def install(tmp_path, monkeypatch, count=1):
    public = research_store(tmp_path)
    root = tmp_path / 'history'
    old = bundle()
    old.adjustment = 'raw_all_and_split'
    for row in old.series.values():
        for point in row.bars: point.split_adjusted_close = point.raw_close
    if count > 1:
        template = old.series.pop('AAPL')
        for index in range(count):
            symbol = f'T{index:02d}'
            old.series[symbol] = template.model_copy(deep=True, update={'symbol':symbol,'cik':1000+index})
        from alpaca_history import import_plan
        validated = import_plan(public,['AAPL'],start=old.start,as_of=date(2026,10,29),now=NOW)
        def planned(public_root,symbols,*,start,as_of,now):
            assert 1 <= len(symbols) <= 24
            return {**validated,'symbols':sorted(set(symbols)|{'SPY'}),
                'bindings':{symbol:old.series[symbol].cik for symbol in symbols}}
        monkeypatch.setattr('daily_stock_refresh.import_plan',planned)
    else:
        from alpaca_history import import_plan
        old.directory_sha256 = import_plan(public,['AAPL'],start=old.start,as_of=DAY,now=NOW)['directory_sha256']
    before = publish_history(root,old)
    monkeypatch.setattr('daily_stock_refresh.credentials',lambda:{'APCA-API-KEY-ID':'SENSITIVE_TEST_KEY'})
    monkeypatch.setattr('alpaca_history.provider_turn',lambda *args,**kwargs:__import__('contextlib').nullcontext())
    return public, root, before


def transport(calls, *, refuse=None, omit=None, benchmark_change=False):
    def get(request,timeout):
        query = parse_qs(urlparse(request.full_url).query)
        symbols = query['symbols'][0].split(',')
        calls.append(query)
        assert query['feed'] == ['iex'] and query['asof'] == ['2026-10-29']
        if refuse and refuse in symbols:
            raise HTTPError(request.full_url,403,'SENSITIVE_PROVIDER_ERROR',{},io.BytesIO(b'SENSITIVE_PROVIDER_ERROR'))
        payload = {symbol:[bar(day,101 if symbol=='SPY' and benchmark_change and 'T24' in symbols else 100)
            for day in (26,27,28,29) if not (omit and (symbol,day)==omit)] for symbol in symbols}
        return Response({'bars':payload,'next_page_token':None},request.full_url)
    return get


def run(public,root,**kwargs):
    return refresh_installed_history(public,root,as_of=date(2026,10,29),now=NOW,
        clock=lambda:NOW+timedelta(minutes=1),**kwargs)


def test_full_window_refresh_publishes_only_once_and_retains_exact_cohort(tmp_path,monkeypatch):
    public,root,before = install(tmp_path,monkeypatch,count=25)
    seen=[];calls=[]
    def progress(row):
        assert load_history(root)[0] == before
        seen.append(row)
    result=run(public,root,opener=transport(calls),progress=progress)
    digest,history=load_history(root)
    assert result.status=='published' and digest==result.published_sha256!=before
    assert len(calls)==6 and len(history.series)==26 and result.batches_completed==2
    assert all(len(row.bars)==4 and row.bars[-1].day==date(2026,10,29) for row in history.series.values())
    assert all(row.source_retrieved_at==NOW+timedelta(minutes=1) for row in history.series.values())
    assert history.feed=='iex' and not history.security_identity_verified and not history.public_redistribution_allowed
    assert (root/'artifacts'/(before+'.json')).exists()
    assert result.earliest_batch_retrieval==result.latest_batch_retrieval
    assert not result.automatic_schedule_enabled


def test_failed_second_batch_preserves_pointer_and_retry_resumes_first_batch(tmp_path,monkeypatch):
    public,root,before=install(tmp_path,monkeypatch,count=25)
    first_calls=[]
    failed=run(public,root,opener=transport(first_calls,refuse='T24'))
    assert failed.status=='not_published' and failed.batches_completed==1 and load_history(root)[0]==before
    assert 'SENSITIVE' not in (root/'LAST_REFRESH.json').read_text(encoding='utf-8')
    calls=[]
    # Retry begins after the completed stage's retrieval clock.
    result=refresh_installed_history(public,root,as_of=date(2026,10,29),now=NOW+timedelta(minutes=2),
        clock=lambda:NOW+timedelta(minutes=3),opener=transport(calls))
    assert result.status=='published' and result.batches_resumed==1 and len(calls)==3


@pytest.mark.parametrize('missing',[('AAPL',27),('AAPL',29),('SPY',29)])
def test_new_omissions_cannot_replace_a_good_snapshot(tmp_path,monkeypatch,missing):
    public,root,before=install(tmp_path,monkeypatch)
    result=run(public,root,opener=transport([],omit=missing))
    assert result.status=='not_published' and load_history(root)[0]==before


def test_existing_gap_remains_disclosed_without_synthetic_fill(tmp_path,monkeypatch):
    public,root,_=install(tmp_path,monkeypatch)
    _,old=load_history(root);old.series['AAPL'].bars.pop(1);publish_history(root,old)
    result=run(public,root,opener=transport([],omit=('AAPL',27)))
    assert result.status=='published'
    assert result.historical_missing_sessions=={'AAPL':[date(2026,10,27)]}


def test_adjusted_history_is_rebuilt_instead_of_splicing_old_prices(tmp_path,monkeypatch):
    public,root,_=install(tmp_path,monkeypatch)
    def split(request,timeout):
        query=parse_qs(urlparse(request.full_url).query)
        price=50 if query['adjustment'][0] in ('split','all') else 100
        return Response({'bars':{symbol:[bar(day,price) for day in (26,27,28,29)] for symbol in ('AAPL','SPY')},'next_page_token':None},request.full_url)
    result=run(public,root,opener=split)
    assert result.status=='published'
    _,current=load_history(root)
    assert [point.adjusted_close for point in current.series['AAPL'].bars]==[Decimal(50)]*4


def test_benchmark_changes_between_batches_withhold_publication(tmp_path,monkeypatch):
    public,root,before=install(tmp_path,monkeypatch,count=25)
    result=run(public,root,opener=transport([],benchmark_change=True))
    assert result.reason_code=='benchmark_changed_between_batches' and load_history(root)[0]==before


def test_staged_corruption_is_refused_and_explicit_restart_recovers(tmp_path,monkeypatch):
    public,root,before=install(tmp_path,monkeypatch,count=25)
    result=run(public,root,opener=transport([],refuse='T24'))
    job=root/'refresh_jobs'/result.plan_sha256[:16]
    pointer=json.loads((job/'batch-0.json').read_text(encoding='utf-8'))
    (job/'artifacts'/(pointer['sha256']+'.json')).write_text('{}',encoding='utf-8')
    retry=run(public,root,opener=lambda *args,**kwargs:pytest.fail('Corrupt stage must fail before transport'))
    assert retry.status=='not_published' and retry.reason_code=='invalid_staged_batch' and load_history(root)[0]==before
    assert run(public,root,opener=transport([]),resume=False).status=='published'


def test_expired_batches_are_downloaded_again(tmp_path,monkeypatch):
    public,root,_=install(tmp_path,monkeypatch,count=25)
    run(public,root,opener=transport([],refuse='T24'))
    calls=[]
    later=NOW+timedelta(hours=7)
    result=refresh_installed_history(public,root,as_of=date(2026,10,29),now=later,
        clock=lambda:later+timedelta(minutes=1),opener=transport(calls))
    assert result.status=='published' and result.batches_resumed==0 and len(calls)==6


def test_short_job_locator_still_requires_the_full_plan_checksum(tmp_path,monkeypatch):
    from public_data_store import atomic_json, canonical_bytes
    import hashlib
    public,root,before=install(tmp_path,monkeypatch,count=25)
    failed=run(public,root,opener=transport([],refuse='T24'))
    job=root/'refresh_jobs'/failed.plan_sha256[:16]
    pointer=json.loads((job/'batch-0.json').read_text(encoding='utf-8'))
    staged=json.loads((job/'artifacts'/(pointer['sha256']+'.json')).read_text(encoding='utf-8'))
    # A different full digest with the same directory prefix must never be reused,
    # even if its byte checksum and pointer were recomputed consistently.
    staged['plan_sha256']=failed.plan_sha256[:16]+'0'*48
    digest=hashlib.sha256(canonical_bytes(staged)).hexdigest()
    atomic_json(job/'artifacts'/(digest+'.json'),staged)
    atomic_json(job/'batch-0.json',{'sha256':digest})
    retry=run(public,root,opener=lambda *args,**kwargs:pytest.fail('Wrong plan must fail before transport'))
    assert retry.status=='not_published' and load_history(root)[0]==before


def test_windows_workspace_path_budget_does_not_break_staging(tmp_path,monkeypatch):
    import daily_stock_refresh
    # Match the real Windows workspace's path depth; emulate its usual 260-char
    # file limit on Linux CI too. This originally failed after successful download.
    padded=tmp_path
    while len(str(padded.resolve()))<105:padded=padded/'workspace'
    public,root,before=install(padded,monkeypatch,count=25)
    original=daily_stock_refresh.atomic_json
    def windows_write(path,value):
        if len(str(path.resolve()))>=260:raise FileNotFoundError('Windows path length')
        original(path,value)
    monkeypatch.setattr(daily_stock_refresh,'atomic_json',windows_write)
    result=run(public,root,opener=transport([]))
    assert result.status=='published' and load_history(root)[0]!=before


def test_competing_history_writer_is_not_overwritten(tmp_path,monkeypatch):
    public,root,before=install(tmp_path,monkeypatch)
    rival_id=[]
    def replace(row):
        _,rival=load_history(root)
        rival.series['AAPL'].bars[0].raw_close=Decimal(150)
        rival_id.append(publish_history(root,rival,expected_previous=before))
    result=run(public,root,opener=transport([]),progress=replace)
    assert result.status=='not_published' and result.reason_code=='history_changed_during_refresh'
    assert load_history(root)[0]==rival_id[0]


def test_changed_public_release_is_refused_at_commit(tmp_path,monkeypatch):
    from data_pipeline import build_release
    public,root,before=install(tmp_path,monkeypatch)
    def replace(row):
        build_release(tmp_path/'raw',public,as_of=date(2026,10,29),source_ids=['sec_companyfacts_aapl'],now=NOW)
    result=run(public,root,opener=transport([]),progress=replace)
    assert result.status=='not_published' and result.reason_code=='source_release_changed'
    assert load_history(root)[0]==before


def test_no_new_completed_session_is_an_offline_noop(tmp_path,monkeypatch):
    public,root,before=install(tmp_path,monkeypatch)
    monkeypatch.setattr('daily_stock_refresh.credentials',lambda:pytest.fail('No credentials needed for no-op'))
    result=refresh_installed_history(public,root,as_of=DAY,now=NOW)
    assert result.status=='already_current' and result.published_sha256==before
    _,old=load_history(root);old.series['AAPL'].bars.pop(1);publish_history(root,old)
    result=refresh_installed_history(public,root,as_of=DAY,now=NOW)
    assert result.historical_missing_sessions=={'AAPL':[date(2026,10,27)]}


def test_preflight_refuses_backward_dates_or_changed_issuer_binding(tmp_path,monkeypatch):
    public,root,_=install(tmp_path,monkeypatch)
    with pytest.raises(ValueError):plan_daily_refresh(public,root,as_of=date(2026,10,27),now=NOW)
    _,old=load_history(root);old.series['AAPL'].cik=123;publish_history(root,old)
    with pytest.raises(ValueError):plan_daily_refresh(public,root,as_of=date(2026,10,29),now=NOW)


def test_explicit_rollback_is_cas_guarded_and_displays_old_observation_date(tmp_path,monkeypatch):
    public,root,before=install(tmp_path,monkeypatch)
    published=run(public,root,opener=transport([]))
    with pytest.raises(ValueError):rollback_history(root,before,expected_current=before,now=NOW+timedelta(minutes=2))
    restored=rollback_history(root,before,expected_current=published.published_sha256,now=NOW+timedelta(minutes=2))
    assert restored.status=='rolled_back' and restored.completed_through==DAY
    assert load_history(root)[0]==before
    with pytest.raises(ValueError):rollback_history(root,'../outside',expected_current=before,now=NOW)


def test_status_write_failure_does_not_misreport_successful_publication(tmp_path,monkeypatch):
    import daily_stock_refresh
    public,root,before=install(tmp_path,monkeypatch)
    original=daily_stock_refresh.atomic_json
    def fail_status(path,value):
        if path.name=='LAST_REFRESH.json':raise OSError('Disk failure')
        original(path,value)
    monkeypatch.setattr(daily_stock_refresh,'atomic_json',fail_status)
    result=run(public,root,opener=transport([]))
    assert result.status=='published' and result.report_write_failed
    assert load_history(root)[0]==result.published_sha256!=before


def test_refresh_status_uses_current_pointer_not_an_old_report(tmp_path,monkeypatch):
    from daily_stock_refresh import read_refresh_status
    public,root,before=install(tmp_path,monkeypatch)
    assert read_refresh_status(root).status=='withheld'
    assert read_refresh_status(root,mode='local_research').report_unavailable
    result=run(public,root,opener=transport([]))
    status=read_refresh_status(root,mode='local_research')
    assert status.report_matches_snapshot and status.completed_through==date(2026,10,29)
    rollback_history(root,before,expected_current=result.published_sha256,now=NOW+timedelta(minutes=2))
    status=read_refresh_status(root,mode='local_research')
    assert not status.report_matches_snapshot and status.completed_through==DAY
    (root/'LAST_REFRESH.json').write_text('SENSITIVE_CORRUPT_STATUS',encoding='utf-8')
    assert read_refresh_status(root,mode='local_research').report_unavailable


def test_refresh_panel_is_lazy_and_preserves_withheld_mode(tmp_path,monkeypatch):
    import os
    if os.getenv('RUN_UI_TESTS')!='1':pytest.skip('Enable Streamlit UI tests')
    from streamlit.testing.v1 import AppTest
    import stock_refresh_ui
    from config import get_settings
    public,root,_=install(tmp_path,monkeypatch)
    settings=get_settings().model_copy(update={'market_history_store':root,'market_data_mode':'local_research'})
    monkeypatch.setattr(stock_refresh_ui,'get_settings',lambda:settings)
    import daily_stock_refresh
    reads=[]
    real=stock_refresh_ui.read_refresh_status
    def read(*args,**kwargs):reads.append(kwargs);return real(*args,**kwargs)
    monkeypatch.setattr(stock_refresh_ui,'read_refresh_status',read)
    app=AppTest.from_string('from stock_refresh_ui import render_stock_refresh_status\nrender_stock_refresh_status()').run()
    assert not app.exception and not reads
    app.session_state['stock_refresh_status']=True
    app.run()
    assert not app.exception and app.metric[0].value==str(DAY)
    settings.market_data_mode='withheld'
    app.run()
    assert not app.exception and not app.metric
