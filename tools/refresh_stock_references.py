"""Plan offline; explicitly download a bounded complete stock-reference cohort."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reference_refresh import plan_reference_refresh,refresh_references
from public_data_store import atomic_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--as-of',type=date.fromisoformat,required=True)
    p.add_argument('--cache',type=Path,default=Path('data_cache'))
    p.add_argument('--store',type=Path,default=Path('data_cache/published'))
    p.add_argument('--download',action='store_true')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:
        result=(refresh_references(args.cache,args.store,as_of=args.as_of) if args.download else
            plan_reference_refresh(args.store,as_of=args.as_of))
        atomic_json(args.output,result.model_dump(mode='json'))
        print(json.dumps({'status':result.status if args.download else 'plan_only_no_network',
            'sources':4,'strict_recommendations_enabled':False}))
        return 0 if not args.download or result.status=='published' else 1
    except (ValueError,OSError,KeyError,TypeError):
        print(json.dumps({'status':'not_completed','reason':'Check installed reference integrity and source configuration; no provider response or credentials are logged.'}))
        return 1


if __name__=='__main__':raise SystemExit(main())
