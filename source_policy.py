"""Reviewed source roles and conservative research freshness policies.

These are application gates, not a legal opinion or provider service-level
agreement. Access and public display are distinct decisions.
"""

from dataclasses import asdict, dataclass

from market_sources import source_for_id
from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceAccessSettings(BaseSettings):
    model_config=SettingsConfigDict(env_file=".env",env_file_encoding="utf-8",extra="ignore")
    sec_user_agent: str | None = None


@dataclass(frozen=True)
class SourcePolicy:
    provider: str
    refresh_hours: int
    observation_max_age_days: int | None
    documentation_url: str
    rights_evidence_url: str | None
    public_display_allowed: bool = False
    rights_status: str = "review_required"
    reviewed_on: str = "2026-10-28"


def policy_for(source_id):
    source_for_id(source_id)
    if source_id.startswith('sec_cover_'):
        return SourcePolicy('SEC filing cover',168,550,
            'https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data',
            None,public_display_allowed=False,rights_status='local_class_metadata_public_display_review_required',reviewed_on='2026-10-31')
    if source_id in ('nasdaq_listed_directory','nasdaq_other_directory'):
        return SourcePolicy('Nasdaq Trader',24,7,'https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs',
            None,public_display_allowed=False,rights_status='local_listing_metadata_public_display_review_required',reviewed_on='2026-10-29')
    if source_id.startswith("sec_"):
        return SourcePolicy("SEC EDGAR",24,550 if "companyfacts" in source_id else None,
            "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
            "https://www.sec.gov/about/webmaster-frequently-asked-questions",
            public_display_allowed=True,rights_status="reviewed_edgar_filing_metadata" if "submissions" in source_id else "reviewed_edgar_numeric_filing_data")
    if source_id.startswith("zillow_"):
        return SourcePolicy("Zillow Research",168,90,"https://www.zillow.com/research/data/",
            "https://www.zillow.com/corporate/terms-of-use/")
    if source_id=="ivv_holdings_proxy":
        return SourcePolicy("iShares",24,7,
            "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf",
            None)
    if source_id=="census_zcta_county_2020":
        return SourcePolicy("U.S. Census Bureau",8760,None,
            "https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html",
            None)
    if source_id=="hud_safmr_2027":
        return SourcePolicy("HUD",168,None,
            "https://www.huduser.gov/portal/datasets/fmr/smallarea/index.html",
            "https://www.hud.gov/sites/documents/webpubstandards.pdf")
    return SourcePolicy("Alpha Vantage demo",24,7,"https://www.alphavantage.co/documentation/",
        "https://www.alphavantage.co/terms_of_service/")


def policy_dict(source_id):
    return asdict(policy_for(source_id))
