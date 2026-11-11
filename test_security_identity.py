from datetime import date, datetime, timezone
from types import SimpleNamespace
import pytest
from security_identity import normalize_filing_cover, corroborate_filing_class
from security_listing import ListingEvidence


DAY=date(2026,10,31)


@pytest.mark.parametrize('status,expected',[('stale','stale'),('unavailable','unavailable'),('ambiguous','ambiguous')])
def test_missing_listing_support_is_not_a_confirmed_filing_conflict(status,expected):
    ref=SimpleNamespace(source_url='https://example.test/filing',source_sha256='a'*64)
    row=dict(cik=320193,symbol='AAPL',class_title='Common Stock',filed_on='2025-10-31',
        period_end='2025-09-27',accession='test',common_stock_label=True,exchange='NASDAQ')
    result=corroborate_filing_class(320193,'AAPL',ListingEvidence(status=status),[(ref,[row])],
        today=DAY,directory_fresh=True)
    assert result.status==expected


def html(symbol='AAPL',cik='0000320193',period='2025-09-27',exchange='The Nasdaq Stock Market LLC'):
    def fact(name,value,context='base',attrs=''):
        return f'<ix:nonNumeric name="dei:{name}" contextRef="{context}" {attrs}>{value}</ix:nonNumeric>'
    return ('<html>'+fact('DocumentType','10-K')+fact('EntityCentralIndexKey',cik)+fact('DocumentPeriodEndDate',period)+
        fact('Security12bTitle','Common Stock, $0.00001 par value per share','class-a')+
        fact('TradingSymbol',symbol,'class-a')+fact('SecurityExchangeName',exchange,'class-a')+'</html>')


def normalized(tmp_path,body=None):
    path=tmp_path/'cover.html';path.write_text(body or html(),encoding='utf-8')
    return normalize_filing_cover('sec_cover_aapl_2025',path,as_of=DAY)


def test_cover_facts_keep_context_identity_and_dated_provenance(tmp_path):
    table=normalized(tmp_path)
    row=table['records'][0]
    assert row['symbol']=='AAPL' and row['cik']==320193 and row['exchange']=='NASDAQ'
    assert row['accession']=='0000320193-25-000079' and row['filed_on']=='2025-10-31'
    assert not table['summary']['all_economic_classes_verified']


def test_nested_unknown_ix_fact_does_not_truncate_the_english_period_date(tmp_path):
    body=html().replace('contextRef="base" >2025-09-27',
        'contextRef="base" format="ixt:date-monthname-day-year-en"><ix:nonNumeric name="dei:CurrentFiscalYearEndDate" contextRef="base">September 27</ix:nonNumeric>, 2025')
    assert normalized(tmp_path,body)['records'][0]['period_end']=='2025-09-27'


@pytest.mark.parametrize('body',[
    html(cik='0001045810'),html(period='2024-09-27'),html(exchange='Unknown Exchange'),
    html().replace('name="dei:SecurityExchangeName" contextRef="class-a"','name="dei:SecurityExchangeName" contextRef="class-b"'),
    html().replace('</html>','<ix:nonNumeric name="dei:TradingSymbol" contextRef="class-a">EVIL</ix:nonNumeric></html>'),
    html().replace('name="dei:TradingSymbol"','continuedAt="elsewhere" name="dei:TradingSymbol"'),
    '<html>Access denied</html>',
])
def test_bad_identity_dates_contexts_conflicts_and_continuations_are_refused(tmp_path,body):
    with pytest.raises(ValueError):normalized(tmp_path,body)


def test_corroboration_requires_current_directory_and_listing_but_never_certifies_market_cap(tmp_path):
    table=normalized(tmp_path)
    ref=SimpleNamespace(source_url='https://www.sec.gov/Archives/example',source_sha256='a'*64)
    listing=ListingEvidence(status='corroborated',exchange='NASDAQ')
    def check(**changes):
        values=dict(cik=320193,symbol='AAPL',listing=listing,tables=[(ref,table['records'])],today=DAY,directory_fresh=True)
        return corroborate_filing_class(**{**values,**changes})
    result=check()
    assert result.status=='corroborated_filing_class'
    assert not result.all_economic_classes_verified and not result.issuer_valuation_verified
    assert check(directory_fresh=False).status=='stale'
    assert check(listing=ListingEvidence(status='corroborated',exchange='NYSE')).status=='conflict'
    assert check(symbol='OTHER').status=='unavailable'
    assert check(tables=[(ref,table['records'])]*2).status=='ambiguous'
