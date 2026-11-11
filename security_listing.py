"""Exact official listing metadata cross-checks; never guessed CIK/class mappings."""
import csv
from datetime import date,datetime
from zoneinfo import ZoneInfo
import re
from collections import defaultdict
from typing import Literal
from pydantic import Field
from data_pipeline import Contract


LISTING_SOURCES=('nasdaq_listed_directory','nasdaq_other_directory')
EXCHANGES={'N':'NYSE','A':'NYSE_AMERICAN','P':'NYSE_ARCA','Z':'CBOE_BZX','V':'IEX'}
# CBOE's SEC label is corroborated by its own primary-listing transfer notice:
# https://cdn.cboe.com/resources/release_notes/2018/Cboe-Corporate-Listing-Transfer.pdf
SEC_EXCHANGES={'Nasdaq':'NASDAQ','NYSE':'NYSE','NYSE American':'NYSE_AMERICAN','NYSEArca':'NYSE_ARCA','Cboe BZX':'CBOE_BZX','CBOE':'CBOE_BZX'}


def normalize_listing_directory(source_id,path,*,as_of):
    from source_adapters import _table
    nasdaq=source_id=='nasdaq_listed_directory'
    if source_id not in LISTING_SOURCES:raise ValueError('Unregistered listing source')
    text=path.read_text(encoding='utf-8-sig')
    if len(text)>8*1024*1024:raise ValueError('Listing directory exceeds byte budget')
    lines=text.splitlines()
    if not 3<=len(lines)<=25002:raise ValueError('Listing directory row budget')
    footer=re.fullmatch(r'File Creation Time: (\d{8})(\d{2}):(\d{2})\|*',lines[-1])
    if not footer:raise ValueError('Missing final creation timestamp')
    stamp=datetime.strptime(footer[1]+footer[2]+footer[3],'%m%d%Y%H%M')
    if stamp.date()>as_of:raise ValueError('Future listing observation')
    expected=(['Symbol','Security Name','Market Category','Test Issue','Financial Status','Round Lot Size','ETF','NextShares'] if nasdaq else
        ['ACT Symbol','Security Name','Exchange','CQS Symbol','ETF','Round Lot Size','Test Issue','NASDAQ Symbol'])
    reader=csv.DictReader(lines[:-1],delimiter='|')
    if reader.fieldnames!=expected:raise ValueError('Unexpected listing columns')
    rows=[]
    for row in reader:
        if None in row or any(value is None for value in row.values()):raise ValueError('Truncated listing row')
        if any(row[key] not in ('Y','N') for key in ('ETF','Test Issue')):raise ValueError('Invalid listing flags')
        if not row['Security Name'].strip() or len(row['Security Name'])>512:raise ValueError('Invalid security name')
        aliases=({'NASDAQ':row['Symbol']} if nasdaq else {name:row[key] for name,key in [('ACT','ACT Symbol'),('CQS','CQS Symbol'),('NASDAQ','NASDAQ Symbol')]})
        if any(not value or len(value)>30 or not value.isascii() or any(ord(char)<32 for char in value) for value in aliases.values()):
            raise ValueError('Invalid explicit source symbol')
        if nasdaq and row['Market Category'] not in ('Q','G','S'):raise ValueError('Unknown Nasdaq market category')
        if not row['Round Lot Size'].isdigit() or not 1<=int(row['Round Lot Size'])<=1000000:raise ValueError('Invalid round lot')
        title=row['Security Name'];lower=title.casefold()
        kind='ETF' if row['ETF']=='Y' else 'test_issue' if row['Test Issue']=='Y' else (
            'other_security' if any(token in lower for token in ('preferred','warrant','depositary','depository','units','rights','notes','debenture')) else
            'common_equity_name' if any(token in lower for token in ('common stock','common shares','ordinary share')) else 'unclassified')
        rows.append({'record_id':row['Symbol'] if nasdaq else row['ACT Symbol'],'aliases':aliases,'security_name':title,
            'exchange':'NASDAQ' if nasdaq else EXCHANGES.get(row['Exchange'],'unsupported:'+row['Exchange']),
            'etf':row['ETF']=='Y','test_issue':row['Test Issue']=='Y','financial_status':row['Financial Status'] if nasdaq else None,
            'security_kind_hint':kind,'provider_creation_stamp':stamp.isoformat(),'creation_timezone':'not_asserted'})
    return _table('security_listing_metadata',rows,stamp.date().isoformat(),listing_schema_version='nasdaq-directory-v1',
        observation_date_basis='provider_file_creation_date_timezone_unspecified',security_count=len(rows),
        official_index_membership_verified=False,issuer_identity_verified=False)


