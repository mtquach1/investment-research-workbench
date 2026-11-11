from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import pytest
from decision_snapshots import freeze_decision,restore_decision,review_decision,MAX_SNAPSHOT_BYTES
from stock_decisions import DecisionContext,assess_decisions
from test_experimental_basket import research_universe
from public_data_store import canonical_bytes


def saved(tmp_path):
    screen=research_universe(tmp_path)
    context=DecisionContext(acknowledge_experimental=True,new_cash_cents=100003)
    original=assess_decisions(screen,context)
    return screen,freeze_decision(original,name='Quality research',saved_on=screen.checked_on)


def reseal(payload):
    data=deepcopy(payload);data.pop('fingerprint',None)
    data['fingerprint']=hashlib.sha256(canonical_bytes(data)).hexdigest()
    return json.dumps(data)


def test_round_trip_recomputes_exact_cents_without_mutating_the_original(tmp_path):
    screen,record=saved(tmp_path);before=record.model_dump_json()
    restored=restore_decision(before,today=screen.checked_on)
    result=review_decision(restored,screen,acknowledge_experimental=True)
    assert result.status=='reviewed' and not result.changes and not result.changed_inputs
    assert result.current.context.new_cash_cents==100003 and result.current.cash_unassigned_cents==3
    assert not result.recorded_results_attested and not result.current.live_recommendations_enabled
    assert record.model_dump_json()==before and restored==record


def test_changed_constraints_are_explained_without_rewriting_saved_assessment(tmp_path):
    screen,record=saved(tmp_path)
    context=record.assessment.context.model_copy(update={'horizon_years':1})
    result=review_decision(record,screen,acknowledge_experimental=True,context_override=context)
    assert result.context_changed and 'Research settings' in result.changed_inputs
    assert result.changes and all(item.current_outcome=='pass' for item in result.changes)
    assert result.current.outcome_counts=={'pass':20} and result.current.cash_unassigned_cents==100003
    assert record.assessment.outcome_counts.get('buy_candidate')==10


def test_source_change_is_visible_even_when_outcomes_do_not_change(tmp_path):
    screen,record=saved(tmp_path);screen.market_snapshot_sha256='b'*64
    result=review_decision(record,screen,acknowledge_experimental=True)
    assert result.changed_inputs==['Price snapshot'] and not result.changes


def test_missing_evidence_and_changed_coverage_never_carry_old_candidates_forward(tmp_path):
    screen,record=saved(tmp_path)
    target=next(card.issuer_key for card in record.assessment.cards if card.outcome=='buy_candidate')
    row=next(row for row in screen.rows if row.issuer_key==target);row.price_status='fail'
    result=review_decision(record,screen,acknowledge_experimental=True)
    change=next(item for item in result.changes if item.identity=='issuer:'+target)
    assert change.current_outcome=='insufficient_evidence' and change.current_addition_cents==0
    screen.rows=[row for row in screen.rows if row.issuer_key!=target]
    result=review_decision(record,screen,acknowledge_experimental=True)
    change=next(item for item in result.changes if item.identity=='issuer:'+target)
    assert change.current_outcome is None and 'Company/holding coverage changed' in change.triggers


def test_consent_and_current_evidence_are_mandatory(tmp_path):
    screen,record=saved(tmp_path)
    assert review_decision(record,screen).status=='acknowledgement_required'
    screen.universe.fresh=False
    result=review_decision(record,screen,acknowledge_experimental=True)
    assert result.status=='unavailable' and not result.changes and not result.current.cards
    with pytest.raises(ValueError):freeze_decision(result.current,name='Unavailable',saved_on=screen.checked_on)


@pytest.mark.parametrize('fault',['checksum','version','source_path','negative_cash','negative_purchase','cash_mismatch',
    'false_verification','duplicate_card','counts','holdings','boolean_cents','empty_symbols','oversized_text'])
def test_malformed_or_forged_incoherent_records_fail_closed(tmp_path,fault):
    screen,record=saved(tmp_path);data=record.model_dump(mode='json');a=data['assessment']
    if fault=='checksum':data['name']='changed'
    if fault=='version':data['snapshot_version']='future-version'
    if fault=='source_path':a['public_release_id']='../secret'
    if fault=='negative_cash':a['cash_unassigned_cents']=-1
    if fault=='negative_purchase':a['cards'][0]['paper_addition_cents']=-1
    if fault=='cash_mismatch':a['cash_unassigned_cents']+=1
    if fault=='false_verification':a['live_recommendations_enabled']=True
    if fault=='duplicate_card':a['cards'].append(deepcopy(a['cards'][0]))
    if fault=='counts':a['outcome_counts']['hold']=1
    if fault=='holdings':a['cards'][0]['held_value_cents']=100
    if fault=='boolean_cents':a['cards'][0]['paper_addition_cents']=True
    if fault=='empty_symbols':a['cards'][0]['symbols']=[]
    if fault=='oversized_text':a['cards'][0]['company']='x'*3001
    with pytest.raises(ValueError):restore_decision(json.dumps(data) if fault=='checksum' else reseal(data),today=screen.checked_on)


def test_future_duplicate_duplicate_json_keys_and_oversized_inputs_are_refused(tmp_path):
    screen,record=saved(tmp_path);payload=record.model_dump_json()
    with pytest.raises(ValueError):restore_decision(payload,today=record.saved_on-timedelta(days=1))
    with pytest.raises(ValueError):restore_decision(payload,today=record.saved_on,known_fingerprints=[record.fingerprint])
    with pytest.raises(ValueError):restore_decision('{"name":"one","name":"two"}',today=record.saved_on)
    with pytest.raises(ValueError):restore_decision('x'*(MAX_SNAPSHOT_BYTES+1),today=record.saved_on)
    with pytest.raises(ValueError):restore_decision('['*2000+']'*2000,today=record.saved_on)


def test_plausible_forgery_is_still_unattested_and_cannot_change_current_result(tmp_path):
    screen,record=saved(tmp_path);data=record.model_dump(mode='json')
    data['assessment']['cards'][0]['company']='User supplied record name'
    forged=restore_decision(reseal(data),today=screen.checked_on)
    result=review_decision(forged,screen,acknowledge_experimental=True)
    assert not result.recorded_results_attested
    assert result.current==assess_decisions(screen,record.assessment.context)
