"""Small independent fixtures for geographic/period coverage and non-claims."""

import csv
from datetime import date
import json

import pytest

from data_audit import annual_issuer_coverage, county_zctas, holdings_proxy, housing_coverage


AS_OF = date(2026, 10, 28)


def write_csv(path, fields, rows, delimiter=","):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter=delimiter)
        writer.writerow(fields)
        writer.writerows(rows)
    return path


def test_geography_keeps_partial_overlap_separate_from_county_membership(tmp_path):
    path = write_csv(tmp_path/"geography.txt", ["GEOID_ZCTA5_20", "GEOID_COUNTY_20", "AREALAND_PART"], [
        ["01234", "06059", 25], ["01234", "06037", 75], ["01235", "06059", 100],
        ["01236", "06059", 0], ["", "06059", 10],
    ], "|")
    result = county_zctas(path)
    assert set(result) == {"01234", "01235"}
    assert result["01234"]["county_land_share"] == .25
    assert result["01234"]["shared_county"]
    assert result["01234"]["largest_land_county"] == "06037"


def test_geography_duplicates_are_not_silently_merged(tmp_path):
    path = write_csv(tmp_path/"geography.txt", ["GEOID_ZCTA5_20", "GEOID_COUNTY_20", "AREALAND_PART"],
                     [["01234", "06059", 25], ["01234", "06059", 75]], "|")
    with pytest.raises(ValueError, match="duplicate"):
        county_zctas(path)


def test_series_dates_exclude_future_and_invalid_values_without_zero_imputation(tmp_path):
    path = write_csv(tmp_path/"housing.csv", ["RegionID", "RegionName", "RegionType", "2026-01-31", "2026-02-28", "2026-09-30", "2026-11-30"], [
        [1, "01234", "zip", 100, "", 120, 999], [2, "01235", "zip", 100, "NaN", "", ""],
        [3, "01236", "zip", "", "", "", ""],
    ])
    result = housing_coverage(path, as_of=AS_OF)
    assert result["future_values_excluded"] == 1
    assert result["records"]["01234"]["last_observation"] == "2026-09-30"
    assert result["records"]["01234"]["missing_within_history"] == 1
    assert result["records"]["01235"]["status"] == "stale"
    assert result["records"]["01235"]["invalid_values"] == 1
    assert result["records"]["01236"]["status"] == "missing"


def test_provider_county_filter_does_not_import_other_states_or_counties(tmp_path):
    fields = ["RegionID", "RegionName", "RegionType", "State", "CountyName", "2026-09-30"]
    path = write_csv(tmp_path/"housing.csv", fields, [
        [1, "01234", "zip", "CA", "Orange County", 100],
        [2, "01235", "zip", "FL", "Orange County", 100],
        [3, "01236", "zip", "CA", "Other County", 100],
    ])
    assert set(housing_coverage(path, as_of=AS_OF, county_filter=True)["records"]) == {"01234"}


def test_stock_proxy_excludes_cash_and_never_asserts_index_or_history_coverage(tmp_path):
    path = tmp_path/"holdings.csv"
    path.write_text('Fund Holdings as of,"Oct 26, 2026"\nTicker,Sector,Asset Class,Market Value,Price\nA,Industrials,Equity,100,10\nB,Energy,Equity,100,NaN\nUSD,Cash,Cash,100,1\n')
    result = holdings_proxy(path, as_of=AS_OF)
    assert result["equity_security_rows"] == 2
    assert result["snapshot_prices_available"] == 1
    assert result["non_equity_rows"] == {"Cash": 1}
    assert not result["index_membership_verified"]
    assert not result["price_history_verified"]


def test_annual_tag_audit_respects_publication_date_and_coherent_periods(tmp_path):
    facts = {"RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
        {"start": "2025-01-01", "end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "val": 100},
        {"start": "2025-01-01", "end": "2025-12-31", "filed": "2026-11-01", "form": "10-K/A", "val": 200},
    ]}}, "OperatingIncomeLoss": {"units": {"USD": [
        {"start": "2025-07-01", "end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "val": 20},
    ]}}}
    path = tmp_path/"company.json"
    path.write_text(json.dumps({"cik": 1, "entityName": "Synthetic", "facts": {"us-gaap": facts}}))
    result = annual_issuer_coverage(path, as_of=AS_OF)
    assert result["metrics"]["revenue"]["filed"] == "2026-02-01"
    assert result["metrics"]["operating_income"]["status"] == "missing_aligned_fact"
    assert not result["valuation_ready"] and not result["recommendation_ready"]


def test_offline_cli_never_downloads_and_labels_missing_coverage(tmp_path, monkeypatch, capsys):
    from tools import audit_market_data
    import sys

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline audit must not use the network")
    monkeypatch.setattr(audit_market_data, "fetch_source", forbidden)
    monkeypatch.setattr(sys, "argv", ["audit", "--as-of", "2026-10-28", "--cache", str(tmp_path/"cache"),
                                    "--output", str(tmp_path/"reports")])
    audit_market_data.main()
    report = json.loads((tmp_path/"reports/market-coverage-2026-10-28.json").read_text())
    assert not report["public_display_cleared"]
    assert not report["historical_point_in_time_dataset"]
    assert report["assessment_state"] == "partial_source_feasibility_not_release_ready"
    assert "rentals" not in report and "stocks" not in report
    assert all(row["status"] == "snapshot_unavailable" for row in report["source_failures"].values())
