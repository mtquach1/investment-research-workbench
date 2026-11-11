"""Plan SEC company imports; --download explicitly executes the bounded plan."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from sec_import import execute_sec_import, plan_sec_import


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers",nargs="+",required=True)
    parser.add_argument("--as-of",type=date.fromisoformat,required=True)
    parser.add_argument("--cache",type=Path,default=Path("data_cache"))
    parser.add_argument("--store",type=Path,default=Path("data_cache/published"))
    parser.add_argument("--maximum-new",type=int,default=25)
    parser.add_argument("--download",action="store_true")
    args=parser.parse_args()
    if args.download:
        plan,digest,manifest=execute_sec_import(args.cache,args.store,args.tickers,as_of=args.as_of,
            maximum_new_issuers=args.maximum_new)
        print(json.dumps({"release_id":digest,"plan":plan.model_dump(),
            "requested_issuer_failures":{row.source_id:manifest.failures[row.source_id].model_dump(mode="json")
                for row in plan.issuers if row.source_id in manifest.failures}},indent=2))
    else:
        print(plan_sec_import(args.store,args.tickers,maximum_new_issuers=args.maximum_new).model_dump_json(indent=2))


if __name__=="__main__":
    main()
