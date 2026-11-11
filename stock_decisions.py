"""Pure experimental decision triage. Scores, evidence and personal fit stay separate."""
from collections import Counter
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from data_pipeline import Contract
from experimental_basket import Symbol, ExperimentalRequest, experimental_basket
from stock_strategy import SPEC_HASH
from public_data_store import canonical_bytes
from stock_evidence import company_evidence, CompanyEvidence

POLICY = json.loads((Path(__file__).parent / 'strategies/decision_policy_v1.json').read_text(encoding='utf-8'))
POLICY_HASH = hashlib.sha256(canonical_bytes(POLICY)).hexdigest()


class DecisionHolding(Contract):
    symbol: Symbol
    value_cents: int = Field(gt=0, le=100000000, strict=True)


class DecisionContext(Contract):
    acknowledge_experimental: bool = Field(default=False, strict=True)
    new_cash_cents: int = Field(default=1000000, ge=0, le=100000000, strict=True)
    monthly_contribution_cents: int = Field(default=0, ge=0, le=10000000, strict=True)
    horizon_years: int = Field(default=5, ge=0, le=60, strict=True)
    maximum_direct_weight: Decimal = Field(default=Decimal('.30'), gt=0, le=1, allow_inf_nan=False)
    maximum_volatility: Decimal | None = Field(default=None, ge=0, le=10, allow_inf_nan=False)
    excluded_symbols: list[Symbol] = Field(default_factory=list, max_length=100)
    holdings: list[DecisionHolding] = Field(default_factory=list, max_length=25)

    @model_validator(mode='after')
    def bounded_unique(self):
        if len(set(self.excluded_symbols)) != len(self.excluded_symbols):
            raise ValueError('Duplicate exclusions')
        if len({row.symbol for row in self.holdings}) != len(self.holdings):
            raise ValueError('Duplicate holdings')
        if sum(row.value_cents for row in self.holdings) > 100000000:
            raise ValueError('Total holdings exceed $1 million')
        return self


class DecisionReason(Contract):
    code: str
    detail: str


class DecisionCard(Contract):
    issuer_key: str | None = None
    company: str
    symbols: list[str]
    outcome: Literal['buy_candidate', 'hold', 'review_for_trim_or_sell', 'pass', 'insufficient_evidence']
    reasons: list[DecisionReason]
    review_flags: list[DecisionReason] = Field(default_factory=list)
    evidence: CompanyEvidence | None = None
    research_score: float | None = None
    held_value_cents: int = 0
    paper_addition_cents: int = 0
    supporting_evidence: list[str] = Field(default_factory=list)
    contrary_evidence: list[str] = Field(default_factory=list)
    revisit_when: list[str] = Field(default_factory=list)


class DecisionAssessment(Contract):
    model_version: Literal['stock-decision-workflow-v1'] = 'stock-decision-workflow-v1'
    policy_sha256: str = POLICY_HASH
    strategy_sha256: str = SPEC_HASH
    checked_on: date
    status: Literal['acknowledgement_required', 'unavailable', 'experimental']
    context: DecisionContext
    public_release_id: str | None
    market_snapshot_sha256: str | None
    universe_sha256: str | None
    listing_reference_hashes: dict[str, str]
    baseline_status: str | None = None
    cards: list[DecisionCard] = Field(default_factory=list)
    outcome_counts: dict[str, int] = Field(default_factory=dict)
    cash_unassigned_cents: int
    live_recommendations_enabled: Literal[False] = False
    notice: str = 'Experimental research triage, not a verified recommendation or complete hold/sell judgment. Hold means these limited rules still pass. Review means investigate, not execute a sale. News, taxes, costs, share-class aggregation and ETF look-through are incomplete. Monthly contributions are recorded intentions, not allocated or forecast.'


