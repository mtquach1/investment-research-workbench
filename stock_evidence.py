"""Read-only, dated evidence inventory. No downloads or verification promotion."""
from collections import Counter
from datetime import date
from typing import Literal
from pydantic import Field
from data_pipeline import Contract
from stock_screen import StockScreen


class EvidenceCheck(Contract):
    code: str
    status: Literal['pass', 'fail', 'missing', 'provisional']
    detail: str


class CompanyEvidence(Contract):
    issuer_key: str
    company: str
    symbols: list[str]
    checks: list[EvidenceCheck]


class EvidenceSnapshot(Contract):
    status: str
    checked_on: date
    public_release_id: str | None
    market_snapshot_sha256: str | None
    universe_observed_on: date | None
    universe_fresh: bool
    listing_reference_hashes: dict[str, str]


class EvidenceInventory(Contract):
    model_version: Literal['stock-evidence-inventory-v1'] = 'stock-evidence-inventory-v1'
    screen: EvidenceSnapshot
    counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    companies: list[CompanyEvidence] = Field(default_factory=list)
    strict_recommendations_enabled: Literal[False] = False
    automatic_refresh_enabled: Literal[False] = False
    notice: str = 'Inventory of installed evidence, not source certification. Refresh is operator-run; a recent check date does not mean recent observations. Public display rights are reviewed separately.'


def company_evidence(row):
    checks = []
    def add(code, status, detail):
        checks.append(EvidenceCheck(code=code, status=status, detail=detail))
    observed_failures = [detail for detail in row.financial_reasons if detail not in row.financial_missing_reasons]
    financial_detail = ('Annual strategy financial checks pass.' if row.financial_status == 'pass' else
        'Annual financial assessment is incomplete; see missing financial inputs.' if row.financial_status == 'unavailable' else
        'Observed financial failures: ' + ('; '.join(observed_failures) or 'Required financial rules do not pass.'))
    for code, status, detail in (
        ('financials', row.financial_status, financial_detail),
        ('sector', row.sector_status, row.sector or 'No supported sector mapping.'),
        ('price', row.price_status, f'Price observation: {row.valuation.price_date or "unavailable"}.'),
        ('risk_history', row.history_count_status, 'Strategy requires 756 complete return observations.'),
    ):
        add(code, 'missing' if status == 'unavailable' or (code in ('price', 'risk_history') and status != 'pass') else status, detail)
    missing_financials = bool(row.financial_missing_reasons) or row.financial_status == 'unavailable'
    add('financial_inputs', 'missing' if missing_financials else 'pass',
        ('Unavailable inputs needed to test these rules: ' + '; '.join(row.financial_missing_reasons)
        if row.financial_missing_reasons else 'Required annual financial inputs are unavailable.' if missing_financials
        else 'No missing annual financial checks reported.'))
    add('financial_basis', 'missing' if row.financial_evidence_reasons else 'pass',
        'Unusable financial vintage: ' + '; '.join(row.financial_evidence_reasons) if row.financial_evidence_reasons
        else 'No fiscal-age or filing-vintage failures reported.')
    quality = [row.metrics.get(name) for name in ('return_on_assets', 'operating_margin', 'free_cashflow_margin')]
    quality_complete = all(m and m.status == 'available' and m.value is not None for m in quality)
    add('quality_features', 'pass' if quality_complete else 'missing',
        'All three annual quality features are available and fresh.' if quality_complete else
        'Some annual quality features are missing or stale; unavailable features are not zero.')
    add('valuation', 'provisional' if row.valuation.status == 'estimated' else 'missing', row.valuation.reason)
    exact = row.listing_evidence.get(row.tickers[0]) if len(row.tickers) == 1 else None
    listing_status = exact.status if exact else 'unavailable'
    add('listing', 'pass' if listing_status == 'corroborated' else 'fail' if listing_status in ('not_found', 'exchange_conflict', 'flagged_security') else 'missing',
        f'Listing cross-check: {listing_status}. This does not verify share class or index membership.')
    add('security_identity', 'missing', 'Canonical security/share-class identity is not yet verified.')
    filing = row.filing_class_evidence.get(row.tickers[0]) if len(row.tickers)==1 else None
    add('filing_class', 'provisional' if filing and filing.status=='corroborated_filing_class' else 'missing',
        filing.reason if filing else 'No unique installed filing-class corroboration. This is separate from complete identity verification.')
    add('class_share_reconciliation', 'missing',
        'Issuer count is not assigned to economic classes; class quantities and issuer-wide valuation remain unverified.'
        if row.class_share_ledger else 'No installed class/share ledger. Class quantities remain unverified.')
    add('index_membership', 'missing', 'Dated ETF holdings are a proxy, not verified official index membership.')
    return CompanyEvidence(issuer_key=row.issuer_key, company=row.company, symbols=row.tickers, checks=checks)


def evidence_inventory(screen: StockScreen):
    companies = [company_evidence(row) for row in sorted(screen.rows, key=lambda row: row.issuer_key)] if screen.status == 'available' else []
    counts = {}
    for code in sorted({check.code for row in companies for check in row.checks}):
        tally = Counter(check.status for row in companies for check in row.checks if check.code == code)
        counts[code] = {status: tally[status] for status in ('pass', 'fail', 'missing', 'provisional')}
    return EvidenceInventory(screen={'status': screen.status, 'checked_on': str(screen.checked_on),
        'public_release_id': screen.public_release_id, 'market_snapshot_sha256': screen.market_snapshot_sha256,
        'universe_observed_on': str(screen.universe.observed_on) if screen.universe.observed_on else None,
        'universe_fresh': screen.universe.fresh, 'listing_reference_hashes': screen.listing_reference_hashes},
        counts=counts, companies=companies)
