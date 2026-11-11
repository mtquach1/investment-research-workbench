"""Bounded capability checks must not mutate subscriptions or publish data."""
from datetime import date, datetime, timezone
import json
from urllib.error import HTTPError
from io import BytesIO
import pytest
from tools.probe_stock_data_access import probe


NOW=datetime(2026,10,31,20,tzinfo=timezone.utc)


class Response(BytesIO):
    status=200


class FakeTransport:
    def __init__(self, fail=None):self.requests=[];self.fail=fail
    def open(self, request, timeout):
        self.requests.append(request)
        if self.fail:raise self.fail
        bar={'t':'2026-10-28T04:00:00Z','o':100,'h':101,'l':99,'c':100}
        return Response(json.dumps({'bars':{key:[bar] for key in ('AAPL','NVDA','SPY')},'next_page_token':None}).encode())


def run(tmp_path, transport):
    return probe(start=date(2026,10,27),end=date(2026,10,30),now=NOW,
        headers={'APCA-API-KEY-ID':'PRIVATE_TEST_KEY'},transport_root=tmp_path,opener=transport)


def test_fixed_data_host_six_requests_no_credentials_prices_or_publication(tmp_path):
    transport=FakeTransport();report=run(tmp_path,transport)
    assert len(transport.requests)==6 and all(row['status']=='accessible_sample' for row in report['results'])
    assert all(request.full_url.startswith('https://data.alpaca.markets/v2/stocks/bars?') for request in transport.requests)
    rendered=json.dumps(report)
    assert 'PRIVATE_TEST_KEY' not in rendered and 'raw_close' not in rendered
    assert not report['subscription_changed'] and not report['published'] and not report['public_redistribution_verified']


def test_entitlement_error_body_is_never_read_or_echoed(tmp_path):
    body=BytesIO(b'SENSITIVE_PROVIDER_ERROR_BODY')
    transport=FakeTransport(HTTPError('https://data.alpaca.markets',403,'refused',{},body))
    report=run(tmp_path,transport)
    assert len(transport.requests)==2  # one attempt per explicitly requested feed
    assert all(row['http_status']==403 for row in report['results'])
    assert 'SENSITIVE_PROVIDER_ERROR_BODY' not in json.dumps(report)
    assert body.closed


@pytest.mark.parametrize('start,end',[
    (date(2026,10,1),date(2026,10,30)),(date(2026,10,30),date(2026,11,1)),
    (date(2026,10,30),date(2026,10,30)),
])
def test_unbounded_future_and_empty_windows_fail_before_network(tmp_path,start,end):
    transport=FakeTransport()
    with pytest.raises(ValueError):probe(start=start,end=end,now=NOW,headers={},transport_root=tmp_path,opener=transport)
    assert not transport.requests


def test_missing_symbol_or_pagination_cannot_pass_capability_check(tmp_path):
    class Incomplete:
        def open(self,request,timeout):
            return Response(b'{"bars":{"AAPL":[]},"next_page_token":"unbounded"}')
    result=run(tmp_path,Incomplete())
    assert all(row['status']=='transport_or_payload_failure' for row in result['results'])
