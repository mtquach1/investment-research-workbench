"""Local educational UI for the Tax & Investment Strategy Optimizer API."""

from typing import Any

import streamlit as st

from api_client import ApiClientError, get_json, post_json
from config import get_settings
from goal_explorer_ui import render_goal_explorer
from allocation_ui import render_allocation
from research_workbench_ui import render_research_workbench
from investment_workspace_ui import render_rental_workspace, render_stock_workspace
from privacy import clear_financial_session


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _api_error(error: ApiClientError) -> None:
    st.error(str(error))
    if error.status_code == 422:
        st.caption("Review the highlighted assumptions and input ranges, then submit again.")


def _time_budget_fields(key_prefix: str) -> dict[str, float]:
    include_estimate = st.checkbox("Include a time-budget estimate", key=f"{key_prefix}_include_time_budget")
    if not include_estimate:
        return {}
    left, right = st.columns(2)
    with left:
        estimated = st.number_input(
            "Estimated hours per month for this strategy", min_value=0.0, max_value=1000.0,
            value=4.0, step=1.0, key=f"{key_prefix}_estimated_monthly_hours",
        )
    with right:
        available = st.number_input(
            "Hours per month available for investing", min_value=0.0, max_value=1000.0,
            value=8.0, step=1.0, key=f"{key_prefix}_available_monthly_hours",
        )
    return {"estimated_monthly_hours": estimated, "available_monthly_hours": available}


def _show_time_budget(result: dict[str, Any]) -> None:
    estimate = result.get("estimated_monthly_hours")
    available = result.get("available_monthly_hours")
    fits = result.get("fits_time_budget")
    if estimate is None or available is None:
        st.info("Add both time estimates to check whether this scenario fits your schedule.")
    elif fits:
        st.success(f"Estimated workload: {estimate:g} of {available:g} available hours per month.")
    else:
        st.warning(f"Estimated workload: {estimate:g} hours per month, above your {available:g}-hour budget.")
    utilization = result.get("time_budget_utilization")
    if utilization is not None:
        st.caption(f"Time-budget use: {utilization:.0%}. This is based on your own estimates.")


def _render_tax(api_url: str) -> None:
    st.subheader("2026 single-filer W-2 estimate")
    st.caption("This narrow educational estimate does not prepare a tax return or include every deduction or credit.")
    with st.form("tax_estimate"):
        income, age = st.columns(2)
        gross_income = income.number_input("Annual W-2 income", min_value=1.0, max_value=10_000_000.0,
                                           value=100_000.0, step=5_000.0)
        user_age = age.number_input("Age", min_value=18, max_value=100, value=35, step=1)
        contribution, state_rate = st.columns(2)
        retirement_contribution = contribution.number_input(
            "Traditional 401(k) contribution", min_value=0.0, max_value=100_000.0, value=0.0, step=1_000.0
        )
        state_tax_rate = state_rate.number_input(
            "Illustrative state tax rate (%)", min_value=0.0, max_value=25.0, value=8.0, step=0.5
        )
        submitted = st.form_submit_button("Estimate taxes", type="primary")

    if not submitted:
        return
    payload = {
        "gross_income": gross_income,
        "age": user_age,
        "traditional_401k_contribution": retirement_contribution,
        "state_tax_rate": state_tax_rate / 100,
    }
    try:
        result = post_json(api_url, "/calculate", payload)
    except ApiClientError as error:
        _api_error(error)
        return

    total_tax, take_home, marginal = st.columns(3)
    total_tax.metric("Estimated total tax", _money(result["total_estimated_tax"]))
    take_home.metric("Estimated take-home", _money(result["estimated_take_home"]))
    marginal.metric("Federal marginal rate", f"{result['federal_marginal_rate']:.0%}")
    st.markdown(f"**Strategy note:** {result['strategic_pivot']}")
    with st.expander("Calculation details and assumptions"):
        st.json(result)


def _render_portfolio(api_url: str) -> None:
    st.subheader("Portfolio growth scenario")
    st.caption("Choose your own return and fee assumptions. The result is a deterministic illustration, not a forecast.")
    with st.form("portfolio_projection"):
        left, right = st.columns(2)
        monthly = left.number_input("Monthly contribution", min_value=0.0, max_value=1_000_000.0,
                                    value=500.0, step=50.0)
        years = right.number_input("Years", min_value=1, max_value=60, value=10, step=1)
        return_rate, fee_rate = st.columns(2)
        annual_return = return_rate.number_input("Annual return assumption (%)", min_value=-95.0,
                                                 max_value=100.0, value=6.0, step=0.5)
        annual_fee = fee_rate.number_input("Annual fee assumption (%)", min_value=0.0,
                                           max_value=10.0, value=0.2, step=0.1)
        time_fields = _time_budget_fields("portfolio")
        submitted = st.form_submit_button("Project portfolio", type="primary")

    if not submitted:
        return
    payload = {
        "monthly_contribution": monthly,
        "years": years,
        "annual_return_assumption": annual_return / 100,
        "annual_fee_assumption": annual_fee / 100,
        **time_fields,
    }
    try:
        result = post_json(api_url, "/scenarios/portfolio", payload)
    except ApiClientError as error:
        _api_error(error)
        return

    balance, deposits, growth = st.columns(3)
    balance.metric("Projected balance", _money(result["projected_balance"]))
    deposits.metric("Contributions", _money(result["total_contributions"]))
    growth.metric("Hypothetical growth", _money(result["projected_growth"]))
    _show_time_budget(result)
    st.caption(result["disclaimer"])


