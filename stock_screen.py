"""Real-data research eligibility. Provisional inputs never become live scores."""

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field,model_validator
from company_research import _year
from company_strategy import explain_company_strategy
from data_pipeline import Contract, load_release, read_table
from issuer_mapping import ticker_issuer_index
from market_history import load_history, series_risk
from source_policy import policy_for
from stock_strategy import SPEC,SPEC_HASH
from stock_metrics import Metric,screen_metrics,CANONICAL_SECTORS
from security_listing import ListingEvidence,LISTING_SOURCES,listing_index,corroborate_listing,listing_reference_fresh
from security_identity import FilingClassEvidence,corroborate_filing_class
from class_share_ledger import ClassShareLedger,build_class_share_ledger
from class_quantity_review import load_quantity_reviews

SECTOR_LABELS={name:name for name in CANONICAL_SECTORS}
SECTOR_LABELS["Communication"]="Communication Services"


class UniverseEvidence(Contract):
    sector_mapping_version: Literal["ishares-sector-labels-v1"] = "ishares-sector-labels-v1"
    basis: Literal["dated_fund_holdings_proxy"] = "dated_fund_holdings_proxy"
    observed_on: date | None = None
    source_sha256: str | None = None
    securities: int = 0
    uniquely_mapped_securities: int = 0
    fresh: bool = False
    official_index_membership_verified: Literal[False] = False


class ValuationEstimate(Contract):
    method_version: Literal["reported-shares-split-estimate-v1"] = "reported-shares-split-estimate-v1"
    currency: Literal["USD"] = "USD"
    status: Literal["estimated","unavailable","ambiguous","stale","multiple_securities","split_evidence_missing"]
    measured_on: date | None = None
    filed_on: date | None = None
    accession: str | None = None
    reported_shares: Decimal | None = None
    split_factor: Decimal | None = None
    split_reference_on: date | None = None
    shares_at_price_date_estimate: Decimal | None = None
    price_date: date | None = None
    raw_price: Decimal | None = None
    market_cap_estimate: Decimal | None = None
    annual_earnings_yield_estimate: Decimal | None = None
    annual_fcf_yield_estimate: Decimal | None = None
    annual_pe_estimate: Decimal | None = None
    verified_current_market_cap: Literal[False] = False
    reason: str

    @model_validator(mode="after")
    def coherent_estimate(self):
        if self.status=="estimated":
            values=(self.reported_shares,self.split_factor,self.shares_at_price_date_estimate,self.raw_price,self.market_cap_estimate)
            if any(value is None or not value.is_finite() or value<=0 for value in values):
                raise ValueError("Estimated valuation requires positive input evidence")
            if not self.measured_on or not self.filed_on or not self.price_date or not self.accession:
                raise ValueError("Estimated valuation requires dated filing evidence")
            if not self.measured_on<=self.filed_on<=self.price_date or self.market_cap_estimate!=self.raw_price*self.shares_at_price_date_estimate:
                raise ValueError("Estimated valuation inputs do not reconcile")
        return self


