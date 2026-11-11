"""Pure coverage parsers. These summarize evidence, not investment opportunities."""

from collections import Counter, defaultdict
import csv
from datetime import date, datetime
from math import isfinite
from pathlib import Path
import re
import json


AUDIT_VERSION = "source-coverage-v1"

ANNUAL_TAGS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "operating_cashflow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capital_expenditures": ("PaymentsToAcquirePropertyPlantAndEquipment",),
}


def annual_issuer_coverage(path, *, as_of):
    """Sample annual-period tag availability only; not a normalized TTM engine."""
    with Path(path).open(encoding="utf-8-sig") as stream:
        company = json.load(stream)
    facts = company.get("facts", {}).get("us-gaap", {})

    def candidates(tag, annual=True):
        found = []
        for fact in facts.get(tag, {}).get("units", {}).get("USD", []):
            try:
                end = date.fromisoformat(fact["end"])
                filed = date.fromisoformat(fact["filed"])
                valid = filed <= as_of and end <= as_of and fact.get("form") in ("10-K", "10-K/A")
                valid = valid and isfinite(float(fact["val"]))
                if annual:
                    duration = (end-date.fromisoformat(fact["start"])).days
                    valid = valid and 330 <= duration <= 400
                if valid:
                    found.append(fact)
            except (KeyError, ValueError, TypeError):
                continue
        return found

    revenues = [(tag, fact) for tag in ANNUAL_TAGS["revenue"] for fact in candidates(tag)]
    anchor = max(revenues, key=lambda item: (item[1]["end"], item[1]["filed"], -ANNUAL_TAGS["revenue"].index(item[0]))) if revenues else None
    metrics = {}
    for name, tags in ANNUAL_TAGS.items():
        selected = []
        for tag in tags:
            selected += [(tag, fact) for fact in candidates(tag)
                         if anchor and (fact["start"], fact["end"]) == (anchor[1]["start"], anchor[1]["end"])]
        chosen = max(selected, key=lambda item: (item[1]["filed"], -tags.index(item[0]))) if selected else None
        metrics[name] = {"status": "aligned_annual_fact_available" if chosen else "missing_aligned_fact",
                         "tag": chosen[0] if chosen else None,
                         "filed": chosen[1]["filed"] if chosen else None}
    for name, tag in (("assets", "Assets"), ("liabilities", "Liabilities")):
        selected = [fact for fact in candidates(tag, annual=False) if anchor and fact["end"] == anchor[1]["end"]]
        chosen = max(selected, key=lambda fact: fact["filed"]) if selected else None
        metrics[name] = {"status": "aligned_annual_fact_available" if chosen else "missing_aligned_fact",
                         "tag": tag if chosen else None, "filed": chosen["filed"] if chosen else None}
    return {"cik": company["cik"], "issuer": company["entityName"],
            "period_start": anchor[1]["start"] if anchor else None,
            "period_end": anchor[1]["end"] if anchor else None,
            "audit_kind": "sample_annual_tags_not_TTM_or_full_universe", "metrics": metrics,
            "valuation_ready": False, "recommendation_ready": False}


def _required(fields, expected):
    if not expected.issubset(fields or []):
        raise ValueError("Source schema is missing required columns")


def county_zctas(path, county="06059"):
    """2020 ZCTA positive land overlap, not USPS or residential-address membership."""
    intersections = defaultdict(dict)
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="|")
        _required(reader.fieldnames, {"GEOID_ZCTA5_20", "GEOID_COUNTY_20", "AREALAND_PART"})
        for row in reader:
            zcta, county_id = row["GEOID_ZCTA5_20"], row["GEOID_COUNTY_20"]
            if not zcta:
                continue  # Census includes county territory outside any ZCTA.
            if not re.fullmatch(r"\d{5}", zcta) or not re.fullmatch(r"\d{5}", county_id):
                raise ValueError("Malformed geographic identifier")
            land = int(row["AREALAND_PART"])
            if land < 0 or county_id in intersections[zcta]:
                raise ValueError("Invalid or duplicate geographic intersection")
            intersections[zcta][county_id] = land
    result = {}
    for zcta, parts in sorted(intersections.items()):
        if parts.get(county, 0) <= 0:
            continue
        positive = {key: value for key, value in parts.items() if value > 0}
        result[zcta] = {"zcta": zcta, "county_land_share": positive[county]/sum(positive.values()),
                        "shared_county": len(positive) > 1,
                        "largest_land_county": min(positive, key=lambda key: (-positive[key], key))}
    return result


def housing_coverage(path, *, as_of, identifiers=None, county_filter=False, max_age_days=90):
    """Summarize series dates only; never infer property rents from a mixed index."""
    records, total, future_values = {}, 0, 0
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        _required(reader.fieldnames, {"RegionID", "RegionName", "RegionType"})
        dates = [name for name in reader.fieldnames if re.fullmatch(r"\d{4}-\d{2}-\d{2}", name)]
        if not dates or dates != sorted(set(dates)):
            raise ValueError("Missing, repeated or unordered observation dates")
        if county_filter:
            _required(reader.fieldnames, {"State", "CountyName"})
        for row in reader:
            total += 1
            identifier = row["RegionName"]
            matched = (identifiers is None and not county_filter) or (identifiers is not None and identifier in identifiers)
            if county_filter:
                matched = matched or (row["State"] == "CA" and row["CountyName"] == "Orange County")
            if not matched:
                continue
            if row["RegionType"] == "zip" and not re.fullmatch(r"\d{5}", identifier):
                raise ValueError("ZIP identifier lost its five-digit representation")
            if identifier in records:
                raise ValueError("Duplicate housing geography")
            observed, invalid = [], 0
            for period in dates:
                value = row.get(period)
                if value is None:
                    raise ValueError("Truncated housing row")
                if not value.strip():
                    continue
                try:
                    valid = isfinite(float(value)) and float(value) > 0
                except ValueError:
                    valid = False
                if not valid:
                    invalid += 1
                elif date.fromisoformat(period) > as_of:
                    future_values += 1
                else:
                    observed.append(period)
            last = observed[-1] if observed else None
            status = "missing" if last is None else "stale" if (as_of-date.fromisoformat(last)).days > max_age_days else "available"
            in_span = [period for period in dates if observed and observed[0] <= period <= observed[-1]]
            records[identifier] = {
                "region_id": row["RegionID"], "region_type": row["RegionType"],
                "provider_county": row.get("CountyName"), "state": row.get("State", row.get("StateName")),
                "first_observation": observed[0] if observed else None, "last_observation": last,
                "observations": len(observed), "missing_within_history": len(in_span)-len(observed),
                "invalid_values": invalid, "status": status,
            }
    return {"national_rows": total, "file_last_period": dates[-1], "future_values_excluded": future_values,
            "freshness_threshold_days": max_age_days, "records": records}


