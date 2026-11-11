from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import pytest

from class_quantity_review import load_quantity_reviews,match_historical_class_quantity,ReviewRegistry
from class_share_ledger import ClassObservation,FilingPointObservation,LedgerSource

DAY=date(2026,11,3)


def evidence():
    registry=load_quantity_reviews()
    source=LedgerSource(source_url='https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm',
        source_sha256='c28f94b10f309d5433f9381221dbf961668a419d832c6990c23a7643850db0da',retrieved_at='2026-10-31T12:00:00Z')
    cover=ClassObservation(symbol='AAPL',class_title='Common Stock, $0.00001 par value per share',exchange='NASDAQ',
        context_ref='c-2',accession='0000320193-25-000079',period_end='2025-09-27',filed_on='2025-10-31',source=source)
    point=FilingPointObservation(tag='us-gaap:CommonStockSharesOutstanding',context_ref='c-20',measured_on='2025-09-27',
        filed_on='2025-10-31',accession='0000320193-25-000079',cik=320193,shares='14773260000',scale=3,decimals='-3',
        dimensions={},scope='issuer_unallocated',source=source)
    security=SimpleNamespace(symbol='AAPL',directory_status='unique_issuer',listing_status='corroborated',
        filing_status='corroborated_filing_class',filing_observations=[cover])
    return dict(cik=320193,security=security,points=[point],today=DAY,directory_fresh=True,registry=registry)


def ledger_with_review():
    from class_share_ledger import build_class_share_ledger
    from test_class_share_ledger import inputs
    values=inputs();facts=evidence();cover=facts['security'].filing_observations[0]
    row=cover.model_dump(mode='json',exclude={'source'});row['cik']=320193
    point=facts['points'][0].model_dump(mode='json',exclude={'source'})
    values.update(cik=320193,directory={'AAPL':{320193}},today=DAY,
        class_tables=[(cover.source,[row])],filing_share_tables=[(cover.source,[point])],
        listings={'AAPL':SimpleNamespace(status='corroborated')},
        filing_checks={'AAPL':SimpleNamespace(status='corroborated_filing_class')})
    return build_class_share_ledger(**values)


def test_reviewed_statement_link_keeps_current_quantity_and_rights_unverified():
    result=match_historical_class_quantity(**evidence())
    assert result.status=='matched_historical_statement' and result.review.shares==Decimal('14773260000')
    assert result.review.measured_on==date(2025,9,27) and len(result.registry_sha256)==64
    assert not result.current_class_quantity_verified and not result.economic_rights_review_complete


def test_ledger_serialization_never_replaces_the_latest_issuer_count_or_current_class_gate():
    from class_share_ledger import ClassShareLedger
    ledger=ledger_with_review()
    restored=ClassShareLedger.model_validate_json(ledger.model_dump_json())
    security=restored.securities[0]
    assert security.historical_quantity.status=='matched_historical_statement'
    assert security.assigned_shares is None and restored.share_observation.shares==100
    assert not restored.class_quantities_reconciled and not restored.issuer_valuation_verified
    payload=restored.model_dump(mode='json')
    payload['securities'][0]['historical_quantity']['current_class_quantity_verified']=True
    with pytest.raises(ValueError):ClassShareLedger.model_validate(payload)


def test_historical_review_cannot_appear_before_its_availability_date():
    values=evidence();values['today']=date(2026,11,2)
    result=match_historical_class_quantity(**values)
    assert result.status=='review_not_yet_available' and result.review is None


@pytest.mark.parametrize('fault',['hash','title','cover_context','share_context','shares','precision','scale','cover_accession','point_accession','point_issuer','point_date','point_scope','source_url'])
def test_mismatched_source_identity_quantity_and_precision_never_match(fault):
    values=evidence();cover=values['security'].filing_observations[0];point=values['points'][0]
    if fault=='hash':point.source=point.source.model_copy(update={'source_sha256':'b'*64})
    if fault=='title':cover.class_title='Class B Common Stock'
    if fault=='cover_context':cover.context_ref='other'
    if fault=='share_context':point.context_ref='other'
    if fault=='shares':point.shares+=1
    if fault=='precision':point.decimals='-6'
    if fault=='scale':point.scale=6
    if fault=='cover_accession':cover.accession='0000320193-26-000001'
    if fault=='point_accession':point.accession='0000320193-26-000001'
    if fault=='point_issuer':point.cik=1
    if fault=='point_date':point.measured_on=date(2025,9,28)
    if fault=='point_scope':point.scope='dimensional_unassigned'
    if fault=='source_url':point.source=point.source.model_copy(update={'source_url':'https://example.com/other'})
    assert match_historical_class_quantity(**values).status in ('evidence_conflict','evidence_unavailable')


@pytest.mark.parametrize('fault',['directory','listing','filing','stale_directory','duplicate_cover','duplicate_quantity','dimensional_only','duplicate_review'])
def test_incomplete_or_ambiguous_evidence_does_not_choose_a_convenient_match(fault):
    values=evidence();security=values['security']
    if fault=='directory':security.directory_status='ambiguous_issuer'
    if fault=='listing':security.listing_status='exchange_conflict'
    if fault=='filing':security.filing_status='stale'
    if fault=='stale_directory':values['directory_fresh']=False
    if fault=='duplicate_cover':security.filing_observations*=2
    if fault=='duplicate_quantity':values['points']*=2
    if fault=='dimensional_only':values['points'][0].dimensions={'custom:ClassAxis':'custom:A'}
    if fault=='duplicate_review':
        digest,reviews=values['registry'];values['registry']=(digest,reviews+[deepcopy(reviews[0])])
    assert match_historical_class_quantity(**values).status!='matched_historical_statement'


def test_missing_review_and_registry_conflicts_are_explicit():
    values=evidence();values['security'].symbol='OTHER'
    assert match_historical_class_quantity(**values).status=='not_reviewed'
    _,reviews=load_quantity_reviews()
    with pytest.raises(ValueError):ReviewRegistry(review_version='dated-class-statement-review-v1',reviews=reviews+[reviews[0]])
