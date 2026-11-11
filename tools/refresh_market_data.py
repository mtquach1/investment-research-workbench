"""Build a reproducible public-data release; offline unless --download is given."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from data_pipeline import build_release
from market_sources import SOURCES
from coverage_report import coverage_report
from public_data_store import atomic_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of",type=date.fromisoformat,required=True)
    parser.add_argument("--cache",type=Path,default=Path("data_cache"))
    parser.add_argument("--store",type=Path,default=Path("data_cache/published"))
    parser.add_argument("--download",action="store_true",help="Fetch missing/due registered sources only")
    parser.add_argument("--force-refresh",action="store_true")
    parser.add_argument("--source",action="append",help="Registered source ID or canonical sec_companyfacts_cik##########")
    parser.add_argument("--coverage-report",type=Path,help="Write local public-data audit matrices; not a user plan export")
    args=parser.parse_args()
    if args.force_refresh and not args.download:
        parser.error("--force-refresh requires --download")
    started=perf_counter()
    digest,manifest=build_release(args.cache,args.store,as_of=args.as_of,download=args.download,
        force_refresh=args.force_refresh,source_ids=args.source)
    if args.coverage_report:
        atomic_json(args.coverage_report,coverage_report(args.store))
    print(json.dumps({"release_id":digest,"elapsed_seconds":round(perf_counter()-started,3),
        "table_count":len(manifest.tables),"normalized_rows":sum(table.row_count for table in manifest.tables.values()),
        "failures":{key:value.model_dump(mode="json") for key,value in manifest.failures.items()},
        "stock_recommendations_ready":manifest.stock_recommendations_ready,
        "rental_discovery_ready":manifest.rental_discovery_ready},indent=2))


if __name__=="__main__":
    main()
