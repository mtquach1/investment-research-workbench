"""Plan/refresh SEC facts for installed issuers only; no private input or scheduler."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fundamental_refresh import plan_fundamental_refresh,refresh_fundamentals
from public_data_store import atomic_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',type=date.fromisoformat,required=True)
    parser.add_argument('--cache',type=Path,default=Path('data_cache'))
    parser.add_argument('--store',type=Path,default=Path('data_cache/published'))
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if not args.download:
            plan=plan_fundamental_refresh(args.store,as_of=args.as_of)
            atomic_json(args.output,plan.model_dump(mode='json'))
            print(json.dumps({'status':'plan_only_no_network','installed_issuers':len(plan.observations),'release_id':plan.previous_release_id}))
            return 0
        def progress(row):
            if row['completed_sources']%8==0 or row['completed_sources']==row['total_sources']:
                print(json.dumps({'progress':row['completed_sources'],'total_sources':row['total_sources']}),flush=True)
        result=refresh_fundamentals(args.cache,args.store,as_of=args.as_of,progress=progress)
        atomic_json(args.output,result.model_dump(mode='json'))
        print(json.dumps({key:value for key,value in result.model_dump(mode='json').items() if key!='changes'},indent=2))
        return 1 if result.status=='degraded' else 0
    except (ValueError,OSError,KeyError,TypeError):
        print(json.dumps({'status':'not_completed','reason':'Check installed source integrity, fresh directory and SEC identification. No provider error body or credentials are logged.'}))
        return 1


if __name__=='__main__':raise SystemExit(main())
