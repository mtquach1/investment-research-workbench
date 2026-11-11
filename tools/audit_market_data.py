"""Refresh explicitly, then audit offline: no user financial inputs or AI calls."""

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_audit import AUDIT_VERSION, annual_issuer_coverage, holdings_proxy, rental_report
from market_data import SourceDownloadError, fetch_source, load_snapshot
from market_sources import SOURCES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--cache", type=Path, default=Path("data_cache"))
    parser.add_argument("--output", type=Path, default=Path("output/audits"))
    parser.add_argument("--download", action="store_true", help="Explicitly permit public source downloads")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.refresh and not args.download:
        parser.error("--refresh requires --download")
    snapshots, failures = {}, {}
    failure_file = args.cache / "last_fetch_failures.json"
    if not args.download and failure_file.exists():
        failures = json.loads(failure_file.read_text(encoding="utf-8"))
    for source_id, source in SOURCES.items():
        try:
            snapshot = fetch_source(source, args.cache, refresh=args.refresh) if args.download else load_snapshot(source_id, args.cache)
            snapshots[source_id] = snapshot
            failures.pop(source_id, None)
            print(f"Audited snapshot: {source_id}", file=sys.stderr)
        except (SourceDownloadError, OSError, ValueError) as error:
            failures.setdefault(source_id, {})
            if args.download or not failures[source_id]:
                failures[source_id] = {"status": "access_failed" if args.download else "snapshot_unavailable",
                                       "http_status": getattr(error, "status_code", None),
                                       "observed_at": datetime.now(timezone.utc).isoformat()}
            print(f"Unavailable: {source_id}", file=sys.stderr)
        if args.download and source_id.startswith("sec_"):
            time.sleep(.6)
    if args.download:
        args.cache.mkdir(parents=True, exist_ok=True)
        failure_file.write_text(json.dumps(failures, indent=2), encoding="utf-8")
    report = {"audit_version": AUDIT_VERSION, "as_of": args.as_of.isoformat(),
              "assessment_state": "partial_source_feasibility_not_release_ready",
              "historical_point_in_time_dataset": False,
              "source_snapshots": {key: value.metadata for key, value in snapshots.items()},
              "source_failures": failures, "public_display_cleared": False}
    rental_ids = {"census_zcta_county_2020", "zillow_sfr_value_zip", "zillow_mixed_rent_zip", "zillow_sfr_rent_metro"}
    if rental_ids.issubset(snapshots):
        report["rentals"] = rental_report(snapshots, as_of=args.as_of)
    if "ivv_holdings_proxy" in snapshots:
        report["stocks"] = holdings_proxy(snapshots["ivv_holdings_proxy"].path, as_of=args.as_of)
        if "sec_ticker_exchange" in snapshots:
            data = json.loads(snapshots["sec_ticker_exchange"].path.read_text(encoding="utf-8-sig"))
            mapped = {dict(zip(data["fields"], row))["ticker"] for row in data["data"]}
            report["stocks"]["exact_ticker_mapping_matches"] = sum(row["ticker"] in mapped for row in report["stocks"]["equities"])
        report["stocks"]["sample_issuer_fundamentals"] = {
            key.removeprefix("sec_companyfacts_").upper(): annual_issuer_coverage(snapshot.path, as_of=args.as_of)
            for key, snapshot in snapshots.items() if key.startswith("sec_companyfacts_")}
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / f"market-coverage-{args.as_of.isoformat()}.json"
    temporary = path.with_name(f"{uuid4().hex}.json.part")
    try:
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    stock_summary = {key: value for key, value in report.get("stocks", {}).items()
                     if key not in ("equities", "sample_issuer_fundamentals")}
    stock_summary["sample_issuer_metric_coverage"] = {
        ticker: {"period_end": issuer["period_end"],
                 "missing_annual_tags": [key for key, value in issuer["metrics"].items()
                                         if value["status"] == "missing_aligned_fact"]}
        for ticker, issuer in report.get("stocks", {}).get("sample_issuer_fundamentals", {}).items()}
    summary = {"report": str(path.resolve()), "source_failures": failures,
               "rentals": {key: value for key, value in report.get("rentals", {}).items() if key not in ("coverage", "sfr_metro_rent_context")},
               "stocks": stock_summary}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
