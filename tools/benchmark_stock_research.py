"""Bounded offline stock-research latency; no HTTP/load-test or performance claim."""
import argparse
from datetime import date
import json
from math import ceil
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stock_screen import stock_screen
from public_data_store import atomic_json


def benchmark(public,history,*,as_of,iterations=3,run=stock_screen,clock=perf_counter):
    if type(iterations) is not int or not 1<=iterations<=7:raise ValueError('Use one to seven observations')
    timings=[];identity=None
    for _ in range(iterations):
        started=clock()
        result=run(public,history,mode='local_research',today=as_of)
        elapsed=clock()-started
        if result.status!='available' or elapsed<0:raise ValueError('Research unavailable or invalid measurement clock')
        current=(result.public_release_id,result.market_snapshot_sha256)
        if None in current or identity is not None and current!=identity:
            raise ValueError('Source snapshots changed during measurement')
        identity=current;timings.append(round(elapsed*1000,3))
    return dict(benchmark_version='stock-research-latency-v1',checked_on=str(as_of),
        public_release_id=identity[0],market_snapshot_sha256=identity[1],
        installed_financial_issuers=len(result.rows),reference_securities=len(result.security_coverage),
        iterations=iterations,observed_ms=timings,median_ms=median(timings),
        observed_p95_ms=sorted(timings)[ceil(.95*len(timings))-1],
        environment={'python':platform.python_version(),'system':platform.system()},
        notice='Sequential in-process reads/calculations with artifact integrity checks. The OS file cache is not cleared; the first observation is not a guaranteed cold start. Small-sample p95 is descriptive, not a latency guarantee, HTTP benchmark, concurrency test or investment result.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--as-of',required=True,type=date.fromisoformat)
    p.add_argument('--public-store',type=Path,default=Path('data_cache/published'))
    p.add_argument('--history-store',type=Path,default=Path('data_cache/local_market_history'))
    p.add_argument('--iterations',type=int,default=3)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        result=benchmark(a.public_store,a.history_store,as_of=a.as_of,iterations=a.iterations)
        atomic_json(a.output,result);print(json.dumps(result,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError):
        print(json.dumps({'status':'not_completed','reason':'Stable available source snapshots required; no timing result published.'}));return 1


if __name__=='__main__':raise SystemExit(main())
