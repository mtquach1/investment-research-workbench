"""Date-window semantics and faithful chart input values."""

from datetime import date
import pytest
from history_chart import range_start,comparison_chart
from market_history import compare_history
from test_market_history import series


def test_ranges_use_calendar_months_and_leap_days():
    assert range_start("1M",date(2026,3,31))==date(2026,2,28)
    assert range_start("1Y",date(2024,2,29))==date(2023,2,28)
    assert range_start("YTD",date(2026,10,28))==date(2026,1,1)
    assert range_start("1W",date(2026,10,28))==date(2026,10,21)
    assert range_start("All",date(2026,10,28)) is None
    with pytest.raises(KeyError):range_start("invalid",date(2026,10,28))


def test_chart_retains_observed_dates_and_does_not_smooth_financial_paths():
    points=compare_history(series([100,120,90]),series([100,101,102],"SPY")).points
    chart=comparison_chart(points,company_label="AAPL")
    spec=chart.to_dict()
    datasets=list(spec["datasets"].values())
    rows=next(rows for rows in datasets if rows and "Primary" in rows[0])
    assert [row["Primary"] for row in rows]==[100,120,90]
    assert [row["Exact date"] for row in rows]==["2026-10-26","2026-10-27","2026-10-28"]
    assert next(layer for layer in spec["layer"] if layer.get("mark",{}).get("type")=="line")["mark"]["interpolate"]=="linear"


def test_share_price_uses_unadjusted_dollars_and_hides_benchmark():
    from decimal import Decimal
    a=series([100,120,90]);b=series([100,101,102],"SPY")
    a.bars[0].raw_close=Decimal('200');a.bars[1].raw_close=Decimal('240');a.bars[2].raw_close=Decimal('180')
    spec=comparison_chart(compare_history(a,b).points,company_label="AAPL",share_price=True,raw_price=True).to_dict()
    rows=next(rows for rows in spec['datasets'].values() if rows and 'Primary' in rows[0])
    assert [row['Primary'] for row in rows]==[200,240,180]
    line=next(layer for layer in spec['layer'] if layer.get('mark',{}).get('type')=='line')
    assert line['transform'][0]['fold']==['Primary']
