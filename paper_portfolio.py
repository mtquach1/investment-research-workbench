"""Frozen prospective paper records; no backdated current-winner backtests."""
from datetime import date,datetime,timedelta
from decimal import Decimal,ROUND_HALF_UP
from zoneinfo import ZoneInfo
from typing import Literal
from typing import Annotated
from pydantic import Field,model_validator
from data_pipeline import Contract
from public_data_store import canonical_bytes,strict_json
from collections import Counter
from hashlib import sha256
from market_history import session_dates
from experimental_basket import ExperimentalBasket


class PaperRecord(Contract):
    version: Literal['prospective-paper-v1']='prospective-paper-v1'
    created_at: datetime
    earliest_entry_date: date
    entry_cost_bps: int = Field(ge=0,le=1000,strict=True)
    basket: ExperimentalBasket
    security_ciks: dict[str,Annotated[int,Field(gt=0,strict=True)]]
    fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def coherent(self):
        if self.created_at.tzinfo is None:raise ValueError('Creation clock must include timezone')
        if self.basket.status!='research_basket':raise ValueError('A complete experimental basket is required')
        selected=self.basket.selected
        if len(selected)!=10 or len({row.symbol for row in selected})!=10 or set(self.security_ciks)!={row.symbol for row in selected}:
            raise ValueError('Ten distinct securities and exact frozen issuer identities are required')
        if len(set(self.security_ciks.values()))!=10 or not self.basket.inputs.acknowledge_proxy_and_estimates:
            raise ValueError('Unique issuers and experimental acknowledgement are required')
        if any(row.purchase_cents!=self.basket.inputs.budget_cents//10 or row.purchase_cents<1 or row.weight!=Decimal('.1') for row in selected):
            raise ValueError('Paper positions must follow the fixed equal-weight cent allocation')
        if max(Counter(row.sector for row in selected).values())>self.basket.inputs.maximum_stocks_per_sector:
            raise ValueError('Paper sector cap exceeded')
        if self.basket.checked_on!=self.created_at.astimezone(ZoneInfo('America/Los_Angeles')).date():
            raise ValueError('Basket assessment must match the decision date')
        if sum(row.purchase_cents for row in selected)+self.basket.cash_unallocated_cents!=self.basket.inputs.budget_cents:
            raise ValueError('Paper funding must reconcile')
        payload=self.model_dump(mode='json',exclude={'fingerprint'})
        if sha256(canonical_bytes(payload)).hexdigest()!=self.fingerprint:raise ValueError('Paper record checksum mismatch')
        if self.earliest_entry_date<=self.created_at.astimezone(ZoneInfo('America/New_York')).date():raise ValueError('Entry must follow the recorded decision date')
        return self


def freeze_paper_basket(basket,*,now,security_ciks,entry_cost_bps=10):
    if now.tzinfo is None:raise ValueError('Creation clock must include timezone')
    if basket.checked_on!=now.astimezone(ZoneInfo('America/Los_Angeles')).date():raise ValueError('Freeze only a basket assessed today')
    day=now.astimezone(ZoneInfo('America/New_York')).date()
    entry=session_dates(day+timedelta(days=1),day+timedelta(days=14))[0]
    draft=PaperRecord.model_construct(created_at=now,earliest_entry_date=entry,entry_cost_bps=entry_cost_bps,
        basket=basket.model_copy(deep=True),security_ciks=security_ciks,fingerprint='0'*64)
    payload=draft.model_dump(mode='json',exclude={'fingerprint'})
    return PaperRecord(**payload,fingerprint=sha256(canonical_bytes(payload)).hexdigest())


def restore_paper_record(payload,*,now,known_fingerprints=()):
    if len(payload)>524288:raise ValueError('Record exceeds size limit')
    record=PaperRecord.model_validate(strict_json(payload))
    if now.tzinfo is None or record.created_at>now:raise ValueError('Future or ambiguous creation time')
    if record.fingerprint in known_fingerprints:raise ValueError('Already restored')
    return record


def track_paper_record(record,bundle,*,today):
    record=PaperRecord.model_validate(record.model_dump())
    base={'record_sha256':record.fingerprint,'status':'pending','points':[],
        'historical_strategy_performance_verified':False,'notice':'Prospective paper tracking only. No rebalancing, taxes, sale costs, slippage or calibrated risk model. All-adjusted IEX closes are a provider return proxy. A checksum detects edits but is not a trusted timestamp or proof of strategy outperformance.'}
    if record.created_at.astimezone(ZoneInfo('America/New_York')).date()>today:
        return dict(base,status='unavailable',reason='Record creation is in the future.')
    if bundle.completed_through<record.earliest_entry_date or today<record.earliest_entry_date:
        return dict(base,reason=f'Awaiting installed prices on or after {record.earliest_entry_date}. No past prices are used to manufacture results.')
    end=min(today,bundle.completed_through)
    days=session_dates(record.earliest_entry_date,end)
    if not days:return dict(base,reason='No completed evaluation session is installed.')
    needed={row.symbol for row in record.basket.selected}|{'SPY'};bars={}
    for symbol in needed:
        series=bundle.series.get(symbol)
        purchase=next((item for item in record.basket.selected if item.symbol==symbol),None)
        if series is None or (symbol=='SPY' and series.role!='benchmark_proxy') or (purchase and (series.role!='issuer_security' or series.cik!=record.security_ciks[symbol])):
            return dict(base,status='unavailable',reason='An exact security/issuer or benchmark series is missing; no substitute is selected.')
        lookup={bar.day:bar.adjusted_close for bar in series.bars}
        if any(day not in lookup for day in days):
            return dict(base,status='unavailable',reason='A required trading session is missing. The comparison is withheld rather than intersecting away the gap.')
        bars[symbol]=lookup
    budget=Decimal(record.basket.inputs.budget_cents)/100
    cost=(budget*record.entry_cost_bps/10000).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    capital=budget-cost
    if capital<=0:return dict(base,status='unavailable',reason='Positive funded capital is required.')
    points=[]
    for day in days:
        gross=Decimal(record.basket.cash_unallocated_cents)/100
        for row in record.basket.selected:
            gross+=Decimal(row.purchase_cents)/100*bars[row.symbol][day]/bars[row.symbol][days[0]]
        net=gross*capital/budget
        benchmark_gross=budget*bars['SPY'][day]/bars['SPY'][days[0]]
        points.append({'day':str(day),'basket_gross':str(gross),'basket_net':str(net),
            'benchmark_gross':str(benchmark_gross),'benchmark_net':str(benchmark_gross*capital/budget)})
    return dict(base,status='available',reason='Frozen basket evaluated only from the first eligible subsequent session close.',
        entry_date=str(days[0]),last_date=str(days[-1]),entry_cost=str(cost),initial_budget=str(budget),points=points,
        basket_gain=str(Decimal(points[-1]['basket_net'])-budget),benchmark_gain=str(Decimal(points[-1]['benchmark_net'])-budget),
        difference_dollars=str(Decimal(points[-1]['basket_net'])-Decimal(points[-1]['benchmark_net'])))
