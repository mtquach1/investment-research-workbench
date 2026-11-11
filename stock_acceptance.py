"""Deterministic connected-workflow checks with fixed example inputs, not returns."""
from datetime import date
from decimal import Decimal
from collections import Counter
from typing import Literal
from pydantic import Field
from data_pipeline import Contract
from stock_decisions import DecisionContext, DecisionHolding, assess_decisions, POLICY_HASH
from stock_strategy import SPEC_HASH
from stock_monthly import plan_monthly_contribution
from decision_snapshots import freeze_decision, restore_decision, review_decision
from holding_notes import save_holding_note, restore_holding_note
from holding_research import HoldingReviewInputs


class WorkflowCheck(Contract):
    check_id: str
    title: str
    status: Literal['passed', 'failed', 'blocked']
    detail: str


class EvaluationInputs(Contract):
    screen_status: str
    references_fresh: bool
    reference_observed_on: date | None
    company_count: int
    candidate_count: int | None
    oldest_price_date: date | None
    newest_price_date: date | None
    blocking_reason_counts: dict[str, int] = Field(default_factory=dict)


class StockWorkflowEvaluation(Contract):
    model_version: Literal['stock-workflow-evaluation-v1'] = 'stock-workflow-evaluation-v1'
    checked_on: date
    status: Literal['passed', 'failed', 'incomplete']
    input_summary: EvaluationInputs
    checks: list[WorkflowCheck] = Field(default_factory=list)
    public_release_id: str | None
    market_snapshot_sha256: str | None
    universe_sha256: str | None
    listing_reference_hashes: dict[str, str]
    policy_sha256: str = POLICY_HASH
    strategy_sha256: str = SPEC_HASH
    production_ready: Literal[False] = False
    investment_performance_verified: Literal[False] = False
    notice: str = ('Software behavior checks using fixed example inputs and installed evidence, not your holdings. '
        'Passing does not certify source accuracy, coverage, investment performance, security or production readiness. '
        'No historical strategy backtest, observed beginner study or public-display approval is established.')


class _Blocked(Exception):
    pass


