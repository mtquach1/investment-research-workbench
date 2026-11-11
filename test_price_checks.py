from datetime import date,datetime,timezone
from decimal import Decimal
import json
import pytest
from market_history import publish_history
from test_market_history import bundle
from price_checks import check_price,load_price_check,fetch_reference,freshness_label


def test_diagnostic_agreement_discrepancy_failure_and_snapshot_binding(tmp_path):
    digest=publish_history(tmp_path,bundle())
    now=datetime(2026,10,29,2,tzinfo=timezone.utc)
    close=bundle().series['AAPL'].bars[-1].raw_close
    result=check_price(tmp_path,'AAPL',now=now,fetch=lambda *_:close+Decimal('.01'))
    assert result.status=='within_tolerance' and not result.full_history_verified
    assert load_price_check(tmp_path,'AAPL',digest,result.price_date)==result
    assert load_price_check(tmp_path,'AAPL','0'*64,result.price_date) is None
    assert load_price_check(tmp_path,'../AAPL',digest,result.price_date) is None
    result=check_price(tmp_path,'AAPL',now=now,fetch=lambda *_:close*2)
    assert result.status=='discrepancy' and result.difference_percent==50
    def unavailable(*_):raise ValueError('No reference')
    assert check_price(tmp_path,'AAPL',now=now,fetch=unavailable).status=='unavailable'
    assert bundle().series['AAPL'].bars[-1].raw_close==close


def test_reference_checks_identity_dates_duplicates_and_values():
    payload={'chart':{'error':None,'result':[{'meta':{'symbol':'AAPL','currency':'USD','exchangeTimezoneName':'America/New_York'},
             'timestamp':[1793213400],'indicators':{'quote':[{'close':[123.45]}]}}]}}
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def read(self,n):return json.dumps(payload).encode()
    class Opener:
        def open(self,request,timeout):
            assert request.full_url.startswith('https://query1.finance.yahoo.com/') and timeout==15
            return Response()
    observed=datetime.fromtimestamp(1793213400,timezone.utc).date()
    assert fetch_reference('AAPL',observed,opener=Opener())==Decimal('123.45')
    payload['chart']['result'][0]['meta']['currency']='CAD'
    with pytest.raises(ValueError):fetch_reference('AAPL',observed,opener=Opener())
    payload['chart']['result'][0]['meta']['currency']='USD'
    payload['chart']['result'][0]['indicators']['quote'][0]['close']=[True]
    with pytest.raises(ValueError):fetch_reference('AAPL',observed,opener=Opener())
    with pytest.raises(ValueError):fetch_reference('../AAPL',observed,opener=Opener())


def test_freshness_uses_completed_sessions_not_weekend_calendar_age():
    sunday=datetime(2026,11,1,18,tzinfo=timezone.utc)
    assert 'Latest completed trading session' in freshness_label(date(2026,10,30),sunday)
    assert 'refresh needed' in freshness_label(date(2026,10,29),sunday)
    assert 'future' in freshness_label(date(2026,11,2),sunday)