def _render_goal_risk(api_url: str) -> None:
    st.subheader("Goal outcome risk analysis")
    st.caption(
        "Explore a distribution of possible ending balances under assumptions you choose. "
        "This is a mathematical simulation, not a market forecast."
    )
    with st.form("goal_risk_analysis"):
        first, second = st.columns(2)
        current_balance = first.number_input("Current invested balance", min_value=0.0, value=10_000.0, step=1_000.0)
        monthly_contribution = second.number_input("Monthly contribution", min_value=0.0, value=500.0, step=50.0)
        years, target = st.columns(2)
        duration = years.number_input("Years until goal", min_value=1, max_value=60, value=15, step=1)
        target_today = target.number_input(
            "Goal cost in today's dollars (optional)", min_value=0.0, value=None, step=10_000.0,
            placeholder="Leave blank to skip goal probability",
        )
        expected_return, volatility = st.columns(2)
        return_pct = expected_return.number_input(
            "Expected annual return before fees (%)", min_value=-95.0, max_value=100.0, value=6.0, step=0.5,
            help="This is a user assumption used to calibrate the simulation, not a forecast.",
        )
        volatility_pct = volatility.number_input(
            "Annualized volatility (%)", min_value=0.0, max_value=150.0, value=15.0, step=1.0,
            help="Volatility controls the spread of monthly returns; use a scenario assumption you can explain.",
        )
        fee, inflation = st.columns(2)
        fee_pct = fee.number_input("Annual fee assumption (%)", min_value=0.0, max_value=10.0, value=0.2, step=0.1)
        inflation_pct = inflation.number_input("Annual inflation assumption (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.25)
        paths, seed = st.columns(2)
        simulation_count = paths.number_input("Number of simulated paths", min_value=100, max_value=5000, value=2000, step=100)
        random_seed = seed.number_input("Reproducibility seed", min_value=0, max_value=2_147_483_647, value=42, step=1)
        save_run = st.checkbox("Save this run to local scenario history",
                               disabled=not get_settings().saved_runs_enabled,
                               help="Available only in explicitly configured trusted local mode.")
        save_run = save_run and get_settings().saved_runs_enabled
        run_label = st.text_input(
            "Scenario label", value="Goal scenario", max_chars=80,
            help="Used only when saving this run to local scenario history.",
        )
        submitted = st.form_submit_button("Simulate goal outcomes", type="primary")

    if not submitted:
        st.info("The simulation assumes independent, lognormally distributed monthly returns and end-of-month contributions.")
        return
    if save_run and len(run_label.strip()) < 2:
        st.warning("Enter a scenario label with at least two characters before saving.")
        return
    payload = {
        "current_balance": current_balance,
        "monthly_contribution": monthly_contribution,
        "years": duration,
        "annual_return_assumption": return_pct / 100,
        "annual_volatility_assumption": volatility_pct / 100,
        "annual_fee_assumption": fee_pct / 100,
        "annual_inflation_assumption": inflation_pct / 100,
        "target_amount_today": target_today,
        "simulation_count": simulation_count,
        "random_seed": random_seed,
    }
    try:
        if save_run:
            saved_run = post_json(api_url, "/scenario-runs/goal-risk", {"label": run_label, "analysis": payload})
            result = saved_run["result"]
        else:
            saved_run = None
            result = post_json(api_url, "/scenarios/goal-risk-analysis", payload)
    except ApiClientError as error:
        _api_error(error)
        return

    if result["probability_of_reaching_goal"] is not None:
        st.metric("Simulated paths reaching the goal", f"{result['probability_of_reaching_goal']:.1%}")
        st.caption(f"Inflation-adjusted target at year {duration}: {_money(result['target_amount_future_dollars'])}")
    else:
        st.info("Enter a goal amount to calculate the simulated share of paths reaching it.")
    low, median, high = st.columns(3)
    low.metric("10th percentile · today's dollars", _money(result["ending_balance_p10_in_today_dollars"]))
    median.metric("Median · today's dollars", _money(result["ending_balance_median_in_today_dollars"]))
    high.metric("90th percentile · today's dollars", _money(result["ending_balance_p90_in_today_dollars"]))
    st.caption(f"{result['simulation_count']:,} paths · seed {result['random_seed']} · contributions: {_money(result['total_contributions'])}")
    if saved_run is not None:
        st.success(f"Saved “{saved_run['label']}” · run {saved_run['run_id']} · model {saved_run['model_version']}")
    st.warning(result["disclaimer"])


def _render_scenario_history(api_url: str) -> None:
    if not get_settings().saved_runs_enabled:
        st.info("Database history is disabled in session-only mode. Use Goal Explorer session plans or JSON export.")
        return
    st.subheader("Saved goal scenario history")
    st.caption("Saved runs are stored in the local SQLite database configured for the API.")
    if st.button("Refresh saved runs"):
        try:
            st.session_state["saved_goal_risk_runs"] = get_json(api_url, "/scenario-runs/goal-risk?limit=50").get("runs", [])
        except ApiClientError as error:
            _api_error(error)
            return
    runs = st.session_state.get("saved_goal_risk_runs", [])
    if not runs:
        st.info("Refresh to load saved runs. To create one, open Goal risk analysis and enable local scenario history when you submit.")
        return

    labels = {
        run["run_id"]: (
            f"{run['label']} · {run['created_at']} · median "
            f"{_money(run['result']['ending_balance_median_in_today_dollars'])}"
        )
        for run in runs
    }
    ids = list(labels)
    if len(ids) == 1:
        st.info("Save another run with the same starting balance, monthly contribution, horizon, inflation, and goal to compare outcomes.")
        st.json(runs[0])
        return

    left, right = st.columns(2)
    baseline_id = left.selectbox("Baseline run", ids, format_func=lambda run_id: labels[run_id], key="history_baseline")
    comparison_options = [run_id for run_id in ids if run_id != baseline_id]
    comparison_id = right.selectbox("Compare with", comparison_options,
                                    format_func=lambda run_id: labels[run_id], key="history_comparison")
    if st.button("Compare saved runs", type="primary"):
        try:
            result = post_json(api_url, "/scenario-runs/goal-risk/compare", {
                "baseline_run_id": baseline_id,
                "comparison_run_id": comparison_id,
            })
        except ApiClientError as error:
            _api_error(error)
            return
        st.markdown(f"**{result['comparison']['label']} compared with {result['baseline']['label']}**")
        p10, median, p90 = st.columns(3)
        p10.metric("10th percentile change", _money(result["p10_balance_delta_today_dollars"]))
        median.metric("Median balance change", _money(result["median_balance_delta_today_dollars"]))
        p90.metric("90th percentile change", _money(result["p90_balance_delta_today_dollars"]))
        probability_delta = result["goal_probability_delta"]
        if probability_delta is not None:
            st.metric("Goal-reaching share change", f"{probability_delta:+.1%}")
        st.caption("Positive values mean the comparison run is higher for that modeled metric; negative values mean lower.")
        st.warning(result["disclaimer"])

    with st.expander("Saved run details"):
        st.json(runs)


def _render_goal_sensitivity(api_url: str) -> None:
    st.subheader("Goal assumption sensitivity")
    st.caption(
        "See how your selected low and high assumptions change the projected goal balance. "
        "Each factor changes on its own; the other assumptions stay at their base values."
    )
    with st.form("goal_sensitivity"):
        goal = st.text_input("Goal name", value="Down payment")
        first, second, third = st.columns(3)
        current_balance = first.number_input("Current balance", min_value=0.0, value=10_000.0, step=1_000.0)
        years = second.number_input("Years", min_value=1, max_value=60, value=15, step=1)
        target_today = third.number_input(
            "Goal in today's dollars (optional)", min_value=0.0, value=None, step=10_000.0,
            placeholder="Optional",
        )

        st.markdown("**Monthly contribution range**")
        contribution_low, contribution_base, contribution_high = st.columns(3)
        contribution_low_value = contribution_low.number_input("Low monthly contribution", min_value=0.0, value=400.0, step=50.0)
        contribution_base_value = contribution_base.number_input("Base monthly contribution", min_value=0.0, value=500.0, step=50.0)
        contribution_high_value = contribution_high.number_input("High monthly contribution", min_value=0.0, value=600.0, step=50.0)

        st.markdown("**Annual return range (%)**")
        return_low, return_base, return_high = st.columns(3)
        return_low_value = return_low.number_input("Low return", min_value=-95.0, max_value=100.0, value=4.0, step=0.5)
        return_base_value = return_base.number_input("Base return", min_value=-95.0, max_value=100.0, value=6.0, step=0.5)
        return_high_value = return_high.number_input("High return", min_value=-95.0, max_value=100.0, value=8.0, step=0.5)

        st.markdown("**Annual fee range (%)**")
        fee_low, fee_base, fee_high = st.columns(3)
        fee_low_value = fee_low.number_input("Low fee", min_value=0.0, max_value=10.0, value=0.1, step=0.1)
        fee_base_value = fee_base.number_input("Base fee", min_value=0.0, max_value=10.0, value=0.2, step=0.1)
        fee_high_value = fee_high.number_input("High fee", min_value=0.0, max_value=10.0, value=0.3, step=0.1)

        st.markdown("**Annual inflation range (%)**")
        inflation_low, inflation_base, inflation_high = st.columns(3)
        inflation_low_value = inflation_low.number_input("Low inflation", min_value=0.0, max_value=20.0, value=2.0, step=0.25)
        inflation_base_value = inflation_base.number_input("Base inflation", min_value=0.0, max_value=20.0, value=3.0, step=0.25)
        inflation_high_value = inflation_high.number_input("High inflation", min_value=0.0, max_value=20.0, value=4.0, step=0.25)
        submitted = st.form_submit_button("Rank assumption sensitivity", type="primary")

    if not submitted:
        return
    payload = {
        "goal_name": goal,
        "current_balance": current_balance,
        "monthly_contribution": contribution_base_value,
        "years": years,
        "annual_return_assumption": return_base_value / 100,
        "annual_fee_assumption": fee_base_value / 100,
        "annual_inflation_assumption": inflation_base_value / 100,
        "target_amount_today": target_today,
        "sensitivity_ranges": {
            "monthly_contribution": {"low": contribution_low_value, "high": contribution_high_value},
            "annual_return": {"low": return_low_value / 100, "high": return_high_value / 100},
            "annual_fee": {"low": fee_low_value / 100, "high": fee_high_value / 100},
            "annual_inflation": {"low": inflation_low_value / 100, "high": inflation_high_value / 100},
        },
    }
    try:
        result = post_json(api_url, "/scenarios/goal-sensitivity", payload)
    except ApiClientError as error:
        _api_error(error)
        return

    largest = result["factors"][0]
    st.metric("Largest modeled driver", largest["assumption"].replace("_", " ").title(),
              delta=_money(largest["balance_span_today_dollars"]) + " across your range")
    percent_assumptions = {"annual_return", "annual_fee", "annual_inflation"}
    display_rows = []
    for factor in result["factors"]:
        is_rate = factor["assumption"] in percent_assumptions
        format_input = (lambda value: f"{value:.2%}") if is_rate else _money
        display_rows.append({
            "Rank": factor["impact_rank"],
            "Assumption": factor["assumption"].replace("_", " ").title(),
            "Low input": format_input(factor["low_input"]),
            "Base input": format_input(factor["base_input"]),
            "High input": format_input(factor["high_input"]),
            "Balance at low input": _money(factor["balance_at_low_input_today_dollars"]),
            "Balance at high input": _money(factor["balance_at_high_input_today_dollars"]),
            "Balance span": _money(factor["balance_span_today_dollars"]),
        })
    st.dataframe(display_rows, hide_index=True, width="stretch")
    st.caption(result["method"])
    st.warning(result["disclaimer"])


def _render_rental(api_url: str) -> None:
    st.subheader("Rental and house-hack underwriting")
    st.caption("Use your own property, financing, rent, and operating-cost assumptions.")
    with st.form("rental_underwriting"):
        price, down = st.columns(2)
        purchase_price = price.number_input("Purchase price", min_value=1.0, value=500_000.0, step=10_000.0)
        down_payment = down.number_input("Down payment", min_value=0.0, value=100_000.0, step=5_000.0)
        closing, rent = st.columns(2)
        closing_costs = closing.number_input("Closing costs", min_value=0.0, value=10_000.0, step=1_000.0)
        rent_per_unit = rent.number_input("Monthly rent per rented unit", min_value=0.0, value=2_000.0, step=100.0)
        repairs, reserves = st.columns(2)
        initial_repairs = repairs.number_input("Initial repairs", min_value=0.0, value=0.0, step=1_000.0)
        initial_reserves = reserves.number_input("Initial operating reserves held as cash", min_value=0.0,
                                                value=0.0, step=1_000.0)
        st.caption("Operating reserves are held cash, separate from repair spending and the annual capital reserve. All inputs are your assumptions, not verified ZIP-level estimates.")
        rented, owner, total_units = st.columns(3)
        rented_units = rented.number_input("Rented units", min_value=0, max_value=100, value=1, step=1)
        owner_units = owner.number_input("Owner-occupied units", min_value=0, max_value=100, value=0, step=1)
        units = total_units.number_input("Total units", min_value=1, max_value=100, value=1, step=1)
        vacancy, management = st.columns(2)
        vacancy_rate = vacancy.number_input("Vacancy rate (%)", min_value=0.0, max_value=100.0, value=5.0, step=1.0)
        management_rate = management.number_input("Management rate (%)", min_value=0.0, max_value=100.0, value=8.0, step=1.0)
        prop_tax, insurance, maintenance, capex = st.columns(4)
        annual_tax = prop_tax.number_input("Annual property tax", min_value=0.0, value=6_000.0, step=500.0)
        annual_insurance = insurance.number_input("Annual insurance", min_value=0.0, value=2_000.0, step=250.0)
        annual_maintenance = maintenance.number_input("Annual maintenance", min_value=0.0, value=5_000.0, step=500.0)
        annual_capex = capex.number_input("Annual capital reserve", min_value=0.0, value=3_000.0, step=500.0)
        hoa, utilities = st.columns(2)
        annual_hoa = hoa.number_input("Annual HOA costs", min_value=0.0, value=0.0, step=100.0)
        annual_utilities = utilities.number_input("Annual owner-paid utilities", min_value=0.0, value=0.0, step=100.0)
        interest, term, owner_cost = st.columns(3)
        annual_interest = interest.number_input("Annual interest rate (%)", min_value=0.0, max_value=50.0,
                                                value=6.5, step=0.25)
        loan_term = term.number_input("Loan term (years)", min_value=1, max_value=50, value=30, step=1)
        monthly_owner_costs = owner_cost.number_input("Monthly owner costs", min_value=0.0, value=0.0, step=100.0)
        time_fields = _time_budget_fields("rental")
        submitted = st.form_submit_button("Underwrite rental", type="primary")

    if not submitted:
        return
    payload = {
        "purchase_price": purchase_price, "down_payment": down_payment, "closing_costs": closing_costs,
        "monthly_rent_per_unit": rent_per_unit, "rented_units": rented_units,
        "owner_occupied_units": owner_units, "total_units": units,
        "vacancy_rate": vacancy_rate / 100, "annual_property_tax": annual_tax,
        "annual_insurance": annual_insurance, "annual_maintenance": annual_maintenance,
        "annual_capex_reserve": annual_capex, "annual_management_rate": management_rate / 100,
        "annual_interest_rate": annual_interest / 100, "loan_term_years": loan_term,
        "monthly_owner_costs": monthly_owner_costs, **time_fields,
        "initial_repairs": initial_repairs, "initial_operating_reserves": initial_reserves,
        "annual_hoa": annual_hoa, "annual_owner_paid_utilities": annual_utilities,
    }
    try:
        result = post_json(api_url, "/real-estate/rental-underwriting", payload)
    except ApiClientError as error:
        _api_error(error)
        return

    cash_flow, coc, dscr, cap_rate = st.columns(4)
    cash_flow.metric("Annual pre-tax cash flow", _money(result["annual_pre_tax_cash_flow"]))
    coc.metric("Cash-on-cash return", "Undefined" if result['cash_on_cash_return'] is None else f"{result['cash_on_cash_return']:.1%}",
               help="Annual cash flow after capital reserve, divided by initial capital including held operating reserves.")
    dscr.metric("Debt-service coverage", "Not applicable" if result['dscr'] is None else f"{result['dscr']:.2f}x")
    cap_rate.metric("Cap rate", f"{result['cap_rate']:.1%}")
    capital, break_even, noi = st.columns(3)
    capital.metric("Initial cash required", _money(result["initial_cash_required"]))
    break_even.metric("Break-even rent per unit / month", "No rental solution" if result["break_even_monthly_rent_per_unit"] is None
                      else _money(result["break_even_monthly_rent_per_unit"]))
    noi.metric("Annual operating NOI", _money(result["annual_noi"]))
    st.caption("NOI excludes debt service and the capital reserve. Cash flow deducts both; held initial operating reserves are included in required capital, not operating expenses.")
    _show_time_budget(result)
    st.caption(result["disclaimer"])
    with st.expander("Full underwriting details"):
        st.json(result)


def _render_flip(api_url: str) -> None:
    st.subheader("Fix-and-flip scenario")
    st.caption("This is project math from user-entered assumptions; unexpected repairs and delays can change the result.")
    with st.form("flip_underwriting"):
        price, rehab = st.columns(2)
        purchase_price = price.number_input("Purchase price", min_value=1.0, value=200_000.0, step=10_000.0)
        rehab_budget = rehab.number_input("Rehab budget", min_value=0.0, value=50_000.0, step=5_000.0)
        contingency, months = st.columns(2)
        contingency_rate = contingency.number_input("Rehab contingency (%)", min_value=0.0, max_value=100.0,
                                                    value=15.0, step=1.0)
        holding_months = months.number_input("Expected holding months", min_value=0, max_value=60, value=6, step=1)
        monthly_holding, selling_rate = st.columns(2)
        monthly_cost = monthly_holding.number_input("Monthly holding costs", min_value=0.0, value=2_000.0, step=250.0)
        sale_rate = selling_rate.number_input("Selling costs (%)", min_value=0.0, max_value=25.0, value=7.0, step=0.5)
        financing, closing = st.columns(2)
        financing_costs = financing.number_input("Financing costs", min_value=0.0, value=10_000.0, step=500.0)
        closing_costs = closing.number_input("Purchase closing costs", min_value=0.0, value=4_000.0, step=500.0)
        resale_value = st.number_input("Estimated resale value", min_value=0.0, value=350_000.0, step=10_000.0)
        time_fields = _time_budget_fields("flip")
        submitted = st.form_submit_button("Analyze flip", type="primary")

    if not submitted:
        return
    payload = {
        "purchase_price": purchase_price, "rehab_budget": rehab_budget,
        "contingency_rate": contingency_rate / 100, "holding_months": holding_months,
        "monthly_holding_cost": monthly_cost, "selling_cost_rate": sale_rate / 100,
        "financing_costs": financing_costs, "estimated_resale_value": resale_value,
        "closing_costs": closing_costs, **time_fields,
    }
    try:
        result = post_json(api_url, "/real-estate/flip-underwriting", payload)
    except ApiClientError as error:
        _api_error(error)
        return

    profit, return_cost, breakeven = st.columns(3)
    profit.metric("Estimated pre-tax profit", _money(result["estimated_profit_before_tax"]))
    return_cost.metric("Return on cost", f"{result['estimated_return_on_cost']:.1%}")
    breakeven.metric("Break-even resale", _money(result["break_even_resale_price"]))
    _show_time_budget(result)
    st.caption(result["disclaimer"])
    with st.expander("Full project cost details"):
        st.json(result)


def _render_readiness(api_url: str) -> None:
    st.subheader("Financial readiness and strategy fit")
    st.caption(
        "A self-check for constraints that can affect strategy execution. It does not score your readiness, "
        "rank investments, or tell you what to buy."
    )
    strategy_labels = {
        "portfolio": "Public-market portfolio",
        "rental_property": "Rental property / house hack",
        "property_flip": "Property flip",
        "other": "Other strategy",
    }
    with st.form("financial_readiness"):
        strategy = st.selectbox("Strategy you are considering", [None, *strategy_labels],
                                format_func=lambda value: "Choose a strategy" if value is None else strategy_labels[value])
        st.markdown("**Emergency savings**")
        savings, essentials, target = st.columns(3)
        emergency_savings = savings.number_input("Dedicated emergency savings", min_value=0.0,
                                                 value=5_000.0, step=500.0)
        monthly_expenses = essentials.number_input("Essential expenses per month", min_value=1.0,
                                                   value=3_000.0, step=250.0)
        target_months = target.number_input(
            "Your own reserve target (months)", min_value=0.1, max_value=120.0, value=None, step=0.5,
            placeholder="Enter a target you chose",
            help="Choose a target that reflects your circumstances; the tool does not prescribe one.",
        )

        st.markdown("**Debt cost**")
        include_debt = st.checkbox("Compare a debt balance and APR")
        debt_balance = debt_apr = debt_comparison = None
        if include_debt:
            balance_col, apr_col, threshold_col = st.columns(3)
            debt_balance = balance_col.number_input("Balance at the APR being assessed", min_value=0.0,
                                                    value=0.0, step=500.0)
            debt_apr = apr_col.number_input("Debt APR (%)", min_value=0.0, max_value=100.0,
                                            value=None, step=0.5)
            debt_comparison = threshold_col.number_input(
                "Your comparison APR (%)", min_value=0.0, max_value=100.0, value=None, step=0.5,
                help="Optional; choose your own rate for comparison. No universal high-interest cutoff is used.",
            )

        st.markdown("**Liquidity and time**")
        liquidity_col, available_col = st.columns(2)
        liquidity_horizon = liquidity_col.number_input(
            "Months until you may need these funds (optional)", min_value=0, max_value=600,
            value=None, step=1,
        )
        time_fields = _time_budget_fields("readiness")
        if not time_fields:
            available_col.caption("Use the checkbox above to compare available hours with estimated workload.")

        st.markdown("**Risk comfort and financial ability to absorb loss**")
        tolerance_col, capacity_col = st.columns(2)
        tolerance = tolerance_col.selectbox(
            "Willingness to accept volatility or loss", [None, 1, 2, 3, 4, 5], index=0,
            format_func=lambda value: "Choose a rating" if value is None else f"{value} — " + ("low willingness" if value == 1 else "high willingness" if value == 5 else ""),
            help="1 = low willingness; 5 = high willingness.",
        )
        capacity = capacity_col.selectbox(
            "Ability to absorb a financial loss", [None, 1, 2, 3, 4, 5], index=0,
            format_func=lambda value: "Choose a rating" if value is None else f"{value} — " + ("low capacity" if value == 1 else "high capacity" if value == 5 else ""),
            help="Consider obligations, liquidity needs, and whether a loss could disrupt your goals. 1 = low; 5 = high.",
        )
        submitted = st.form_submit_button("Review my constraints", type="primary")

    if not submitted:
        st.caption("The reserve target is your choice. Debt rate and time comparisons remain unknown when inputs are omitted.")
        return
    if strategy is None or target_months is None or tolerance is None or capacity is None:
        st.warning("Choose a strategy, your reserve target, and both risk ratings before reviewing the prompts.")
        return

    payload: dict[str, Any] = {
        "strategy_category": strategy,
        "emergency_savings": emergency_savings,
        "monthly_essential_expenses": monthly_expenses,
        "emergency_fund_target_months": target_months,
        "available_monthly_hours": time_fields.get("available_monthly_hours"),
        "estimated_strategy_monthly_hours": time_fields.get("estimated_monthly_hours"),
        "risk_tolerance_rating": tolerance,
        "risk_capacity_rating": capacity,
    }
    if include_debt:
        payload["debt_balance_at_highest_apr"] = debt_balance or 0.0
        if debt_apr is not None:
            payload["highest_debt_apr"] = debt_apr / 100
        if debt_comparison is not None:
            payload["user_debt_apr_comparison"] = debt_comparison / 100
    if liquidity_horizon is not None:
        payload["liquidity_horizon_months"] = liquidity_horizon

    try:
        result = post_json(api_url, "/scenarios/readiness-check", payload)
    except ApiClientError as error:
        _api_error(error)
        return

    reserve, debt, time, risk = st.columns(4)
    reserve.metric("Emergency reserve", f"{result['emergency_savings_months']:.1f} months")
    reserve.caption(f"Self-selected target gap: {_money(result['emergency_target_gap'])}")
    debt_flag = result["debt_apr_above_user_threshold"]
    debt.metric("Debt APR comparison", "Above threshold" if debt_flag else "Not above" if debt_flag is False else "Not assessed")
    time_fit = result["fits_time_budget"]
    time.metric("Time budget", "Fits estimate" if time_fit else "Exceeds estimate" if time_fit is False else "Not assessed")
    difference = result["risk_rating_difference"]
    risk.metric("Tolerance minus capacity", f"{difference:+d} points")

    st.markdown(f"**Strategy considered:** {strategy_labels[result['strategy_category']]}")
    st.markdown("#### Review prompts")
    for prompt in result["review_prompts"]:
        st.info(prompt)
    st.caption(result["disclaimer"])
    st.markdown(
        "Learn more: [CFPB emergency savings guide](https://www.consumerfinance.gov/an-essential-guide-to-building-an-emergency-fund/) · "
        "[Investor.gov risk and time horizon guide](https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/gauge-your-risk-tolerance)"
    )


def _render_debt_payoff(api_url: str) -> None:
    st.subheader("Debt payoff methods")
    st.caption(
        "Compare highest-APR-first (avalanche) with smallest-balance-first (snowball). "
        "Both pay every entered minimum, then apply the remaining fixed budget by priority order."
    )
    st.info(
        "This illustration compounds interest monthly at APR ÷ 12 and treats each minimum payment as fixed. "
        "Actual card issuers may calculate interest daily and change minimums; check your agreements and statements."
    )
    with st.form("debt_payoff"):
        count = st.number_input("Number of debts to compare", min_value=1, max_value=10, value=2, step=1)
        debts: list[dict[str, Any]] = []
        for index in range(count):
            st.markdown(f"**Debt {index + 1}**")
            name_col, balance_col, apr_col, min_col = st.columns(4)
            name = name_col.text_input("Name", value=f"Debt {index + 1}", key=f"debt_name_{index}")
            balance = balance_col.number_input("Balance", min_value=0.01, value=1_000.0,
                                               step=100.0, key=f"debt_balance_{index}")
            apr = apr_col.number_input("APR (%)", min_value=0.0, max_value=500.0,
                                       value=18.0, step=0.5, key=f"debt_apr_{index}")
            minimum = min_col.number_input("Monthly minimum", min_value=0.01,
                                           value=50.0, step=10.0, key=f"debt_minimum_{index}")
            debts.append({
                "name": name,
                "balance": balance,
                "annual_apr": apr / 100,
                "minimum_monthly_payment": minimum,
            })
        extra, horizon = st.columns(2)
        extra_payment = extra.number_input("Extra monthly payment above minimums", min_value=0.0,
                                           value=200.0, step=25.0)
        max_months = horizon.number_input("Maximum months to simulate", min_value=1,
                                          max_value=1200, value=600, step=12)
        submitted = st.form_submit_button("Compare payoff paths", type="primary")

    if not submitted:
        return
    try:
        result = post_json(api_url, "/scenarios/debt-payoff", {
            "debts": debts,
            "extra_monthly_payment": extra_payment,
            "max_months": max_months,
        })
    except ApiClientError as error:
        _api_error(error)
        return

    st.caption(f"Constant monthly payment budget: {_money(result['monthly_payment_budget'])}")
    avalanche, snowball = st.columns(2)
    for column, label, scenario in (
        (avalanche, "Avalanche · highest APR first", result["avalanche"]),
        (snowball, "Snowball · smallest balance first", result["snowball"]),
    ):
        with column:
            st.markdown(f"### {label}")
            months_label = (
                f"{scenario['payoff_months']} months"
                if scenario["payoff_months"] is not None
                else f"Not paid off in {result['simulation_horizon_months']} months"
            )
            st.metric("Time to payoff", months_label)
            st.metric("Modeled interest", _money(scenario["total_interest"]))
            st.metric("Modeled total paid", _money(scenario["total_paid"]))
            if scenario["remaining_balance_after_horizon"] > 0:
                st.warning("Some balance remains at the end of the selected simulation period.")
            with st.expander("Payoff month by debt"):
                st.json(scenario["debt_results"])

    interest_difference = result["avalanche_interest_minus_snowball"]
    if interest_difference is not None:
        if interest_difference < 0:
            st.info(f"In this simulation, avalanche accrues {_money(abs(interest_difference))} less interest.")
        elif interest_difference > 0:
            st.info(f"In this simulation, snowball accrues {_money(interest_difference)} less interest.")
        else:
            st.info("Both methods accrue the same modeled interest under these inputs.")
    st.caption(result["disclaimer"])


def _reset_workspace() -> None:
    navigation = {key: st.session_state[key] for key in ("workspace_section", "support_tool") if key in st.session_state}
    clear_financial_session(st.session_state)
    st.session_state.update(navigation)
    st.session_state["_workspace_cleared"] = True


def main() -> None:
    st.set_page_config(page_title="Tax & Investment Strategy Optimizer", page_icon="📊", layout="wide")
    st.markdown("""<style>
        .stMainBlockContainer {padding-top: 2rem; padding-bottom: 3rem;}
        [data-testid="stMetricValue"] {font-size: 1.65rem;}
        [data-testid="stMetric"] {background: color-mix(in srgb, currentColor 4%, transparent); padding: 1rem 1.15rem; border-radius: 16px; border: 1px solid color-mix(in srgb, currentColor 8%, transparent);}
        [data-testid="stSidebar"] {border-right: 1px solid #ffffff10;}
        h1, h2, h3 {letter-spacing: -.025em;}
        [data-testid="stSidebar"] [data-testid="stRadio"] label {padding-block: .25rem;}
        @media (max-width: 640px) {
            .stMainBlockContainer {padding-inline: 1rem;}
            h1 {font-size: 1.9rem;}
        }
    </style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("Investment workspace")
        st.caption("Explore a decision. Understand the trade-offs.")
        section = st.radio("Explore", ["Real estate", "Stocks", "Goals", "Tools"], key="workspace_section")
        settings = get_settings()
        pages = [
            "Goal Explorer", "Tax estimate", "Portfolio scenario", "Goal risk analysis", "Goal sensitivity", "Scenario history", "Rental property", "Fix-and-flip", "Readiness guide",
            "Debt payoff methods", "Contribution allocator", "Research workbench",
        ]
        if not settings.saved_runs_enabled:
            pages.remove("Scenario history")
        if section == "Tools":
            st.divider()
            page = st.selectbox("Choose a calculator", pages, key="support_tool")
        else:
            page = {"Real estate":"Real estate", "Stocks":"Stocks", "Goals":"Goal Explorer"}[section]
        api_url = settings.api_base_url
        st.caption("Session-only mode" if not settings.saved_runs_enabled else "Trusted local mode")
        if settings.saved_runs_enabled:
            st.warning("Local history has no user isolation. Keep this instance private.")
        st.button("Clear session workspace", on_click=_reset_workspace,
                  help="Reset this session's inputs, comparisons, and selected uploads. Downloaded files and local database history are unaffected.")
        with st.expander("Where your information goes"):
            st.write("Real estate, Stocks, Goals, Contribution allocator and Research workbench process inputs on this Streamlit server. They do not call AI or write plans to the database. Other tools send submitted inputs to the configured API.")
            st.write("Downloads contain your assumptions and are not encrypted. Import uploads a file to this server. Clearing the workspace removes application references, not secure memory erasure.")
            st.write("No names, account numbers, or credentials are needed. Use a generic goal label.")
            st.caption("PDF gives you a readable report. Keep JSON as well if you want to reopen and edit a plan. Neither format is encrypted by this app.")
        if section == "Tools" and page not in ("Goal Explorer", "Contribution allocator", "Research workbench"):
            st.caption("Backend: " + api_url)
        if section == "Tools" and page not in ("Goal Explorer", "Contribution allocator", "Research workbench") and st.button("Check API connection"):
            try:
                health = get_json(api_url, "/health")
                st.success(f"API ready · tax year {health.get('tax_year', 'unknown')}")
            except ApiClientError as error:
                _api_error(error)

    if section not in ("Real estate", "Stocks"):
        st.title("Goal Explorer" if page == "Goal Explorer" else "Tax & Investment Strategy Optimizer")
    if st.session_state.pop("_workspace_cleared", False):
        st.success("Session workspace reset. Downloaded files and local database history were not deleted.")
    if section not in ("Real estate","Stocks"):
        st.caption("Educational planning scenarios. Results are estimates based on your inputs, not tax or investment advice.")
    if page == "Real estate":
        render_rental_workspace()
    elif page == "Stocks":
        render_stock_workspace()
    elif page == "Goal Explorer":
        render_goal_explorer()
    elif page == "Contribution allocator":
        render_allocation()
    elif page == "Research workbench":
        render_research_workbench()
    elif page == "Tax estimate":
        _render_tax(api_url)
    elif page == "Portfolio scenario":
        _render_portfolio(api_url)
    elif page == "Goal risk analysis":
        _render_goal_risk(api_url)
    elif page == "Goal sensitivity":
        _render_goal_sensitivity(api_url)
    elif page == "Scenario history":
        _render_scenario_history(api_url)
    elif page == "Rental property":
        _render_rental(api_url)
    elif page == "Fix-and-flip":
        _render_flip(api_url)
    elif page == "Readiness guide":
        _render_readiness(api_url)
    else:
        _render_debt_payoff(api_url)

    st.divider()
    st.caption("Scenarios help you explore assumptions. They do not establish future returns or guarantee that an investment meets your needs.")


if __name__ == "__main__":
    main()
