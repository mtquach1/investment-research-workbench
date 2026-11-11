"""Read-only public coverage summaries; no provider quotes or financial inputs."""

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field

from data_pipeline import Contract, load_release
from market_sources import source_for_id
from source_policy import policy_for


class CoverageItem(Contract):
    label: str
    count: int = Field(ge=0)
    denominator: int | None = Field(default=None,gt=0)
    unit: str
    status: Literal["available","partial","unverified","incompatible","unavailable","stale"]
    explanation: str


class DomainCoverage(Contract):
    ready: Literal[False] = False
    items: list[CoverageItem]
    blockers: list[str]


class DataReadiness(Contract):
    schema_version: Literal["data-readiness-v1"] = "data-readiness-v1"
    status: Literal["partial","unavailable","integrity_error"]
    release_id: str | None = None
    normalized_as_of: str | None = None
    checked_on: str
    sources: list[dict] = Field(default_factory=list)
    stocks: DomainCoverage
    rentals: DomainCoverage
    notice: str


STOCK_BLOCKERS=["Verify dated S&P 500 membership and security-to-issuer mappings.",
    "Obtain full-universe financials, valuation inputs, adjusted price history and a matched total-return benchmark.",
    "Complete source-specific access and public display review before enabling live recommendations."]
RENTAL_BLOCKERS=["Resolve current ZIP/address membership; the current geography is a dated 2020 ZCTA land-overlap set.",
    "Obtain suitable single-family rental evidence. Mixed-home ZIP rents and metro rents cannot stand in for property rent.",
    "Finish source display review and verify any HUD benchmark rows; HUD gross-rent benchmarks are not achievable single-family rents."]


def load_catalog(root="data_cache/published", *, today=None):
    checked_at=datetime.now(timezone.utc) if today is None else datetime.combine(today,datetime.min.time(),tzinfo=timezone.utc)
    today=checked_at.date()
    sources=[]
    try:
        digest,manifest=load_release(Path(root))
        if manifest.as_of>today:
            raise ValueError("Future release")
    except FileNotFoundError:
        return _empty(today,"unavailable","No verified public-data release is installed. The learning tools still work with manual and synthetic inputs.")
    except (OSError,ValueError):
        return _empty(today,"integrity_error","The public-data release could not be verified. Live data is withheld; manual and synthetic tools remain available.")
    for source_id,reference in sorted(manifest.tables.items()):
        observed=reference.observation_date
        limit=reference.policy["observation_max_age_days"]
        observation_status=("unknown_or_fixed_vintage" if observed is None or limit is None else
                            "stale" if (today-observed).days>limit else "within_research_age_limit")
        sources.append({"source_id":source_id,"provider":reference.policy["provider"],
            "observation_date":observed.isoformat() if observed else None,
            "observation_status":observation_status,"retrieved_at":reference.retrieved_at.isoformat(),
            "rows":reference.row_count,"state":reference.state,
            "refresh_due":(checked_at-reference.retrieved_at).total_seconds()>=reference.policy["refresh_hours"]*3600,
            "public_display_allowed":reference.policy["public_display_allowed"],
            "rights_status":reference.policy["rights_status"],
            "source_url":reference.source_url,"documentation_url":reference.policy["documentation_url"],
            "source_sha256":reference.source_sha256,"table_as_of":reference.table_as_of.isoformat()})
    for source_id,failure in sorted(manifest.failures.items()):
        if source_id not in manifest.tables:
            policy=policy_for(source_id)
            sources.append({"source_id":source_id,"provider":policy.provider,
                            "documentation_url":policy.documentation_url,"source_url":source_for_id(source_id).url,
                            "rights_status":policy.rights_status,"state":"unavailable","failure_code":failure.code,
                            "http_status":failure.http_status,"failure_observed_at":failure.observed_at.isoformat() if failure.observed_at else None,"public_display_allowed":False})
        else:
            next(row for row in sources if row["source_id"]==source_id).update(
                failure_code=failure.code,http_status=failure.http_status,
                failure_observed_at=failure.observed_at.isoformat() if failure.observed_at else None)
    tables=manifest.tables
    summary=lambda name:tables[name].summary if name in tables else {}
    proxy=summary("ivv_holdings_proxy").get("equity_security_rows",0)
    financials=[ref for ref in tables.values() if ref.kind=="annual_financial_sample"]
    complete=sum(ref.summary["complete_issuers"] for ref in financials)
    bars=summary("alphavantage_ibm_daily_demo").get("observations",0)
    geography=summary("census_zcta_county_2020")
    candidates=geography.get("candidate_count",0)
    price=summary("zillow_sfr_value_zip")
    mixed=summary("zillow_mixed_rent_zip")
    candidates_set=set(geography.get("candidate_ids",[]))
    price_dates=price.get("latest_by_entity",{})
    fresh=sum(value is not None and 0<=(today-date.fromisoformat(value)).days<=90
              for entity,value in price_dates.items() if entity in candidates_set)
    stocks=DomainCoverage(items=[
        CoverageItem(label="Fund holdings proxy",count=proxy,unit="securities",status="unverified" if proxy else "unavailable",
            explanation="A dated ETF holdings sample; not verified S&P 500 membership."),
        CoverageItem(label="Complete annual samples",count=complete,denominator=len(financials) or None,unit="sample issuers",status="partial" if financials else "unavailable",
            explanation="Annual disclosure normalization only. This is not coverage of the full stock universe or live valuation."),
        CoverageItem(label="Adjusted daily sample",count=bars,unit="observations for one demo stock",status="partial" if bars else "unavailable",
            explanation="One provider demo. A 100-bar sample does not meet the strategy's 756-observation history requirement."),
        CoverageItem(label="Verified benchmark history",count=0,unit="series",status="unavailable",
            explanation="No matched total-return benchmark has been ingested.")],blockers=STOCK_BLOCKERS)
    rentals=DomainCoverage(items=[
        CoverageItem(label="Dated geographic candidates",count=candidates,unit="2020 ZCTAs",status="partial" if candidates else "unavailable",
            explanation=f"Positive land overlap with Orange County; {geography.get('shared_county_count',0)} cross county boundaries. Not current USPS ZIP membership."),
        CoverageItem(label="Single-family value context",count=fresh,denominator=candidates or None,unit="series within 90-day observation limit",status="unverified" if price and not candidates else "partial" if fresh else "stale" if price else "unavailable",
            explanation=f"{price.get('series_count',0)} observed series total. Area values are not property appraisals; unknown publication dates prevent point-in-time claims."),
        CoverageItem(label="Mixed-home ZIP rent context",count=mixed.get("series_count",0),unit="series",status="incompatible" if mixed else "unavailable",
            explanation="A different housing category. Excluded from single-family cash-flow screening."),
        CoverageItem(label="Verified single-family ZIP rent",count=0,unit="series",status="unavailable",
            explanation="Manual supported property rent is still required. HUD benchmark access did not provide verified data.")],blockers=RENTAL_BLOCKERS)
    return DataReadiness(status="partial",release_id=digest,normalized_as_of=manifest.as_of.isoformat(),
        checked_on=today.isoformat(),sources=sources,stocks=stocks,rentals=rentals,
        notice="Coverage describes audited research samples and context. It does not enable live recommendations or establish county/index completeness.")


def _empty(today,status,notice):
    return DataReadiness(status=status,checked_on=today.isoformat(),notice=notice,
        stocks=DomainCoverage(items=[],blockers=STOCK_BLOCKERS),
        rentals=DomainCoverage(items=[],blockers=RENTAL_BLOCKERS))
