"""One-deposit experimental allocation; no scheduling, forecasts or execution."""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field
from allocation_engine import allocate_contributions
from allocation_models import AllocationRequest, AllocationAsset, AllocationAccount
from data_pipeline import Contract
from experimental_basket import ExperimentalRequest, experimental_basket
from stock_decisions import DecisionContext, assess_decisions, POLICY_HASH
from stock_strategy import SPEC_HASH

CASH = '_CASH'


class MonthlyPosition(Contract):
    symbol: str
    before_cents: int = Field(ge=0, strict=True)
    purchase_cents: int = Field(ge=0, strict=True)
    after_cents: int = Field(ge=0, strict=True)
    target_weight: Decimal
    explanation: str


class MonthlyContributionPlan(Contract):
    model_version: Literal['stock-monthly-contribution-v1'] = 'stock-monthly-contribution-v1'
    status: Literal['allocated', 'cash_only', 'acknowledgement_required', 'nothing_to_allocate',
        'unavailable', 'infeasible', 'input_limit', 'solver_unavailable']
    checked_on: date
    context: DecisionContext
    monthly_amount_cents: int
    entered_holdings_cents: int
    to_stocks_cents: int = 0
    cash_unassigned_cents: int
    positions: list[MonthlyPosition] = Field(default_factory=list)
    explanation: str
    public_release_id: str | None
    market_snapshot_sha256: str | None
    universe_sha256: str | None
    listing_reference_hashes: dict[str, str]
    policy_sha256: str = POLICY_HASH
    strategy_sha256: str = SPEC_HASH
    live_recommendations_enabled: Literal[False] = False
    automatic_schedule_enabled: Literal[False] = False
    notice: str = ('Experimental preview of one deposit using entered holdings only. Initial new cash is excluded; '
        'no previous purchase is assumed. Ten baseline targets stay equal; blocked targets are not replaced. '
        'No forecast, sales, transfers, taxes, fees, prices, ETF look-through or automatic trades. '
        'Dollar purchases assume fractional shares. Optimality concerns allocation constraints, not returns.')


def plan_monthly_contribution(screen, context: DecisionContext) -> MonthlyContributionPlan:
    context = DecisionContext.model_validate(context.model_dump())
    amount = context.monthly_contribution_cents
    holdings = {row.symbol: row.value_cents for row in context.holdings}
    base = dict(checked_on=screen.checked_on, context=context, monthly_amount_cents=amount,
        entered_holdings_cents=sum(holdings.values()), cash_unassigned_cents=amount,
        public_release_id=screen.public_release_id, market_snapshot_sha256=screen.market_snapshot_sha256,
        universe_sha256=screen.universe.source_sha256, listing_reference_hashes=screen.listing_reference_hashes)

    def withheld(status, explanation):
        return MonthlyContributionPlan(**base, status=status, explanation=explanation)

    if not context.acknowledge_experimental:
        return withheld('acknowledgement_required', 'Accept the experimental-research limits before previewing.')
    if not amount:
        return withheld('nothing_to_allocate', 'Enter a monthly amount greater than $0 to preview one deposit.')
    if screen.status != 'available' or not screen.universe.fresh:
        return withheld('unavailable', 'Current reference evidence is unavailable or stale. All deposit money stays unassigned.')
    basket = experimental_basket(screen, ExperimentalRequest(
        acknowledge_proxy_and_estimates=True, budget_cents=amount))
    if basket.status != 'research_basket' or len(basket.selected) != 10:
        return withheld('unavailable', 'A complete ten-stock experimental baseline is unavailable. No purchases proposed.')
    targets = {row.symbol for row in basket.selected}
    symbols = sorted(targets | set(holdings))
    cap = context.maximum_direct_weight
    if len(symbols) + 1 > 30 or cap != cap.quantize(Decimal('.000001')):
        return withheld('input_limit', 'This preview supports 29 distinct stocks/holdings and a concentration limit with at most six decimal places. No holdings were dropped or limits rounded.')
    # Personal eligibility stays separate from hard dollar-cap constraints below.
    eligibility = assess_decisions(screen, context.model_copy(update={
        'new_cash_cents': amount, 'maximum_direct_weight': Decimal(1)}))
    allowed = {symbol for card in eligibility.cards if card.outcome in ('buy_candidate', 'hold')
        for symbol in card.symbols} & targets
    blocked_reasons = {symbol: '; '.join(reason.detail for reason in card.reasons)
        for card in eligibility.cards for symbol in card.symbols if symbol not in allowed}
    total = sum(holdings.values()) + amount
    assets, permissions, caps = [], [CASH], {}
    for symbol in symbols:
        before = holdings.get(symbol, 0)
        target = Decimal('.1') if symbol in targets else Decimal(0)
        below_target = before <= int(target * total)
        effective_cap = min(cap, target) if symbol in targets and below_target else cap
        caps[symbol] = int(effective_cap * total)
        assets.append(AllocationAsset(asset_id=symbol, target_weight=target, max_weight=effective_cap))
        if symbol in allowed and below_target:
            permissions.append(symbol)
    assets.append(AllocationAsset(asset_id=CASH, target_weight=0, max_weight=1))
    request = AllocationRequest(assets=assets, accounts=[AllocationAccount(account_id='monthly',
        account_type='taxable', available_cash=Decimal(amount)/100,
        holdings={key: Decimal(value)/100 for key, value in holdings.items()}, allowed_assets=permissions)])
    result = allocate_contributions(request)
    if result.status == 'infeasible':
        return withheld('infeasible', 'An entered holding still exceeds your concentration limit after this deposit. No sale or relaxed limit is assumed; no purchases proposed.')
    if result.status != 'optimal':
        return withheld('solver_unavailable', 'The allocation could not be verified. All deposit money stays unassigned.')
    purchases = dict.fromkeys(symbols + [CASH], 0)
    for trade in result.trades:
        if (trade.account_id != 'monthly' or trade.asset_id not in permissions
                or type(trade.amount_cents) is not int or trade.amount_cents < 0):
            return withheld('solver_unavailable', 'The allocation failed independent accounting checks. No purchases proposed.')
        purchases[trade.asset_id] += trade.amount_cents
    if sum(purchases.values()) != amount or any(
            holdings.get(symbol, 0) + purchases[symbol] > caps[symbol] for symbol in symbols):
        return withheld('solver_unavailable', 'The allocation failed independent accounting checks. No purchases proposed.')
    cash = purchases[CASH]
    base['cash_unassigned_cents'] = cash

    def position_reason(symbol):
        if symbol not in targets:
            return 'Included in your total holdings; outside the ten-stock baseline, so no addition.'
        if symbol not in allowed:
            return blocked_reasons.get(symbol, 'Required company evidence is unavailable.')
        if holdings.get(symbol, 0) > int(Decimal('.1') * total):
            return 'Already above the 10% baseline target. No sale or additional purchase assumed.'
        return 'Addition limited by the 10% target, your direct-position cap and whole-cent rounding.'

    return MonthlyContributionPlan(**base, status='allocated' if cash < amount else 'cash_only',
        to_stocks_cents=amount-cash,
        positions=[MonthlyPosition(symbol=symbol, before_cents=holdings.get(symbol, 0),
            purchase_cents=purchases[symbol], after_cents=holdings.get(symbol, 0)+purchases[symbol],
            target_weight=Decimal('.1') if symbol in targets else Decimal(0),
            explanation=position_reason(symbol)) for symbol in symbols],
        explanation='One deposit previewed against ten equal experimental targets. Unfilled targets, concentration limits and cent rounding leave money in cash; this is not a recommendation or schedule.')
