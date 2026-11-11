"""Explicit proxy/estimate research variant. Never changes verified recommendation gates."""
from collections import Counter,defaultdict
from datetime import date
from decimal import Decimal
from fractions import Fraction
from typing import Annotated,Literal
from pydantic import Field,model_validator
from data_pipeline import Contract
from stock_strategy import SPEC,SPEC_HASH,FEATURES,tied_percentiles,select_sector_constrained

Symbol=Annotated[str,Field(pattern=r'^[A-Z][A-Z0-9.-]{0,14}$')]


class ExperimentalRequest(Contract):
    acknowledge_proxy_and_estimates: bool = False
    budget_cents: int = Field(default=1000000,ge=0,le=100000000,strict=True)
    maximum_stocks_per_sector: int = Field(default=3,ge=1,le=3,strict=True)
    excluded_symbols: list[Symbol] = Field(default_factory=list,max_length=100)
    maximum_volatility: Decimal | None = Field(default=None,ge=0,le=10,allow_inf_nan=False)

    @model_validator(mode='after')
    def unique_exclusions(self):
        if len(set(self.excluded_symbols))!=len(self.excluded_symbols):raise ValueError('Duplicate exclusions')
        return self


class ExperimentalFinding(Contract):
    issuer_key: str
    symbol: str | None = None
    company: str
    sector: str | None
    reasons: list[str] = Field(default_factory=list)
    features: dict[str,Decimal] = Field(default_factory=dict)
    percentiles: dict[str,float] = Field(default_factory=dict)
    contributions: dict[str,float] = Field(default_factory=dict)
    score: float | None = None
    selected: bool = False


class ResearchPurchase(Contract):
    issuer_key: str
    symbol: str
    company: str
    sector: str
    score: float
    weight: Decimal
    purchase_cents: int
    price_date: str
    reference_price: Decimal
    illustrative_fractional_shares: Decimal


class ExperimentalBasket(Contract):
    model_version: Literal['proxy-estimate-basket-v1'] = 'proxy-estimate-basket-v1'
    strategy_sha256: str = SPEC_HASH
    status: Literal['acknowledgement_required','unavailable','infeasible','research_basket']
    inputs: ExperimentalRequest
    checked_on: date
    reason: str
    public_release_id: str | None
    market_snapshot_sha256: str | None
    universe_sha256: str | None
    universe_observed_on: str | None
    findings: list[ExperimentalFinding] = Field(default_factory=list)
    selected: list[ResearchPurchase] = Field(default_factory=list)
    qualified_sector_counts: dict[str,int] = Field(default_factory=dict)
    cash_unallocated_cents: int
    live_recommendations_enabled: Literal[False] = False
    verified_membership: Literal[False] = False
    verified_current_valuations: Literal[False] = False
    investment_performance_evidence: Literal[False] = False
    notice: str = 'Experimental paper-research basket from a limited dated ETF holdings proxy and filing-based valuation estimates. Not a verified S&P 500 recommendation, suitability assessment or proven strategy. No trade is placed. Concentration, corporate actions, missing companies and source estimates can materially change the result.'