def evaluate_stock_workflow(screen):
    context = DecisionContext(acknowledge_experimental=True, new_cash_cents=100003,
        monthly_contribution_cents=100003)
    checks = []
    state = {}

    def require(condition):
        if not condition:
            raise ValueError('Workflow invariant failed')

    def run(check_id, title, action, detail):
        try:
            action()
            status = 'passed'
        except _Blocked as blocked:
            status, detail = 'blocked', (str(blocked) or 'Required current evidence or a prior check result is unavailable. This path was not accepted.')
        except Exception:
            # Never expose internal exception text, private settings or filesystem paths.
            status, detail = 'failed', 'A software check failed. Inspect local tests; no investment conclusion follows.'
        checks.append(WorkflowCheck(check_id=check_id, title=title, status=status, detail=detail))

    def current():
        result = state.get('assessment')
        if result is None or result.status != 'experimental':
            raise _Blocked()
        return result

    def candidates():
        cards = [card for card in current().cards if card.outcome == 'buy_candidate']
        if len(cards) != 10:
            raise _Blocked(f'Only {len(cards)} of 10 experimental candidates are available. Inspect the input summary and company evidence; this path was not accepted.')
        return cards

    def consent():
        result = assess_decisions(screen, DecisionContext())
        require(result.status == 'acknowledgement_required' and not result.cards)

    def initial_accounting():
        state['assessment'] = assess_decisions(screen, context)
        result = current()
        require(result.cash_unassigned_cents >= 0 and result.cash_unassigned_cents +
            sum(card.paper_addition_cents for card in result.cards) == 100003)
        require(not result.live_recommendations_enabled)

    def short_horizon():
        current()
        result = assess_decisions(screen, context.model_copy(update={'horizon_years': 1}))
        require(not any(card.paper_addition_cents for card in result.cards) and result.cash_unassigned_cents == 100003)

    def portability():
        record = freeze_decision(current(), name='Fixed example workflow check', saved_on=screen.checked_on)
        restored = restore_decision(record.model_dump_json(), today=screen.checked_on)
        require(restored == record and restored.assessment.context.new_cash_cents == 100003)
        state['record'] = restored

    def recompute():
        if 'record' not in state:
            raise _Blocked()
        review = review_decision(state['record'], screen, acknowledge_experimental=True)
        require(review.status == 'reviewed' and not review.changes and review.current == current())

    def monthly():
        candidates()
        result = plan_monthly_contribution(screen, context)
        require(result.status == 'allocated' and result.monthly_amount_cents == 100003)
        require(result.to_stocks_cents + result.cash_unassigned_cents == 100003)
        require(result.to_stocks_cents == sum(row.purchase_cents for row in result.positions))
        require(all(row.before_cents == 0 and row.after_cents == row.purchase_cents and
            row.after_cents <= 10000 for row in result.positions))
        require(not result.automatic_schedule_enabled and not result.live_recommendations_enabled)

    def exclusion():
        original = candidates()
        symbol = original[0].symbols[0]
        result = assess_decisions(screen, context.model_copy(update={'excluded_symbols': [symbol]}))
        before = {card.issuer_key: card.research_score for card in current().cards}
        require(all(card.research_score == before[card.issuer_key] for card in result.cards))
        require(all(not card.paper_addition_cents for card in result.cards if symbol in card.symbols))
        require(sum(card.paper_addition_cents for card in result.cards) + result.cash_unassigned_cents == 100003)

    def cap():
        candidates()
        result = plan_monthly_contribution(screen, context.model_copy(update={'maximum_direct_weight': Decimal('.05')}))
        require(result.status == 'allocated' and result.to_stocks_cents == 50000 and result.cash_unassigned_cents == 50003)
        require(all(row.after_cents <= 5000 for row in result.positions))

    def personal_note():
        # Notes are personal inputs, independent of market freshness or rankings.
        symbol = 'EXAMPLE'
        entered = context.model_copy(update={'holdings': [DecisionHolding(symbol=symbol, value_cents=100003)]})
        note = save_holding_note(entered, symbol, HoldingReviewInputs(notes='Fixed example opinion'), saved_on=screen.checked_on)
        require(restore_holding_note(note.model_dump_json(), entered, today=screen.checked_on) == note)

    def stale():
        old = screen.model_copy(deep=True)
        old.universe.fresh = False
        result = assess_decisions(old, context)
        monthly = plan_monthly_contribution(old, context)
        require(result.status == 'unavailable' and not result.cards and result.cash_unassigned_cents == 100003)
        require(monthly.status == 'unavailable' and monthly.to_stocks_cents == 0 and monthly.cash_unassigned_cents == 100003)

    run('consent', 'Research requires opt-in', consent, 'No company assessment is returned without experimental consent.')
    run('initial_accounting', 'Initial cash reconciles', initial_accounting, 'Example additions and cash total exactly $1,000.03; verified recommendations stay disabled.')
    run('short_horizon', 'Short horizon withholds purchases', short_horizon, 'A one-year example leaves all initial cash unassigned under the published policy.')
    run('decision_portability', 'Save and reopen a decision', portability, 'The bounded JSON roundtrip preserves exact cents and the assessment.')
    run('same_evidence_recompute', 'Same evidence gives the same decision', recompute, 'Recomputing a saved example reports no changes.')
    run('monthly_accounting', 'Monthly deposit reconciles', monthly, 'One $1,000.03 deposit reconciles without assuming the initial proposal was purchased.')
    run('exclusion_sensitivity', 'Exclusions preserve company scores', exclusion, 'Excluding one candidate blocks its addition without rewriting company scores.')
    run('concentration_cap', 'Tighter limits leave cash aside', cap, 'A 5% per-stock cap limits ten additions to $50.00 each and leaves $500.03 in cash.')
    run('holding_note_portability', 'Personal notes reopen separately', personal_note, 'An example personal opinion roundtrips without importing a company judgment.')
    run('stale_withholding', 'Stale references withhold purchases', stale, 'Both initial and monthly examples withhold purchases when references are stale.')
    status = 'failed' if any(row.status == 'failed' for row in checks) else (
        'incomplete' if any(row.status == 'blocked' for row in checks) else 'passed')
    assessment = state.get('assessment')
    available = assessment is not None and assessment.status == 'experimental'
    prices = sorted(row.valuation.price_date for row in screen.rows if row.valuation.price_date is not None)
    summary = EvaluationInputs(screen_status=screen.status, references_fresh=screen.universe.fresh,
        reference_observed_on=screen.universe.observed_on, company_count=len(screen.rows),
        candidate_count=sum(card.outcome == 'buy_candidate' for card in assessment.cards) if available else None,
        oldest_price_date=prices[0] if prices else None, newest_price_date=prices[-1] if prices else None,
        blocking_reason_counts=dict(sorted(Counter(reason.code for card in assessment.cards
            if card.outcome != 'buy_candidate' for reason in card.reasons if reason.code != 'not_selected').items())) if available else {})
    return StockWorkflowEvaluation(checked_on=screen.checked_on, status=status, checks=checks,
        input_summary=summary,
        public_release_id=screen.public_release_id, market_snapshot_sha256=screen.market_snapshot_sha256,
        universe_sha256=screen.universe.source_sha256, listing_reference_hashes=screen.listing_reference_hashes)