def assess_decisions(screen, context: DecisionContext):
    base = dict(checked_on=screen.checked_on, context=context, public_release_id=screen.public_release_id,
        market_snapshot_sha256=screen.market_snapshot_sha256, universe_sha256=screen.universe.source_sha256,
        listing_reference_hashes=screen.listing_reference_hashes, cash_unassigned_cents=context.new_cash_cents)
    if not context.acknowledge_experimental:
        return DecisionAssessment(**base, status='acknowledgement_required')
    if screen.status != 'available' or not screen.universe.fresh:
        return DecisionAssessment(**base, status='unavailable')
    # Personal constraints never change the baseline accounting score/peer set.
    basket = experimental_basket(screen, ExperimentalRequest(acknowledge_proxy_and_estimates=True,
        budget_cents=context.new_cash_cents))
    findings = {row.issuer_key: row for row in basket.findings}
    purchases = {row.issuer_key: row for row in basket.selected}
    holdings = {row.symbol: row.value_cents for row in context.holdings}
    holding_total = sum(holdings.values())
    issuer_counts = Counter(row.cik for row in screen.rows)
    symbol_counts = Counter(symbol for row in screen.rows for symbol in row.tickers)
    cards = []
    def reason(code, detail):
        return DecisionReason(code=code, detail=detail)
    for row in sorted(screen.rows, key=lambda row: row.issuer_key):
        finding = findings[row.issuer_key]
        symbol = row.tickers[0] if len(row.tickers) == 1 else None
        held = sum(holdings.get(item, 0) for item in row.tickers)
        missing, failed, fit = [], [], []
        evidence = company_evidence(row)
        # Strict identity/membership remain missing globally. This explicit variant
        # accepts proxy/estimates only; it cannot alter the strict proposal engine.
        for check in evidence.checks:
            if check.code in ('security_identity', 'index_membership', 'listing', 'filing_class', 'class_share_reconciliation'):
                continue
            if check.status == 'missing': missing.append(reason(check.code, check.detail))
            elif check.status == 'fail': failed.append(reason(check.code, check.detail))
        if issuer_counts[row.cik] != 1 or not symbol or symbol_counts[symbol] != 1:
            missing.append(reason('ambiguous_identity', 'No unique issuer and exact single security mapping; no class or duplicate is guessed.'))
        listing = row.listing_evidence.get(symbol) if symbol else None
        if listing and listing.status in ('exchange_conflict', 'flagged_security', 'not_found', 'ambiguous'):
            missing.append(reason('listing_conflict', 'Listing evidence is unresolved or contradictory. Resolve identity before assessing.'))
        filing = row.filing_class_evidence.get(symbol) if symbol else None
        if filing and filing.status in ('conflict','ambiguous'):
            missing.append(reason('filing_class_conflict', 'Registered class evidence is conflicting or ambiguous. Resolve it before assessing.'))
        if not row.proxy_member:
            missing.append(reason('proxy_membership', 'Issuer is absent from the dated research universe.'))
        yields = (row.valuation.annual_earnings_yield_estimate, row.valuation.annual_fcf_yield_estimate)
        if any(value is None for value in yields):
            missing.append(reason('valuation_yields', 'Both annual valuation yields are required.'))
        elif any(value <= 0 for value in yields):
            failed.append(reason('nonpositive_yield', 'Both annual estimated earnings and free-cash-flow yields must be positive.'))
        if context.maximum_volatility is not None:
            risk = row.metrics.get('annualized_volatility')
            if risk is None or risk.status != 'available' or risk.value is None:
                missing.append(reason('volatility_missing', 'Your volatility limit cannot be checked without available complete risk observations.'))
            elif risk.value > context.maximum_volatility:
                fit.append(reason('volatility_limit', 'Historical annualized volatility exceeds your entered ceiling; this is not a forecast.'))
        if set(row.tickers) & set(context.excluded_symbols):
            fit.append(reason('excluded', 'Matches your explicit purchase exclusion. For an existing holding, review why the restriction changed.'))
        if context.horizon_years < POLICY['minimum_horizon_years']:
            fit.append(reason('short_horizon', 'Below this research policy’s five-year horizon preference; this threshold is not a validated suitability test.'))
        if held and Decimal(held) > context.maximum_direct_weight * holding_total:
            fit.append(reason('concentration', 'Current entered direct holding exceeds your weight cap, measured against entered holdings only. Cash and ETF look-through are excluded.'))
        purchase = purchases.get(row.issuer_key)
        if purchase and not held and Decimal(purchase.purchase_cents) > context.maximum_direct_weight * (holding_total + context.new_cash_cents):
            fit.append(reason('proposed_concentration', 'The original paper addition would exceed your direct-position cap against holdings plus new cash. No smaller amount or replacement is invented.'))
        # Missing evidence wins over negative judgments. Known review flags are
        # still visible, so uncertainty does not erase a concentration problem.
        if missing:
            outcome, reasons = 'insufficient_evidence', missing
        elif held and (failed or fit):
            outcome, reasons = 'review_for_trim_or_sell', failed + fit
        elif failed or fit:
            outcome, reasons = 'pass', failed + fit
        elif finding.score is None:
            outcome, reasons = 'insufficient_evidence', [reason('peer_evidence', '; '.join(finding.reasons) or 'Qualified sector peers are unavailable.')]
        elif held:
            outcome, reasons = 'hold', [reason('holding_rules_pass', 'Existing holding still meets the supported research rules. Rank removal alone is not a sell signal.')]
        elif basket.status != 'research_basket':
            outcome, reasons = 'insufficient_evidence', [reason('basket_infeasible', basket.reason)]
        elif purchase:
            outcome, reasons = 'buy_candidate', [reason('baseline_selected', 'Selected by the baseline quality/value strategy and passes entered constraints. Experimental candidate for investigation only.')]
        else:
            outcome, reasons = 'pass', [reason('not_selected', 'Not selected under the fixed ten-position/sector rules. This is a portfolio opportunity limit, not a failed business or sell signal.')]
        addition = purchase.purchase_cents if purchase and outcome == 'buy_candidate' else 0
        cards.append(DecisionCard(issuer_key=row.issuer_key, company=row.company, symbols=row.tickers,
            outcome=outcome, reasons=reasons, review_flags=failed + fit, evidence=evidence, research_score=finding.score,
            held_value_cents=held, paper_addition_cents=addition,
            supporting_evidence=[f'{check.code}: {check.detail}' for check in evidence.checks if check.status == 'pass'],
            contrary_evidence=[item.detail for item in failed + fit] + ['Membership is a proxy; issuer valuation is a filing-based annual estimate, not TTM or verified current value.'],
            revisit_when=['New filings, updated shares/prices or corporate actions change the evidence.',
                'Entered horizon, exclusions, volatility limit or direct exposure changes.',
                'Review material news, acquisition lots, fees and taxes before any real buy or sale.']))
    covered_symbols = {symbol for row in screen.rows for symbol in row.tickers}
    for symbol, amount in sorted(holdings.items()):
        if symbol not in covered_symbols:
            flags = [reason('concentration', 'Entered direct holding exceeds your cap against entered holdings only; underlying fund exposure is unresolved.')] if Decimal(amount) > context.maximum_direct_weight * holding_total else []
            cards.append(DecisionCard(company=symbol, symbols=[symbol], outcome='insufficient_evidence', held_value_cents=amount,
                reasons=[reason('holding_not_covered', 'No installed company evidence for this exact symbol; ETF and renamed-symbol mappings are not inferred.')],
                review_flags=flags, contrary_evidence=[item.detail for item in flags],
                revisit_when=['Install and verify exact security evidence.']))
    base['cash_unassigned_cents'] -= sum(card.paper_addition_cents for card in cards)
    return DecisionAssessment(**base, status='experimental', baseline_status=basket.status, cards=cards,
        outcome_counts=dict(Counter(card.outcome for card in cards)))
