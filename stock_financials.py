"""Coherent annual SEC fact normalization. No prices, ranking or recommendations.

Income/cash-flow facts and beginning/ending balances must belong to the same
accession as the selected revenue anchor. Partial amendments fail closed rather
than silently mixing filing vintages. All source values retain their evidence.
"""

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from data_audit import ANNUAL_TAGS


MODEL_VERSION = "annual-financials-v2"


@dataclass(frozen=True)
class FactEvidence:
    value: Decimal
    tag: str
    start: str | None
    end: str
    filed: str
    accession: str
    unit: str = "USD"
    inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnnualFinancials:
    model_version: str
    cik: int
    issuer: str
    as_of: str
    period_start: str | None
    period_end: str | None
    accession: str | None
    source_sha256: str | None
    facts: dict[str, FactEvidence]
    metrics: dict[str, Decimal | None]
    metric_status: dict[str, str]
    issues: list[str]
    financials_complete: bool
    recommendation_ready: bool = False
    basis: str = "reported_fiscal_year_not_TTM"

    def to_dict(self):
        return asdict(self)


def normalize_annual_financials(company: dict[str, Any], *, as_of: date,
                               source_sha256: str | None = None,
                               period_end: date | None = None) -> AnnualFinancials:
    if (not isinstance(company.get("cik"), int) or isinstance(company.get("cik"), bool) or company["cik"] <= 0 or
            not isinstance(company.get("entityName"), str) or not company["entityName"].strip()):
        raise ValueError("Missing issuer identity")
    facts = company.get("facts", {}).get("us-gaap", {})
    evidence, issues = {}, []

    def observations(tag, annual=False):
        result = []
        for item in facts.get(tag, {}).get("units", {}).get("USD", []):
            try:
                if isinstance(item["val"], bool):
                    continue
                value = Decimal(str(item["val"]))
                end, filed = date.fromisoformat(item["end"]), date.fromisoformat(item["filed"])
                start = date.fromisoformat(item["start"]) if item.get("start") else None
                accession = item.get("accn")
                if (not value.is_finite() or end > as_of or filed > as_of or filed < end or
                        item.get("form") not in ("10-K", "10-K/A") or not accession):
                    continue
                if annual and (start is None or not 330 <= (end-start).days <= 400):
                    continue
                result.append(FactEvidence(value, tag, start.isoformat() if start else None,
                                           end.isoformat(), filed.isoformat(), accession))
            except (KeyError, TypeError, ValueError, InvalidOperation):
                continue
        return result

    revenue_tags = ANNUAL_TAGS["revenue"]
    anchors = [fact for tag in revenue_tags for fact in observations(tag, annual=True)]
    if period_end is not None:
        anchors = [fact for fact in anchors if fact.end == period_end.isoformat()]
    anchor = max(anchors, key=lambda fact: (fact.end, fact.filed, -revenue_tags.index(fact.tag), fact.accession)) if anchors else None

    def choose(name, tags, *, end, start=None, annual=False):
        for tag in tags:
            matches = [fact for fact in observations(tag, annual=annual)
                       if fact.accession == anchor.accession and fact.end == end and fact.start == start]
            if not matches:
                continue
            if len({fact.value for fact in matches}) > 1:
                issues.append(f"ambiguous_fact:{name}")
                return
            evidence[name] = max(matches, key=lambda fact: fact.filed)
            return
        issues.append(f"missing_fact:{name}")

    if anchor:
        for name, tags in ANNUAL_TAGS.items():
            choose(name, tags, end=anchor.end, start=anchor.start, annual=True)
        start_balance_date = (date.fromisoformat(anchor.start)-timedelta(days=1)).isoformat()
        choose("assets_start", ("Assets",), end=start_balance_date)
        choose("assets_end", ("Assets",), end=anchor.end)
        choose("liabilities_end", ("Liabilities",), end=anchor.end)
        if "liabilities_end" not in evidence and "ambiguous_fact:liabilities_end" not in issues:
            # Current/noncurrent are disjoint reported totals. Do not replace
            # either with debt-only components or assume an absent value is zero.
            choose("current_liabilities_end", ("LiabilitiesCurrent",), end=anchor.end)
            choose("noncurrent_liabilities_end", ("LiabilitiesNoncurrent",), end=anchor.end)
            current, noncurrent = evidence.get("current_liabilities_end"), evidence.get("noncurrent_liabilities_end")
            if current is not None and noncurrent is not None:
                if current.value >= 0 and noncurrent.value >= 0:
                    evidence["liabilities_end"] = FactEvidence(current.value+noncurrent.value,
                        "derived:current_plus_noncurrent_liabilities", None, anchor.end,
                        max(current.filed,noncurrent.filed), anchor.accession,
                        inputs=("current_liabilities_end","noncurrent_liabilities_end"))
                    issues.remove("missing_fact:liabilities_end")
                else: issues.append("invalid_negative_liability_component")
        if ("liabilities_end" not in evidence and "ambiguous_fact:liabilities_end" not in issues
            and not any(issue in issues for issue in ('ambiguous_fact:current_liabilities_end',
                'ambiguous_fact:noncurrent_liabilities_end','invalid_negative_liability_component'))):
            choose("total_equity_end", ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",), end=anchor.end)
            if "assets_end" in evidence and "total_equity_end" in evidence:
                assets, equity = evidence["assets_end"], evidence["total_equity_end"]
                liabilities = assets.value-equity.value
                if liabilities >= 0:
                    evidence["liabilities_end"] = FactEvidence(liabilities, "derived:assets_minus_total_equity",
                        None, anchor.end, max(assets.filed, equity.filed), anchor.accession,
                        inputs=("assets_end", "total_equity_end"))
                    issues.remove("missing_fact:liabilities_end")
                else:
                    issues.append("invalid_balance_identity")
        if "operating_cashflow" in evidence and "capital_expenditures" in evidence:
            cashflow, capex = evidence["operating_cashflow"], evidence["capital_expenditures"]
            if capex.value >= 0:
                evidence["free_cashflow"] = FactEvidence(cashflow.value-capex.value, "derived:ocf_minus_cash_capex",
                    anchor.start, anchor.end, max(cashflow.filed, capex.filed), anchor.accession,
                    inputs=("operating_cashflow", "capital_expenditures"))
            else:
                issues.append("invalid_negative_cash_capex")
    else:
        issues.append("no_known_annual_revenue_period")

    metrics, statuses = {}, {}

    def ratio(name, numerator, denominator):
        if numerator is None or denominator is None:
            metrics[name], statuses[name] = None, "missing_aligned_inputs"
        elif denominator <= 0:
            metrics[name], statuses[name] = None, "nonpositive_denominator"
        else:
            metrics[name], statuses[name] = numerator/denominator, "available"

    def value(name):
        return evidence[name].value if name in evidence else None

    assets_start, assets_end = value("assets_start"), value("assets_end")
    average_assets = (assets_start+assets_end)/2 if assets_start is not None and assets_end is not None else None
    if any(amount is not None and amount <= 0 for amount in (assets_start, assets_end)):
        issues.append("invalid_nonpositive_assets")
        average_assets = None
    ratio("return_on_assets", value("net_income"), average_assets)
    ratio("operating_margin", value("operating_income"), value("revenue"))
    ratio("free_cashflow_margin", value("free_cashflow"), value("revenue"))
    liabilities = value("liabilities_end")
    if liabilities is not None and liabilities < 0:
        issues.append("invalid_negative_liabilities")
        liabilities = None
    ratio("liabilities_to_assets", liabilities, assets_end)
    for name in ("earnings_yield", "free_cashflow_yield"):
        metrics[name], statuses[name] = None, "requires_verified_issuer_market_cap"
    complete = bool(anchor and all(statuses[name] == "available" for name in
                                    ("return_on_assets", "operating_margin", "free_cashflow_margin", "liabilities_to_assets")))
    if anchor and (as_of-date.fromisoformat(anchor.end)).days > 550:
        issues.append("financial_period_older_than_strategy_gate")
        complete = False
    return AnnualFinancials(MODEL_VERSION, company["cik"], company["entityName"], as_of.isoformat(),
                            anchor.start if anchor else None, anchor.end if anchor else None,
                            anchor.accession if anchor else None, source_sha256, evidence,
                            metrics, statuses, issues, complete)


def annual_financial_history(company: dict[str, Any], *, as_of: date, years: int = 5):
    """Each annual point uses one filing vintage; missing inputs remain missing.

    This is revised history available in the current snapshot, not the data an
    investor necessarily knew at each historical date.
    """
    if type(years) is not int or not 1 <= years <= 10:
        raise ValueError("Annual history is bounded to one through ten periods")
    ends = set()
    facts = company.get("facts", {}).get("us-gaap", {})
    for tag in ANNUAL_TAGS["revenue"]:
        for item in facts.get(tag, {}).get("units", {}).get("USD", []):
            try:
                start, end, filed = (date.fromisoformat(item[key]) for key in ("start", "end", "filed"))
                if (not isinstance(item["val"], bool) and Decimal(str(item["val"])).is_finite()
                        and 330 <= (end-start).days <= 400 and end <= filed <= as_of
                        and item.get("form") in ("10-K", "10-K/A") and item.get("accn")):
                    ends.add(end)
            except (KeyError, TypeError, ValueError, InvalidOperation):
                continue
    return [normalize_annual_financials(company, as_of=as_of, period_end=end)
            for end in sorted(ends, reverse=True)[:years]][::-1]