def estimate_valuation(row,series,tickers,*,today):
    ref=row.get("share_reference",{})
    evidence=ref.get("evidence")
    if ref.get("status")=="ambiguous":return ValuationEstimate(status="ambiguous",reason="Conflicting latest reported share counts.")
    if not evidence or series is None:return ValuationEstimate(status="unavailable",reason="Reported point share count or matched price history is unavailable.")
    measured,filed=date.fromisoformat(evidence["measured_on"]),date.fromisoformat(evidence["filed_on"])
    shares=Decimal(evidence["shares"])
    if not shares.is_finite() or not 0<shares<=Decimal("1e15") or filed<measured:raise ValueError("Invalid share evidence")
    latest=series.bars[-1]
    base=dict(measured_on=measured,filed_on=filed,accession=evidence["accession"],reported_shares=shares,
              price_date=latest.day,raw_price=latest.raw_close)
    if len(tickers)!=1:return ValuationEstimate(status="multiple_securities",reason="Multiple directory securities: one quote cannot establish issuer-wide equity value.",**base)
    if latest.day>today or filed>latest.day or measured>latest.day:
        return ValuationEstimate(status="unavailable",reason="Shares must be reported and measured by the price date.",**base)
    if (latest.day-measured).days>120 or (today-latest.day).days>7:
        return ValuationEstimate(status="stale",reason="Share observation exceeds 120 days or price exceeds seven days.",**base)
    previous=[bar for bar in series.bars if bar.day<=measured]
    if not previous or (measured-previous[-1].day).days>7:
        return ValuationEstimate(status="split_evidence_missing",reason="No nearby price observation at the share measurement date.",**base)
    anchor=previous[-1]
    if anchor.split_adjusted_close is None or latest.split_adjusted_close is None:
        return ValuationEstimate(status="split_evidence_missing",reason="Split-only adjustment evidence is required; dividend-adjusted ratios cannot substitute.",**base)
    factor=(anchor.raw_close/anchor.split_adjusted_close)/(latest.raw_close/latest.split_adjusted_close)
    adjusted_shares=shares*factor; cap=adjusted_shares*latest.raw_close
    def fact(name):return Decimal(str(row["facts"][name]["value"])) if name in row["facts"] else None
    earnings,fcf=fact("net_income"),fact("free_cashflow")
    return ValuationEstimate(status="estimated",split_factor=factor,split_reference_on=anchor.day,shares_at_price_date_estimate=adjusted_shares,
        market_cap_estimate=cap,annual_earnings_yield_estimate=earnings/cap if earnings is not None else None,
        annual_fcf_yield_estimate=fcf/cap if fcf is not None else None,
        annual_pe_estimate=cap/earnings if earnings is not None and earnings>0 else None,
        reason="Filing-based estimate, not verified current market cap. Repurchases, issuance, class coverage and other corporate actions may change it. Numerators use reported annual financials, not TTM.",**base)


class ScreenRow(Contract):
    issuer_key: str
    cik: int
    company: str
    financial_period: date | None = None
    financial_source_retrieved_at: datetime | None = None
    tickers: list[str]
    sector: str | None
    provider_sector: str | None = None
    proxy_member: bool
    financial_status: Literal["pass","fail","unavailable"]
    financial_reasons: list[str]
    financial_missing_reasons: list[str] = Field(default_factory=list)
    financial_evidence_reasons: list[str] = Field(default_factory=list)
    sector_status: Literal["pass","fail","unavailable"]
    price_status: Literal["pass","fail","unavailable"]
    history_count_status: Literal["pass","fail","unavailable"]
    eligible_financial_sector_peers: int = 0
    valuation: ValuationEstimate
    metrics: dict[str,Metric] = Field(default_factory=dict)
    listing_evidence: dict[str,ListingEvidence] = Field(default_factory=dict)
    filing_class_evidence: dict[str,FilingClassEvidence] = Field(default_factory=dict)
    class_share_ledger: ClassShareLedger | None = None
    score: None = None
    selected: Literal[False] = False


class SecurityCoverage(Contract):
    symbol: str
    provider_sector: str
    mapping_status: Literal['exact_issuer_match','unresolved','ambiguous']
    cik: int | None = None
    financials_installed: bool
    exact_symbol_history_installed: bool
    current_valuation_verified: Literal[False] = False
    official_membership_verified: Literal[False] = False
    security_identity_verified: Literal[False] = False
    listing: ListingEvidence = Field(default_factory=ListingEvidence)


