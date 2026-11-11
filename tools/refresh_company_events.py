"""Operator-only SEC filing metadata refresh for installed company research."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from company_research import company_directory
from data_pipeline import build_release
from sec_import import plan_sec_import


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of",type=date.fromisoformat,required=True)
    parser.add_argument("--cache",type=Path,default=Path("data_cache"))
    parser.add_argument("--store",type=Path,default=Path("data_cache/published"))
    parser.add_argument("--issuer-key",action="append")
    parser.add_argument("--tickers",nargs="+",help="Resolve exact tickers through the verified SEC directory")
    parser.add_argument("--download",action="store_true")
    args=parser.parse_args()
    expected=None
    if args.tickers:
        if args.issuer_key:parser.error("Choose tickers or installed issuer keys")
        plan=plan_sec_import(args.store,args.tickers)
        source_ids=[f"sec_submissions_cik{entry.cik:010d}" for entry in plan.issuers]
        expected=plan.directory_sha256
    else:
        directory=company_directory(args.store,today=args.as_of)
        entries={entry.issuer_key:entry for entry in directory.entries}
        keys=args.issuer_key or list(entries)
        if not keys or len(keys)>25 or len(set(keys))!=len(keys) or any(key not in entries for key in keys):
            parser.error("Choose at most 25 unique installed research issuers")
        source_ids=[f"sec_submissions_cik{entries[key].cik:010d}" for key in keys]
    digest,manifest=build_release(args.cache,args.store,as_of=args.as_of,download=args.download,
                                source_ids=source_ids,expected_directory_sha=expected)
    print(json.dumps(dict(release_id=digest,requested_issuers=len(source_ids),
        installed=sum(key in manifest.tables for key in source_ids),
        failures={key:value.model_dump(mode="json") for key,value in manifest.failures.items() if key in source_ids}),indent=2))


if __name__=="__main__":main()
