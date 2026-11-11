"""Local strategy examples and manual property constraints; no market-data calls."""

from decimal import Decimal

from pydantic import ValidationError
import streamlit as st

from rental_feasibility import RentalFeasibilityRequest, solve_rental_feasibility
from stock_strategy import StrategyDemoRequest, strategy_demo


def render_research_workbench():
    st.subheader("Research workbench")
    st.caption("Runs shared Python calculations in this Streamlit session. No AI, market feed, database writes or trade execution.")
    stock, rental = st.tabs(["Synthetic stock strategy", "Rental purchase constraints"])
    with stock:
        st.warning("Synthetic companies only. This demonstrates strategy decisions, not real stock recommendations or evidence of beating the S&P 500.")
        with st.form("stock_strategy_example"):
            scenario = st.selectbox("Synthetic scenario", ["balanced", "sector_bottleneck", "missing_data"],
                                    format_func=lambda value: value.replace("_", " ").title())
            budget = st.number_input("Illustrative stock cash budget", min_value=0.0, max_value=1_000_000.0,
                                      value=1_000.0, step=100.0)
            submitted = st.form_submit_button("Run synthetic strategy")
        if submitted:
            st.session_state.pop("_stock_strategy_demo", None)
            budget_cents = Decimal(str(budget))*100
            if budget_cents != budget_cents.to_integral_value():
                st.error("Enter a stock cash budget with at most two decimal places.")
            else:
                st.session_state["_stock_strategy_demo"] = strategy_demo(StrategyDemoRequest(
                    scenario=scenario, available_cash_cents=int(budget_cents)))
        result = st.session_state.get("_stock_strategy_demo")
        if result:
            st.caption("Last submitted example. Run again after changing inputs.")
            if result["status"] == "synthetic_proposal":
                st.success("Ten synthetic securities selected under the sector and issuer constraints.")
                st.dataframe([{"Synthetic security": row["security_id"], "Sector": row["sector"],
                               "Strategy score": round(row["score"], 4), "Target (%)": row["target_weight"]*100,
                               "Illustrative purchase ($)": row["purchase_cents"]/100} for row in result["selected"]],
                             hide_index=True, width="stretch")
                st.metric("Unallocated cash", f"${result['cash_unallocated_cents']/100:,.2f}")
            else:
                st.info(result["explanation"])
            with st.expander("Eligibility, feature contributions and limitations"):
                st.json(result)
    with rental:
        st.write("Find the highest purchase price and feasible down payments under your entered assumptions.")
        st.caption("One fully rented property. Rent and fixed expenses stay constant across candidate prices; taxes and closing fees vary by the rates you enter. This does not estimate market rent or lender approval.")
        with st.form("rental_feasibility_editor"):
            left, right = st.columns(2)
            capital = left.number_input("Available property capital", min_value=0.0, max_value=100_000_000.0, value=100_000.0, step=5_000.0)
            rent = right.number_input("Assumed monthly property rent", min_value=0.0, max_value=100_000_000.0, value=3_000.0, step=100.0)
            cap = left.number_input("Price search ceiling", min_value=1.0, max_value=100_000_000.0, value=1_000_000.0, step=25_000.0)
            candidate = right.number_input("Candidate property price", min_value=1.0, max_value=100_000_000.0, value=300_000.0, step=10_000.0)
            down = left.number_input("Minimum down payment (%)", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
            rate = right.number_input("Feasibility loan interest (%)", min_value=0.0, max_value=50.0, value=6.5, step=.25)
            term = left.number_input("Feasibility loan term (years)", min_value=1, max_value=50, value=30)
            closing = right.number_input("Price-based closing costs (%)", min_value=0.0, max_value=100.0, value=2.0, step=.25)
            repairs = left.number_input("Feasibility initial repairs", min_value=0.0, max_value=100_000_000.0, value=5_000.0, step=1_000.0)
            reserve = right.number_input("Feasibility held operating reserves", min_value=0.0, max_value=100_000_000.0, value=10_000.0, step=1_000.0)
            tax = left.number_input("Annual property tax assumption (%)", min_value=0.0, max_value=100.0, value=1.25, step=.05)
            insurance = right.number_input("Feasibility annual insurance", min_value=0.0, max_value=100_000_000.0, value=1_500.0, step=100.0)
            maintenance = left.number_input("Feasibility annual maintenance", min_value=0.0, max_value=100_000_000.0, value=3_000.0, step=100.0)
            capex = right.number_input("Feasibility annual capital reserve", min_value=0.0, max_value=100_000_000.0, value=2_000.0, step=100.0)
            vacancy = left.number_input("Feasibility vacancy (%)", min_value=0.0, max_value=100.0, value=5.0, step=1.0)
            management = right.number_input("Feasibility management (%)", min_value=0.0, max_value=100.0, value=8.0, step=1.0)
            cashflow = left.number_input("Minimum annual property cash flow", min_value=-1_000_000.0, max_value=1_000_000.0, value=0.0, step=500.0)
            return_target = right.number_input("Minimum cash-on-cash return (%) (optional)", min_value=0.0, max_value=100.0, value=None, step=1.0)
            with st.expander("Other costs"):
                fixed_closing = st.number_input("Fixed closing costs in addition to percentage", min_value=0.0, max_value=100_000_000.0, value=0.0, step=500.0)
                assessments = st.number_input("Annual special assessments", min_value=0.0, max_value=100_000_000.0, value=0.0, step=100.0)
                hoa = st.number_input("Feasibility annual HOA", min_value=0.0, max_value=100_000_000.0, value=0.0, step=100.0)
                utilities = st.number_input("Feasibility annual owner-paid utilities", min_value=0.0, max_value=100_000_000.0, value=0.0, step=100.0)
            submitted = st.form_submit_button("Solve property constraints", type="primary")
        if submitted:
            st.session_state.pop("_rental_feasibility_result", None)
            try:
                percent = lambda value: Decimal(str(value))/100
                request = RentalFeasibilityRequest(available_capital=str(capital), monthly_rent=str(rent),
                    maximum_purchase_price=str(cap), candidate_purchase_price=str(candidate),
                    minimum_down_payment_rate=percent(down), annual_interest_rate=percent(rate), loan_term_years=term,
                    fixed_closing_costs=str(fixed_closing), closing_cost_rate=percent(closing), initial_repairs=str(repairs),
                    initial_operating_reserves=str(reserve), annual_property_tax_rate=percent(tax), annual_special_assessments=str(assessments),
                    annual_insurance=str(insurance), annual_maintenance=str(maintenance), annual_hoa=str(hoa),
                    annual_owner_paid_utilities=str(utilities), annual_capex_reserve=str(capex), vacancy_rate=percent(vacancy),
                    management_rate=percent(management), minimum_annual_cash_flow=str(cashflow),
                    minimum_cash_on_cash_return=None if return_target is None else percent(return_target))
                st.session_state["_rental_feasibility_result"] = solve_rental_feasibility(request)
            except (ValidationError, ArithmeticError, ValueError):
                st.error("Review the price bounds, candidate price, amounts and allowed rates. No new result was kept.")
        result = st.session_state.get("_rental_feasibility_result")
        if result:
            st.caption("Last submitted scenario. Solve again after editing assumptions.")
            if result.maximum_feasible:
                maximum = result.maximum_feasible
                st.metric("Maximum feasible price within search", f"${maximum.purchase_price:,.2f}")
                st.write(f"Down payment at that price: ${maximum.minimum_down_payment:,.2f} to ${maximum.maximum_down_payment:,.2f}.".replace("$", "\\$"))
                if result.search_bound_reached:
                    st.info("The search ceiling is feasible. This is a bound-limited result; higher prices have not been evaluated.")
            else:
                st.warning(result.explanation)
            if result.candidate:
                st.success("The candidate price has a feasible down-payment range under these assumptions.")
                st.dataframe([{"Candidate price ($)": result.candidate.purchase_price,
                               "Minimum down ($)": result.candidate.minimum_down_payment,
                               "Maximum down ($)": result.candidate.maximum_down_payment,
                               "Initial cash at minimum down ($)": result.candidate.initial_cash_required_at_minimum_down,
                               "Annual cash flow at minimum down ($)": result.candidate.annual_cash_flow_at_minimum_down}],
                             hide_index=True, width="stretch")
            elif result.candidate_status == "infeasible":
                st.warning("The candidate price does not meet the entered constraints.")
            with st.expander("Calculation details and model limitations"):
                st.json(result.model_dump(mode="json"))
