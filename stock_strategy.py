"""Exact strategy math on synthetic inputs. Live recommendations remain disabled.

One canonical security per issuer is scored. With one sector per issuer, the
selection constraints form sector quotas plus a cardinality cap. Greedy exact
score ordering is optimal for this partition structure; no solver is necessary.
"""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from schemas import StrictModel
from strategy_financial_rules import financial_checks


Amount = Annotated[Decimal, Field(ge=-1e15, le=1e15, decimal_places=8, max_digits=24, allow_inf_nan=False)]
SyntheticID = Annotated[str, Field(pattern=r"^SYN_[A-Z0-9_]{1,30}$")]
FEATURES = ("return_on_assets", "operating_margin", "free_cashflow_margin", "earnings_yield", "free_cashflow_yield")
SPEC = json.loads((Path(__file__).parent/"strategies/quality_value_annual_v1.json").read_text())
SPEC_HASH = hashlib.sha256(json.dumps(SPEC, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
if ({row["name"] for row in SPEC["features"]} != set(FEATURES) or
        sum(Fraction(str(row["weight"])) for row in SPEC["features"]) != 1 or
        Fraction(str(SPEC["portfolio"]["target_weight_per_stock"]))*SPEC["portfolio"]["stock_count"] != 1):
    raise ValueError("Strategy features and weights must reconcile")


class SyntheticStock(StrictModel):
    security_id: SyntheticID
    issuer_id: SyntheticID
    sector: Literal["Communication Services", "Consumer Discretionary", "Consumer Staples", "Energy", "Financials",
                    "Health Care", "Industrials", "Information Technology", "Materials", "Real Estate", "Utilities"]
    period_end: date
    filed: date
    price_date: date
    return_observations: int = Field(ge=0, le=10000)
    revenue: Amount | None
    operating_income: Amount | None
    net_income: Amount | None
    operating_cashflow: Amount | None
    cash_capex: Amount | None
    assets_start: Amount | None
    assets_end: Amount | None
    liabilities: Amount | None
    issuer_market_cap: Amount | None
    price: Amount | None


class SyntheticUniverse(StrictModel):
    data_kind: Literal["synthetic"] = "synthetic"
    as_of: date
    stocks: list[SyntheticStock] = Field(min_length=1, max_length=600)
    available_cash_cents: int = Field(ge=0, le=100_000_000)

    @model_validator(mode="after")
    def coherent_issuers(self):
        if len({row.security_id for row in self.stocks}) != len(self.stocks):
            raise ValueError("Duplicate security identifiers")
        seen = {}
        for row in self.stocks:
            issuer_fields = row.model_dump(exclude={"security_id", "price", "price_date", "return_observations"})
            if row.issuer_id in seen and seen[row.issuer_id] != issuer_fields:
                raise ValueError("Issuer share classes must have the same financials and sector")
            seen[row.issuer_id] = issuer_fields
        return self


class StrategyDemoRequest(StrictModel):
    scenario: Literal["balanced", "sector_bottleneck", "missing_data"] = "balanced"
    available_cash_cents: int = Field(default=100_000, ge=0, le=100_000_000)


class StrategySelection(StrictModel):
    security_id: SyntheticID
    issuer_id: SyntheticID
    sector: str
    score: float
    target_weight: float
    purchase_cents: int


class StrategyFinding(StrictModel):
    security_id: SyntheticID
    issuer_id: SyntheticID
    sector: str
    reasons: list[str]
    score: float | None
    feature_percentiles: dict[str, float]
    score_contributions: dict[str, float] = Field(default_factory=dict)
    selected: bool


class StrategyDemoResponse(StrictModel):
    strategy_id: str
    strategy_sha256: str
    data_kind: Literal["synthetic"]
    status: Literal["synthetic_proposal", "infeasible"]
    as_of: str
    live_recommendations_enabled: Literal[False]
    explanation: str
    selected: list[StrategySelection]
    eligible_issuer_count: int
    findings: list[StrategyFinding]
    cash_unallocated_cents: int
    objective_score_sum: float | None
    limitations: list[str]


def select_sector_constrained(rows, *, count, sector_limit):
    """Input scores are exact Fractions; stable ID ties never perturb scores."""
    selected, sectors = [], Counter()
    for row in sorted(rows, key=lambda item: (-item["score"], item["issuer_id"], item["security_id"])):
        if sectors[row["sector"]] < sector_limit:
            selected.append(row)
            sectors[row["sector"]] += 1
            if len(selected) == count:
                return selected
    return []


def tied_percentiles(values):
    """Map issuer -> exact average-tied-rank percentile. Higher is better."""
    if len(values) < 2:
        raise ValueError("At least two peers are required")
    groups = defaultdict(list)
    for issuer, value in values.items():
        groups[value].append(issuer)
    position, result = 0, {}
    for value in sorted(groups):
        group = groups[value]
        percentile = Fraction(2*position+len(group)-1, 2*(len(values)-1))
        for issuer in group:
            result[issuer] = percentile
        position += len(group)
    return result


def evaluate_synthetic_strategy(request: SyntheticUniverse):
    request = SyntheticUniverse.model_validate(request.model_dump())
    findings, eligible = {}, []
    for row in sorted(request.stocks, key=lambda item: (item.issuer_id, item.security_id)):
        checks=financial_checks(row.model_dump(),SPEC)
        # The leverage check is dependent on assets/liabilities checks. Missing
        # inputs already have their own exclusion; do not claim excessive debt.
        reasons=[check["reason"] for check in checks if check["status"]!="pass"
                 and not (check["key"]=="leverage_limit" and check["status"]=="unavailable")]
        if row.price is None or row.price<=0:
            reasons.append("missing_or_nonpositive:price")
        fcf = row.operating_cashflow-row.cash_capex if row.operating_cashflow is not None and row.cash_capex is not None and row.cash_capex >= 0 else None
        if row.sector in SPEC["excluded_sectors"]:
            reasons.append("unsupported_sector")
        if not 0 <= (request.as_of-row.period_end).days <= SPEC["maximum_financial_period_age_days"]:
            reasons.append("stale_or_future_financial_period")
        if row.filed > request.as_of or row.filed < row.period_end:
            reasons.append("invalid_or_future_filing_date")
        if not 0 <= (request.as_of-row.price_date).days <= SPEC["maximum_price_age_calendar_days"]:
            reasons.append("stale_or_future_price")
        if row.return_observations < SPEC["risk_history"]["minimum_daily_return_observations"]:
            reasons.append("insufficient_return_history")
        finding = {"security_id": row.security_id, "issuer_id": row.issuer_id, "sector": row.sector,
                   "reasons": reasons, "score": None, "feature_percentiles": {}, "selected": False}
        findings[row.security_id] = finding
        if not reasons:
            eligible.append((row, fcf))
    # Collapse alternate share classes before computing sector peer populations.
    canonical, sectors = {}, defaultdict(list)
    for row, fcf in eligible:
        if row.issuer_id in canonical:
            findings[row.security_id]["reasons"].append("alternate_share_class")
            continue
        canonical[row.issuer_id] = row
        sectors[row.sector].append((row, fcf))
    scored = []
    weights = {item["name"]: Fraction(str(item["weight"])) for item in SPEC["features"]}
    for sector, peers in sectors.items():
        if len(peers) < SPEC["minimum_eligible_sector_peers"]:
            for row, _ in peers:
                findings[row.security_id]["reasons"].append("insufficient_sector_peers")
            continue
        metrics = {}
        for row, fcf in peers:
            metrics[row.issuer_id] = {
                "return_on_assets": Fraction(row.net_income)/((Fraction(row.assets_start)+Fraction(row.assets_end))/2),
                "operating_margin": Fraction(row.operating_income)/Fraction(row.revenue),
                "free_cashflow_margin": Fraction(fcf)/Fraction(row.revenue),
                "earnings_yield": Fraction(row.net_income)/Fraction(row.issuer_market_cap),
                "free_cashflow_yield": Fraction(fcf)/Fraction(row.issuer_market_cap)}
        percentiles = {name: tied_percentiles({issuer: values[name] for issuer, values in metrics.items()}) for name in FEATURES}
        for row, _ in peers:
            contributions = {name: weights[name]*percentiles[name][row.issuer_id] for name in FEATURES}
            score = sum(contributions.values())
            finding = findings[row.security_id]
            finding["score"] = float(score)
            finding["feature_percentiles"] = {name: float(percentiles[name][row.issuer_id]) for name in FEATURES}
            finding["score_contributions"] = {name: float(value) for name, value in contributions.items()}
            scored.append(dict(finding, score=score))
    count = SPEC["portfolio"]["stock_count"]
    chosen = select_sector_constrained(scored, count=count, sector_limit=SPEC["portfolio"]["maximum_stocks_per_sector"])
    status = "synthetic_proposal" if chosen and request.available_cash_cents >= count else "infeasible"
    selection = []
    if status == "synthetic_proposal":
        per_stock = request.available_cash_cents//count
        for row in chosen:
            findings[row["security_id"]]["selected"] = True
            selection.append({"security_id": row["security_id"], "issuer_id": row["issuer_id"], "sector": row["sector"],
                              "score": float(row["score"]), "target_weight": 1/count, "purchase_cents": per_stock})
    return {"strategy_id": SPEC["strategy_id"], "strategy_sha256": SPEC_HASH, "data_kind": "synthetic",
            "status": status, "as_of": request.as_of.isoformat(), "live_recommendations_enabled": False,
            "explanation": "Synthetic strategy example only; no real stocks or measured returns." if selection else
                           "The synthetic universe or cash budget cannot satisfy the strategy. No basket produced.",
            "selected": selection, "eligible_issuer_count": len(scored), "findings": list(findings.values()),
            "cash_unallocated_cents": request.available_cash_cents-sum(row["purchase_cents"] for row in selection),
            "objective_score_sum": float(sum(row["score"] for row in chosen)) if selection else None,
            "limitations": ["No live universe, company or price feed is used.", "Strategy scores do not establish S&P 500 outperformance.",
                            "Equal-weight dollar sizing leaves cent remainders uninvested; no fees or actual shares are modeled.",
                            "Existing holdings and account restrictions require the separate funding stage; they are not handled here."]}


def strategy_demo(request: StrategyDemoRequest):
    request = StrategyDemoRequest.model_validate(request.model_dump())
    sectors = ["Industrials", "Information Technology", "Health Care", "Consumer Staples", "Energy", "Materials"]
    stocks = []
    for sector_index, sector in enumerate(sectors):
        for i in range(5):
            identifier = f"SYN_{sector_index}_{i}"
            row = dict(security_id=identifier, issuer_id=identifier, sector=sector,
                       period_end="2025-12-31", filed="2026-02-01", price_date="2026-10-27", return_observations=756,
                       revenue=1000, operating_income=140+15*((2*i+sector_index)%5),
                       net_income=80+10*((i+sector_index)%5),
                       operating_cashflow=150+12*((3*i+2*sector_index)%5), cash_capex=30,
                       assets_start=900, assets_end=1100, liabilities=400,
                       issuer_market_cap=1200+200*((4*i+sector_index)%5), price=20)
            if request.scenario == "sector_bottleneck":
                row["sector"] = "Industrials"
            if request.scenario == "missing_data" and sector_index >= 2:
                row["issuer_market_cap"] = None
            stocks.append(SyntheticStock.model_validate(row))
    return evaluate_synthetic_strategy(SyntheticUniverse(as_of=date(2026, 10, 28), stocks=stocks,
                                                        available_cash_cents=request.available_cash_cents))
