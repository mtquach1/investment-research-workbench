"""Plan or run a complete installed-cohort refresh; never schedules or changes feeds."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from daily_stock_refresh import plan_daily_refresh, refresh_installed_history, rollback_history


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',type=date.fromisoformat)
    parser.add_argument('--public-store',type=Path,default=Path('data_cache/published'))
    parser.add_argument('--store',type=Path,default=Path('data_cache/local_market_history'))
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--restart-staging',action='store_true',help='Re-download every batch; retain old artifacts without reusing checkpoints')
    parser.add_argument('--rollback-to')
    parser.add_argument('--expected-current')
    args=parser.parse_args()
    if args.rollback_to:
        if not args.expected_current or args.download or args.as_of or args.restart_staging: parser.error('Rollback requires --expected-current and no refresh flags')
    elif not args.as_of or args.expected_current: parser.error('Refresh requires --as-of; rollback flags are separate')
    if args.restart_staging and not args.download: parser.error('--restart-staging requires --download')
    try:
        now=datetime.now(timezone.utc)
        if args.rollback_to:
            result=rollback_history(args.store,args.rollback_to,expected_current=args.expected_current,now=now)
        elif args.download:
            result=refresh_installed_history(args.public_store,args.store,as_of=args.as_of,now=now,
                resume=not args.restart_staging,
                progress=lambda row:print(json.dumps({'progress':row}),flush=True))
        else:
            plan,previous=plan_daily_refresh(args.public_store,args.store,as_of=args.as_of,now=now)
            print(json.dumps({'status':'plan_only_no_network','plan_sha256':plan.digest,
                'plan':plan.model_dump(mode='json'),'installed_series':len(previous.series),
                'public_redistribution_allowed':False},indent=2))
            return 0
        print(result.model_dump_json(indent=2))
        return 1 if result.status=='not_published' else 0
    except (ValueError,OSError,KeyError,TypeError):
        print(json.dumps({'status':'not_published','reason':'Refresh preflight or storage validation failed. Check the installed snapshot, fresh issuer directory, requested cutoff and local credentials. CURRENT was not intentionally replaced by this failure.'}))
        return 1


if __name__=='__main__':raise SystemExit(main())
