"""Bounded portability for personal notes; no imported evidence or cost basis."""
from datetime import date
from typing import Literal
from pydantic import Field
from data_pipeline import Contract
from experimental_basket import Symbol
from holding_research import HoldingReviewInputs
from stock_decisions import DecisionContext
from public_data_store import strict_json


class HoldingNote(Contract):
    format_version: Literal['personal-holding-note-v1'] = 'personal-holding-note-v1'
    symbol: Symbol
    saved_on: date
    reason_state: Literal['not_reviewed', 'still_supported', 'concerns', 'no_longer_supported']
    notes: str = Field(max_length=500)


def _require_holding(context, symbol):
    if not context.acknowledge_experimental or not any(row.symbol == symbol for row in context.holdings):
        raise ValueError('Opt in and enter the exact holding before restoring personal notes.')


def save_holding_note(context: DecisionContext, symbol: str, inputs: HoldingReviewInputs, *, saved_on: date):
    _require_holding(context, symbol)
    return HoldingNote(symbol=symbol, saved_on=saved_on, reason_state=inputs.reason_state, notes=inputs.notes)


def restore_holding_note(raw: str | bytes, context: DecisionContext, *, today: date):
    try:
        encoded = raw.encode('utf-8') if isinstance(raw, str) else raw
        if not isinstance(encoded, bytes) or len(encoded) > 16384:
            raise ValueError('Invalid note size')
        note = HoldingNote.model_validate(strict_json(encoded))
        _require_holding(context, note.symbol)
        if note.saved_on > today:
            raise ValueError('Future saved date')
        return note
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError('Could not restore the personal note. Check format, size, date, consent and exact holding.') from None
