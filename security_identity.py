"""Dated filing-class evidence; never a full economic-class or membership certificate."""
from collections import defaultdict
from datetime import date
from html.parser import HTMLParser
import re
from typing import Literal
from data_pipeline import Contract
from market_sources import COVER_FILINGS

FIELDS={'dei:documenttype','dei:entitycentralindexkey','dei:documentperiodenddate',
    'dei:security12btitle','dei:tradingsymbol','dei:securityexchangename'}
EXCHANGES={'The Nasdaq Stock Market LLC':'NASDAQ','The Nasdaq Global Select Market':'NASDAQ',
    'The Nasdaq Global Select Market LLC':'NASDAQ','New York Stock Exchange':'NYSE'}


class _InlineCover(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active=None;self.groups=defaultdict(lambda:defaultdict(set));self.count=0
        self.depth=0;self.active_depth=0;self.excluded=0;self.transform=''
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='ix:nonnumeric':self.depth+=1
        if tag=='ix:exclude' and self.active is not None:self.excluded+=1
        if tag=='ix:nonnumeric' and not self.excluded and attrs.get('name','').lower() in FIELDS:
            if self.active is not None:raise ValueError('Nested cover facts are unsupported')
            if attrs.get('continuedat') or attrs.get('xsi:nil')=='true':raise ValueError('Continued/nil cover facts require unsupported semantics')
            context=attrs.get('contextref','')
            if not context or len(context)>256:raise ValueError('Invalid cover context')
            self.active=(context,attrs['name'].lower(),[])
            self.active_depth=self.depth;self.transform=attrs.get('format','')
    def handle_data(self,data):
        if self.active is not None and not self.excluded:
            self.active[2].append(data)
            if sum(map(len,self.active[2]))>2048:raise ValueError('Cover fact exceeds text budget')
    def handle_endtag(self,tag):
        if tag=='ix:exclude' and self.excluded:self.excluded-=1
        if tag=='ix:nonnumeric' and self.active is not None and self.depth==self.active_depth:
            context,name,parts=self.active
            value=' '.join(''.join(parts).split())
            if name=='dei:documentperiodenddate':
                if self.transform=='ixt:date-monthname-day-year-en':
                    months=('January','February','March','April','May','June','July','August','September','October','November','December')
                    match=re.fullmatch(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',value)
                    if not match or match[1] not in months:raise ValueError('Unsupported filing date text')
                    value=date(int(match[3]),months.index(match[1])+1,int(match[2])).isoformat()
                elif self.transform or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
                    raise ValueError('Unsupported filing date transformation')
            self.groups[context][name].add(value)
            self.count+=1
            if self.count>500:raise ValueError('Too many cover facts')
            self.active=None
        if tag=='ix:nonnumeric':self.depth-=1


def normalize_filing_cover(source_id,path,*,as_of):
    from source_adapters import _table
    reference=COVER_FILINGS[source_id]
    if not date.fromisoformat(reference['period_end'])<=date.fromisoformat(reference['filed_on'])<=as_of:
        raise ValueError('Filing must be known by the assessment date')
    if path.stat().st_size>8*1024*1024:raise ValueError('Filing byte limit')
    body=path.read_text(encoding='utf-8-sig')
    parser=_InlineCover();parser.feed(body);parser.close()
    if parser.active is not None:raise ValueError('Truncated inline fact')
    def singleton(field):
        values={value for group in parser.groups.values() for value in group.get(field,set())}
        if len(values)!=1:raise ValueError('Missing or conflicting filing identity')
        return next(iter(values))
    if (singleton('dei:documenttype')!='10-K' or singleton('dei:documentperiodenddate')!=reference['period_end'] or
        singleton('dei:entitycentralindexkey')!=f"{reference['cik']:010d}"):
        raise ValueError('Filing form, period or issuer does not match registered source')
    rows=[]
    for context,group in sorted(parser.groups.items()):
        if 'dei:tradingsymbol' not in group:continue
        if len(group['dei:tradingsymbol'])!=1:raise ValueError('Conflicting security symbols')
        symbol=next(iter(group['dei:tradingsymbol']))
        if symbol in ('—','–','-','N/A','None'):continue
        if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}',symbol):raise ValueError('Unsupported exact filing symbol')
        title,exchange=group.get('dei:security12btitle',set()),group.get('dei:securityexchangename',set())
        if len(title)!=1 or len(exchange)!=1:raise ValueError('Class fields must share the trading-symbol context')
        title,exchange=next(iter(title)),next(iter(exchange))
        if not title or exchange not in EXCHANGES:raise ValueError('Unsupported class or exchange label')
        rows.append(dict(record_id=symbol,symbol=symbol,cik=reference['cik'],class_title=title,
            exchange=EXCHANGES[exchange],reported_exchange=exchange,context_ref=context,
            accession=reference['accession'],filed_on=reference['filed_on'],period_end=reference['period_end'],
            common_stock_label=bool(re.match(r'^Common (Stock|Shares)\b',title,re.I))))
    from filing_share_evidence import filing_point_shares
    return _table('filing_security_classes',rows,reference['filed_on'],
        evidence_version='sec-cover-class-shares-v2',point_share_observations=filing_point_shares(body,reference),all_economic_classes_verified=False,
        official_membership_verified=False)


class FilingClassEvidence(Contract):
    status: Literal['corroborated_filing_class','unavailable','stale','conflict','ambiguous']='unavailable'
    symbol: str | None = None
    class_title: str | None = None
    filed_on: date | None = None
    period_end: date | None = None
    accession: str | None = None
    source_url: str | None = None
    source_sha256: str | None = None
    reason: str = 'No installed registered-security filing evidence.'
    all_economic_classes_verified: Literal[False] = False
    issuer_valuation_verified: Literal[False] = False
    official_index_membership_verified: Literal[False] = False


def corroborate_filing_class(cik,symbol,listing,tables,*,today,directory_fresh):
    matches=[(ref,row) for ref,rows in tables for row in rows if row['cik']==cik and row['symbol']==symbol]
    if not matches:return FilingClassEvidence(symbol=symbol)
    if len(matches)!=1:return FilingClassEvidence(status='ambiguous',symbol=symbol,reason='Multiple filing references; no newest class is guessed.')
    ref,row=matches[0]
    base=dict(symbol=symbol,class_title=row['class_title'],filed_on=row['filed_on'],period_end=row['period_end'],
        accession=row['accession'],source_url=ref.source_url,source_sha256=ref.source_sha256)
    filed,period=date.fromisoformat(row['filed_on']),date.fromisoformat(row['period_end'])
    if not 0<=(today-period).days<=550 or filed>today or not directory_fresh:
        return FilingClassEvidence(**base,status='stale',reason='Filing age/date or current directory does not meet this evidence policy.')
    if row['common_stock_label']:
        if listing is None or listing.status in ('unavailable','listing_only'):
            return FilingClassEvidence(**base,status='unavailable',reason='Current exact listing/exchange corroboration is unavailable; a conflict is not inferred.')
        if listing.status=='stale':
            return FilingClassEvidence(**base,status='stale',reason='The supporting listing reference is stale; a share-class conflict is not inferred.')
        if listing.status=='ambiguous':
            return FilingClassEvidence(**base,status='ambiguous',reason='The supporting exact listing match is ambiguous; no class mapping is guessed.')
    if not row['common_stock_label'] or listing is None or listing.status!='corroborated' or listing.exchange!=row['exchange']:
        return FilingClassEvidence(**base,status='conflict',reason='Filing common-stock/exchange evidence is not corroborated by the current exact listing.')
    return FilingClassEvidence(**base,status='corroborated_filing_class',reason='Dated registered common-stock class agrees with exact current SEC directory and listing exchange. Other economic/nontraded classes, current share quantities and official membership are not established.')
