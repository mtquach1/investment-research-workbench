"""Bounded operator import plans from the verified SEC issuer directory.

Planning and serving never download. Execution uses the existing transactional
pipeline, with immutable source URLs derived exclusively from validated CIKs.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import re

from pydantic import Field

from data_pipeline import Contract, build_release, load_release, read_table
from issuer_mapping import ticker_issuer_index
from market_sources import source_for_id
from source_policy import policy_for


class ImportIssuer(Contract):
    cik: int
    issuer_name: str
    requested_tickers: list[str]
    source_id: str
    already_published: bool


class SecImportPlan(Contract):
    plan_version: str = "sec-directory-import-v1"
    directory_sha256: str
    directory_retrieved_at: str
    issuers: list[ImportIssuer]
    new_issuer_count: int = Field(ge=0,le=25)
    notice: str = "Issuer financial statements only. Current ticker matching does not verify index membership or share-class suitability."


def plan_sec_import(root, tickers, *, now=None, maximum_new_issuers=25):
    if type(maximum_new_issuers) is not int or not 1<=maximum_new_issuers<=25:
        raise ValueError("Import batches are bounded to at most 25 new issuers")
    if not isinstance(tickers,(list,tuple)) or not 1<=len(tickers)<=50:
        raise ValueError("Choose one through fifty ticker inputs per plan")
    symbols=[]
    for value in tickers:
        if not isinstance(value,str):
            raise ValueError("Ticker inputs must be strings")
        symbol=value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,19}",symbol):
            raise ValueError("Ticker format is unsupported; aliases are not guessed")
        if symbol not in symbols:
            symbols.append(symbol)
    _,manifest=load_release(root)
    directory=manifest.tables.get("sec_ticker_exchange")
    if (directory is None or not directory.policy["public_display_allowed"]
            or not policy_for("sec_ticker_exchange").public_display_allowed):
        raise ValueError("An approved verified SEC directory is required")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None or directory.retrieved_at>now+timedelta(minutes=5) or now-directory.retrieved_at>timedelta(days=7):
        raise ValueError("Refresh the SEC directory before expanding issuer coverage")
    records=read_table(root,directory)["records"]
    index=ticker_issuer_index(records)
    wanted=defaultdict(list)
    for symbol in symbols:
        candidates=index.get(symbol,set())
        if len(candidates)!=1:
            raise ValueError("A requested ticker is missing or maps to multiple issuers; no import was started")
        wanted[next(iter(candidates))].append(symbol)
    existing={}
    for source_id,reference in sorted(manifest.tables.items()):
        if reference.kind=="annual_financial_sample":
            row=read_table(root,reference)["records"][0]
            if row["cik"] in existing:
                raise ValueError("Published issuer coverage contains duplicate CIKs")
            existing[row["cik"]]=source_id
    names={row["cik"]:row["name"] for row in records}
    rows=[]
    for cik,symbols in sorted(wanted.items()):
        source_id=existing.get(cik,f"sec_companyfacts_cik{cik:010d}")
        source_for_id(source_id)
        rows.append(ImportIssuer(cik=cik,issuer_name=names[cik],requested_tickers=sorted(symbols),
            source_id=source_id,already_published=cik in existing))
    new=sum(not row.already_published for row in rows)
    if new>maximum_new_issuers:
        raise ValueError("Plan exceeds the new-issuer batch limit; no import was started")
    return SecImportPlan(directory_sha256=directory.source_sha256,
        directory_retrieved_at=directory.retrieved_at.isoformat(),issuers=rows,new_issuer_count=new)


def execute_sec_import(cache_root, root, tickers, *, as_of, now=None, maximum_new_issuers=25):
    # Re-plan immediately before execution; a saved plan is not authority to use
    # a changed/stale mapping. Every request still revalidates its registered CIK.
    plan=plan_sec_import(root,tickers,now=now,maximum_new_issuers=maximum_new_issuers)
    digest,manifest=build_release(cache_root,root,as_of=as_of,download=True,now=now,
        source_ids=[row.source_id for row in plan.issuers],expected_directory_sha=plan.directory_sha256)
    return plan,digest,manifest
