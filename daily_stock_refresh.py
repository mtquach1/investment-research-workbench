"""Resumable full-cohort IEX refresh. Readers see one old or new snapshot.

Re-download the full installed window: appending newly adjusted prices to an old
adjusted series can introduce artificial returns after splits/distributions.
Known old gaps remain explicit; new omissions cannot silently replace good data.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
from pathlib import Path
import re
from typing import Literal

from pydantic import Field, model_validator
from alpaca_history import import_plan, download_history, credentials, HistoryImportError, NY
from data_pipeline import Contract, load_release
from market_history import HistoryBundle, HistorySeries, load_history, publish_history, session_dates
from public_data_store import atomic_json, canonical_bytes, file_lock, read_verified, strict_json


class RefreshValidationError(HistoryImportError):
    def __init__(self, code, symbol=None, missing_days=None):
        super().__init__(code)
        self.code, self.symbol, self.missing_days = code, symbol, missing_days or []


class RefreshPlan(Contract):
    model_version: Literal['daily-stock-refresh-v1'] = 'daily-stock-refresh-v1'
    feed: Literal['iex'] = 'iex'
    previous_sha256: str
    public_release_id: str
    directory_sha256: str
    start: date
    previous_cutoff: date
    completed_through: date
    planned_at: datetime
    batches: list[list[str]]
    bindings: dict[str, int]
    calendar_version: str

    @property
    def digest(self):
        # Same baseline/reference/cutoff can resume; a clock change is not a job.
        return hashlib.sha256(canonical_bytes(self.model_dump(mode='json', exclude={'planned_at'}))).hexdigest()


class StagedBatch(Contract):
    plan_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    batch_index: int = Field(ge=0, le=99, strict=True)
    retrieved_at: datetime
    series: dict[str, HistorySeries]

    @model_validator(mode='after')
    def aware(self):
        if self.retrieved_at.tzinfo is None: raise ValueError('Aware batch clock required')
        return self


class RefreshResult(Contract):
    model_version: Literal['daily-stock-refresh-result-v1'] = 'daily-stock-refresh-result-v1'
    status: Literal['published', 'already_current', 'not_published', 'rolled_back']
    reason_code: str
    checked_at: datetime
    previous_sha256: str | None = None
    published_sha256: str | None = None
    plan_sha256: str | None = None
    completed_through: date | None = None
    batches_completed: int = 0
    batches_resumed: int = 0
    installed_series: int = 0
    historical_missing_sessions: dict[str, list[date]] = Field(default_factory=dict)
    earliest_batch_retrieval: datetime | None = None
    latest_batch_retrieval: datetime | None = None
    report_write_failed: bool = False
    failed_symbol: str | None = None
    failure_type: str | None = None
    missing_required_sessions: list[date] = Field(default_factory=list)
    automatic_schedule_enabled: Literal[False] = False
    public_redistribution_allowed: Literal[False] = False
    notice: str = 'Operator-run local IEX refresh, not verified security identity, exact total return, independent price validation or public-data permission. One completed cutoff does not imply simultaneous provider observations. Known historical gaps remain disclosed.'


class RefreshStatus(Contract):
    status: Literal['withheld', 'unavailable', 'available']
    snapshot_sha256: str | None = None
    completed_through: date | None = None
    retrieved_at: datetime | None = None
    series_count: int = 0
    last_recorded_attempt: RefreshResult | None = None
    report_matches_snapshot: bool = False
    report_unavailable: bool = False


def read_refresh_status(history_root, *, mode='withheld'):
    if mode != 'local_research': return RefreshStatus(status='withheld')
    try: digest, bundle = load_history(history_root)
    except (OSError, ValueError, KeyError, TypeError): return RefreshStatus(status='unavailable')
    base = dict(status='available', snapshot_sha256=digest, completed_through=bundle.completed_through,
        retrieved_at=bundle.retrieved_at, series_count=len(bundle.series))
    try:
        with (Path(history_root)/'LAST_REFRESH.json').open('rb') as stream: body=stream.read(65537)
        if len(body)>65536: raise ValueError('Status report exceeds byte budget')
        report=RefreshResult.model_validate(strict_json(body))
    except (OSError, ValueError, KeyError, TypeError): return RefreshStatus(**base, report_unavailable=True)
    expected=report.previous_sha256 if report.status=='not_published' else report.published_sha256
    return RefreshStatus(**base, last_recorded_attempt=report, report_matches_snapshot=expected==digest)


def plan_daily_refresh(public_root, history_root, *, as_of, now):
    previous_id, previous = load_history(history_root)
    if now.tzinfo is None or previous.retrieved_at > now:
        raise HistoryImportError('Current aware clock must follow the installed snapshot')
    symbols = sorted(symbol for symbol, row in previous.series.items() if row.role == 'issuer_security')
    if not symbols: raise HistoryImportError('An installed issuer cohort is required')
    # Freeze current reference and exact issuer bindings across all batches.
    release_id, _ = load_release(public_root)
    batches = [symbols[index:index+24] for index in range(0, len(symbols), 24)]
    plans = [import_plan(public_root, batch, start=previous.start, as_of=as_of, now=now) for batch in batches]
    if load_release(public_root, verify_tables=False)[0] != release_id:
        raise HistoryImportError('Reference release changed during planning')
    first = plans[0]
    bindings = {symbol:cik for plan in plans for symbol,cik in plan['bindings'].items()}
    if any(previous.series[symbol].cik != cik for symbol,cik in bindings.items()):
        raise HistoryImportError('Installed issuer binding differs from the current directory; review ticker reuse')
    if any(plan['last'] != first['last'] or plan['directory_sha256'] != first['directory_sha256'] for plan in plans):
        raise HistoryImportError('Batch plans must use one cutoff and directory')
    if first['last'] < previous.completed_through:
        raise HistoryImportError('Daily refresh cannot move the cutoff backwards; use explicit rollback')
    if any(row.bars[-1].day != previous.completed_through for row in previous.series.values()):
        raise HistoryImportError('Installed cohort has inconsistent endpoints; repair it explicitly first')
    import exchange_calendars
    plan = RefreshPlan(previous_sha256=previous_id, public_release_id=release_id,
        directory_sha256=first['directory_sha256'], start=previous.start,
        previous_cutoff=previous.completed_through, completed_through=first['last'], planned_at=now,
        batches=batches, bindings=bindings, calendar_version=exchange_calendars.__version__)
    return plan, previous


def _historical_gaps(series, start, cutoff):
    sessions = session_dates(start, cutoff)
    gaps = {}
    for symbol,row in series.items():
        observed = {bar.day for bar in row.bars}
        missing = [day for day in sessions if day not in observed]
        if missing: gaps[symbol] = missing
    return gaps


def _validate_batch(staged, plan, index, previous):
    if staged.plan_sha256 != plan.digest or staged.batch_index != index:
        raise HistoryImportError('Staged batch belongs to a different plan')
    expected = set(plan.batches[index]) | {'SPY'}
    if set(staged.series) != expected:
        raise HistoryImportError('Staged batch does not contain the exact planned securities')
    sessions = set(session_dates(plan.start, plan.completed_through))
    new_days = {day for day in sessions if day > plan.previous_cutoff}
    for symbol, row in staged.series.items():
        if (row.symbol != symbol or row.cik != plan.bindings.get(symbol) or
            row.role != ('benchmark_proxy' if symbol == 'SPY' else 'issuer_security')):
            raise HistoryImportError('Staged issuer/security identity mismatch')
        days = {bar.day for bar in row.bars}
        required = {bar.day for bar in previous.series[symbol].bars} | new_days
        if not required <= days or not days <= sessions or row.bars[-1].day != plan.completed_through:
            raise RefreshValidationError('missing_or_out_of_window_sessions', symbol, sorted(required-days))
        if any(bar.split_adjusted_close is None for bar in row.bars):
            raise HistoryImportError('Split-only evidence missing')


def _stage_pointer(path):
    # Validate the digest before it becomes any part of a filesystem path.
    with path.open('rb') as stream: body = stream.read(1025)
    if len(body) > 1024: raise ValueError('Oversized staging pointer')
    pointer = strict_json(body)
    if not isinstance(pointer, dict) or set(pointer) != {'sha256'} or not isinstance(pointer['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', pointer['sha256']):
        raise ValueError('Invalid staging pointer')
    return pointer['sha256']


def refresh_installed_history(public_root, history_root, *, as_of, now=None, opener=None,
                              progress=None, clock=None, resume=True):
    """No scheduling. Full-window staging is isolated from CURRENT until commit.

    Resume only within six hours and the same NY day. All consumed stage bytes
    are checksum-verified and revalidated against the frozen plan. Expired stage
    is replaced by a complete new batch, never mixed with another baseline.
    """
    now = now or datetime.now(timezone.utc)
    clock = clock or (lambda: datetime.now(timezone.utc))
    root = Path(history_root)
    plan, previous = plan_daily_refresh(public_root, root, as_of=as_of, now=now)
    base = dict(checked_at=now, previous_sha256=plan.previous_sha256, plan_sha256=plan.digest,
        completed_through=plan.completed_through, installed_series=len(previous.series))
    if plan.completed_through == previous.completed_through and plan.directory_sha256 == previous.directory_sha256 and previous.adjustment == 'raw_all_and_split':
        return RefreshResult(**base, status='already_current', reason_code='no_new_completed_session',
            published_sha256=plan.previous_sha256,
            historical_missing_sessions=_historical_gaps(previous.series, previous.start, previous.completed_through))
    # Windows' common MAX_PATH limit is easily exceeded by nested 64-character
    # hashes in this workspace. A short directory key is only a locator: every
    # cached batch still binds and verifies the complete 256-bit plan digest.
    job = root / 'refresh_jobs' / plan.digest[:16]
    completed = resumed = 0
    collected = {}
    stamps = []
    reason = 'job_busy'
    try:
        with file_lock(job / 'job.lock', timeout=0):
            atomic_json(job / 'plan.json', plan.model_dump(mode='json'))
            headers = None  # Validate credentials only if a batch needs transport.
            for index, symbols in enumerate(plan.batches):
                reason = 'invalid_staged_batch'
                pointer_path = job / f'batch-{index}.json'
                staged = None
                if resume and pointer_path.exists():
                    digest = _stage_pointer(pointer_path)
                    staged = StagedBatch.model_validate(read_verified(job / 'artifacts' / (digest+'.json'), digest))
                    _validate_batch(staged, plan, index, previous)
                    if staged.retrieved_at > now:
                        raise HistoryImportError('Future staged retrieval clock')
                    if now-staged.retrieved_at > timedelta(hours=6) or staged.retrieved_at.astimezone(NY).date() != now.astimezone(NY).date():
                        staged = None
                    else: resumed += 1
                if staged is None:
                    reason = 'download_or_validation_failed'
                    headers = credentials() if headers is None else headers
                    # Copy explicit frozen inputs; import_plan was already validated.
                    end = datetime.combine(plan.completed_through+timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                    payload = download_history(dict(symbols=sorted(set(symbols)|{'SPY'}),
                        bindings={symbol:plan.bindings[symbol] for symbol in symbols}, start=plan.start,
                        last=plan.completed_through, end=end), root / 'transport', headers=headers, opener=opener)
                    stamp = clock()
                    if stamp.tzinfo is None or stamp < now or stamp-now > timedelta(hours=6) or stamp.astimezone(NY).date() != now.astimezone(NY).date():
                        raise HistoryImportError('Refresh exceeded its bounded clock window')
                    staged = StagedBatch(plan_sha256=plan.digest, batch_index=index, retrieved_at=stamp, series=payload)
                    _validate_batch(staged, plan, index, previous)
                    encoded = canonical_bytes(staged.model_dump(mode='json'))
                    if len(encoded) > 32*1024*1024: raise HistoryImportError('Staged batch exceeds byte budget')
                    digest = hashlib.sha256(encoded).hexdigest()
                    atomic_json(job / 'artifacts' / (digest+'.json'), staged.model_dump(mode='json'))
                    atomic_json(pointer_path, {'sha256':digest})
                reason = 'benchmark_changed_between_batches'
                if 'SPY' in collected and collected['SPY'].bars != staged.series['SPY'].bars:
                    raise HistoryImportError('Benchmark evidence differs between batches')
                for symbol, row in staged.series.items():
                    collected[symbol] = row.model_copy(update={'source_retrieved_at':staged.retrieved_at})
                stamps.append(staged.retrieved_at)
                completed += 1
                if progress: progress({'batch':completed, 'total_batches':len(plan.batches), 'resumed_batches':resumed})
            reason = 'candidate_validation_failed'
            committed_at = clock()
            if committed_at.tzinfo is None or committed_at < max(stamps) or committed_at-min(stamps) > timedelta(hours=6) or committed_at.astimezone(NY).date() != now.astimezone(NY).date():
                raise HistoryImportError('Commit clock outside bounded refresh window')
            if set(collected) != set(previous.series): raise HistoryImportError('Refresh changed installed cohort')
            candidate = HistoryBundle(start=plan.start, completed_through=plan.completed_through,
                retrieved_at=committed_at, directory_sha256=plan.directory_sha256, calendar_version=plan.calendar_version,
                adjustment='raw_all_and_split', series=collected)
            gaps = _historical_gaps(candidate.series, plan.start, plan.completed_through)
            result_base = {**base, 'checked_at':committed_at}
            candidate_result = RefreshResult(**result_base, status='published', reason_code='complete_cohort_published',
                batches_completed=completed, batches_resumed=resumed, historical_missing_sessions=gaps,
                earliest_batch_retrieval=min(stamps), latest_batch_retrieval=max(stamps))
            # Fixed lock order: source writer then history writer. No network while
            # holding either publication lock. A competing legacy importer is CAS-checked.
            reason = 'source_release_changed'
            with file_lock(Path(public_root) / 'writer.lock'):
                if load_release(public_root)[0] != plan.public_release_id:
                    raise HistoryImportError('Source release changed during refresh')
                reason = 'history_changed_during_refresh'
                digest = publish_history(root, candidate, expected_previous=plan.previous_sha256)
            result = candidate_result.model_copy(update={'published_sha256':digest})
    except (ValueError, OSError, KeyError, TypeError, TimeoutError) as error:
        # Never log raw exceptions: transports/configuration may contain secrets.
        known_transport_errors = {
            'Missing symbol or unmatched adjustment dates; prior history preserved':'adjustment_date_mismatch',
            'Market-data request budget exceeded':'transport_time_budget_exceeded',
            'Market-data authentication or entitlement refused; no paid fallback was attempted':'authentication_or_entitlement_refused',
            'Invalid or repeated market-data page token':'invalid_page_token',
            'Bar lies outside the completed daily interval':'bar_outside_requested_window',
            'Unexpected daily bar schema':'unexpected_bar_schema',
            'Invalid bar timestamp':'invalid_bar_timestamp',
            'Bar timestamp requires a timezone':'missing_bar_timezone',
            'Boolean price refused':'boolean_price',
            'Invalid price value':'invalid_price_value',
            'Invalid price range':'invalid_price_range',
            'Incoherent OHLC bar':'incoherent_ohlc',
            'Unexpected market-data response':'unexpected_transport_response',
            'Oversized market-data page':'oversized_page',
            'Market-data batch exceeds byte budget':'transport_byte_budget_exceeded',
            'Market-data service unavailable; prior history preserved':'provider_unavailable',
            'Market-data request failed; prior history preserved':'transport_failed',
            'Unexpected market-data response schema':'unexpected_payload_schema',
            'Unrequested ticker in market-data response':'unrequested_symbol',
            'Invalid bar list':'invalid_bar_list',
            'Provider exceeded requested page limit':'page_limit_exceeded',
            'Duplicate market-data date across pages':'duplicate_observation',
            'Market-data pagination exceeds ten pages per adjustment':'page_budget_exceeded',
            'Refresh exceeded its bounded clock window':'batch_clock_window_exceeded',
        }
        if isinstance(error, RefreshValidationError): reason = error.code
        elif type(error) is HistoryImportError: reason = known_transport_errors.get(str(error), reason)
        result = RefreshResult(**base, status='not_published', reason_code=reason,
            batches_completed=completed, batches_resumed=resumed,
            failure_type=type(error).__name__,
            failed_symbol=error.symbol if isinstance(error, RefreshValidationError) else None,
            missing_required_sessions=error.missing_days if isinstance(error, RefreshValidationError) else [])
    # Advisory status is not the serving pointer. CURRENT is authoritative even
    # when a later run overwrites this report or the report write itself fails.
    try: atomic_json(root / 'LAST_REFRESH.json', result.model_dump(mode='json'))
    except OSError: result = result.model_copy(update={'report_write_failed':True})
    return result


def rollback_history(history_root, target_sha256, *, expected_current, now=None):
    """Explicit compare-and-swap rollback to an existing valid same-cohort artifact."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or not all(isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) for value in (target_sha256,expected_current)):
        raise ValueError('Valid snapshot digests and aware clock required')
    current_id, current = load_history(history_root)
    if current_id != expected_current: raise ValueError('Current history changed before rollback')
    target = HistoryBundle.model_validate(read_verified(Path(history_root)/'artifacts'/(target_sha256+'.json'), target_sha256, maximum_bytes=64*1024*1024))
    if (target.retrieved_at > now or target.completed_through > current.completed_through or
        set(target.series) != set(current.series) or any(target.series[symbol].cik != row.cik for symbol,row in current.series.items())):
        raise ValueError('Rollback requires an older existing snapshot with the same issuer cohort')
    digest = publish_history(history_root, target, expected_previous=expected_current)
    return RefreshResult(status='rolled_back', reason_code='explicit_same_cohort_rollback', checked_at=now,
        previous_sha256=current_id, published_sha256=digest, completed_through=target.completed_through, installed_series=len(target.series))