class StockScreen(Contract):
    metrics_version: Literal['stock-research-metrics-v1'] = 'stock-research-metrics-v1'
    status: Literal["available","withheld","unavailable","integrity_error"]
    checked_on: date
    public_release_id: str | None = None
    market_snapshot_sha256: str | None = None
    strategy_id: str = SPEC["strategy_id"]
    strategy_sha256: str = SPEC_HASH
    universe: UniverseEvidence = Field(default_factory=UniverseEvidence)
    rows: list[ScreenRow] = Field(default_factory=list)
    security_coverage: list[SecurityCoverage] = Field(default_factory=list)
    listing_reference_hashes: dict[str,str] = Field(default_factory=dict)
    selection_status: Literal["blocked_by_unverified_inputs"] = "blocked_by_unverified_inputs"
    live_recommendations_enabled: Literal[False] = False
    blockers: list[str] = Field(default_factory=lambda:[
        "Official dated index membership and security/share-class identity remain unverified.",
        "Filing-based market-cap estimates do not satisfy the strategy's verified valuation requirement.",
        "IEX adjusted-price research does not establish consolidated exact total-return coverage.",
        "A limited installed sample is not the full eligible universe or outperformance evidence."])


def stock_screen(public_root,history_root,*,mode="withheld",today=None):
    today=today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    if mode!="local_research":return StockScreen(status="withheld",checked_on=today)
    try:
        release_id,manifest=load_release(public_root)
        if manifest.as_of>today:raise ValueError("Future public release")
        mapping=manifest.tables.get("sec_ticker_exchange")
        if not mapping or not mapping.policy["public_display_allowed"] or not policy_for("sec_ticker_exchange").public_display_allowed:
            return StockScreen(status="unavailable",checked_on=today)
        directory_rows=read_table(public_root,mapping)['records']
        index=ticker_issuer_index(directory_rows)
        exchanges=defaultdict(set)
        for entry in directory_rows:exchanges[(entry['ticker'],entry['cik'])].add(entry['exchange'])
        listing_tables={source:(manifest.tables[source],read_table(public_root,manifest.tables[source])['records']) for source in LISTING_SOURCES if source in manifest.tables}
        listing_lookup=listing_index(listing_tables)
        class_tables=[];filing_share_tables=[]
        for ref in manifest.tables.values():
            if ref.kind=='filing_security_classes':
                table=read_table(public_root,ref)
                class_tables.append((ref,table['records']))
                filing_share_tables.append((ref,table.get('summary',{}).get('point_share_observations',[])))
        directory_fresh=0<=(today-mapping.retrieved_at.astimezone(ZoneInfo('America/Los_Angeles')).date()).days<=7
        complete_listings=len(listing_tables)==2 and all(listing_reference_fresh(ref,today=today) for ref,_ in listing_tables.values())
        tickers=defaultdict(set)
        for symbol,ciks in index.items():
            if len(ciks)==1:tickers[next(iter(ciks))].add(symbol)
        proxy=manifest.tables.get("ivv_holdings_proxy")
        sectors=defaultdict(set);proxy_issuers=set();evidence=UniverseEvidence();proxy_rows=[]
        if proxy:
            table=read_table(public_root,proxy)
            proxy_rows=table['records']
            matched=0
            for row in table["records"]:
                ciks=index.get(row["ticker"],set())
                if len(ciks)==1:
                    cik=next(iter(ciks));matched+=1;proxy_issuers.add(cik);sectors[cik].add(row["sector"])
            evidence=UniverseEvidence(observed_on=proxy.observation_date,source_sha256=proxy.source_sha256,
                securities=len(table["records"]),uniquely_mapped_securities=matched,
                fresh=proxy.observation_date is not None and 0<=(today-proxy.observation_date).days<=7)
        try:history_id,history=load_history(history_root)
        except FileNotFoundError:history_id,history=None,None
        prices=defaultdict(list)
        if history:
            if history.completed_through>today:raise ValueError("Future market history")
            for series in history.series.values():
                if series.role=="issuer_security":prices[series.cik].append(series)
        rows=[];ledger_inputs={};quantity_reviews=load_quantity_reviews()
        for key,reference in sorted(manifest.tables.items()):
            if reference.kind!="annual_financial_sample" or not reference.policy["public_display_allowed"] or not policy_for(key).public_display_allowed:continue
            raw=read_table(public_root,reference)["records"][0]
            ledger_inputs[raw['cik']]=(raw,reference)
            cik=raw["cik"];year=_year(raw);assessment=explain_company_strategy(year,as_of=today)
            failed=[check.explanation for check in assessment.financial_checks if check.status=="fail"]
            absent=[check.explanation for check in assessment.financial_checks if check.status=="unavailable"]
            normalized_sectors={SECTOR_LABELS.get(label) for label in sectors[cik]}
            sector=next(iter(normalized_sectors)) if len(normalized_sectors)==1 else None
            candidate=prices[cik][0] if len(prices[cik])==1 else None
            # An issuer's formerly associated ticker cannot price a different
            # current security just because its stored CIK matches.
            price=candidate if candidate and candidate.symbol in tickers[cik] else None
            risk=series_risk(price) if price and len(price.bars)>1 else None
            rows.append(ScreenRow(issuer_key=key.removeprefix("sec_companyfacts_"),cik=cik,company=raw["issuer"],financial_period=raw["period_end"],
                financial_source_retrieved_at=reference.retrieved_at,tickers=sorted(tickers[cik]),sector=sector,provider_sector=" / ".join(sorted(sectors[cik])) or None,
                proxy_member=cik in proxy_issuers,financial_status="fail" if failed else "unavailable" if absent else "pass",
                financial_reasons=failed+absent,financial_missing_reasons=absent,
                financial_evidence_reasons=[check.explanation for check in assessment.financial_checks
                    if check.key in ('financial_period_age','filing_evidence') and check.status!='pass'],
                sector_status="unavailable" if sector is None or not evidence.fresh else "fail" if sector in SPEC["excluded_sectors"] else "pass",
                price_status="unavailable" if price is None else "pass" if 0<=(today-price.bars[-1].day).days<=7 else "fail",
                history_count_status="unavailable" if risk is None else "pass" if risk.minimum_history_gate_passed else "fail",
                valuation=estimate_valuation(raw,price,tickers[cik],today=today),
                metrics=screen_metrics(year,raw.get('annual_history',[]),risk,today=today),
                listing_evidence={symbol:corroborate_listing(symbol,exchanges[(symbol,cik)],listing_lookup,today=today,complete_fresh=complete_listings) for symbol in sorted(tickers[cik])}))
        peers=defaultdict(int)
        for row in rows:
            if row.financial_status==row.sector_status=="pass":peers[row.sector]+=1
        for row in rows:row.eligible_financial_sector_peers=peers[row.sector]
        for row in rows:
            row.filing_class_evidence={symbol:corroborate_filing_class(row.cik,symbol,row.listing_evidence.get(symbol),
                class_tables,today=today,directory_fresh=directory_fresh) for symbol in row.tickers}
            raw,reference=ledger_inputs[row.cik]
            row.class_share_ledger=build_class_share_ledger(row.cik,raw,reference,index,mapping,class_tables,
                row.listing_evidence,row.filing_class_evidence,today=today,directory_fresh=directory_fresh,
                filing_share_tables=filing_share_tables,quantity_reviews=quantity_reviews)
        installed={row.cik for row in rows};coverage=[]
        for item in proxy_rows:
            candidates=index.get(item['ticker'],set());cik=next(iter(candidates)) if len(candidates)==1 else None
            exact=history.series.get(item['ticker']) if history else None
            coverage.append(SecurityCoverage(symbol=item['ticker'],provider_sector=item['sector'],
                mapping_status='exact_issuer_match' if cik else 'ambiguous' if candidates else 'unresolved',cik=cik,
                financials_installed=cik in installed,exact_symbol_history_installed=exact is not None and exact.cik==cik,
                listing=corroborate_listing(item['ticker'],exchanges[(item['ticker'],cik)],listing_lookup,today=today,complete_fresh=complete_listings)))
        return StockScreen(status="available",checked_on=today,public_release_id=release_id,market_snapshot_sha256=history_id,universe=evidence,rows=rows,security_coverage=coverage,
            listing_reference_hashes={source:ref.source_sha256 for source,(ref,_) in listing_tables.items()})
    except FileNotFoundError:return StockScreen(status="unavailable",checked_on=today)
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError):return StockScreen(status="integrity_error",checked_on=today)
