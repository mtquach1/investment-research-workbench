"""Bounded installed-issuer SEC refresh with explicit observation-vs-retrieval dates."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from decimal import Decimal
import time
from typing import Literal
from pydantic import Field
from data_pipeline import Contract, load_release, read_table, build_release
from market_data import fetch_source, SourceDownloadError
from market_sources import companyfacts_cik
from issuer_mapping import ticker_issuer_index
from source_policy import policy_for


class FundamentalObservation(Contract):
    source_id: str
    cik: int
    company: str
    retrieved_at: datetime
    source_sha256: str
    annual_period_end: date | None = None
    share_status: str
    share_measured_on: date | None = None
    share_filed_on: date | None = None
    share_accession: str | None = None
    reported_shares: Decimal | None = None
    share_scope: Literal['entity_wide_report_not_complete_class_ledger']='entity_wide_report_not_complete_class_ledger'


class FundamentalPlan(Contract):
    model_version: Literal['installed-sec-refresh-plan-v1']='installed-sec-refresh-plan-v1'
    previous_release_id: str
    directory_sha256: str
    as_of: date
    checked_at: datetime
    observations: list[FundamentalObservation] = Field(min_length=1,max_length=100)


class FundamentalChange(Contract):
    before: FundamentalObservation
    after: FundamentalObservation
    source_refetched: bool
    source_bytes_changed: bool
    annual_period_changed: bool
    share_evidence_changed: bool
    retained_after_failure: bool


class FundamentalRefreshResult(Contract):
    model_version: Literal['installed-sec-refresh-v1']='installed-sec-refresh-v1'
    status: Literal['refreshed','degraded']
    previous_release_id: str
    published_release_id: str
    as_of: date
    source_count: int
    refetched_sources: int
    failed_sources: list[str]
    budget_exhausted: bool
    changes: list[FundamentalChange]
    strict_recommendations_enabled: Literal[False]=False
    automatic_schedule_enabled: Literal[False]=False
    notice: str='SEC source retrieval and reported observation dates are separate. Re-downloading unchanged bytes does not make old shares or annual accounts current. Refreshed shares do not establish class coverage, intervening issuance/repurchases or verified issuer valuation. Failed sources retain visible earlier evidence.'


def _observation(key,reference,row):
    share=row.get('share_reference',{});evidence=share.get('evidence') or {}
    return FundamentalObservation(source_id=key,cik=row['cik'],company=row['issuer'],
        retrieved_at=reference.retrieved_at,source_sha256=reference.source_sha256,
        annual_period_end=row.get('period_end'),share_status=share.get('status','unavailable'),
        share_measured_on=evidence.get('measured_on'),share_filed_on=evidence.get('filed_on'),
        share_accession=evidence.get('accession'),reported_shares=evidence.get('shares'))


def plan_fundamental_refresh(public_root,*,as_of,now=None):
    now=now or datetime.now(timezone.utc)
    if type(as_of) is not date or now.tzinfo is None or as_of>now.date():raise ValueError('Valid assessment date/aware clock required')
    release,manifest=load_release(public_root)
    if manifest.as_of>as_of:raise ValueError('Cannot move the installed evidence assessment backwards')
    directory=manifest.tables.get('sec_ticker_exchange')
    if (directory is None or not directory.policy['public_display_allowed'] or not policy_for('sec_ticker_exchange').public_display_allowed
        or directory.retrieved_at>now+timedelta(minutes=5) or now-directory.retrieved_at>timedelta(days=7)):
        raise ValueError('A fresh approved current directory is required')
    mappings=ticker_issuer_index(read_table(public_root,directory)['records'])
    supported={next(iter(ciks)) for ciks in mappings.values() if len(ciks)==1}
    observations=[];seen=set()
    for key,reference in sorted(manifest.tables.items()):
        if reference.kind!='annual_financial_sample':continue
        row=read_table(public_root,reference)['records'][0]
        if companyfacts_cik(key)!=row['cik'] or row['cik'] in seen or row['cik'] not in supported:
            raise ValueError('Installed issuer is ambiguous, duplicate or absent from current exact directory')
        if not reference.policy['public_display_allowed'] or not policy_for(key).public_display_allowed:
            raise ValueError('Source use is not approved for the installed financial-data role')
        seen.add(row['cik']);observations.append(_observation(key,reference,row))
    return FundamentalPlan(previous_release_id=release,directory_sha256=directory.source_sha256,
        as_of=as_of,checked_at=now,observations=observations)


def refresh_fundamentals(cache_root,public_root,*,as_of,now=None,fetch=fetch_source,progress=None,
                         clock=time.monotonic,budget_seconds=600):
    if isinstance(budget_seconds,bool) or not 1<=budget_seconds<=900:raise ValueError('Use a bounded one-to-900-second transport budget')
    now=now or datetime.now(timezone.utc)
    plan=plan_fundamental_refresh(public_root,as_of=as_of,now=now)
    started=clock();exhausted=False
    def bounded_fetch(source,*args,**kwargs):
        nonlocal exhausted
        if clock()-started>=budget_seconds:
            exhausted=True
            raise SourceDownloadError('Cohort transport budget exhausted; previous source retained')
        return fetch(source,*args,**kwargs)
    release,manifest=build_release(cache_root,public_root,as_of=as_of,now=now,
        source_ids=[item.source_id for item in plan.observations],download=True,force_refresh=True,
        expected_directory_sha=plan.directory_sha256,expected_release_id=plan.previous_release_id,
        fetch=bounded_fetch,progress=progress,
        receipt_clock=lambda:now+timedelta(seconds=max(0,clock()-started)))
    changes=[];failed=[]
    for before in plan.observations:
        reference=manifest.tables[before.source_id]
        after=_observation(before.source_id,reference,read_table(public_root,reference)['records'][0])
        failure=before.source_id in manifest.failures
        if failure:failed.append(before.source_id)
        changes.append(FundamentalChange(before=before,after=after,
            source_refetched=not failure and after.retrieved_at>=now,
            source_bytes_changed=before.source_sha256!=after.source_sha256,
            annual_period_changed=before.annual_period_end!=after.annual_period_end,
            share_evidence_changed=(before.share_measured_on,before.share_filed_on,before.share_accession,before.share_status,before.reported_shares)!=(after.share_measured_on,after.share_filed_on,after.share_accession,after.share_status,after.reported_shares),
            retained_after_failure=failure))
    return FundamentalRefreshResult(status='degraded' if failed else 'refreshed',previous_release_id=plan.previous_release_id,
        published_release_id=release,as_of=as_of,source_count=len(changes),
        refetched_sources=sum(item.source_refetched for item in changes),failed_sources=failed,budget_exhausted=exhausted,changes=changes)
