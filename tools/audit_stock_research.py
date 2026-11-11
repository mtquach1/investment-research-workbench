"""Offline measured stock coverage. No credentials, network, user budgets or recommendations."""
import argparse
from collections import Counter
from datetime import date
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stock_screen import stock_screen
from market_history import load_history
from public_data_store import atomic_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',type=date.fromisoformat,required=True)
    parser.add_argument('--public-store',type=Path,default=Path('data_cache/published'))
    parser.add_argument('--history-store',type=Path,default=Path('data_cache/local_market_history'))
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    screen=stock_screen(args.public_store,args.history_store,mode='local_research',today=args.as_of)
    if screen.status!='available':
        print(json.dumps({'status':screen.status,'live_recommendations_enabled':False}));return 1
    digest,history=load_history(args.history_store)
    report={'audit_version':'stock-input-audit-v1','checked_on':str(args.as_of),'public_release_id':screen.public_release_id,
        'market_snapshot_sha256':digest,'strategy_sha256':screen.strategy_sha256,'universe_sha256':screen.universe.source_sha256,
        'universe_date':str(screen.universe.observed_on),'reference_securities':len(screen.security_coverage),
        'installed_financial_issuers':len(screen.rows),'installed_market_series':len(history.series),
        'security_date_records':sum(len(row.bars) for row in history.series.values()),
        'financial_states':dict(Counter(row.financial_status for row in screen.rows)),
        'valuation_states':dict(Counter(row.valuation.status for row in screen.rows)),
        'listing_states':dict(Counter(row.listing.status for row in screen.security_coverage)),
        'listing_reference_hashes':screen.listing_reference_hashes,
        'class_share_ledger_scope':'installed_financial_issuers_only',
        'class_share_ledger_states':dict(Counter(row.class_share_ledger.share_observation.status for row in screen.rows if row.class_share_ledger)),
        'class_share_reconciled_issuers':sum(bool(row.class_share_ledger and row.class_share_ledger.class_quantities_reconciled) for row in screen.rows),
        'historical_class_statement_matches':sum(item.historical_quantity is not None and item.historical_quantity.status=='matched_historical_statement'
            for row in screen.rows if row.class_share_ledger for item in row.class_share_ledger.securities),
        'historical_class_review_states':dict(Counter(item.historical_quantity.status for row in screen.rows if row.class_share_ledger
            for item in row.class_share_ledger.securities if item.historical_quantity)),
        'class_share_ledgers':{row.issuer_key:row.class_share_ledger.model_dump(mode='json') for row in screen.rows if row.class_share_ledger},
        'filing_class_corroborated_issuers':sum(any(item.status=='corroborated_filing_class' for item in row.filing_class_evidence.values()) for row in screen.rows),
        'filing_class_evidence':{row.issuer_key:{symbol:item.model_dump(mode='json') for symbol,item in row.filing_class_evidence.items()
            if item.status!='unavailable'} for row in screen.rows if any(item.status!='unavailable' for item in row.filing_class_evidence.values())},
        'metric_states':{key:dict(Counter(row.metrics[key].status for row in screen.rows)) for key in screen.rows[0].metrics} if screen.rows else {},
        'sector_counts':dict(Counter(row.sector or 'unavailable' for row in screen.rows)),
        'security_coverage':[row.model_dump(mode='json') for row in screen.security_coverage],
        'blocking_requirements':screen.blockers,'live_recommendations_enabled':False,'public_market_data_redistribution_allowed':False}
    if args.output:atomic_json(args.output,report)
    print(json.dumps({key:value for key,value in report.items() if key not in ('security_coverage','metric_states','class_share_ledgers')},indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
