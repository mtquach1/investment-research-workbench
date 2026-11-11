"""Small read-only Alpaca feed diagnostic; never publishes or upgrades a plan.

Uses existing credentials only against data.alpaca.markets. Results contain
counts/dates and response hashes, never credentials, prices or error bodies.
This is deliberately separate from the IEX-only production importer.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alpaca_history import BASE, NoRedirects, credentials, _bar
from public_data_store import atomic_json, strict_json, provider_turn


def probe(*, start, end, now, headers, transport_root, opener=None):
    if now.tzinfo is None or type(start) is not date or type(end) is not date:
        raise ValueError('Explicit dates and aware clock required')
    # A tiny completed historical window only, outside even the stricter delay.
    if not 1 <= (end - start).days <= 7 or datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc) > now - timedelta(days=1):
        raise ValueError('Use a one-to-seven-day window ending at least one day ago')
    opener = opener or build_opener(NoRedirects())
    results = []
    for feed in ('iex', 'sip'):
        for adjustment in ('raw', 'split', 'all'):
            params = dict(symbols='AAPL,NVDA,SPY', timeframe='1Day', start=start.isoformat()+'T00:00:00Z',
                end=end.isoformat()+'T00:00:00Z', limit=100, feed=feed, adjustment=adjustment, sort='asc')
            result = {'feed': feed, 'adjustment': adjustment, 'status': 'unavailable'}
            try:
                with provider_turn(transport_root, 'data.alpaca.markets', .5):
                    with opener.open(Request(BASE+'?'+urlencode(params), headers=headers), timeout=20) as response:
                        if response.status != 200:
                            result['http_status'] = response.status
                            results.append(result)
                            break
                        body = response.read(1024*1024+1)
                if len(body) > 1024*1024:
                    raise ValueError('Response byte limit')
                payload = strict_json(body)
                if (not isinstance(payload, dict) or set(payload)-{'bars', 'next_page_token'} or
                    not isinstance(payload.get('bars'), dict) or payload.get('next_page_token') is not None or
                    set(payload['bars']) != {'AAPL', 'NVDA', 'SPY'}):
                    raise ValueError('Unexpected bounded probe payload')
                dates = {}
                for symbol, bars in payload['bars'].items():
                    if not isinstance(bars, list) or not 1 <= len(bars) <= 7:
                        raise ValueError('Missing or excessive bars')
                    days = [_bar(bar, start=start, last=end-timedelta(days=1))[0].isoformat() for bar in bars]
                    if len(set(days)) != len(days): raise ValueError('Duplicate bars')
                    dates[symbol] = sorted(days)
                result.update(status='accessible_sample', response_sha256=hashlib.sha256(body).hexdigest(),
                    observation_dates=dates, bar_counts={key:len(value) for key,value in dates.items()})
            except HTTPError as error:
                result['http_status'] = error.code
                result['status'] = 'authentication_or_entitlement_refused' if error.code in (401,403) else 'http_failure'
                error.close()  # Never read or emit provider error bodies.
                results.append(result)
                break  # No retries, different symbols or paid endpoint fallback.
            except (URLError, OSError, TimeoutError, ValueError, TypeError, KeyError):
                result['status'] = 'transport_or_payload_failure'
                results.append(result)
                break
            results.append(result)
    return {'diagnostic_version':'alpaca-feed-access-probe-v1','checked_at':now.isoformat(),
        'window_start':start.isoformat(),'window_end_exclusive':end.isoformat(),'results':results,
        'published':False,'subscription_changed':False,'public_redistribution_verified':False,
        'notice':'Bounded access diagnostic only. Sample access does not establish plan identity, full history coverage, adjustment accuracy, exact total return or public redistribution rights.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start',type=date.fromisoformat,required=True)
    parser.add_argument('--end-exclusive',type=date.fromisoformat,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=probe(start=args.start,end=args.end_exclusive,now=datetime.now(timezone.utc),headers=credentials(),
        transport_root=Path('data_cache/local_market_history/transport'))
    atomic_json(args.output,report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
