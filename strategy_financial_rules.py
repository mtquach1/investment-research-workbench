"""Shared financial eligibility checks for research and the synthetic strategy.

Missing evidence differs from an observed rule failure. Exact cross products
avoid rounding a liability ratio across the configured boundary.
"""

from fractions import Fraction


def financial_checks(values, spec, *, include_market_cap=True):
    checks=[]
    positive=[name for name in spec["required_positive_fields"]
              if name!="free_cashflow" and (include_market_cap or name!="issuer_market_cap")]
    for name in positive:
        value=values.get(name)
        checks.append(dict(key=name,status="unavailable" if value is None else "pass" if value>0 else "fail",
                           reason=f"missing_or_nonpositive:{name}"))
    capex=values.get("cash_capex")
    checks.append(dict(key="cash_capex",status="unavailable" if capex is None else "pass" if capex>=0 else "fail",
                       reason="missing_or_negative:cash_capex"))
    ocf=values.get("operating_cashflow")
    fcf=ocf-capex if ocf is not None and capex is not None and capex>=0 else None
    checks.append(dict(key="free_cashflow",status="unavailable" if fcf is None else "pass" if fcf>0 else "fail",
                       reason="missing_or_nonpositive:free_cashflow"))
    liabilities,assets=values.get("liabilities"),values.get("assets_end")
    checks.append(dict(key="liabilities",status="unavailable" if liabilities is None else "pass" if liabilities>=0 else "fail",
                       reason="missing_or_negative:liabilities"))
    status="unavailable"
    if liabilities is not None and liabilities>=0 and assets is not None and assets>0:
        status="pass" if Fraction(liabilities)<=Fraction(str(spec["maximum_liabilities_to_assets"]))*Fraction(assets) else "fail"
    checks.append(dict(key="leverage_limit",status=status,reason="liabilities_above_strategy_limit"))
    return checks
