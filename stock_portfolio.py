"""Server-owned recommendation readiness; client budgets cannot certify data."""
from collections import Counter
from typing import Literal
from pydantic import Field
from data_pipeline import Contract
from stock_strategy import SPEC,SPEC_HASH


class ProposalRequest(Contract):
    budget_cents: int = Field(default=1000000,ge=0,le=100000000,strict=True)
    maximum_stocks_per_sector: int = Field(default=3,ge=1,le=3,strict=True)
    excluded_symbols: list[str] = Field(default_factory=list,max_length=100)


class ProposalFinding(Contract):
    issuer_key: str
    company: str
    symbols: list[str]
    blockers: list[str]


class StockProposal(Contract):
    model_version: Literal['verified-stock-proposal-gate-v1'] = 'verified-stock-proposal-gate-v1'
    strategy_sha256: str = SPEC_HASH
    status: Literal['blocked_by_data','infeasible']
    inputs: ProposalRequest
    source_release_id: str | None
    market_snapshot_sha256: str | None
    required_stock_count: int = SPEC['portfolio']['stock_count']
    findings: list[ProposalFinding]
    global_blockers: list[str]
    sector_financial_pass_counts: dict[str,int]
    selected: list[dict] = Field(default_factory=list,max_length=0)
    cash_unallocated_cents: int
    live_recommendations_enabled: Literal[False] = False


def stock_proposal(screen,request):
    findings=[]
    for row in screen.rows:
        blockers=[]
        if set(row.tickers)&set(request.excluded_symbols):blockers.append('Excluded by your purchase restrictions.')
        if row.financial_status!='pass':blockers.extend(row.financial_reasons or ['Financial evidence does not pass.'])
        if row.sector_status!='pass':blockers.append('Unsupported, stale or unavailable sector evidence.')
        if row.price_status!='pass' or row.history_count_status!='pass':blockers.append('Fresh price and complete risk history required.')
        if not row.valuation.verified_current_market_cap:blockers.append('Current issuer valuation remains unverified; an estimate cannot satisfy this gate.')
        blockers.append('Official dated membership and canonical security identity remain unverified.')
        findings.append(ProposalFinding(issuer_key=row.issuer_key,company=row.company,symbols=row.tickers,blockers=blockers))
    constraints=[]
    if request.budget_cents<SPEC['portfolio']['stock_count']:constraints.append('Budget must fund at least one cent per required position.')
    counts=Counter(row.sector for row in screen.rows if row.sector and row.financial_status==row.sector_status=='pass')
    capacity=sum(min(value,request.maximum_stocks_per_sector) for value in counts.values() if value>=SPEC['minimum_eligible_sector_peers'])
    if capacity<SPEC['portfolio']['stock_count']:constraints.append('Installed financially passing sector populations cannot fill the basket under the peer and sector limits; verified eligibility may reduce capacity further.')
    return StockProposal(status='infeasible' if constraints else 'blocked_by_data',inputs=request,
        source_release_id=screen.public_release_id,market_snapshot_sha256=screen.market_snapshot_sha256,findings=findings,
        global_blockers=constraints+screen.blockers,sector_financial_pass_counts=dict(counts),cash_unallocated_cents=request.budget_cents)
