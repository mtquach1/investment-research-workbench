"""Class/share reconciliation boundaries over independent evidence fixtures."""
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from class_share_ledger import build_class_share_ledger, ClassShareLedger
from stock_evidence import company_evidence
from stock_screen import stock_screen, StockScreen
from test_stock_screen import screen_store


DAY=date(2026,10,31)
REF=SimpleNamespace(source_url='https://www.sec.gov/example',source_sha256='a'*64,
                    retrieved_at=datetime(2026,10,30,tzinfo=timezone.utc))


def inputs():
    return dict(cik=1,raw={'share_reference':{'status':'reported_point','evidence':{
        'shares':'100','unit':'shares','tag':'dei:EntityCommonStockSharesOutstanding',
        'measured_on':'2026-10-01','filed_on':'2026-10-20','accession':'point'}}},
        reference=REF,directory={'ONE':{1}},directory_reference=REF,class_tables=[],
        listings={},filing_checks={},today=DAY,directory_fresh=True)


def test_single_ticker_never_assigns_issuer_count_or_certifies_economic_classes():
    ledger=build_class_share_ledger(**inputs())
    assert ledger.share_observation.shares==100
    assert ledger.share_observation.status=='reported_unallocated'
    assert ledger.securities[0].assigned_shares is None
    assert not ledger.all_economic_classes_verified and not ledger.issuer_valuation_verified
    assert not ledger.class_quantities_reconciled
    data=ledger.model_dump(mode='json');data['class_quantities_reconciled']=True
    with pytest.raises(ValueError):ClassShareLedger.model_validate(data)


def test_ambiguous_directory_and_filing_only_symbols_are_kept_with_every_context():
    values=inputs();values['directory']={'ONE':{1,2},'TWO':{1},'UNRELATED':{3}}
    observation=dict(cik=1,symbol='OLD',class_title='Class B',exchange='NYSE',context_ref='B',
                     accession='cover',period_end='2025-12-31',filed_on='2026-02-01')
    values['class_tables']=[(REF,[observation,dict(observation,context_ref='second')])]
    ledger=build_class_share_ledger(**values)
    assert [(item.symbol,item.directory_status) for item in ledger.securities]==[
        ('OLD','filing_only'),('ONE','ambiguous_issuer'),('TWO','unique_issuer')]
    assert len(ledger.securities[0].filing_observations)==2
    assert ledger.share_observation.shares==100
    assert all(item.assigned_shares is None for item in ledger.securities)
    assert any('absent' in gap for gap in ledger.gaps) and any('more than one issuer' in gap for gap in ledger.gaps)


@pytest.mark.parametrize('change',[
    {'shares':'1.5'}, {'shares':'NaN'}, {'shares':'0'}, {'shares':True},
    {'unit':'USD'}, {'tag':'us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding'},
    {'measured_on':'2026-10-21'}, {'filed_on':'2026-11-01'}, {'accession':''},
])
def test_invalid_quantity_basis_and_future_evidence_are_refused(change):
    values=inputs();values['raw']['share_reference']['evidence'].update(change)
    with pytest.raises(ValueError):build_class_share_ledger(**values)


def test_share_and_directory_age_are_not_reset_by_recent_downloads():
    values=inputs();values['raw']['share_reference']['evidence'].update(measured_on='2026-07-03')
    assert build_class_share_ledger(**values).share_observation.status=='reported_unallocated'
    values['raw']['share_reference']['evidence']['measured_on']='2026-07-02'
    values['directory_fresh']=False
    ledger=build_class_share_ledger(**values)
    assert ledger.share_observation.status=='stale'
    assert ledger.share_observation.shares==100 and not ledger.directory_fresh
    assert ledger.share_observation.source.retrieved_at==REF.retrieved_at


@pytest.mark.parametrize('status',['ambiguous','unavailable'])
def test_missing_and_conflicting_counts_never_become_zero(status):
    values=inputs();values['raw']['share_reference']={'status':status,'evidence':None}
    ledger=build_class_share_ledger(**values)
    assert ledger.share_observation.status==status and ledger.share_observation.shares is None


def test_screen_api_contract_keeps_ledger_without_changing_estimates_or_strict_gates(tmp_path):
    public,history=screen_store(tmp_path)
    screen=stock_screen(public,history,mode='local_research',today=DAY)
    assert screen.status=='available'
    restored=StockScreen.model_validate_json(screen.model_dump_json())
    row=restored.rows[0];ledger=row.class_share_ledger
    assert ledger.share_observation.shares==row.valuation.reported_shares==100
    assert row.valuation.status=='estimated' and not screen.live_recommendations_enabled
    assert ledger.directory_source.source_sha256 and ledger.share_observation.source.source_sha256
    assert ledger.securities[0].symbol=='AAPL' and ledger.securities[0].assigned_shares is None
    check=next(item for item in company_evidence(row).checks if item.code=='class_share_reconciliation')
    assert check.status=='missing'
