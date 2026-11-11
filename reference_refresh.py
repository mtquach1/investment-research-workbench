"""All-or-nothing refresh of the four installed stock reference sources."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import time
from typing import Literal
from pydantic import Field,model_validator
from data_pipeline import Contract, load_release, build_release
from market_data import fetch_source, SourceDownloadError
from public_data_store import atomic_json, strict_json

REFERENCE_SOURCES=('sec_ticker_exchange','nasdaq_listed_directory','nasdaq_other_directory','ivv_holdings_proxy')


class ReferenceObservation(Contract):
    source_id: Literal['sec_ticker_exchange','nasdaq_listed_directory','nasdaq_other_directory','ivv_holdings_proxy']
    source_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    retrieved_at: datetime
    observed_on: date | None
    rows: int = Field(gt=0)


class ReferencePlan(Contract):
    previous_release_id: str
    as_of: date
    checked_at: datetime
    sources: list[ReferenceObservation] = Field(min_length=4,max_length=4)


class ReferenceRefreshReport(Contract):
    model_version: Literal['stock-reference-refresh-v1']='stock-reference-refresh-v1'
    status: Literal['published','not_published']
    previous_release_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    installed_release_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    checked_at: datetime
    reason: Literal['complete_cohort','source_failure_or_stale','release_changed_or_invalid']
    failed_sources: list[str] = Field(default_factory=list,max_length=4)
    before: list[ReferenceObservation] = Field(min_length=4,max_length=4)
    candidate: list[ReferenceObservation] = Field(default_factory=list,max_length=4)
    automatic_schedule_enabled: Literal[False]=False
    official_membership_verified: Literal[False]=False
    notice: str='A coordinated download is not verified membership or security identity. Financial statements and prices are not refreshed by this job. Failed candidates do not replace the installed release.'

    @model_validator(mode='after')
    def complete_cohorts(self):
        for cohort in (self.before,self.candidate):
            if cohort and {item.source_id for item in cohort}!=set(REFERENCE_SOURCES):
                raise ValueError('Reference receipts must cover the declared cohort exactly')
        if self.checked_at.tzinfo is None or any(item.retrieved_at.tzinfo is None for item in self.before+self.candidate):
            raise ValueError('Aware reference clocks required')
        if self.status=='published' and (not self.candidate or self.failed_sources or self.reason!='complete_cohort'):
            raise ValueError('Published report requires a successful complete cohort')
        return self


def reference_observations(manifest):
    return [ReferenceObservation(source_id=key,source_sha256=manifest.tables[key].source_sha256,
        retrieved_at=manifest.tables[key].retrieved_at,observed_on=manifest.tables[key].observation_date,
        rows=manifest.tables[key].row_count) for key in REFERENCE_SOURCES]


def plan_reference_refresh(root,*,as_of,now=None):
    now=now or datetime.now(timezone.utc)
    if type(as_of) is not date or now.tzinfo is None or as_of>now.date():
        raise ValueError('Valid assessment date and aware clock required')
    digest,manifest=load_release(root)
    if manifest.as_of>as_of:raise ValueError('Cannot move the reference assessment backwards')
    return ReferencePlan(previous_release_id=digest,as_of=as_of,checked_at=now,sources=reference_observations(manifest))


def refresh_references(cache,root,*,as_of,now=None,fetch=fetch_source,clock=time.monotonic,budget_seconds=180):
    if isinstance(budget_seconds,bool) or not 1<=budget_seconds<=300:raise ValueError('Use a bounded transport budget')
    now=now or datetime.now(timezone.utc)
    plan=plan_reference_refresh(root,as_of=as_of,now=now)
    candidate=[];failed=[];started=clock()
    def bounded_fetch(source,*args,**kwargs):
        if clock()-started>=budget_seconds:raise SourceDownloadError('Reference transport budget exhausted')
        return fetch(source,*args,**kwargs)
    def validate(manifest):
        candidate.extend(reference_observations(manifest))
        receipt_now=now+timedelta(seconds=max(0,clock()-started))
        for item in candidate:
            ref=manifest.tables[item.source_id]
            if (item.source_id in manifest.failures or ref.state!='normalized'
                or not now<=item.retrieved_at<=receipt_now+timedelta(minutes=5)
                or (item.source_id!='sec_ticker_exchange' and (item.observed_on is None
                    or not 0<=(as_of-item.observed_on).days<=7))):
                failed.append(item.source_id)
        if failed:raise ValueError('Required reference source failed validation')
    try:
        installed,_=build_release(cache,root,as_of=as_of,source_ids=list(REFERENCE_SOURCES),
            download=True,force_refresh=True,now=now,fetch=bounded_fetch,
            expected_release_id=plan.previous_release_id,publication_check=validate,
            receipt_clock=lambda:now+timedelta(seconds=max(0,clock()-started)))
        status,reason='published','complete_cohort'
    except (ValueError,OSError,KeyError,TypeError):
        installed,_=load_release(root)
        status='not_published';reason='source_failure_or_stale' if failed else 'release_changed_or_invalid'
    report=ReferenceRefreshReport(status=status,reason=reason,previous_release_id=plan.previous_release_id,
        installed_release_id=installed,checked_at=now,before=plan.sources,candidate=candidate,failed_sources=failed)
    atomic_json(Path(root)/'reference_refresh.json',report.model_dump(mode='json'))
    return report


def read_reference_report(root):
    try:
        with (Path(root)/'reference_refresh.json').open('rb') as stream:payload=stream.read(65537)
        if len(payload)>65536:return None
        return ReferenceRefreshReport.model_validate(strict_json(payload))
    except (OSError,ValueError,TypeError):return None
