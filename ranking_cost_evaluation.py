"""Bounded ranking diagnostics and entry-cost illustrations, never returns."""
from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import Field
from data_pipeline import Contract
from experimental_basket import ExperimentalRequest, experimental_basket
from stock_decision_review import basket_sensitivity
from stock_strategy import SPEC_HASH


class EntryCostCase(Contract):
    scenario_id: str
    label: str
    status: Literal['illustrated','unaffordable']
    rate_bps: int
    fee_per_trade_cents: int
    basket_trades: int
    benchmark_trades: int = 1
    basket_cost_cents: int
    benchmark_cost_cents: int
    basket_capital_cents: int | None
    benchmark_capital_cents: int | None
    extra_basket_cost_cents: int


class RankingCostEvaluation(Contract):
    model_version: Literal['ranking-entry-cost-evaluation-v1'] = 'ranking-entry-cost-evaluation-v1'
    status: Literal['acknowledgement_required','unavailable','infeasible','evaluated']
    checked_on: date
    inputs: ExperimentalRequest
    reason: str
    strategy_sha256: str = SPEC_HASH
    public_release_id: str | None
    market_snapshot_sha256: str | None
    universe_sha256: str | None
    listing_reference_hashes: dict[str,str]
    strategy_score_total: Decimal | None = None
    alphabetical_score_total: Decimal | None = None
    alphabetical_symbols: list[str] = Field(default_factory=list)
    selected_symbols: list[str] = Field(default_factory=list)
    row_order_invariant: bool | None = None
    uniform_yield_scale_invariant: bool | None = None
    sensitivity: list[dict] = Field(default_factory=list)
    scenarios_with_changes: int = 0
    minimum_retained: int | None = None
    costs: list[EntryCostCase] = Field(default_factory=list)
    investment_performance_verified: Literal[False] = False
    live_recommendations_enabled: Literal[False] = False
    notice: str = ('Experimental diagnostics on the installed covered sample. Hypothetical yield changes are not observations, probabilities or return forecasts. '
        'Score totals measure the ranking objective only. Entry costs are assumed illustrations, not broker quotes. '
        'No historical strategy backtest, tax analysis, sale costs, price slippage or public-display approval is established.')


def evaluate_ranking_costs(screen, request: ExperimentalRequest):
    request=ExperimentalRequest.model_validate(request.model_dump())
    base=dict(checked_on=screen.checked_on,inputs=request,public_release_id=screen.public_release_id,
        market_snapshot_sha256=screen.market_snapshot_sha256,universe_sha256=screen.universe.source_sha256,
        listing_reference_hashes=screen.listing_reference_hashes)
    basket=experimental_basket(screen,request)
    if basket.status!='research_basket':
        return RankingCostEvaluation(**base,status=basket.status,reason=basket.reason)
    scored=[item for item in basket.findings if item.score is not None]
    if len(scored)>150:
        return RankingCostEvaluation(**base,status='unavailable',reason='This diagnostic supports at most 150 scored issuers; no sample is silently dropped.')
    count=len(basket.selected)
    alphabetical=[];sectors=Counter()
    for item in sorted(scored,key=lambda row:(row.symbol,row.issuer_key)):
        if sectors[item.sector]<request.maximum_stocks_per_sector:
            alphabetical.append(item);sectors[item.sector]+=1
        if len(alphabetical)==count:break
    if len(alphabetical)!=count:
        raise ValueError('The comparison baseline could not satisfy the same constraints')
    def identities(result):return [item.issuer_key for item in result.selected]
    baseline_ids=identities(basket)
    reordered=screen.model_copy(deep=True);reordered.rows.reverse()
    row_order=identities(experimental_basket(reordered,request))==baseline_ids
    uniform=True
    for factor in (Decimal('.9'),Decimal('1.1')):
        changed=screen.model_copy(deep=True)
        for row in changed.rows:
            for field in ('annual_earnings_yield_estimate','annual_fcf_yield_estimate'):
                value=getattr(row.valuation,field)
                if value is not None:setattr(row.valuation,field,value*factor)
        uniform=uniform and identities(experimental_basket(changed,request))==baseline_ids
    sensitivity=basket_sensitivity(screen,basket,shock=Decimal('.10'))
    costs=[];budget=request.budget_cents
    for case,label,bps,flat in [('zero','No entry costs',0,0),
            ('ten_bps','0.10% of starting cash',10,0),('fifty_bps','0.50% of starting cash',50,0),
            ('one_dollar_per_trade','$1 per purchase',0,100)]:
        proportional=(budget*bps+5000)//10000  # nearest cent, half up, charged once
        basket_fee=proportional+count*flat;benchmark_fee=proportional+flat
        affordable=max(basket_fee,benchmark_fee)<=budget
        costs.append(EntryCostCase(scenario_id=case,label=label,status='illustrated' if affordable else 'unaffordable',
            rate_bps=bps,fee_per_trade_cents=flat,basket_trades=count,basket_cost_cents=basket_fee,
            benchmark_cost_cents=benchmark_fee,basket_capital_cents=budget-basket_fee if affordable else None,
            benchmark_capital_cents=budget-benchmark_fee if affordable else None,
            extra_basket_cost_cents=basket_fee-benchmark_fee))
    return RankingCostEvaluation(**base,status='evaluated',
        reason='Fixed ranking scenarios and entry-cost assumptions evaluated. This does not measure investment performance.',
        strategy_score_total=sum((Decimal(str(item.score)) for item in basket.selected),Decimal(0)),
        alphabetical_score_total=sum((Decimal(str(item.score)) for item in alphabetical),Decimal(0)),
        alphabetical_symbols=[item.symbol for item in alphabetical],selected_symbols=[item.symbol for item in basket.selected],
        row_order_invariant=row_order,uniform_yield_scale_invariant=uniform,sensitivity=sensitivity,
        scenarios_with_changes=sum(item['Changed positions']>0 for item in sensitivity),
        minimum_retained=min((item['Retained positions'] for item in sensitivity),default=count),costs=costs)
