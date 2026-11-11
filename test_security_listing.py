from datetime import date,datetime,timezone,timedelta
from types import SimpleNamespace
from copy import deepcopy
import pytest
from security_listing import normalize_listing_directory,listing_index,corroborate_listing
from test_public_data_pipeline import seed
from data_pipeline import build_release
from test_stock_screen import screen_store
from stock_screen import stock_screen
from experimental_basket import experimental_basket,ExperimentalRequest
from test_experimental_basket import research_universe


DAY=date(2026,10,28)
NASDAQ='Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\nAAPL|Apple Inc. - Common Stock|Q|N|N|40|N|N\nFUND|Example ETF|G|N|N|100|Y|N\n'
OTHER='ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nBRK.B|Example Class B Common Stock|N|BRK.B|N|100|N|BRK-B\n'
FOOTER='File Creation Time: 1028202617:01|||||||\n'


@pytest.mark.parametrize('receipt,expected',[
    (datetime(2026,11,8,3,tzinfo=timezone.utc),'corroborated'),  # Nov 7 in Los Angeles
    (datetime(2026,11,8,12,tzinfo=timezone.utc),'stale'),  # truly future local day
    (datetime(2026,10,31,3,tzinfo=timezone.utc),'stale'),  # Oct 30 locally: eight days old
    (datetime(2026,11,1,3,tzinfo=timezone.utc),'corroborated'),  # Oct 31 locally: seven days old
])
def test_listing_receipt_age_uses_the_assessment_calendar(tmp_path,receipt,expected):
    _,rows=normalized(tmp_path)
    ref=SimpleNamespace(source_sha256='a'*64,observation_date=date(2026,11,6),retrieved_at=receipt)
    index=listing_index({'nasdaq_listed_directory':(ref,rows)})
    assert corroborate_listing('AAPL',['Nasdaq'],index,today=date(2026,11,7)).status==expected


def test_missing_match_uses_locally_fresh_complete_directories(tmp_path):
    from security_listing import listing_reference_fresh
    ref=SimpleNamespace(observation_date=date(2026,11,6),retrieved_at=datetime(2026,11,8,3,tzinfo=timezone.utc))
    complete=all(listing_reference_fresh(item,today=date(2026,11,7)) for item in [ref,ref])
    assert corroborate_listing('MISSING',set(),{},today=date(2026,11,7),complete_fresh=complete).status=='not_found'
    ref.retrieved_at=datetime(2026,11,8,3)  # no assumed timezone
    assert not listing_reference_fresh(ref,today=date(2026,11,7))


def normalized(tmp_path,source='nasdaq_listed_directory',text=NASDAQ):
    path=tmp_path/(source+'.txt');path.write_text(text+FOOTER,encoding='utf-8')
    table=normalize_listing_directory(source,path,as_of=DAY)
    ref=SimpleNamespace(source_sha256='a'*64,observation_date=DAY,retrieved_at=datetime(2026,10,28,23,tzinfo=timezone.utc))
    return ref,table['records']


def test_exact_namespaced_aliases_flags_and_exchange_agreement(tmp_path):
    tables={'nasdaq_listed_directory':normalized(tmp_path),'nasdaq_other_directory':normalized(tmp_path,'nasdaq_other_directory',OTHER)}
    index=listing_index(tables)
    evidence=corroborate_listing('AAPL',{'Nasdaq'},index,today=DAY)
    assert evidence.status=='corroborated' and evidence.matched_namespaces==['NASDAQ']
    assert not evidence.issuer_identity_verified and not evidence.index_membership_verified
    assert corroborate_listing('AAPL',{'NYSE'},index,today=DAY).status=='exchange_conflict'
    assert corroborate_listing('FUND',{'Nasdaq'},index,today=DAY).status=='flagged_security'
    assert corroborate_listing('BRK-B',{'NYSE'},index,today=DAY).matched_namespaces==['NASDAQ']
    assert corroborate_listing('BRK B',{'NYSE'},index,today=DAY,complete_fresh=True).status=='not_found'
    assert corroborate_listing('BRK B',{'NYSE'},index,today=DAY).status=='unavailable'


