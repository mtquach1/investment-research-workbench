"""Sourced issuer research over verified releases; no network or stock picking."""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import Field

from data_pipeline import Contract, load_release, read_table
from issuer_mapping import ticker_issuer_index
from source_policy import policy_for
from market_sources import companyfacts_cik
from company_strategy import CompanyStrategyEvidence, explain_company_strategy


class CompanyEntry(Contract):
    issuer_key: str
    issuer_id: str
    name: str
    cik: int
    tickers: list[str]
    ticker_mapping: Literal["matched_sec_directory", "not_available"]
    period_end: str | None
    source_as_of: str
    financials_available: bool = True


class CompanyDirectory(Contract):
    status: Literal["available", "unavailable", "integrity_error"]
    entries: list[CompanyEntry] = Field(default_factory=list)
    notice: str


class ResearchFact(Contract):
    value: Decimal
    unit: str
    tag: str
    filed: str
    accession: str
    inputs: list[str] = Field(default_factory=list)


class ResearchYear(Contract):
    period_start: str | None
    period_end: str | None
    accession: str | None
    facts: dict[str, ResearchFact]
    metrics: dict[str, Decimal | None]
    metric_status: dict[str, str]
    issues: list[str]


class CompanyResearch(Contract):
    status: Literal["available", "unavailable", "integrity_error", "display_not_cleared"]
    company: CompanyEntry | None = None
    latest: ResearchYear | None = None
    history: list[ResearchYear] = Field(default_factory=list)
    strategy_evidence: CompanyStrategyEvidence | None = None
    source_url: str | None = None
    source_sha256: str | None = None
    release_id: str | None = None
    retrieved_at: str | None = None
    source_as_of: str | None = None
    financial_period_age_days: int | None = None
    current_strategy_period_gate_passed: bool = False
    live_recommendations_enabled: Literal[False] = False
    notice: str


def _read(root, today):
    # Verify the manifest here; read_table verifies each consumed artifact.
    # A single-company view must not re-read every unrelated listing/rental file.
    digest, manifest = load_release(root,verify_tables=False)
    if manifest.as_of > today:
        raise ValueError("Future research release")
    return digest, manifest


def _symbols(root, manifest):
    symbols = defaultdict(set)
    reference = manifest.tables.get("sec_ticker_exchange")
    if reference and reference.policy["public_display_allowed"] and policy_for("sec_ticker_exchange").public_display_allowed:
        mapping = read_table(root, reference)
        for ticker, ciks in ticker_issuer_index(mapping["records"]).items():
            if len(ciks) == 1:
                symbols[next(iter(ciks))].add(ticker)
    return symbols


def _entry(manifest, source_id, row, symbols_by_issuer):
    symbols = symbols_by_issuer.get(row["cik"], set())
    return CompanyEntry(issuer_key=source_id.removeprefix("sec_companyfacts_"),
        issuer_id=row["issuer_id"], name=row["issuer"], cik=row["cik"], tickers=sorted(symbols),
        ticker_mapping="matched_sec_directory" if symbols else "not_available",
        period_end=row["period_end"], source_as_of=manifest.tables[source_id].table_as_of.isoformat())


def company_directory(root, *, today=None):
    today = today or datetime.now(timezone.utc).date()
    try:
        _, manifest = _read(root, today)
        entries = []
        symbols = _symbols(root, manifest)
        for source_id, reference in sorted(manifest.tables.items()):
            if (reference.kind == "annual_financial_sample" and reference.policy["public_display_allowed"]
                    and policy_for(source_id).public_display_allowed):
                entries.append(_entry(manifest, source_id, read_table(root, reference)["records"][0], symbols))
        covered={entry.cik for entry in entries}
        for source_id,reference in sorted(manifest.tables.items()):
            if (reference.kind=="issuer_filing_events" and reference.policy["public_display_allowed"]
                    and policy_for(source_id).public_display_allowed):
                row=read_table(root,reference)["records"][0]
                if row["cik"] not in covered:
                    entries.append(CompanyEntry(issuer_key=f"cik{row['cik']:010d}",issuer_id=f"sec:{row['cik']:010d}",
                        name=row.get("issuer_name",f"SEC issuer {row['cik']}"),cik=row["cik"],
                        tickers=sorted(symbols.get(row["cik"],set())),ticker_mapping="matched_sec_directory" if symbols.get(row["cik"]) else "not_available",
                        period_end=None,source_as_of=reference.table_as_of.isoformat(),financials_available=False))
                    covered.add(row["cik"])
        return CompanyDirectory(status="available" if entries else "unavailable", entries=entries,
            notice="Supported cached issuers, not a complete stock universe. Current ticker associations do not establish S&P membership.")
    except FileNotFoundError:
        return CompanyDirectory(status="unavailable", notice="No verified research release is installed.")
    except (ValueError, OSError, KeyError, TypeError):
        return CompanyDirectory(status="integrity_error", notice="Company research could not be verified.")


def _year(row):
    return ResearchYear(period_start=row["period_start"], period_end=row["period_end"],
        accession=row["accession"], facts={name: ResearchFact(**{key: fact[key]
            for key in ("value", "unit", "tag", "filed", "accession", "inputs")}) for name, fact in row["facts"].items()},
        metrics=row["metrics"], metric_status=row["metric_status"], issues=row["issues"])


def company_research(root, issuer_key, *, today=None):
    # Route keys select installed snapshots; serving never performs a download.
    try:
        companyfacts_cik("sec_companyfacts_"+issuer_key)
    except (ValueError,TypeError):
        return CompanyResearch(status="unavailable", notice="This issuer has no supported financial snapshot yet.")
    today = today or datetime.now(timezone.utc).date()
    try:
        digest, manifest = _read(root, today)
        source_id = "sec_companyfacts_" + issuer_key
        reference = manifest.tables.get(source_id)
        if reference is None:
            return CompanyResearch(status="unavailable", notice="This issuer's financial snapshot is unavailable.")
        if not reference.policy["public_display_allowed"] or not policy_for(source_id).public_display_allowed:
            return CompanyResearch(status="display_not_cleared", notice="This release's source policy does not permit displaying the financial data.")
        row = read_table(root, reference)["records"][0]
        age = (today-date.fromisoformat(row["period_end"])).days if row["period_end"] else None
        latest=_year(row)
        return CompanyResearch(status="available", company=_entry(manifest, source_id, row, _symbols(root, manifest)),
            latest=latest, history=[_year(item) for item in row.get("annual_history", [])],
            strategy_evidence=explain_company_strategy(latest,as_of=today),
            source_url=reference.source_url, source_sha256=reference.source_sha256, release_id=digest,
            retrieved_at=reference.retrieved_at.isoformat(), source_as_of=reference.table_as_of.isoformat(),
            financial_period_age_days=age, current_strategy_period_gate_passed=age is not None and 0 <= age <= 550,
            notice="Reported annual financials from cached SEC filings. History may reflect later restatements. No current price, valuation, historical investment return or purchase recommendation is inferred.")
    except FileNotFoundError:
        return CompanyResearch(status="unavailable", notice="No verified research release is installed.")
    except (ValueError, OSError, KeyError, TypeError):
        return CompanyResearch(status="integrity_error", notice="The company snapshot could not be verified.")
