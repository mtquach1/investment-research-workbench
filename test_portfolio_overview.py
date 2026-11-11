"""Portfolio geometry and dollar allocations reconcile to exact entered weights."""

import pytest

from portfolio_overview import PortfolioComposition,PortfolioHolding,composition_rows,example_composition


def test_user_example_has_exact_six_slices_and_allocated_dollars():
    request=example_composition()
    rows=composition_rows(request)
    assert [row["weight_percent"] for row in rows]==[20,15,25,15,10,15]
    assert sum(row["weight_bps"] for row in rows)==10000
    assert [row["amount_cents"] for row in rows]==[200000,150000,250000,150000,100000,150000]
    assert request.origin=="user_defined" and rows[-1]["kind"]=="Index placeholder"


def test_cash_cent_rounding_and_overallocation_are_explicit():
    request=PortfolioComposition(budget_cents=101,holdings=[
        PortfolioHolding(symbol="AAA",name="A",kind="Stock",weight_bps=3333),
        PortfolioHolding(symbol="BBB",name="B",kind="Stock",weight_bps=3333)])
    rows=composition_rows(request)
    assert sum(row["amount_cents"] for row in rows)==101
    assert rows[-1]["symbol"]=="CASH" and rows[-1]["weight_bps"]==3334
    assert [row["amount_cents"] for row in rows]==[34,33,34]
    bad=example_composition().model_dump();bad["holdings"][0]["weight_bps"]=3000
    with pytest.raises(ValueError):PortfolioComposition.model_validate(bad)
    bad=example_composition().model_dump();bad["holdings"][1]["symbol"]="AAPL"
    with pytest.raises(ValueError):PortfolioComposition.model_validate(bad)


def test_zero_weights_are_cash_and_fake_strategy_origin_is_rejected():
    request=PortfolioComposition(budget_cents=3,holdings=[PortfolioHolding(symbol="AAA",name="A",kind="Stock",weight_bps=0)])
    assert composition_rows(request)[0]["symbol"]=="CASH"
    with pytest.raises(ValueError):PortfolioComposition.model_validate(dict(example_composition().model_dump(),origin="synthetic_strategy"))
