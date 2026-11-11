"""Session portfolio composition and exact cent allocation, not stock selection."""

from decimal import Decimal
from typing import Literal
from pydantic import Field, model_validator

from data_pipeline import Contract


class PortfolioHolding(Contract):
    symbol: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._ -]{0,29}$")
    name: str = Field(min_length=1,max_length=80)
    kind: Literal["Stock","ETF","Index placeholder","Synthetic"]
    weight_bps: int = Field(ge=0,le=10000,strict=True)


class PortfolioComposition(Contract):
    budget_cents: int = Field(ge=0,le=100_000_000,strict=True)
    holdings: list[PortfolioHolding] = Field(min_length=1,max_length=25)
    origin: Literal["user_defined","synthetic_strategy"] = "user_defined"

    @model_validator(mode="after")
    def bounded(self):
        if len({row.symbol for row in self.holdings})!=len(self.holdings):raise ValueError("Each symbol must appear once; combine duplicate holdings")
        if any(row.symbol=="CASH" for row in self.holdings):raise ValueError("Cash is computed automatically")
        if sum(row.weight_bps for row in self.holdings)>10000:raise ValueError("Weights exceed 100%; reduce allocations before charting")
        if self.origin=="synthetic_strategy" and any(row.kind!="Synthetic" for row in self.holdings):
            raise ValueError("Synthetic basket must retain synthetic labels")
        return self


def composition_rows(request):
    request=PortfolioComposition.model_validate(request.model_dump())
    rows=[dict(symbol=row.symbol,name=row.name,kind=row.kind,weight_bps=row.weight_bps) for row in request.holdings if row.weight_bps]
    residual=10000-sum(row["weight_bps"] for row in rows)
    if residual:rows.append(dict(symbol="CASH",name="Unallocated cash",kind="Cash",weight_bps=residual))
    for row in rows:row["amount_cents"]=request.budget_cents*row["weight_bps"]//10000
    extra=request.budget_cents-sum(row["amount_cents"] for row in rows)
    ranked=sorted(rows,key=lambda row:(-(request.budget_cents*row["weight_bps"]%10000),row["symbol"]))
    for row in ranked[:extra]:row["amount_cents"]+=1
    for row in rows:
        row.update(weight_percent=row["weight_bps"]/100,amount=row["amount_cents"]/100)
    return rows


def example_composition(budget_cents=1_000_000):
    return PortfolioComposition(budget_cents=budget_cents,holdings=[PortfolioHolding(symbol=symbol,name=name,kind=kind,weight_bps=weight)
        for symbol,name,kind,weight in [("AAPL","Apple","Stock",2000),("MSFT","Microsoft","Stock",1500),
            ("NVDA","NVIDIA","Stock",2500),("VOO","Vanguard S&P 500 ETF","ETF",1500),
            ("AMZN","Amazon","Stock",1000),("SP500_INDEX","S&P 500 · fund unspecified","Index placeholder",1500)]])