def holdings_proxy(path, *, as_of):
    equities, sectors, other_types = [], Counter(), Counter()
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        observed_date, header = None, None
        for row in reader:
            if row and row[0].strip() == "Fund Holdings as of":
                observed_date = datetime.strptime(row[1], "%b %d, %Y").date()
            if row and row[0].strip() == "Ticker":
                header = [name.strip() for name in row]
                break
        _required(header, {"Ticker", "Sector", "Asset Class", "Market Value", "Price"})
        if observed_date is None or observed_date > as_of:
            raise ValueError("Missing or future holdings date")
        seen = set()
        for row in reader:
            if not row or len(row) < len(header):
                continue  # Blank rows and fund legal footer are not holdings.
            entry = dict(zip(header, row))
            kind = entry["Asset Class"].strip()
            if kind != "Equity":
                if kind:
                    other_types[kind] += 1
                continue
            ticker = entry["Ticker"].strip()
            if not ticker or ticker in seen:
                raise ValueError("Missing or duplicate equity ticker")
            seen.add(ticker)
            try:
                price = float(entry["Price"].replace(",", ""))
                price_valid = isfinite(price) and price > 0
            except ValueError:
                price_valid = False
            equities.append({"ticker": ticker, "sector": entry["Sector"].strip(),
                             "has_snapshot_price": price_valid})
            sectors[entry["Sector"].strip()] += 1
    return {"universe_kind": "ETF_holdings_proxy_not_verified_index_membership",
            "holdings_as_of": observed_date.isoformat(), "equity_security_rows": len(equities),
            "sectors": dict(sorted(sectors.items())), "non_equity_rows": dict(other_types),
            "snapshot_prices_available": sum(row["has_snapshot_price"] for row in equities),
            "price_history_verified": False, "fundamentals_verified": False,
            "index_membership_verified": False, "equities": equities}


def rental_report(snapshots, *, as_of):
    geography = county_zctas(snapshots["census_zcta_county_2020"].path)
    prices = housing_coverage(snapshots["zillow_sfr_value_zip"].path, as_of=as_of,
                              identifiers=set(geography), county_filter=True)
    universe = set(geography) | set(prices["records"])
    rents = housing_coverage(snapshots["zillow_mixed_rent_zip"].path, as_of=as_of,
                             identifiers=universe, county_filter=True)
    universe |= set(rents["records"])
    metro = housing_coverage(snapshots["zillow_sfr_rent_metro"].path, as_of=as_of,
                             identifiers={"Los Angeles, CA", "Anaheim, CA", "Santa Ana, CA"})
    rows = []
    for identifier in sorted(universe):
        price = prices["records"].get(identifier, {})
        rent = rents["records"].get(identifier, {})
        geo = geography.get(identifier, {})
        rows.append({"zip_or_zcta": identifier,
                     "geography_basis": "2020_zcta_positive_land_overlap" if geo else "provider_county_label_only",
                     "shared_county": geo.get("shared_county"), "county_land_share": geo.get("county_land_share"),
                     "sfr_price_status": price.get("status", "missing"),
                     "sfr_price_last_observation": price.get("last_observation"),
                     "mixed_rent_status": rent.get("status", "missing"),
                     "mixed_rent_last_observation": rent.get("last_observation"),
                     "sfr_zip_rent_status": "not_available_in_audited_download_options",
                     "single_family_cashflow_screening_supported": False})
    return {"county": "Orange County, California", "county_fips": "06059",
            "universe_kind": "2020_ZCTA_overlap_union_provider_county_labels_not_current_USPS",
            "candidate_count": len(rows), "census_land_overlap_zctas": len(geography),
            "shared_county_zctas": sum(row["shared_county"] for row in geography.values()),
            "sfr_price_status_counts": dict(Counter(row["sfr_price_status"] for row in rows)),
            "mixed_rent_status_counts": dict(Counter(row["mixed_rent_status"] for row in rows)),
            "sfr_value_file_last_period": prices["file_last_period"],
            "mixed_rent_file_last_period": rents["file_last_period"],
            "sfr_metro_rent_context": metro["records"], "freshness_threshold_days": 90,
            "single_family_cashflow_screening_supported": False,
            "limitations": ["2020 land overlap is not current residential ZIP membership.",
                            "Mixed-home rents cannot stand in for single-family rents.",
                            "Audited SFR rent selector offered Metro & U.S. only, not ZIP geography.",
                            "Property-level rent/expenses must be supplied or sourced separately.",
                            "Public display/redistribution rights are not cleared."],
            "coverage": rows}
