"""Historical cash-flow replay from installed evidence; never a strategy backtest."""
from datetime import date,datetime,timezone
from decimal import Decimal,localcontext,ROUND_HALF_UP
from typing import Literal
from zoneinfo import ZoneInfo
from pydantic import Field,model_validator
from data_pipeline import Contract
from market_history import session_dates
from company_market import company_market


class ReplayRequest(Contract):
    issuer_key: str = Field(pattern=r'^[a-z0-9_]{1,64}$')
    symbol: str | None = Field(default=None,pattern=r'^[A-Z][A-Z0-9.-]{0,14}$')
    start: date
    end: date
    initial_cents: int = Field(default=100000,ge=0,le=100000000,strict=True)
    monthly_cents: int = Field(default=10000,ge=0,le=10000000,strict=True)
    purchase_fee_rate: Decimal = Field(default=0,ge=0,le='.05',allow_inf_nan=False)
    annual_account_fee_rate: Decimal = Field(default=0,ge=0,le='.1',allow_inf_nan=False)
    basis: Literal['split_adjusted_price_only','provider_all_adjusted_proxy'] = 'split_adjusted_price_only'

    @model_validator(mode='after')
    def coherent(self):
        if self.end<=self.start or (self.end-self.start).days>3660:raise ValueError('Choose a positive interval up to ten years')
        if not self.initial_cents and not self.monthly_cents:raise ValueError('A contribution is required')
        return self


class ReplayPoint(Contract):
    day: date
    deposit_cents: int
    cumulative_deposits_cents: int
    company_value: Decimal
    benchmark_value: Decimal
    company_fees: Decimal
    benchmark_fees: Decimal


class StockReplay(Contract):
    model_version: Literal['stock-cashflow-replay-v1'] = 'stock-cashflow-replay-v1'
    status: Literal['available','unavailable','withheld']
    reason: str
    inputs: ReplayRequest
    symbol: str | None = None
    snapshot_sha256: str | None = None
    points: list[ReplayPoint] = Field(default_factory=list)
    total_deposits_cents: int = 0
    company_ending_value: Decimal | None = None
    benchmark_ending_value: Decimal | None = None
    company_net_growth: Decimal | None = None
    benchmark_net_growth: Decimal | None = None
    strategy_performance_evidence: Literal[False] = False
    notice: str = 'Historical single-security alternative versus SPY under identical deposits and modeled fees. Fractional adjusted-value units at daily closes; not executable historical share quantities. Price-only excludes dividends. Provider all-adjusted mode is not verified exact reinvested total return. No taxes, spread or slippage modeled; additional account fees are beyond costs already embedded in market prices.'


def _round(value):return value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)


def calculate_replay(request,points):
    selected=[point for point in points if request.start<=point.day<=request.end]
    if len(selected)<2:raise ValueError('Two observed dates required')
    first,last=selected[0].day,selected[-1].day
    if [point.day for point in selected]!=session_dates(request.start,request.end):raise ValueError('Missing shared trading sessions; no replay is filled')
    if request.basis=='split_adjusted_price_only':
        pairs=[(p.company_split_adjusted_close,p.benchmark_split_adjusted_close) for p in selected]
    else:pairs=[(p.company_adjusted_close,p.benchmark_adjusted_close) for p in selected]
    if any(a is None or b is None or a<=0 or b<=0 for a,b in pairs):raise ValueError('Selected adjustment basis is unavailable')
    # Recurring cash starts in the next calendar month. Holidays/weekends roll
    # forward to the first shared trading close. No deposit in a prior month.
    start_month=request.start.year*12+request.start.month
    scheduled_month=start_month+1
    deposits=0;balances=[Decimal(0),Decimal(0)];fees=[Decimal(0),Decimal(0)];rows=[]
    with localcontext() as context:
        context.prec=40
        for index,(point,prices) in enumerate(zip(selected,pairs)):
            cash=request.initial_cents if index==0 else 0
            ordinal=point.day.year*12+point.day.month
            if ordinal>=scheduled_month:
                cash+=request.monthly_cents
                scheduled_month=ordinal+1
            deposits+=cash
            buy_fee=_round(Decimal(cash)/100*request.purchase_fee_rate)
            for side in range(2):
                if index:
                    balances[side]*=prices[side]/pairs[index-1][side]
                    days=Decimal((point.day-selected[index-1].day).days)
                    account_fee=balances[side]*(1-(1-request.annual_account_fee_rate)**(days/Decimal('365.2425')))
                    balances[side]-=account_fee;fees[side]+=account_fee
                balances[side]+=Decimal(cash)/100-buy_fee;fees[side]+=buy_fee
            rows.append(ReplayPoint(day=point.day,deposit_cents=cash,cumulative_deposits_cents=deposits,
                company_value=_round(balances[0]),benchmark_value=_round(balances[1]),
                company_fees=_round(fees[0]),benchmark_fees=_round(fees[1])))
    return rows


def replay_stock(public_root,history_root,request,*,mode='withheld',today=None):
    base=dict(inputs=request)
    if mode!='local_research':return StockReplay(**base,status='withheld',reason='Local market research is disabled.')
    today=today or datetime.now(ZoneInfo('America/Los_Angeles')).date()
    if request.end>today:return StockReplay(**base,status='unavailable',reason='Future dates cannot be replayed.')
    market=company_market(public_root,history_root,request.issuer_key,symbol=request.symbol,mode=mode,today=today)
    if market.status!='available':return StockReplay(**base,status='unavailable',reason='Choose an installed, unambiguous company security with price evidence.')
    points=market.comparison.points
    if request.start<points[0].day or request.end>points[-1].day:
        return StockReplay(**base,status='unavailable',reason='Requested dates extend outside installed history; no extrapolation is performed.')
    try:rows=calculate_replay(request,points)
    except (ValueError,ArithmeticError):return StockReplay(**base,status='unavailable',reason='Shared trading sessions or the selected adjustment evidence are incomplete.')
    last=rows[-1];deposited=Decimal(last.cumulative_deposits_cents)/100
    return StockReplay(**base,status='available',reason='Same deposits, purchase dates and fee assumptions for both alternatives.',
        symbol=market.selected_symbol,snapshot_sha256=market.snapshot_sha256,points=rows,total_deposits_cents=last.cumulative_deposits_cents,
        company_ending_value=last.company_value,benchmark_ending_value=last.benchmark_value,
        company_net_growth=last.company_value-deposited,benchmark_net_growth=last.benchmark_value-deposited)
