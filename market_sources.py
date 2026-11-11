"""Public research source inventory. Access is not permission to redistribute."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PublicSource:
    source_id: str
    url: str
    format: str
    role: str
    rights_status: str = "public_display_not_cleared"


SOURCES = {
    item.source_id: item for item in [
        PublicSource("hud_safmr_2027",
                     "https://www.huduser.gov/portal/datasets/fmr/fmr2027/FY27_safmrs.xlsx",
                     "hud_xlsx", "FY2027 ZIP/bedroom HUD gross-rent benchmarks, not single-family market rents"),
        PublicSource("alphavantage_ibm_daily_demo",
                     "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey=demo",
                     "adjusted_daily_json", "Provider demo for one security; not full stock/benchmark coverage"),
        PublicSource("census_zcta_county_2020",
                     "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt",
                     "pipe", "2020 ZCTA/county intersections; not a current USPS ZIP universe"),
        PublicSource("zillow_sfr_value_zip",
                     "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfr_tier_0.33_0.67_sm_sa_month.csv",
                     "csv", "Single-family ZIP-level ZHVI price context"),
        PublicSource("zillow_mixed_rent_zip",
                     "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv",
                     "csv", "Mixed-home ZIP rent context; incompatible with single-family underwriting"),
        PublicSource("zillow_sfr_rent_metro",
                     "https://files.zillowstatic.com/research/public_csvs/zori/Metro_zori_uc_sfr_sm_month.csv",
                     "csv", "Single-family metro rent context; not ZIP-specific rent"),
        PublicSource("ivv_holdings_proxy",
                     "https://www.ishares.com/us/products/239726/ishares-core-s-p-500-etf/latest-holdings.csv",
                     "holdings_csv", "ETF sponsor holdings proxy; not authoritative S&P membership"),
        PublicSource("sec_ticker_exchange",
                     "https://www.sec.gov/files/company_tickers_exchange.json",
                     "json", "Issuer/ticker mapping; not index membership or a price feed"),
        PublicSource("nasdaq_listed_directory",
                     "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
                     "symbol_directory_pipe", "Nasdaq-listed security metadata; not index membership or issuer valuation"),
        PublicSource("nasdaq_other_directory",
                     "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
                     "symbol_directory_pipe", "Other-exchange listing metadata published by Nasdaq Trader; not an issuer/share-class master"),
        *[PublicSource(f"sec_companyfacts_{ticker.lower()}",
                       f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
                       "companyfacts_json", f"Sample issuer financial disclosure audit: {ticker}")
          for ticker, cik in (("AAPL", 320193), ("MSFT", 789019), ("KO", 21344), ("JPM", 19617))],
    ]
}

# Reviewed primary documents, not user-provided URLs. Filing dates are checked
# against the SEC accession index; the HTML adapter verifies CIK/form/period.
COVER_FILINGS = {
    'sec_cover_aapl_2025':dict(cik=320193,accession='0000320193-25-000079',
        period_end='2025-09-27',filed_on='2025-10-31',document='aapl-20250927.htm'),
    'sec_cover_nvda_2026':dict(cik=1045810,accession='0001045810-26-000021',
        period_end='2026-01-25',filed_on='2026-02-25',document='nvda-20260125.htm'),
}
for _key,_filing in COVER_FILINGS.items():
    SOURCES[_key]=PublicSource(_key,
        f"https://www.sec.gov/Archives/edgar/data/{_filing['cik']}/{_filing['accession'].replace('-','')}/{_filing['document']}",
        'sec_filing_html','Dated registered-security class evidence; not a complete current economic-class master')


def source_for_id(source_id: str) -> PublicSource:
    """Resolve fixed sources or a canonical SEC CIK path, never an input URL."""
    if not isinstance(source_id,str):
        raise ValueError("Source ID must be a string")
    if source_id in SOURCES:
        return SOURCES[source_id]
    match=re.fullmatch(r"sec_companyfacts_cik([0-9]{10})",source_id)
    if match and int(match[1])>0:
        return PublicSource(source_id,
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{match[1]}.json",
            "companyfacts_json","SEC issuer financial disclosure, selected by verified directory CIK")
    match=re.fullmatch(r"sec_submissions_cik([0-9]{10})",source_id)
    if match and int(match[1])>0:
        return PublicSource(source_id,f"https://data.sec.gov/submissions/CIK{match[1]}.json",
                            "submissions_json","Recent SEC filing metadata; not a complete news feed")
    raise ValueError("Unregistered source ID")


def companyfacts_cik(source_id: str) -> int:
    source=source_for_id(source_id)
    if source.format!="companyfacts_json":
        raise ValueError("Source is not issuer financial facts")
    return int(re.search(r"/CIK(\d{10})\.json$",source.url)[1])
