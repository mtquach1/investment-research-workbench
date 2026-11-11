"""Offline issuer event context; no sentiment score or price-causality inference."""

from datetime import date, datetime, timedelta, timezone
import hashlib
from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator

from company_research import company_directory
from data_pipeline import Contract, load_release, read_table
from public_data_store import strict_json
from source_policy import policy_for


CATALOG=Path(__file__).parent/"data/company_event_context.json"
OFFICIAL_HOSTS={2488:"ir.amd.com",2023554:"investor.sandisk.com"}


class ReviewedEvent(Contract):
    event_id: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    cik: int = Field(gt=0,strict=True)
    kind: Literal["announcement","earnings_call"]
    published_on: date
    reviewed_on: date
    scheduled_at: datetime | None
    headline: str = Field(min_length=1,max_length=200)
    fact: str = Field(min_length=1,max_length=500)
    considerations: str = Field(min_length=1,max_length=600)
    source_url: str

    @model_validator(mode="after")
    def official_identity(self):
        url=urlparse(self.source_url)
        if (url.scheme!="https" or url.hostname!=OFFICIAL_HOSTS.get(self.cik) or url.username
                or url.password or url.port or url.fragment or url.query):
            raise ValueError("Event source must be the registered official issuer site")
        if self.reviewed_on<self.published_on:raise ValueError("Review precedes publication")
        if self.kind=="earnings_call" and (self.scheduled_at is None or self.scheduled_at.tzinfo is None):
            raise ValueError("Earnings call requires a timezone-aware scheduled time")
        if self.scheduled_at is not None and self.scheduled_at.tzinfo is None:raise ValueError("Timezone required")
        if self.scheduled_at is not None and self.scheduled_at.date()<self.published_on:raise ValueError("Schedule precedes announcement")
        return self


class ContextEvent(ReviewedEvent):
    schedule_status: Literal["announced","upcoming","scheduled_time_passed_outcome_unverified"]
    review_stale: bool


class FilingEvent(Contract):
    record_id: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    cik: int = Field(gt=0,strict=True)
    form: str
    filed_on: date
    items: list[str]
    topics: list[str]
    headline: str
    source_url: str

    @model_validator(mode="after")
    def safe_filing_link(self):
        prefix=f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{self.record_id.replace('-','')}/"
        if not self.source_url.startswith(prefix):raise ValueError("Unexpected filing destination")
        filename=self.source_url.removeprefix(prefix)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}\.html?",filename) or ".." in filename:
            raise ValueError("Unsafe filing link")
        return self


class CompanyEvents(Contract):
    status: Literal["available","unavailable","integrity_error"]
    issuer_key: str
    cik: int | None = None
    checked_at: datetime
    events: list[ContextEvent] = Field(default_factory=list)
    filings: list[FilingEvent] = Field(default_factory=list)
    filings_retrieved_at: datetime | None = None
    filings_refresh_due: bool = False
    filings_refresh_failed: bool = False
    filing_source_sha256: str | None = None
    release_id: str | None = None
    context_catalog_sha256: str | None = None
    context_catalog_status: Literal["reviewed_limited","unavailable"] = "unavailable"
    complete_news_coverage: Literal[False] = False
    affects_strategy_score: Literal[False] = False
    notice: str


def load_reviewed_events(path=CATALOG):
    payload=Path(path).read_bytes()
    if len(payload)>65536:raise ValueError("Oversized event catalog")
    data=strict_json(payload)
    if set(data)!={"version","events"} or data["version"]!="reviewed-company-events-v1" or not isinstance(data["events"],list) or len(data["events"])>100:
        raise ValueError("Invalid event catalog")
    events=[ReviewedEvent.model_validate(row) for row in data["events"]]
    if len({row.event_id for row in events})!=len(events):raise ValueError("Duplicate event IDs")
    return events,hashlib.sha256(payload).hexdigest()


def company_events(root,issuer_key,*,now=None,catalog_path=CATALOG):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("Timezone-aware assessment clock required")
    base=dict(issuer_key=issuer_key,checked_at=now,
        notice="Limited official-source context, not a complete news feed. Filing dates are not event occurrence dates. No sentiment score, price forecast or causal price explanation is inferred.")
    try:
        directory=company_directory(root,today=now.date())
        if directory.status=="integrity_error":return CompanyEvents(status="integrity_error",**base)
        entry=next((row for row in directory.entries if row.issuer_key==issuer_key),None)
        if entry is None:return CompanyEvents(status="unavailable",**base)
        digest,manifest=load_release(root)
        key=f"sec_submissions_cik{entry.cik:010d}"
        reference=manifest.tables.get(key)
        filings=[]; metadata={"filings_refresh_failed":key in manifest.failures}
        if reference and reference.policy["public_display_allowed"] and policy_for(key).public_display_allowed:
            row=read_table(root,reference)["records"][0]
            if row["cik"]!=entry.cik:raise ValueError("Wrong event issuer")
            filings=[FilingEvent.model_validate(item) for item in row["filings"] if date.fromisoformat(item["filed_on"])<=now.date()][:100]
            if any(item.cik!=entry.cik for item in filings):raise ValueError("Wrong filing issuer")
            metadata=dict(filings_retrieved_at=reference.retrieved_at,
                filings_refresh_due=now-reference.retrieved_at>timedelta(hours=24),
                filing_source_sha256=reference.source_sha256,filings_refresh_failed=key in manifest.failures)
        context=[]; context_hash=None; context_status="unavailable"
        try:
            reviewed,context_hash=load_reviewed_events(catalog_path)
            context_status="reviewed_limited"
            for event in reviewed:
                if event.cik!=entry.cik or event.published_on>now.date() or event.reviewed_on>now.date():continue
                status="announced" if event.scheduled_at is None else "upcoming" if event.scheduled_at>now else "scheduled_time_passed_outcome_unverified"
                context.append(ContextEvent(**event.model_dump(),schedule_status=status,
                    review_stale=(now.date()-event.reviewed_on).days>7))
            context.sort(key=lambda item:(item.published_on,item.event_id),reverse=True)
        except (OSError,ValueError,TypeError,KeyError):
            pass  # A broken editorial catalog never invents or erases verified filings.
        return CompanyEvents(status="available",cik=entry.cik,release_id=digest,events=context,filings=filings,
            context_catalog_sha256=context_hash,context_catalog_status=context_status,**metadata,**base)
    except (OSError,ValueError,KeyError,TypeError):
        return CompanyEvents(status="integrity_error",**base)
