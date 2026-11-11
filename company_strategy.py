"""Explain the evidence available for a strategy, without inventing a live score."""

from datetime import date
from decimal import Decimal
from typing import Literal

from data_pipeline import Contract
from stock_strategy import SPEC, SPEC_HASH
from strategy_financial_rules import financial_checks


class EvidenceCheck(Contract):
    key: str
    status: Literal["pass","fail","unavailable"]
    explanation: str


class FeatureEvidence(Contract):
    key: str
    weight: Decimal
    formula: str
    value: Decimal | None
    status: Literal["available","unavailable"]


class CompanyStrategyEvidence(Contract):
    strategy_id: str
    strategy_sha256: str
    period_end: str | None
    evaluated_as_of: str
    financial_checks: list[EvidenceCheck]
    features: list[FeatureEvidence]
    unresolved_requirements: list[str]
    score: None = None
    recommendation_enabled: Literal[False] = False
    notice: str


def explain_company_strategy(year, *, as_of):
    """`year` is a validated ResearchYear; all calculations use its one vintage."""
    value=lambda key: year.facts[key].value if key in year.facts else None
    values={name:value(name) for name in SPEC["required_positive_fields"] if name!="issuer_market_cap"}
    values.update(cash_capex=value("capital_expenditures"),liabilities=value("liabilities_end"))
    raw=financial_checks(values,SPEC,include_market_cap=False)
    labels={"cash_capex":"Cash capital expenditure must be nonnegative.",
            "leverage_limit":f"Liabilities / assets must not exceed {SPEC['maximum_liabilities_to_assets']:.0%}.",
            "liabilities":"Reported liabilities must be nonnegative."}
    checks=[EvidenceCheck(key=row["key"],status=row["status"],explanation=labels.get(row["key"],
            row["key"].replace("_"," ").capitalize()+" must be positive.")) for row in raw]
    age=(as_of-date.fromisoformat(year.period_end)).days if year.period_end else None
    checks.append(EvidenceCheck(key="financial_period_age",status="unavailable" if age is None else
        "pass" if 0<=age<=SPEC["maximum_financial_period_age_days"] else "fail",
        explanation=f"Fiscal year end must be within {SPEC['maximum_financial_period_age_days']} days of the assessment date."))
    dates=[date.fromisoformat(fact.filed) for fact in year.facts.values()]
    aligned=bool(year.accession and year.facts and all(fact.accession==year.accession for fact in year.facts.values()))
    known=bool(dates and year.period_end and all(date.fromisoformat(year.period_end)<=d<=as_of for d in dates))
    checks.append(EvidenceCheck(key="filing_evidence",status="pass" if aligned and known else "fail",
                               explanation="Inputs must share one accession and have filing dates known by the assessment date."))
    def ratio(numerator,denominator):
        return numerator/denominator if numerator is not None and denominator is not None and denominator>0 else None
    start,end=value("assets_start"),value("assets_end")
    average=(start+end)/2 if start is not None and end is not None and start>0 and end>0 else None
    ocf,capex=value("operating_cashflow"),value("capital_expenditures")
    fcf=ocf-capex if ocf is not None and capex is not None and capex>=0 else None
    metrics={"return_on_assets":ratio(value("net_income"),average),
             "operating_margin":ratio(value("operating_income"),value("revenue")),
             "free_cashflow_margin":ratio(fcf,value("revenue"))}
    features=[FeatureEvidence(key=row["name"],weight=Decimal(str(row["weight"])),formula=row["formula"],
        value=metrics.get(row["name"]),status="available" if metrics.get(row["name"]) is not None
        else "unavailable") for row in SPEC["features"]]
    return CompanyStrategyEvidence(strategy_id=SPEC["strategy_id"],strategy_sha256=SPEC_HASH,
        period_end=year.period_end,evaluated_as_of=as_of.isoformat(),financial_checks=checks,features=features,
        unresolved_requirements=["Verified dated S&P 500 membership and canonical tradable security",
            "Supported sector classification; Financials and Real Estate are excluded",
            "Verified issuer market capitalization for valuation yields",
            f"Price no more than {SPEC['maximum_price_age_calendar_days']} calendar days old",
            f"At least {SPEC['risk_history']['minimum_daily_return_observations']} daily total-return observations",
            f"At least {SPEC['minimum_eligible_sector_peers']} eligible issuers per sector for percentile ranking",
            "Holdings, concentration and purchase constraints before portfolio sizing",
            "Matched benchmark and evaluation evidence before performance claims"],
        notice="Available ratios describe reported financials, not attractiveness at today's price. Missing features are never reweighted; no score or purchase recommendation is produced.")
