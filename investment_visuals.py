"""Chart-ready model outputs. No UI state, forecast, network or shared cache."""

from collections import Counter
from decimal import Decimal, ROUND_CEILING

from rental_feasibility import RentalFeasibilityRequest, solve_rental_feasibility
from scenario_engine import underwrite_rental


def rental_funding_landscape(request: RentalFeasibilityRequest, *, points=25):
    """Exact model checks at sampled prices; include exact limit and inspected price."""
    if not 2 <= points <= 41:
        raise ValueError("Chart sampling must be between 2 and 41 points")
    request = RentalFeasibilityRequest.model_validate(request.model_dump())
    solved = solve_rental_feasibility(request)
    low, high = int(request.minimum_purchase_price*100), int(request.maximum_purchase_price*100)
    prices = {low+(high-low)*i//(points-1) for i in range(points)}
    if solved.maximum_feasible:
        prices.add(round(solved.maximum_feasible.purchase_price*100))
    if request.candidate_purchase_price is not None:
        prices.add(int(request.candidate_purchase_price*100))
    rows = []
    for price_cents in sorted(prices):
        price = Decimal(price_cents)/100
        sample = solve_rental_feasibility(request.model_copy(update={
            "minimum_purchase_price": price, "maximum_purchase_price": price, "candidate_purchase_price": None,
        })).maximum_feasible
        rows.append({"price": float(price), "minimum_down": sample.minimum_down_payment if sample else None,
                     "maximum_down": sample.maximum_down_payment if sample else None,
                     "feasible": sample is not None})
    return solved, rows


def inspect_rental(request: RentalFeasibilityRequest, down_payment: Decimal):
    """Operating view uses the shared underwriting model and the same cost rounding."""
    request = RentalFeasibilityRequest.model_validate(request.model_dump())
    price = request.candidate_purchase_price
    if price is None or not down_payment.is_finite() or not 0 <= down_payment <= price:
        raise ValueError("A candidate price and valid down payment are required")
    closing = request.fixed_closing_costs+(request.closing_cost_rate*price).quantize(Decimal(".01"), rounding=ROUND_CEILING)
    tax = request.annual_special_assessments+(request.annual_property_tax_rate*price).quantize(Decimal(".01"), rounding=ROUND_CEILING)
    result = underwrite_rental(purchase_price=float(price), down_payment=float(down_payment), closing_costs=float(closing),
        monthly_rent_per_unit=float(request.monthly_rent), rented_units=1, total_units=1,
        vacancy_rate=float(request.vacancy_rate), annual_property_tax=float(tax),
        annual_insurance=float(request.annual_insurance), annual_maintenance=float(request.annual_maintenance),
        annual_capex_reserve=float(request.annual_capex_reserve), annual_management_rate=float(request.management_rate),
        annual_interest_rate=float(request.annual_interest_rate), loan_term_years=request.loan_term_years,
        initial_repairs=float(request.initial_repairs), initial_operating_reserves=float(request.initial_operating_reserves),
        annual_hoa=float(request.annual_hoa), annual_owner_paid_utilities=float(request.annual_owner_paid_utilities))
    return result


def rental_cashflow_curve(request, *, points=25):
    if not 2 <= points <= 41 or request.candidate_purchase_price is None:
        raise ValueError("Bounded points and a candidate price are required")
    maximum = int(request.candidate_purchase_price*100)
    return [{"down_payment": cents/100, "annual_cash_flow": inspect_rental(request, Decimal(cents)/100).annual_pre_tax_cash_flow}
            for cents in sorted({maximum*i//(points-1) for i in range(points)})]


def rental_waterfall(result):
    steps = [("Collected rent", result.monthly_effective_rent*12),
             ("Operating costs", -result.monthly_operating_expenses*12),
             ("Loan payments", -result.monthly_debt_service*12),
             ("Capital reserve", -result.annual_capex_reserve)]
    running, rows = 0.0, []
    for index, (label, amount) in enumerate(steps):
        ending = running+amount
        rows.append({"order": index, "item": label, "start": min(running, ending), "end": max(running, ending),
                     "amount": round(amount, 2), "kind": "Income" if amount >= 0 else "Cost"})
        running = ending
    rows.append({"order": 4, "item": "Cash remaining", "start": min(0, result.annual_pre_tax_cash_flow),
                 "end": max(0, result.annual_pre_tax_cash_flow), "amount": result.annual_pre_tax_cash_flow,
                 "kind": "Surplus" if result.annual_pre_tax_cash_flow >= 0 else "Deficit"})
    return rows


def stock_chart_data(result):
    points, features = [], {}
    feature_labels = {"return_on_assets":"Return on assets", "operating_margin":"Operating margin",
                      "free_cashflow_margin":"FCF margin", "earnings_yield":"Earnings yield",
                      "free_cashflow_yield":"FCF yield"}
    labels = {row["security_id"]: f"Example {i+1:02d}" for i, row in enumerate(result["findings"])}
    for row in result["findings"]:
        if row["score"] is None:
            continue
        contributions = row["score_contributions"]
        points.append({"security_id": row["security_id"], "company": labels[row["security_id"]], "sector": row["sector"],
                       "quality": sum(contributions[name] for name in ("return_on_assets", "operating_margin", "free_cashflow_margin"))/.6*100,
                       "valuation": sum(contributions[name] for name in ("earnings_yield", "free_cashflow_yield"))/.4*100,
                       "score": row["score"]*100, "basket": "In basket" if row["selected"] else "Eligible, outside basket"})
        features[row["security_id"]] = [{"feature": feature_labels[name],
            "percentile": row["feature_percentiles"][name]*100, "contribution": amount*100}
            for name, amount in contributions.items()]
    counts = Counter(row["sector"] for row in result["selected"])
    sectors = [{"sector": sector, "weight": count*10} for sector, count in sorted(counts.items())]
    return points, features, sectors, labels
