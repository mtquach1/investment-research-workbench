"""Domain normalization over public snapshots, independent of transport and UI.

Reported periods are not publication dates. Revised historical observations do
not become a point-in-time dataset merely because this adapter filters dates.
"""

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re

from data_audit import county_zctas, holdings_proxy
from stock_financials import normalize_annual_financials, annual_financial_history
from public_data_store import strict_json
from market_sources import companyfacts_cik


ADAPTER_VERSION = "public-normalization-v1"
HOUSING = {
    "zillow_sfr_value_zip": ("single_family", "zip", "typical_home_value", "USD_index_level"),
    "zillow_mixed_rent_zip": ("mixed_single_family_condo_multifamily", "zip", "observed_rent", "USD_per_month_index"),
    "zillow_sfr_rent_metro": ("single_family", "metro", "observed_rent", "USD_per_month_index"),
}


def _number(value, *, positive=False, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a financial observation")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("Invalid financial observation") from None
    if (not number.is_finite() or abs(number) > Decimal("1e24") or
            positive and number <= 0 or nonnegative and number < 0):
        raise ValueError("Out-of-range financial observation")
    return number


def _table(kind, records, observation_date, **summary):
    ids = [row["record_id"] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate normalized record")
    if not records:
        raise ValueError("No supported observations")
    return {"adapter_version":ADAPTER_VERSION,"kind":kind,"observation_date":observation_date,
            "summary":summary,"records":records}


def normalize_source(source_id, path, *, as_of, geography=None):
    if source_id.startswith('sec_cover_'):
        from security_identity import normalize_filing_cover
        return normalize_filing_cover(source_id,path,as_of=as_of)
    if source_id in ('nasdaq_listed_directory','nasdaq_other_directory'):
        from security_listing import normalize_listing_directory
        return normalize_listing_directory(source_id,path,as_of=as_of)
    if source_id.startswith("sec_submissions_cik"):
        from filing_events import normalize_submissions
        return normalize_submissions(source_id,strict_json(path.read_bytes()),as_of=as_of)
    if source_id == "census_zcta_county_2020":
        if as_of < date(2020,1,1):
            raise ValueError("Geography vintage is later than the requested date")
        rows = list(county_zctas(path).values())
        for row in rows:
            row.update(record_id=row["zcta"], geography_kind="2020_ZCTA", county_fips="06059")
        return _table("rental_geography", rows, None, geography_vintage=2020,candidate_count=len(rows),
            candidate_ids=[row["zcta"] for row in rows],
            shared_county_count=sum(row["shared_county"] for row in rows),
            dominant_county_count=sum(row["largest_land_county"]=="06059" for row in rows),
            membership_rule="positive_land_overlap", current_usps_membership_verified=False,
            observation_date_basis="geography_vintage_not_market_observation")
    if source_id in HOUSING:
        return _housing(source_id,path,as_of=as_of,geography=geography or set())
    if source_id == "ivv_holdings_proxy":
        coverage = holdings_proxy(path,as_of=as_of)
        rows = [dict(row,record_id=row["ticker"], security_id="ivv_proxy:"+row["ticker"],
                     issuer_id=None,identifier_mapping_status="unverified", index_membership_verified=False)
                for row in coverage.pop("equities")]
        return _table("stock_universe_proxy",rows,coverage["holdings_as_of"],**coverage)
    if source_id.startswith("sec_companyfacts_"):
        with path.open(encoding="utf-8-sig") as stream:
            company=strict_json(stream.read())
        expected=companyfacts_cik(source_id)
        if company.get("cik") != expected:
            raise ValueError("Issuer does not match the registered source")
        result=normalize_annual_financials(company,as_of=as_of)
        row=json.loads(json.dumps(result.to_dict(),default=str,allow_nan=False))
        row.update(record_id=f"sec:{expected:010d}",issuer_id=f"sec:{expected:010d}")
        from equity_reference import reported_share_reference
        row["share_reference"]=reported_share_reference(company,as_of=as_of)
        row["annual_history_version"]="annual-history-v1"
        row["annual_history"]=json.loads(json.dumps([item.to_dict() for item in
            annual_financial_history(company,as_of=as_of)],default=str,allow_nan=False))
        return _table("annual_financial_sample",[row],result.period_end,
                      complete_issuers=int(result.financials_complete), issuer_count=1,
                      recommendation_ready=False, valuation_ready=False,
                      observation_date_basis="fiscal_year_end",latest_filing=max((f.filed for f in result.facts.values()),default=None))
    if source_id == "sec_ticker_exchange":
        with path.open(encoding="utf-8-sig") as stream:
            data=strict_json(stream.read())
        fields=data["fields"]
        if not {"cik","name","ticker","exchange"}.issubset(fields) or len(fields)!=len(set(fields)):
            raise ValueError("Unexpected issuer mapping fields")
        rows=[]
        for entry in data["data"]:
            if len(entry)!=len(fields):
                raise ValueError("Truncated issuer mapping")
            row=dict(zip(fields,entry))
            if type(row["cik"]) is not int or row["cik"]<=0 or not row["ticker"]:
                raise ValueError("Invalid issuer mapping")
            row.update(record_id=f"{row['cik']}:{row['exchange']}:{row['ticker']}",
                       issuer_id=f"sec:{row['cik']:010d}",historical_mapping_verified=False)
            rows.append(row)
        return _table("issuer_mapping",rows,None,observation_date_basis="provider_did_not_supply_snapshot_date")
    if source_id == "alphavantage_ibm_daily_demo":
        return _adjusted_daily(path,as_of=as_of)
    raise ValueError("No verified adapter for this source")


def _housing(source_id,path,*,as_of,geography):
    category,level,metric,unit=HOUSING[source_id]
    rows, entities, future = [], {}, 0
    with path.open(encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream)
        fields=reader.fieldnames or []
        required={"RegionID","RegionName","RegionType"}
        if level=="zip":
            required|={"State","CountyName"}
        if not required.issubset(fields) or len(fields)!=len(set(fields)):
            raise ValueError("Missing or duplicate housing columns")
        periods=[name for name in fields if re.fullmatch(r"\d{4}-\d{2}-\d{2}",name)]
        if not periods or periods != sorted(periods):
            raise ValueError("Missing or unordered housing periods")
        for period in periods:
            date.fromisoformat(period)
        for row in reader:
            entity=row["RegionName"]
            in_county=row.get("State")=="CA" and row.get("CountyName")=="Orange County"
            matched=entity in geography or in_county if level=="zip" else entity=="Los Angeles, CA"
            if not matched:
                continue
            expected_level="zip" if level=="zip" else "msa"
            if (row["RegionType"]!=expected_level or level=="zip" and not re.fullmatch(r"\d{5}",entity)
                    or entity in entities):
                raise ValueError("Invalid or duplicate housing geography")
            entities[entity]=[]
            for period in periods:
                raw=row.get(period)
                if raw is None:
                    raise ValueError("Truncated housing row")
                if not raw.strip():
                    continue
                value=_number(raw,positive=True)
                if date.fromisoformat(period)>as_of:
                    future+=1
                    continue
                entities[entity].append(period)
                rows.append({"record_id":f"{entity}:{period}","entity_id":entity,"region_id":row["RegionID"],
                    "geography_kind":level,"county_basis":"provider_label" if in_county else "2020_land_overlap",
                    "category":category,"metric":metric,"unit":unit,"period_end":period,"value":str(value),
                    "publication_date":None,"historical_point_in_time":False,
                    "property_underwriting_rent_supported":False})
    latest=max((row["period_end"] for row in rows),default=None)
    return _table("rental_context",rows,latest,series_count=sum(bool(periods) for periods in entities.values()),
        latest_by_entity={entity:periods[-1] if periods else None for entity,periods in entities.items()},
        category=category,geography_kind=level,metric=metric,unit=unit,future_observations_excluded=future,
        property_underwriting_rent_supported=False)


def _adjusted_daily(path,*,as_of):
    with path.open(encoding="utf-8-sig") as stream:
        data=strict_json(stream.read())
    metadata=data.get("Meta Data",{})
    if metadata.get("2. Symbol")!="IBM" or metadata.get("5. Time Zone")!="US/Eastern":
        raise ValueError("Unexpected provider identity or timezone")
    series=data.get("Time Series (Daily)")
    if not isinstance(series,dict) or not series or len(series)>100000:
        raise ValueError("No bounded daily series")
    refreshed=date.fromisoformat(metadata["3. Last Refreshed"])
    rows, future=[],0
    names={"open":"1. open","high":"2. high","low":"3. low","close":"4. close",
           "adjusted_close":"5. adjusted close","volume":"6. volume","dividend":"7. dividend amount","split":"8. split coefficient"}
    for period,values in sorted(series.items()):
        day=date.fromisoformat(period)
        if day>refreshed:
            raise ValueError("Observation is later than provider refresh date")
        numbers={key:_number(values[field],positive=key not in ("volume","dividend"),nonnegative=key in ("volume","dividend")) for key,field in names.items()}
        if (numbers["low"]>min(numbers["open"],numbers["close"]) or
                numbers["high"]<max(numbers["open"],numbers["close"]) or
                numbers["volume"]!=numbers["volume"].to_integral_value()):
            raise ValueError("Incoherent OHLC or volume")
        if day>as_of:
            future+=1
            continue
        rows.append({"record_id":"IBM:"+period,"security_id":"provider_demo:IBM","ticker":"IBM",
            "period_end":period,"quote_currency":"USD","timezone":"US/Eastern",
            **{key:str(value) for key,value in numbers.items()},
            "adjustment_basis":"provider_split_and_dividend_adjusted_do_not_add_dividends_again",
            "index_membership_verified":False,"historical_point_in_time":False})
    if max(series)!=refreshed.isoformat():
        raise ValueError("Provider refresh date does not match latest daily bar")
    return _table("daily_price_sample",rows,rows[-1]["period_end"] if rows else None,
        security_count=1,observations=len(rows),first_observation=rows[0]["period_end"] if rows else None,
        nonzero_dividend_events=sum(Decimal(row["dividend"])>0 for row in rows),
        non_unit_split_events=sum(Decimal(row["split"])!=1 for row in rows),
        future_observations_excluded=future,full_universe_coverage=False,benchmark_coverage=False,
        replay_ready=False,three_year_history_verified=len(rows)>=756)
