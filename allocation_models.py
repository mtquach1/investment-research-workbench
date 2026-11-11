"""Contracts for contribution-only allocation; all trade amounts are integer cents."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, model_validator

from schemas import StrictModel


Money = Annotated[Decimal, Field(ge=0, le=10_000_000, decimal_places=2, allow_inf_nan=False)]
Weight = Annotated[Decimal, Field(ge=0, le=1, decimal_places=6, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")]


class AllocationAsset(StrictModel):
    asset_id: Identifier
    target_weight: Weight
    max_weight: Weight = Decimal(1)


class AllocationAccount(StrictModel):
    account_id: Identifier
    account_type: Literal["taxable", "traditional", "roth"]
    available_cash: Money
    holdings: dict[Identifier, Money] = Field(default_factory=dict, max_length=30)
    allowed_assets: list[Identifier] = Field(max_length=30)

    @model_validator(mode="after")
    def unique_allowed_assets(self):
        if len(self.allowed_assets) != len(set(self.allowed_assets)):
            raise ValueError("Allowed assets must be unique")
        return self


class AllocationRequest(StrictModel):
    assets: list[AllocationAsset] = Field(min_length=1, max_length=30)
    accounts: list[AllocationAccount] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def consistent_universe(self):
        ids = {asset.asset_id for asset in self.assets}
        if len(ids) != len(self.assets):
            raise ValueError("Asset identifiers must be unique")
        if len({account.account_id for account in self.accounts}) != len(self.accounts):
            raise ValueError("Account identifiers must be unique")
        if sum(asset.target_weight for asset in self.assets) != Decimal(1):
            raise ValueError("Target weights must sum to exactly one")
        for account in self.accounts:
            if not set(account.holdings).issubset(ids) or not set(account.allowed_assets).issubset(ids):
                raise ValueError("Holdings and permissions must reference declared assets")
        if not any(account.available_cash or any(account.holdings.values()) for account in self.accounts):
            raise ValueError("Portfolio must contain holdings or cash")
        return self


class AllocationTrade(StrictModel):
    account_id: str
    asset_id: str
    amount_cents: int


class AllocationExposure(StrictModel):
    asset_id: str
    before_cents: int
    purchase_cents: int
    after_cents: int
    target_weight: float
    after_weight: float
    max_weight: float


class AllocationBaseline(StrictModel):
    name: str
    feasible: bool
    absolute_weight_drift: float
    trades: list[AllocationTrade]


class AllocationResponse(StrictModel):
    model_version: Literal["contribution-allocation-l1-v1"] = "contribution-allocation-l1-v1"
    status: Literal["optimal", "infeasible", "limit", "error"]
    explanation: str
    total_after_cents: int
    cash_to_invest_cents: int
    trades: list[AllocationTrade] = Field(default_factory=list)
    exposures: list[AllocationExposure] = Field(default_factory=list)
    absolute_weight_drift: float | None = None
    solver_lower_bound_drift: float | None = None
    solver_gap: float | None = None
    elapsed_ms: float
    baselines: list[AllocationBaseline] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=lambda: [
        "Targets and permissions are user inputs, not recommended investments.",
        "Cash is already available inside each account; contribution eligibility and affordability are not checked.",
        "Account types are descriptive; this version does not optimize taxes or asset location.",
        "No sales, transfers, fees, prices, share lots, returns, correlations, or trade execution are modeled.",
        "Dollar purchases assume fractional-share availability. Optimality concerns this allocation model only.",
    ])
