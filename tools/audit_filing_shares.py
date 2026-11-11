"""Offline reconciliation to a fixed, manually read two-filing reference cohort."""
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stock_screen import stock_screen
from public_data_store import atomic_json


def reconcile(screen,cases):
    rows={row.issuer_key:row for row in screen.rows} if screen.status=='available' else {}
    findings=[]
    for case in cases:
        row=rows.get(case['issuer_key'])
        ledger=row.class_share_ledger if row else None
        matches=[item for item in ledger.filing_point_observations if item.tag==case['tag']
            and str(item.measured_on)==case['measured_on'] and item.accession==case['accession']
            and item.source.source_sha256==case['source_sha256'] and not item.dimensions] if ledger else []
        status='unavailable' if not matches else 'ambiguous' if len(matches)!=1 else (
            'pass' if matches[0].shares==Decimal(case['shares']) and matches[0].decimals==case['decimals'] else 'mismatch')
        findings.append(dict(**case,status=status,observed_shares=str(matches[0].shares) if len(matches)==1 else None))
    return findings


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',type=date.fromisoformat,required=True)
    parser.add_argument('--public-store',type=Path,default=Path('data_cache/published'))
    parser.add_argument('--history-store',type=Path,default=Path('data_cache/local_market_history'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    references=json.loads((Path(__file__).resolve().parents[1]/'data/filing_share_reference_cases.json').read_text())
    screen=stock_screen(args.public_store,args.history_store,mode='local_research',today=args.as_of)
    findings=reconcile(screen,references['cases'])
    report=dict(audit_version='filing-share-reference-audit-v1',reference_version=references['reference_version'],
        checked_on=str(args.as_of),status=screen.status,public_release_id=screen.public_release_id,
        counts=dict(Counter(item['status'] for item in findings)),findings=findings,
        notice='Checks tagged quantities and precision against manually read same-filing references. Not an independent issuer source, complete class reconciliation, current valuation or strategy validation.')
    atomic_json(args.output,report)
    print(json.dumps({key:value for key,value in report.items() if key!='findings'},indent=2))
    return 0 if len(findings)==4 and all(item['status']=='pass' for item in findings) else 1


if __name__=='__main__':raise SystemExit(main())
