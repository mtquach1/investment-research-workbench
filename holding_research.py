"""Grounded holding-review explanations and opt-in pre-tax illustrations."""
from datetime import date
from typing import Literal
from decimal import Decimal
from pydantic import Field
from data_pipeline import Contract
from experimental_basket import Symbol
from stock_decisions import DecisionContext,assess_decisions


class HoldingReviewInputs(Contract):
    reason_state: Literal['not_reviewed','still_supported','concerns','no_longer_supported']='not_reviewed'
    notes: str = Field(default='',max_length=500)
    illustrate_full_sale: bool = Field(default=False,strict=True)
    assumed_sale_fee_cents: int = Field(default=0,ge=0,le=100000000,strict=True)
    purchase_cost_cents: int | None = Field(default=None,ge=0,le=1000000000,strict=True)


class HoldingReviewRequest(Contract):
    context: DecisionContext
    symbol: Symbol
    inputs: HoldingReviewInputs = Field(default_factory=HoldingReviewInputs)


class SaleIllustration(Contract):
    entered_value_cents: int
    assumed_fee_cents: int
    cash_before_tax_cents: int
    change_from_entered_cost_cents: int | None
    fee_percent_of_value: Decimal
    notice: str='Whole-position illustration using your entered value, not a live execution quote. Taxes, tax lots, spreads and price changes are not modeled. No loss tax benefit is assumed. Cash stays pre-tax; this does not recommend selling.'


class HoldingReview(Contract):
    model_version: Literal['holding-research-review-v1']='holding-research-review-v1'
    status: Literal['acknowledgement_required','needs_evidence','review_needed','limited_checks_pass']
    checked_on: date
    symbol: str
    summary: str
    inputs: HoldingReviewInputs | None = None
    research_outcome: str | None = None
    concerns: list[str] = Field(default_factory=list)
    evidence_details: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    illustration: SaleIllustration | None = None
    sale_recommended: Literal[False]=False
    llm_used: Literal[False]=False


def review_owned_holding(screen,request: HoldingReviewRequest):
    base=dict(checked_on=screen.checked_on,symbol=request.symbol)
    if not request.context.acknowledge_experimental:
        return HoldingReview(**base,status='acknowledgement_required',summary='Opt in to experimental research before reviewing a holding.')
    holding=next((item for item in request.context.holdings if item.symbol==request.symbol),None)
    if holding is None:raise ValueError('An exact entered holding is required')
    assessment=assess_decisions(screen,request.context)
    card=next((item for item in assessment.cards if request.symbol in item.symbols),None)
    inputs=request.inputs;concerns=[]
    if inputs.reason_state=='not_reviewed':concerns.append('You have not reviewed your original reason for owning this stock.')
    elif inputs.reason_state=='concerns':concerns.append('You reported concerns about your original reason for owning this stock.')
    elif inputs.reason_state=='no_longer_supported':concerns.append('You reported that your original reason no longer holds. This is your judgment, not a verified company fact.')
    if card:concerns.extend(item.detail for item in card.review_flags)
    if card is None or card.outcome=='insufficient_evidence':
        status='needs_evidence';summary='More company evidence is needed. A data gap does not mean the company is doing badly.'
    elif card.outcome!='hold' or inputs.reason_state!='still_supported':
        status='review_needed';summary='Review the concerns before deciding whether to keep or change this holding. No sale is recommended by this tool.'
    else:
        status='limited_checks_pass';summary='The limited company checks and your stated reason still pass. This does not establish that holding is the best choice.'
    illustration=None
    if inputs.illustrate_full_sale:
        value=holding.value_cents;fee=inputs.assumed_sale_fee_cents
        if fee>value:raise ValueError('Assumed sale fee cannot exceed the entered holding value')
        cash=value-fee
        illustration=SaleIllustration(entered_value_cents=value,assumed_fee_cents=fee,cash_before_tax_cents=cash,
            change_from_entered_cost_cents=cash-inputs.purchase_cost_cents if inputs.purchase_cost_cents is not None else None,
            fee_percent_of_value=Decimal(fee)/Decimal(value)*100)
    return HoldingReview(**base,status=status,summary=summary,inputs=inputs,
        research_outcome=card.outcome if card else None,concerns=concerns,
        evidence_details=[item.detail for item in card.reasons] if card else ['Current research data is stale, withheld or unavailable. Existing settings are preserved.'],
        next_steps=['Check new filings and important company announcements.',
            'Review your reason for owning it and the largest position you are comfortable with.',
            'Check purchase records, actual trading costs and taxes before any real sale.'],illustration=illustration)
