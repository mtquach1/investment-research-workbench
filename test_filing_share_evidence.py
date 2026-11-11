from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from filing_share_evidence import filing_point_shares
from market_sources import COVER_FILINGS
from security_identity import normalize_filing_cover
from test_security_identity import html
from test_class_share_ledger import inputs, REF
from class_share_ledger import build_class_share_ledger
from tools.audit_filing_shares import reconcile

REFERENCE=COVER_FILINGS['sec_cover_aapl_2025']


def evidence(*,quantity='14,773.26',scale='6',decimals='-3',context_extra='',fact_extra=''):
    return ('<xbrli:context id="point"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>'+context_extra+
        '</xbrli:entity><xbrli:period><xbrli:instant>2025-09-27</xbrli:instant></xbrli:period></xbrli:context>'
        '<xbrli:unit id="shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>'
        f'<ix:nonFraction name="us-gaap:CommonStockSharesOutstanding" contextRef="point" unitRef="shares" format="ixt:num-dot-decimal" scale="{scale}" decimals="{decimals}" {fact_extra}>{quantity}</ix:nonFraction>')


def test_scaled_point_counts_keep_precision_and_do_not_assign_a_class(tmp_path):
    body=html()+evidence()
    path=tmp_path/'cover.html';path.write_text(body)
    rows=normalize_filing_cover('sec_cover_aapl_2025',path,as_of=date(2026,10,31))['summary']['point_share_observations']
    assert len(rows)==1 and Decimal(rows[0]['shares'])==14773260000
    assert rows[0]['decimals']=='-3' and rows[0]['scope']=='issuer_unallocated'
    assert rows[0]['measured_on']=='2025-09-27' and rows[0]['dimensions']=={}


@pytest.mark.parametrize('body',[
    evidence().replace('2025-09-27','2026-01-01'),
    evidence().replace('0000320193','0001045810'),
    evidence().replace('xbrli:shares','iso4217:USD'),
    evidence().replace('<xbrli:instant>2025-09-27</xbrli:instant>','<xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-09-27</xbrli:endDate>'),
    evidence(quantity='12,34'),evidence(quantity='1.5',scale='0'),evidence(scale='99'),
    evidence(decimals=''),evidence(fact_extra='continuedAt="other"'),evidence(fact_extra='sign="-"'),
    evidence(fact_extra='xsi:nil="true"'),evidence().replace('ixt:num-dot-decimal','ixt:unknown'),
    evidence(context_extra='<xbrldi:typedMember dimension="custom:ClassAxis">A</xbrldi:typedMember>'),
    evidence()+'<xbrli:unit id="shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>',
])
def test_unsupported_or_malformed_share_semantics_fail_closed(body):
    with pytest.raises((ValueError,KeyError)):filing_point_shares(body,REFERENCE)


def test_explicit_dimensions_are_preserved_but_never_equated_to_a_ticker():
    body=evidence(context_extra='<xbrli:segment><xbrldi:explicitMember dimension="custom:StockClassAxis">custom:ClassAMember</xbrldi:explicitMember></xbrli:segment>')
    point=filing_point_shares(body,REFERENCE)[0]
    assert point['dimensions']=={'custom:StockClassAxis':'custom:ClassAMember'}
    assert point['scope']=='dimensional_unassigned'


def test_nested_issued_fact_requires_identical_context_units_and_numeric_text():
    body=evidence(quantity='<ix:nonFraction name="us-gaap:CommonStockSharesIssued" contextRef="point" unitRef="shares" format="ixt:num-dot-decimal" scale="6" decimals="-3">14,773.26</ix:nonFraction>')
    assert Decimal(filing_point_shares(body,REFERENCE)[0]['shares'])==14773260000
    with pytest.raises(ValueError):filing_point_shares(body.replace('Issued" contextRef="point"','Issued" contextRef="different"'),REFERENCE)


def test_other_dates_and_conflicting_duplicate_facts_are_not_collapsed_or_averaged():
    body=evidence()+evidence(quantity='24,304').split('</xbrli:unit>')[1]
    assert len(filing_point_shares(body,REFERENCE))==2
    assert filing_point_shares('<html>No share facts</html>',REFERENCE)==[]


def test_ledger_and_reference_reconciliation_preserve_sources_and_detect_missing_or_mismatch():
    point=filing_point_shares(evidence(),REFERENCE)[0]
    values=inputs();values['cik']=320193;values['directory']={'AAPL':{320193}}
    ledger=build_class_share_ledger(**values,filing_share_tables=[(REF,[point])])
    assert ledger.filing_point_observations[0].shares==14773260000
    assert not ledger.class_quantities_reconciled and ledger.securities[0].assigned_shares is None
    row=SimpleNamespace(issuer_key='aapl',class_share_ledger=ledger)
    screen=SimpleNamespace(status='available',rows=[row])
    case=dict(issuer_key='aapl',tag=point['tag'],measured_on=point['measured_on'],accession=point['accession'],
        source_sha256=REF.source_sha256,shares=point['shares'],decimals=point['decimals'])
    assert reconcile(screen,[case])[0]['status']=='pass'
    assert reconcile(screen,[dict(case,shares='1')])[0]['status']=='mismatch'
    assert reconcile(screen,[dict(case,source_sha256='b'*64)])[0]['status']=='unavailable'
    ledger.filing_point_observations.append(deepcopy(ledger.filing_point_observations[0]))
    assert reconcile(screen,[case])[0]['status']=='ambiguous'
