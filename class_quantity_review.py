"""Exact, dated statement links from a small reviewed registry; no current valuation."""
from datetime import date
from decimal import Decimal
import hashlib
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from data_pipeline import Contract
from public_data_store import strict_json


class QuantityReview(Contract):
    review_id: str = Field(pattern=r'^[a-z0-9-]{1,64}$')
    cik: int = Field(gt=0,lt=10000000000)
    symbol: str = Field(pattern=r'^[A-Z][A-Z0-9.-]{0,14}$')
    class_title: str = Field(min_length=1,max_length=256)
    class_context_ref: str = Field(min_length=1,max_length=256)
    share_context_ref: str = Field(min_length=1,max_length=256)
    accession: str = Field(pattern=r'^\d{10}-\d{2}-\d{6}$')
    source_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    measured_on: date
    filed_on: date
    reviewed_on: date
    shares: Decimal = Field(gt=0,le=Decimal('1e15'))
    scale: int = Field(ge=-12,le=12)
    decimals: str = Field(pattern=r'^(INF|-?\d{1,2})$')
    statement_location: str = Field(min_length=1,max_length=512)
    review_basis: str = Field(min_length=1,max_length=1500)

    @model_validator(mode='after')
    def dated_integer(self):
        if not self.measured_on<=self.filed_on<=self.reviewed_on or self.shares!=self.shares.to_integral_value():
            raise ValueError('A reviewed quantity requires a dated filing and integer shares')
        return self


class ReviewRegistry(Contract):
    review_version: Literal['dated-class-statement-review-v1']
    reviews: list[QuantityReview] = Field(max_length=32)

    @model_validator(mode='after')
    def unique_ids(self):
        if len({item.review_id for item in self.reviews})!=len(self.reviews):
            raise ValueError('Duplicate class quantity review ID')
        return self


class HistoricalClassQuantity(Contract):
    status: Literal['matched_historical_statement','not_reviewed','review_not_yet_available',
                    'evidence_unavailable','evidence_conflict']
    review: QuantityReview | None = None
    registry_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    matched_source_url: str | None = None
    reason: str
    current_class_quantity_verified: Literal[False] = False
    economic_rights_review_complete: Literal[False] = False


def load_quantity_reviews():
    path=Path(__file__).with_name('data')/'reviewed_class_quantities.json'
    with path.open('rb') as stream:payload=stream.read(65537)
    if len(payload)>65536:raise ValueError('Review registry exceeds byte budget')
    registry=ReviewRegistry.model_validate(strict_json(payload))
    return hashlib.sha256(payload).hexdigest(),registry.reviews


def match_historical_class_quantity(cik,security,points,*,today,directory_fresh,registry):
    digest,reviews=registry
    candidates=[item for item in reviews if item.cik==cik and item.symbol==security.symbol]
    def result(status,reason,review=None,url=None):
        return HistoricalClassQuantity(status=status,reason=reason,review=review,
            registry_sha256=digest,matched_source_url=url)
    if not candidates:return result('not_reviewed','No reviewed class/statement link is installed for this ticker.')
    available=[item for item in candidates if item.reviewed_on<=today]
    if not available:return result('review_not_yet_available','No review was available by this check date.')
    if len(available)!=1:return result('evidence_conflict','Multiple available class reviews; no newest mapping is guessed.')
    review=available[0]
    if (not directory_fresh or security.directory_status!='unique_issuer'
            or security.listing_status!='corroborated' or security.filing_status!='corroborated_filing_class'):
        return result('evidence_unavailable','A fresh unique directory, listing and filing-class corroboration are required.',review)
    covers=security.filing_observations
    # Every row for this security must agree. An extra conflicting cover cannot
    # be hidden by selecting only the registered hash/context.
    if len(covers)!=1:return result('evidence_conflict','Registered-class observations are missing or ambiguous.',review)
    cover=covers[0]
    if (cover.source.source_sha256!=review.source_sha256 or cover.accession!=review.accession
        or cover.symbol!=review.symbol or cover.class_title!=review.class_title
        or cover.context_ref!=review.class_context_ref or cover.period_end!=review.measured_on
        or cover.filed_on!=review.filed_on):
        return result('evidence_conflict','Installed class evidence differs from the reviewed filing/context/title.',review)
    observations=[point for point in points if point.cik==cik and point.accession==review.accession
        and point.tag=='us-gaap:CommonStockSharesOutstanding' and point.measured_on==review.measured_on]
    if not observations:return result('evidence_unavailable','The reviewed outstanding-share observation is not installed.',review)
    # Dimensions are retained as separate evidence, never silently summed into
    # the undimensioned statement quantity. Only one undimensioned row may match.
    undimensioned=[point for point in observations if not point.dimensions]
    if len(undimensioned)!=1:return result('evidence_conflict','Statement quantity is missing or has duplicate undimensioned observations.',review)
    point=undimensioned[0]
    if (point.source.source_sha256!=review.source_sha256 or point.source!=cover.source
        or point.context_ref!=review.share_context_ref or point.shares!=review.shares
        or point.filed_on!=review.filed_on or point.scale!=review.scale or point.decimals!=review.decimals
        or point.scope!='issuer_unallocated'):
        return result('evidence_conflict','Installed statement quantity, source, context or precision differs from the review.',review)
    return result('matched_historical_statement',
        'The dated statement count matches the reviewed registered common-stock class. Current quantity, economic rights and all-class coverage remain unverified.',
        review,point.source.source_url)
