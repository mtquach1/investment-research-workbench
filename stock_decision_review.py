"""Alternatives, one-at-a-time sensitivity and direct holding exposure."""
from collections import Counter
from decimal import Decimal
from typing import Annotated
from pydantic import Field,model_validator
from data_pipeline import Contract
from experimental_basket import experimental_basket,Symbol


class ExistingHolding(Contract):
    symbol: Symbol
    amount_cents: int = Field(ge=1,le=100_000_000,strict=True)


class HoldingsReviewRequest(Contract):
    holdings: list[ExistingHolding] = Field(default_factory=list,max_length=25)

    @model_validator(mode='after')
    def unique(self):
        if len({row.symbol for row in self.holdings})!=len(self.holdings):raise ValueError('Combine duplicate symbols')
        if sum(row.amount_cents for row in self.holdings)>100_000_000:raise ValueError('Existing holdings exceed supported total')
        return self


def basket_alternatives(result):
    """Feasible one-for-one swaps at frozen baseline scores; no suitability claim."""
    if result.status!='research_basket':return []
    counts=Counter(row.sector for row in result.selected)
    candidates=sorted((row for row in result.findings if row.score is not None and not row.selected),key=lambda row:(-row.score,row.issuer_key))
    output=[]
    for chosen in result.selected:
        finding=next(row for row in result.findings if row.issuer_key==chosen.issuer_key)
        alternative=next((row for row in candidates if counts[row.sector]-(row.sector==chosen.sector)<result.inputs.maximum_stocks_per_sector),None)
        output.append({'Selected':chosen.symbol,'Alternative':alternative.symbol if alternative else 'None covered',
            'Selected score':chosen.score*100,'Alternative score':alternative.score*100 if alternative else None,
            'Score gap':(chosen.score-alternative.score)*100 if alternative else None,
            'Selected ranks higher on':', '.join(key.replace('_',' ') for key,value in finding.contributions.items() if alternative and value>alternative.contributions[key]) or 'No strictly higher contribution',
            'Alternative ranks higher on':', '.join(key.replace('_',' ') for key,value in finding.contributions.items() if alternative and value<alternative.contributions[key]) or 'No strictly higher contribution',
            'Tradeoff':('Same sector; compare the five feature contributions.' if alternative.sector==chosen.sector else 'Changes sector exposure while respecting the position cap.') if alternative else 'No scored unselected company permits this one-position swap.'})
    return output


def basket_sensitivity(screen,result,*,shock=Decimal('.10')):
    """Shock both yield estimates for one qualified issuer at a time; never prices."""
    if not Decimal(0)<shock<=Decimal('.5'):raise ValueError('Use a positive shock no greater than 50%')
    if result.status!='research_basket':return []
    baseline={row.issuer_key for row in result.selected};scored={row.issuer_key for row in result.findings if row.score is not None}
    output=[]
    for row in screen.rows:
        if row.issuer_key not in scored:continue
        for direction in (-1,1):
            perturbed=screen.model_copy(deep=True)
            target=next(item for item in perturbed.rows if item.issuer_key==row.issuer_key)
            for field in ('annual_earnings_yield_estimate','annual_fcf_yield_estimate'):
                setattr(target.valuation,field,getattr(target.valuation,field)*(1+direction*shock))
            candidate=experimental_basket(perturbed,result.inputs)
            selected={item.issuer_key for item in candidate.selected}
            output.append({'Company':row.company,'Yield estimate shock (%)':float(direction*shock*100),
                'Retained positions':len(selected&baseline),'Changed positions':len(baseline-selected),
                'Added':', '.join(item.symbol for item in candidate.selected if item.issuer_key not in baseline),
                'Removed':', '.join(item.symbol for item in result.selected if item.issuer_key not in selected),
                'Status':candidate.status})
    return output


def review_holdings(result,request):
    totals={row.symbol:row.amount_cents for row in request.holdings}
    existing=sum(totals.values());combined=existing+result.inputs.budget_cents
    for row in result.selected:totals[row.symbol]=totals.get(row.symbol,0)+row.purchase_cents
    symbols={row.symbol for row in result.selected}
    output=[{'Symbol':symbol,'Existing ($)':next((row.amount_cents/100 for row in request.holdings if row.symbol==symbol),0),
        'Paper addition ($)':next((row.purchase_cents/100 for row in result.selected if row.symbol==symbol),0),
        'Combined direct weight (%)':float(Decimal(amount)*100/combined) if combined else 0,
        'Already held':symbol in symbols and any(row.symbol==symbol for row in request.holdings)} for symbol,amount in sorted(totals.items())]
    return {'rows':output,'existing_cents':existing,'combined_cents':combined,'cash_cents':result.cash_unallocated_cents,
        'largest_direct_weight':max((row['Combined direct weight (%)'] for row in output),default=0),
        'notice':'Direct ticker exposure only. ETF constituents, share-class/issuer overlap and sector look-through are unresolved. This is an exposure check, not a personalized rebalancing plan. Your manual Portfolio illustration is never assumed to be your real holdings.'}