def experimental_basket(screen,request):
    base=dict(inputs=request,checked_on=screen.checked_on,public_release_id=screen.public_release_id,market_snapshot_sha256=screen.market_snapshot_sha256,
        universe_sha256=screen.universe.source_sha256,universe_observed_on=str(screen.universe.observed_on) if screen.universe.observed_on else None,
        cash_unallocated_cents=request.budget_cents)
    if not request.acknowledge_proxy_and_estimates:
        return ExperimentalBasket(**base,status='acknowledgement_required',reason='Explicit acknowledgement of proxy membership and estimated valuations is required.')
    if screen.status!='available' or not screen.universe.fresh:
        return ExperimentalBasket(**base,status='unavailable',reason='Fresh installed research and ETF reference are required; unavailable/stale data is not substituted.')
    findings={};groups=defaultdict(list);rows={};issuer_counts=Counter(row.cik for row in screen.rows)
    for row in sorted(screen.rows,key=lambda row:row.issuer_key):
        valuation=row.valuation;symbol=row.tickers[0] if len(row.tickers)==1 else None
        finding=ExperimentalFinding(issuer_key=row.issuer_key,symbol=symbol,company=row.company,sector=row.sector)
        findings[row.issuer_key]=finding;rows[row.issuer_key]=row
        if issuer_counts[row.cik]>1:finding.reasons.append('Duplicate issuer evidence; no filing vintage or alternate class is guessed.')
        if not row.proxy_member:finding.reasons.append('Not present in the dated ETF reference.')
        if row.financial_status!='pass':finding.reasons.extend(row.financial_reasons or ['Financial evidence does not pass.'])
        if row.sector_status!='pass':finding.reasons.append('Sector is unsupported, stale or unavailable.')
        if row.price_status!='pass' or row.history_count_status!='pass':finding.reasons.append('Fresh price and 756 complete return observations are required.')
        if symbol is None:finding.reasons.append('Multiple directory securities; no canonical class is guessed.')
        elif symbol in request.excluded_symbols:finding.reasons.append('Excluded by your purchase restrictions.')
        if symbol and symbol in row.listing_evidence and row.listing_evidence[symbol].status in ('exchange_conflict','flagged_security','not_found','ambiguous'):
            finding.reasons.append('Official listing cross-check flags a conflict, security-type concern, absence or ambiguity; no listing is guessed.')
        if symbol and symbol in row.filing_class_evidence and row.filing_class_evidence[symbol].status in ('conflict','ambiguous'):
            finding.reasons.append('Filing-class evidence conflicts with the security mapping or listing; resolve it before research selection.')
        if valuation.status!='estimated':finding.reasons.append('A fresh split-aware filing valuation estimate is unavailable.')
        quality={key:row.metrics.get(key) for key in ('return_on_assets','operating_margin','free_cashflow_margin')}
        if any(metric is None or metric.status!='available' or metric.value is None for metric in quality.values()):
            finding.reasons.append('All three annual quality features must be available and fresh.')
        if request.maximum_volatility is not None:
            risk=row.metrics.get('annualized_volatility')
            if risk is None or risk.status!='available' or risk.value is None or risk.value>request.maximum_volatility:
                finding.reasons.append('Historical volatility is unavailable or above your limit.')
        yields={'earnings_yield':valuation.annual_earnings_yield_estimate,'free_cashflow_yield':valuation.annual_fcf_yield_estimate}
        if any(value is None or value<=0 for value in yields.values()):finding.reasons.append('Both estimated valuation yields must be positive.')
        if finding.reasons:continue
        finding.features={**{key:metric.value for key,metric in quality.items()},**yields}
        groups[row.sector].append(finding)
    counts={sector:len(peers) for sector,peers in groups.items()};scored=[]
    weights={feature['name']:Fraction(str(feature['weight'])) for feature in SPEC['features']}
    for sector,peers in groups.items():
        if len(peers)<SPEC['minimum_eligible_sector_peers']:
            for finding in peers:finding.reasons.append(f'Only {len(peers)} research-qualified sector peers; at least five are required.')
            continue
        percentiles={key:tied_percentiles({peer.issuer_key:Fraction(peer.features[key]) for peer in peers}) for key in FEATURES}
        for finding in peers:
            contributions={key:weights[key]*percentiles[key][finding.issuer_key] for key in FEATURES}
            score=sum(contributions.values())
            finding.percentiles={key:float(percentiles[key][finding.issuer_key]) for key in FEATURES}
            finding.contributions={key:float(value) for key,value in contributions.items()};finding.score=float(score)
            scored.append(dict(security_id=finding.symbol,issuer_id=f'sec:{rows[finding.issuer_key].cik:010d}',issuer_key=finding.issuer_key,sector=sector,score=score))
    count=SPEC['portfolio']['stock_count']
    chosen=select_sector_constrained(scored,count=count,sector_limit=request.maximum_stocks_per_sector)
    result=dict(**base,findings=list(findings.values()),qualified_sector_counts=counts)
    if not chosen or request.budget_cents<count:
        return ExperimentalBasket(**result,status='infeasible',reason='The covered sample, sector/peer rules, purchase restrictions or budget cannot fill ten positions. No constraint is relaxed and no partial basket is recommended.')
    purchases=[];per_stock=request.budget_cents//count
    for selected in chosen:
        finding=findings[selected['issuer_key']];row=rows[finding.issuer_key];finding.selected=True
        purchases.append(ResearchPurchase(issuer_key=finding.issuer_key,symbol=finding.symbol,company=finding.company,
            sector=finding.sector,score=finding.score,weight=Decimal(1)/count,purchase_cents=per_stock,
            price_date=str(row.valuation.price_date),reference_price=row.valuation.raw_price,
            illustrative_fractional_shares=Decimal(per_stock)/100/row.valuation.raw_price))
    for finding in findings.values():
        if finding.score is not None and not finding.selected:finding.reasons.append('Not selected under the score order and sector-position limits.')
    result['cash_unallocated_cents']=request.budget_cents-per_stock*count
    return ExperimentalBasket(**result,status='research_basket',reason='Ten equally weighted paper-research positions selected by exact within-sector percentiles and sector quotas.',selected=purchases)
