import json
from datetime import date
import pytest
from holding_notes import save_holding_note, restore_holding_note
from holding_research import HoldingReviewInputs
from stock_decisions import DecisionContext, DecisionHolding

DAY = date(2026, 11, 7)


def context(consent=True):
    return DecisionContext(acknowledge_experimental=consent,
        holdings=[DecisionHolding(symbol='AAPL', value_cents=100003)])


def test_roundtrip_restores_only_personal_notes_without_financial_assumptions():
    inputs = HoldingReviewInputs(reason_state='concerns', notes='Check next filing',
        illustrate_full_sale=True, assumed_sale_fee_cents=503, purchase_cost_cents=90000)
    note = save_holding_note(context(), 'AAPL', inputs, saved_on=DAY)
    restored = restore_holding_note(note.model_dump_json(), context(), today=DAY)
    assert restored.symbol == 'AAPL' and restored.notes == inputs.notes
    assert restored.reason_state == 'concerns'
    assert 'purchase_cost' not in note.model_dump_json() and 'value_cents' not in note.model_dump_json()
    assert not hasattr(restored, 'research_outcome')
    assert inputs.illustrate_full_sale  # originals preserved


@pytest.mark.parametrize('change', [
    {'symbol':'MSFT'}, {'saved_on':'2027-01-01'}, {'notes':'x'*501},
    {'reason_state':'verified_buy'}, {'research_outcome':'hold'}, {'format_version':'future'},
])
def test_invalid_records_cannot_inject_evidence_or_unknown_holdings(change):
    note = save_holding_note(context(), 'AAPL', HoldingReviewInputs(), saved_on=DAY)
    payload = note.model_dump(mode='json') | change
    with pytest.raises(ValueError):
        restore_holding_note(json.dumps(payload), context(), today=DAY)


def test_restore_is_bounded_and_requires_fresh_consent():
    for raw in [b'bad json', b' '*16385, b'\xff', '[]', '['*7000+'0'+']'*7000,
                '{"symbol":"AAPL","symbol":"MSFT"}']:
        with pytest.raises(ValueError): restore_holding_note(raw, context(), today=DAY)
    note = save_holding_note(context(), 'AAPL', HoldingReviewInputs(), saved_on=DAY)
    with pytest.raises(ValueError): restore_holding_note(note.model_dump_json(), context(False), today=DAY)
    with pytest.raises(ValueError): save_holding_note(context(False), 'AAPL', HoldingReviewInputs(), saved_on=DAY)


def test_changed_holding_value_does_not_turn_a_note_into_a_cost_record():
    note = save_holding_note(context(), 'AAPL', HoldingReviewInputs(notes='Personal judgment'), saved_on=DAY)
    changed = context(); changed.holdings[0].value_cents = 200000
    assert restore_holding_note(note.model_dump_json(), changed, today=DAY).notes == 'Personal judgment'