class ListingEvidence(Contract):
    status: Literal['corroborated','listing_only','unavailable','not_found','stale','ambiguous','exchange_conflict','flagged_security']='unavailable'
    source_id: str | None = None
    source_sha256: str | None = None
    observed_on: date | None = None
    security_name: str | None = None
    exchange: str | None = None
    matched_namespaces: list[str] = Field(default_factory=list)
    security_kind_hint: str | None = None
    etf: bool | None = None
    test_issue: bool | None = None
    financial_status: str | None = None
    reason: str = 'No installed official listing reference.'
    issuer_identity_verified: Literal[False]=False
    index_membership_verified: Literal[False]=False


def listing_index(tables):
    index=defaultdict(dict)
    for source_id,(reference,records) in tables.items():
        for row in records:
            for symbol in set(row['aliases'].values()):
                index[symbol][(source_id,row['record_id'])]=(reference,row,source_id)
    return index


def listing_reference_fresh(reference, *, today):
    """Receipt ages use the same Los Angeles calendar as stock assessment dates."""
    receipt=reference.retrieved_at
    return (reference.observation_date is not None and receipt.tzinfo is not None
        and 0 <= (today-reference.observation_date).days <= 7
        and 0 <= (today-receipt.astimezone(ZoneInfo('America/Los_Angeles')).date()).days <= 7)


def corroborate_listing(symbol,sec_exchanges,index,*,today,complete_fresh=False):
    candidates=list(index.get(symbol,{}).values())
    if not candidates:return ListingEvidence(status='not_found' if complete_fresh else 'unavailable',reason='No exact symbol in both fresh installed directories.' if complete_fresh else 'No exact listing match; directory coverage is incomplete or unavailable. Punctuation aliases are never guessed.')
    if len(candidates)!=1:return ListingEvidence(status='ambiguous',reason='An exact symbol refers to more than one listing record; no preferred mapping is guessed.')
    reference,row,source_id=candidates[0]
    base=dict(source_id=source_id,source_sha256=reference.source_sha256,observed_on=reference.observation_date,
        security_name=row['security_name'],exchange=row['exchange'],matched_namespaces=[key for key,value in row['aliases'].items() if value==symbol],
        security_kind_hint=row['security_kind_hint'],etf=row['etf'],test_issue=row['test_issue'],financial_status=row['financial_status'])
    if not listing_reference_fresh(reference,today=today):
        return ListingEvidence(**base,status='stale',reason='Listing source is stale, future or undated.')
    if row['etf'] or row['test_issue'] or row['security_kind_hint']=='other_security' or row['financial_status'] not in (None,'N'):
        return ListingEvidence(**base,status='flagged_security',reason='Directory flags a fund, test issue, other security type or non-normal listing status. Inspect the source; this is not a common-equity confirmation.')
    exchanges={SEC_EXCHANGES.get(value) for value in sec_exchanges}
    if not sec_exchanges or None in exchanges or row['exchange'].startswith('unsupported:'):
        return ListingEvidence(**base,status='listing_only',reason='Exact listing observed, but supported SEC exchange corroboration is unavailable.')
    if exchanges!={row['exchange']}:
        return ListingEvidence(**base,status='exchange_conflict',reason='SEC and listing exchange references disagree.')
    return ListingEvidence(**base,status='corroborated',reason='Exact source symbol and exchange agree with the SEC directory. Security name/type is provider metadata, not verified legal share-class identity, index membership or issuer valuation.')
