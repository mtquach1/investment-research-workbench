from types import SimpleNamespace
import pytest
from tools.benchmark_stock_research import benchmark


def test_latency_report_refuses_mixed_snapshots_and_unavailable_research():
    results=iter([SimpleNamespace(status='available',public_release_id='a',market_snapshot_sha256='b'),
        SimpleNamespace(status='available',public_release_id='changed',market_snapshot_sha256='b')])
    with pytest.raises(ValueError,match='changed'):
        benchmark(None,None,as_of='2026-11-01',iterations=2,run=lambda *a,**k:next(results))
    with pytest.raises(ValueError,match='unavailable'):
        benchmark(None,None,as_of='2026-11-01',run=lambda *a,**k:SimpleNamespace(status='unavailable'))