@pytest.mark.parametrize('fault',['missing_footer','future','duplicate','bad_flag','bad_header','truncated'])
def test_malformed_directories_never_normalize(tmp_path,fault):
    text=NASDAQ+FOOTER
    if fault=='missing_footer':text=NASDAQ
    if fault=='future':text=text.replace('10282026','10292026')
    if fault=='duplicate':text=text.replace('File Creation',NASDAQ.splitlines()[1]+'\nFile Creation')
    if fault=='bad_flag':text=text.replace('|N|N|40|','|X|N|40|')
    if fault=='bad_header':text=text.replace('ETF|NextShares','ETF|Extra')
    if fault=='truncated':text=text.replace('|40|N|N','|40')
    path=tmp_path/'bad.txt';path.write_text(text,encoding='utf-8')
    with pytest.raises(ValueError):normalize_listing_directory('nasdaq_listed_directory',path,as_of=DAY)


def test_stale_ambiguous_and_listing_only_evidence_is_not_promoted(tmp_path):
    ref,records=normalized(tmp_path)
    index=listing_index({'nasdaq_listed_directory':(ref,records)})
    assert corroborate_listing('AAPL',set(),index,today=DAY).status=='listing_only'
    assert corroborate_listing('AAPL',{'Nasdaq'},index,today=DAY+timedelta(days=8)).status=='stale'
    ref.retrieved_at=datetime(2026,10,1,tzinfo=timezone.utc)
    assert corroborate_listing('AAPL',{'Nasdaq'},index,today=DAY).status=='stale'
    second=deepcopy(records[0]);second['record_id']='COLLISION'
    index=listing_index({'nasdaq_listed_directory':(ref,records+[second])})
    assert corroborate_listing('AAPL',{'Nasdaq'},index,today=DAY).status=='ambiguous'


def test_pipeline_screen_and_local_display_boundary(tmp_path):
    public,history=screen_store(tmp_path);cache=tmp_path/'raw'
    seed(cache,'nasdaq_listed_directory',NASDAQ+FOOTER)
    seed(cache,'nasdaq_other_directory',OTHER+FOOTER)
    _,manifest=build_release(cache,public,as_of=DAY,source_ids=['nasdaq_listed_directory','nasdaq_other_directory'])
    assert not manifest.tables['nasdaq_listed_directory'].policy['public_display_allowed']
    screen=stock_screen(public,history,mode='local_research',today=DAY)
    assert screen.rows[0].listing_evidence['AAPL'].status=='corroborated'
    assert screen.security_coverage[0].listing.status=='corroborated'
    assert not screen.security_coverage[0].security_identity_verified
    assert not stock_screen(public,history,today=DAY).listing_reference_hashes


def test_observed_listing_conflicts_exclude_experimental_candidates(tmp_path):
    from security_listing import ListingEvidence
    screen=research_universe(tmp_path);symbol=screen.rows[0].tickers[0]
    screen.rows[0].listing_evidence={symbol:ListingEvidence(status='exchange_conflict',reason='Independent source conflict')}
    result=experimental_basket(screen,ExperimentalRequest(acknowledge_proxy_and_estimates=True))
    finding=next(row for row in result.findings if row.symbol==symbol)
    assert finding.score is None and any('listing' in reason for reason in finding.reasons)


def test_former_issuer_symbol_cannot_price_a_current_security(tmp_path):
    from market_history import load_history,publish_history
    public,history=screen_store(tmp_path)
    _,bundle=load_history(history)
    old=bundle.series.pop('AAPL');old.symbol='OLD'
    bundle.series['OLD']=old
    publish_history(history,bundle)
    row=stock_screen(public,history,mode='local_research',today=DAY).rows[0]
    assert row.price_status=='unavailable' and row.valuation.status=='unavailable'
    assert row.metrics['annualized_volatility'].status=='missing_inputs'
