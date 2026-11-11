"""Reconcile installed class and share evidence without guessing class quantities.

Companyfacts' undimensioned DEI point count is retained at issuer scope. Neither
a matching ticker nor a registered 12(b) class proves all economic classes exist
in the directory. This ledger deliberately cannot certify issuer valuation.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from data_pipeline import Contract
from class_quantity_review import HistoricalClassQuantity,load_quantity_reviews,match_historical_class_quantity


class LedgerSource(Contract):
    source_url: str
    source_sha256: str
    retrieved_at: datetime


class ClassObservation(Contract):
    symbol: str
    class_title: str
    exchange: str
    context_ref: str
    accession: str
    period_end: date
    filed_on: date
    source: LedgerSource


class LedgerSecurity(Contract):
    symbol: str
    directory_status: Literal['unique_issuer', 'ambiguous_issuer', 'filing_only']
    listing_status: str
    filing_status: str
    filing_observations: list[ClassObservation] = Field(default_factory=list)
    assigned_shares: None = None
    historical_quantity: HistoricalClassQuantity | None = None


class IssuerShareObservation(Contract):
    status: Literal['reported_unallocated', 'stale', 'ambiguous', 'unavailable']
    shares: Decimal | None = None
    measured_on: date | None = None
    filed_on: date | None = None
    accession: str | None = None
    source: LedgerSource
    unit: Literal['shares'] = 'shares'
    scope: Literal['issuer_unallocated'] = 'issuer_unallocated'


class FilingPointObservation(Contract):
    tag: Literal['dei:EntityCommonStockSharesOutstanding', 'us-gaap:CommonStockSharesOutstanding']
    context_ref: str
    measured_on: date
    filed_on: date
    accession: str
    cik: int
    shares: Decimal = Field(ge=0,le=Decimal('1e15'))
    scale: int
    decimals: str
    dimensions: dict[str,str]
    scope: Literal['issuer_unallocated','dimensional_unassigned']
    source: LedgerSource


class ClassShareLedger(Contract):
    model_version: Literal['installed-class-share-ledger-v1'] = 'installed-class-share-ledger-v1'
    cik: int
    checked_on: date
    directory_source: LedgerSource
    directory_fresh: bool
    securities: list[LedgerSecurity]
    share_observation: IssuerShareObservation
    filing_point_observations: list[FilingPointObservation] = Field(default_factory=list)
    gaps: list[str]
    all_economic_classes_verified: Literal[False] = False
    class_quantities_reconciled: Literal[False] = False
    issuer_valuation_verified: Literal[False] = False


def _receipt(reference):
    return LedgerSource(source_url=reference.source_url, source_sha256=reference.source_sha256,
                        retrieved_at=reference.retrieved_at)


def build_class_share_ledger(cik, raw, reference, directory, directory_reference,
                            class_tables, listings, filing_checks, *, today, directory_fresh, filing_share_tables=(),quantity_reviews=None):
    """Pure assembly over already integrity-checked tables; no downloads or prices.

    Include ambiguous directory symbols and filing-only symbols, even though the
    screen's unique-issuer price join cannot use them. Preserve every dated cover
    observation; no latest-filing or class-to-quantity match is guessed.
    """
    symbols = {symbol for symbol, issuers in directory.items() if cik in issuers}
    observed = {}
    for ref, rows in class_tables:
        for row in rows:
            if row['cik'] != cik:
                continue
            observation = ClassObservation(**{name: row[name] for name in (
                'symbol', 'class_title', 'exchange', 'context_ref', 'accession', 'period_end', 'filed_on')},
                source=_receipt(ref))
            if not observation.period_end <= observation.filed_on <= today:
                raise ValueError('Invalid ledger filing dates')
            observed.setdefault(row['symbol'], []).append(observation)
    securities = []
    for symbol in sorted(symbols | observed.keys()):
        directory_status = ('filing_only' if symbol not in symbols else
                            'unique_issuer' if directory[symbol] == {cik} else 'ambiguous_issuer')
        listing, filing = listings.get(symbol), filing_checks.get(symbol)
        securities.append(LedgerSecurity(symbol=symbol, directory_status=directory_status,
            listing_status=listing.status if listing else 'unavailable',
            filing_status=filing.status if filing else 'unavailable',
            filing_observations=sorted(observed.get(symbol, []), key=lambda item: (
                item.filed_on, item.accession, item.context_ref, item.source.source_sha256))))

    filing_points=[]
    for ref, observations in filing_share_tables:
        for observation in observations:
            if observation['cik'] != cik:
                continue
            point=FilingPointObservation(**observation,source=_receipt(ref))
            if not point.measured_on<=point.filed_on<=today:
                raise ValueError('Invalid filing point-share dates')
            filing_points.append(point)
    registry=quantity_reviews if quantity_reviews is not None else load_quantity_reviews()
    for security in securities:
        security.historical_quantity=match_historical_class_quantity(cik,security,filing_points,
            today=today,directory_fresh=directory_fresh,registry=registry)
    share = raw.get('share_reference', {})
    evidence = share.get('evidence')
    status = share.get('status', 'unavailable')
    values = {}
    if status == 'reported_point' and evidence:
        measured, filed = date.fromisoformat(evidence['measured_on']), date.fromisoformat(evidence['filed_on'])
        quantity = Decimal(evidence['shares'])
        if (evidence.get('unit') != 'shares' or evidence.get('tag') != 'dei:EntityCommonStockSharesOutstanding'
                or isinstance(evidence['shares'], bool) or not quantity.is_finite()
                or not 0 < quantity <= Decimal('1e15') or quantity != quantity.to_integral_value()
                or not measured <= filed <= today or not evidence.get('accession')):
            raise ValueError('Invalid ledger point-share evidence')
        values = dict(shares=quantity, measured_on=measured, filed_on=filed, accession=evidence['accession'])
        status = 'stale' if (today - measured).days > 120 else 'reported_unallocated'
    elif status == 'ambiguous':
        status = 'ambiguous'
    elif status == 'unavailable' and not evidence:
        status = 'unavailable'
    else:
        raise ValueError('Inconsistent ledger share state')
    point = IssuerShareObservation(status=status, source=_receipt(reference), **values)
    gaps = []
    if not directory_fresh:
        gaps.append('The ticker directory is older than the seven-day policy or has a future retrieval date.')
    if not securities:
        gaps.append('No directory or filing security observations are installed for this issuer.')
    if any(item.directory_status == 'ambiguous_issuer' for item in securities):
        gaps.append('A directory symbol maps to more than one issuer; no issuer is chosen for it.')
    if any(item.directory_status == 'filing_only' for item in securities):
        gaps.append('A filing symbol is absent from the current issuer directory; no replacement ticker is guessed.')
    if any(item.filing_status != 'corroborated_filing_class' for item in securities):
        gaps.append('Some observed securities lack unique, current, corroborated filing-class evidence.')
    if status != 'reported_unallocated':
        gaps.append({'stale': 'The share measurement is more than 120 calendar days old at this check date.',
                     'ambiguous': 'Latest issuer share observations conflict; no quantity is chosen.',
                     'unavailable': 'No usable reported point share count is installed.'}[status])
    gaps.extend([
        'Registered listings do not establish coverage of all economic or nontraded classes.',
        'The issuer share count has no verified class assignment; quantities cannot be reconciled across classes.',
        'Class prices, splits, issuance, repurchases and conversion rights still need aligned evidence before issuer-wide valuation.'
    ])
    return ClassShareLedger(cik=cik, checked_on=today, directory_source=_receipt(directory_reference),
        directory_fresh=directory_fresh, securities=securities, share_observation=point, gaps=gaps,
        filing_point_observations=filing_points)
