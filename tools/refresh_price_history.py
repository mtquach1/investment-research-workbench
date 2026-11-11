"""Prepare or download a bounded free IEX research batch. No paid fallback."""

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from alpaca_history import HistoryImportError, import_plan, refresh_history


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols",nargs="+",required=True)
    parser.add_argument("--start",type=date.fromisoformat,required=True)
    parser.add_argument("--as-of",type=date.fromisoformat,required=True)
    parser.add_argument("--public-store",type=Path,default=Path("data_cache/published"))
    parser.add_argument("--store",type=Path,default=Path("data_cache/local_market_history"))
    parser.add_argument("--download",action="store_true")
    parser.add_argument("--merge",action="store_true",help="Retain compatible installed series with original retrieval timestamps")
    args=parser.parse_args()
    try:
        if args.download:
            digest,bundle=refresh_history(args.public_store,args.store,args.symbols,start=args.start,as_of=args.as_of,merge=args.merge)
            print(json.dumps(dict(status="published_local_research",sha256=digest,feed=bundle.feed,
                completed_through=bundle.completed_through.isoformat(),
                observations={key:len(row.bars) for key,row in bundle.series.items()},
                public_redistribution_allowed=False),indent=2))
        else:
            plan=import_plan(args.public_store,args.symbols,start=args.start,as_of=args.as_of,now=datetime.now(timezone.utc))
            print(json.dumps(dict(status="plan_only_no_network",symbols=plan["symbols"],start=plan["start"].isoformat(),
                completed_through=plan["last"].isoformat(),feed="iex",adjustments=["raw","all","split"],
                directory_sha256=plan["directory_sha256"],public_redistribution_allowed=False),indent=2))
    except (HistoryImportError,OSError,ValueError,KeyError,TypeError):
        # No raw provider body, request object or configuration validation input.
        print(json.dumps(dict(status="not_published",reason="Check local credentials, verified issuer mapping, completed date interval and provider availability; prior history is preserved.")))
        return 1
    return 0


if __name__=="__main__":raise SystemExit(main())
