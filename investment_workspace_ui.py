"""Decision-first, session-scoped visual workspaces over the shared engines."""

from decimal import Decimal

import altair as alt
import pandas as pd
import streamlit as st

from investment_visuals import (inspect_rental, rental_cashflow_curve,
    rental_funding_landscape, rental_waterfall, stock_chart_data)
from rental_feasibility import RentalFeasibilityRequest
from rental_projection_ui import render_rental_hold
from stock_strategy import StrategyDemoRequest, strategy_demo
from data_readiness_ui import render_data_readiness
from company_research_ui import render_company_research
from market_history_ui import render_history_lab
from portfolio_overview_ui import render_portfolio_overview
from stock_screen_ui import render_stock_screen
from stock_workflows_ui import render_stock_proposal,render_stock_replay


TEAL = "#7cebd3"
GOLD = "#b8b1f1"
RED = "#f398a4"


def _chart(chart, **kwargs):
    return st.altair_chart(chart.configure_view(strokeWidth=0).configure_axis(
        gridColor="#edf1f3", labelColor="#526670", titleColor="#526670"),
        width="stretch", **kwargs)


def _input(label, name, default, *, slider=False, **kwargs):
    """Widget cleanup on navigation must not discard the user's assumptions."""
    saved = st.session_state.setdefault("_rental_visual_inputs", {})
    key = "rv_"+name
    if key not in st.session_state:
        st.session_state[key] = saved.get(name, default)
    if "max_value" in kwargs:
        st.session_state[key] = min(st.session_state[key], kwargs["max_value"])
    value = (st.slider if slider else st.number_input)(label, key=key, **kwargs)
    saved[name] = value
    return value


def render_rental_workspace():
    st.caption("REAL ESTATE / LONG-TERM RENTALS")
    st.title("Find the room in a rental deal")
    st.write("Explore how price, financing and rent change the money left over. Move a slider to see the trade-offs immediately.")
    st.info("Manual scenario · These are illustrative inputs, not Orange County listings, rent estimates or lender quotes. ZIP-code discovery is still in development.")
    render_data_readiness("rentals")
    purchase_tab, hold_tab = st.tabs(["Purchase & cash flow","Holding period & stress"])
    with purchase_tab:
        controls, summary = st.columns([1, 2], gap="large")
        with controls:
            st.subheader("Your starting point")
            capital = _input("Available capital ($)", "capital", 100000, slider=True, min_value=10000, max_value=1000000, step=5000)
            rent = _input("Monthly rent ($)", "rent", 3000, slider=True, min_value=0, max_value=10000, step=100)
            apr = _input("Mortgage rate (%)", "apr", 6.5, slider=True, min_value=0.0, max_value=12.0, step=.25)
            with st.expander("Costs, reserves and requirements"):
                st.caption("Annual amounts unless labeled otherwise. Held reserves count toward required capital.")
                cap = _input("Search ceiling ($)", "cap", 600000, min_value=50000, max_value=5000000, step=50000)
                term = _input("Loan term (years)", "term", 30, min_value=1, max_value=50, step=1)
                down_rate = _input("Minimum down payment (%)", "down_rate", 20.0, min_value=0.0, max_value=100.0, step=5.0)
                tax = _input("Property tax rate (%)", "tax", 1.25, min_value=0.0, max_value=10.0, step=.05)
                closing = _input("Closing costs (% of price)", "closing", 2.0, min_value=0.0, max_value=20.0, step=.25)
                fixed_closing = _input("Additional closing costs ($)", "fixed_closing", 0, min_value=0, max_value=100000, step=500)
                repairs = _input("Initial repairs ($)", "repairs", 5000, min_value=0, max_value=500000, step=1000)
                reserves = _input("Operating reserves held ($)", "reserves", 10000, min_value=0, max_value=500000, step=1000)
                insurance = _input("Insurance ($/year)", "insurance", 1800, min_value=0, max_value=100000, step=100)
                maintenance = _input("Maintenance ($/year)", "maintenance", 2400, min_value=0, max_value=100000, step=100)
                capex = _input("Capital replacement reserve ($/year)", "capex", 1800, min_value=0, max_value=100000, step=100)
                hoa = _input("HOA ($/year)", "hoa", 0, min_value=0, max_value=100000, step=100)
                utilities = _input("Owner-paid utilities ($/year)", "utilities", 0, min_value=0, max_value=100000, step=100)
                assessments = _input("Special assessments ($/year)", "assessments", 0, min_value=0, max_value=100000, step=100)
                vacancy = _input("Vacancy (%)", "vacancy", 5.0, min_value=0.0, max_value=100.0, step=1.0)
                management = _input("Management (% of collected rent)", "management", 8.0, min_value=0.0, max_value=100.0, step=1.0)
                target = _input("Minimum annual cash flow ($)", "target", 0, min_value=-1000000, max_value=1000000, step=500)
                coc = _input("Minimum cash-on-cash return (%) · 0 disables", "coc", 0.0, min_value=0.0, max_value=100.0, step=.5)
        with summary:
            st.subheader("Inspect a purchase")
            price = _input("Purchase price ($)", "price", 300000, slider=True, min_value=50000, max_value=cap, step=1000)
            down = _input("Down payment ($)", "down", 60000, slider=True, min_value=0, max_value=price, step=1000)
            percent = lambda value: Decimal(str(value))/100
            request = RentalFeasibilityRequest(available_capital=capital, monthly_rent=rent,
                minimum_purchase_price=50000, maximum_purchase_price=cap, candidate_purchase_price=price,
                minimum_down_payment_rate=percent(down_rate), annual_interest_rate=percent(apr), loan_term_years=term,
                fixed_closing_costs=fixed_closing, closing_cost_rate=percent(closing), initial_repairs=repairs,
                initial_operating_reserves=reserves, annual_property_tax_rate=percent(tax), annual_special_assessments=assessments,
                annual_insurance=insurance, annual_maintenance=maintenance, annual_hoa=hoa, annual_owner_paid_utilities=utilities,
                annual_capex_reserve=capex, vacancy_rate=percent(vacancy), management_rate=percent(management),
                minimum_annual_cash_flow=target, minimum_cash_on_cash_return=percent(coc) if coc else None)
            signature = request.model_dump_json()
            cached = st.session_state.get("_rental_landscape")
            if cached is None or cached[0] != signature:
                solved, landscape = rental_funding_landscape(request)
                curve = rental_cashflow_curve(request)
                st.session_state["_rental_landscape"] = (signature, solved, landscape, curve)
            else:
                _, solved, landscape, curve = cached
            inspected = inspect_rental(request, Decimal(down))
            st.session_state["_rental_visual_result"] = inspected
            st.session_state["_rental_visual_limit"] = solved
            candidate = solved.candidate
            matches = candidate is not None and candidate.minimum_down_payment <= down <= candidate.maximum_down_payment
            first, second, third = st.columns(3)
            first.metric("Annual cash flow", f"${inspected.annual_pre_tax_cash_flow:,.0f}")
            second.metric("Capital required", f"${inspected.initial_cash_required:,.0f}",
                          f"${capital-inspected.initial_cash_required:,.0f} remaining", delta_color="normal")
            third.metric("Maximum feasible price", f"${solved.maximum_feasible.purchase_price/1000:,.1f}k" if solved.maximum_feasible else "No match")
            if solved.maximum_feasible:
                st.caption(f"Exact modeled price limit: ${solved.maximum_feasible.purchase_price:,.2f}")
            if matches:
                st.success("This price and down payment meet your entered requirements.")
            elif candidate:
                st.warning(f"At this price, down payments from ${candidate.minimum_down_payment:,.2f} to ${candidate.maximum_down_payment:,.2f} meet your requirements. Your inspected down payment is outside that range.")
            else:
                st.warning("No down payment at this price satisfies all of your entered requirements.")
            if solved.search_bound_reached:
                st.caption("The search ceiling is feasible; increase it to explore the limit.")
            if inspected.break_even_monthly_rent_per_unit is not None:
                st.caption(f"Rent needed to cover modeled costs at this financing: ${inspected.break_even_monthly_rent_per_unit:,.0f}/month. This covers expenses and reserves; it is not a market-rent estimate.")
            st.markdown("**What does a larger down payment change?**")
            base = alt.Chart(pd.DataFrame(curve)).encode(x=alt.X("down_payment:Q", title="Down payment ($)", axis=alt.Axis(format="~s")),
                                                         y=alt.Y("annual_cash_flow:Q", title="Annual cash flow ($)"))
            layers = [base.mark_line(color=TEAL, strokeWidth=3).encode(tooltip=[alt.Tooltip("down_payment:Q",format="$,.0f"),alt.Tooltip("annual_cash_flow:Q",format="$,.2f")])]
            if candidate:
                layers.insert(0, alt.Chart(pd.DataFrame([{"low":candidate.minimum_down_payment,"high":candidate.maximum_down_payment}])).mark_rect(color=TEAL,opacity=.10).encode(x="low:Q",x2="high:Q"))
            layers += [alt.Chart(pd.DataFrame([{"target":target}])).mark_rule(strokeDash=[5,4],color=GOLD).encode(y="target:Q"),
                       alt.Chart(pd.DataFrame([{"down_payment":down,"annual_cash_flow":inspected.annual_pre_tax_cash_flow}])).mark_point(size=150,filled=True,color=TEAL if matches else RED).encode(x="down_payment:Q",y="annual_cash_flow:Q")]
            _chart(alt.layer(*layers).properties(height=250), key="rv_cashflow", alt="Annual cash flow rises as more capital is used for the down payment. Shaded range meets the entered requirements.")
            st.caption("Dot = inspected purchase · Shading = qualifying down-payment range · Dashed line = cash-flow target. More down reduces debt but ties up capital.")
            pin, clear = st.columns(2)
            if pin.button("Pin this scenario for comparison", width="stretch"):
                st.session_state["_rental_visual_baseline"] = {"request":signature,"down":down,
                    "cashflow":inspected.annual_pre_tax_cash_flow,"capital":inspected.initial_cash_required,
                    "limit":solved.maximum_feasible.purchase_price if solved.maximum_feasible else None}
            if clear.button("Remove comparison", width="stretch"):
                st.session_state.pop("_rental_visual_baseline", None)
            baseline = st.session_state.get("_rental_visual_baseline")
            if baseline:
                st.caption("Compared with your pinned scenario · held only in this session")
                a,b = st.columns(2)
                a.metric("Cash-flow change / year", f"${inspected.annual_pre_tax_cash_flow-baseline['cashflow']:+,.0f}")
                b.metric("Capital change", f"${inspected.initial_cash_required-baseline['capital']:+,.0f}",help="Positive means more capital committed, including held reserves.")
                with st.expander("Pinned assumptions"):
                    st.json({"down_payment":baseline["down"],"inputs":RentalFeasibilityRequest.model_validate_json(baseline["request"]).model_dump(mode="json")})
        st.divider()
        left, right = st.columns(2, gap="large")
        with left:
            st.subheader("Where can your capital take you?")
            st.caption("Shading shows qualifying down payments at sampled prices. Rent and fixed expenses stay constant as price changes.")
            frame = pd.DataFrame(landscape)
            band = alt.Chart(frame).mark_area(color=TEAL,opacity=.2).encode(
                x=alt.X("price:Q",title="Purchase price ($)",axis=alt.Axis(format="~s")),
                y=alt.Y("minimum_down:Q",title="Down payment ($)"), y2="maximum_down:Q",
                tooltip=[alt.Tooltip("price:Q",format="$,.2f"),alt.Tooltip("minimum_down:Q",format="$,.2f"),alt.Tooltip("maximum_down:Q",format="$,.2f")])
            dot = alt.Chart(pd.DataFrame([{"price":price,"down":down}])).mark_point(size=110,filled=True,color=TEAL if matches else RED).encode(x="price:Q",y="down:Q")
            _chart((band+dot).properties(height=290), key="rv_landscape", alt="Feasible down-payment band by purchase price; inspected purchase is a dot.")
            st.caption("Interpolated visual guide; the selected purchase and maximum price are checked by the cent-level solver. An empty band means no sampled price qualifies.")
        with right:
            st.subheader("Where does the rent go?")
            waterfall = pd.DataFrame(rental_waterfall(inspected))
            chart = alt.Chart(waterfall).mark_bar(cornerRadius=3).encode(
                x=alt.X("item:N",sort=alt.SortField("order"),title=None,axis=alt.Axis(labelAngle=-35,labelOverlap=False,labelFontSize=10,labelLimit=120)),
                y=alt.Y("start:Q",title="Annual dollars ($)"),y2="end:Q",
                color=alt.Color("kind:N",scale=alt.Scale(domain=["Income","Cost","Surplus","Deficit"],range=[TEAL,"#a7bac1",TEAL,RED]),legend=None),
                tooltip=["item",alt.Tooltip("amount:Q",format="$,.2f")])
            _chart(chart.properties(height=290),key="rv_waterfall",alt="Annual collected rent less operating costs, loan payments and capital replacement reserves leaves cash flow.")
            st.caption("Collected rent is after vacancy. Operating costs include management, property tax and the entered expenses. Displayed monthly amounts may introduce a few cents of rounding.")
        with st.expander("Numbers, assumptions and model boundaries"):
            st.write("Pre-income-tax cash flow; no appreciation, sale proceeds, depreciation, PMI or lender qualification. Return on cash includes held operating reserves. Cash flow excludes principal accumulation as spendable income.")
            st.dataframe(pd.DataFrame(curve),hide_index=True,width="stretch")
            st.json({"inputs":request.model_dump(mode="json"),"feasibility":solved.model_dump(mode="json"),"inspected":vars(inspected)})

    with hold_tab:
        render_rental_hold(request, Decimal(down))


def render_stock_workspace():
    st.caption("STOCKS / RESEARCH WORKSPACE")
    current=st.session_state.get("stock_research_view","Portfolio")
    st.title({"Portfolio":"Portfolio overview","Research screen":"Research screen","Company research":"Company research","Strategy lab":"Strategy lab","Build portfolio":"Build portfolio","Historical replay":"Historical replay"}.get(current,"Stock workspace"))
    view = st.radio("Stock workspace", ["Portfolio","Build portfolio","Research screen","Company research","Historical replay","Strategy lab"], horizontal=True, key="stock_research_view",label_visibility="collapsed")
    if view=="Portfolio":
        render_portfolio_overview()
        return
    if view=="Build portfolio":
        render_stock_proposal()
        return
    if view=="Historical replay":
        render_stock_replay()
        return
    if view=="Research screen":
        render_stock_screen()
        return
    render_data_readiness("stocks")
    if view == "Company research":
        render_company_research()
    else:
        _render_strategy_lab()


def _render_strategy_lab():
    model=st.radio("Explore the model",["Stock selection","Historical comparison"],horizontal=True,key="stock_lab_mode")
    if model=="Historical comparison":
        render_history_lab()
        return
    st.caption("STOCKS / STRATEGY LAB")
    st.subheader("See why a company makes the basket")
    st.write("Explore the link between business quality, valuation and portfolio constraints. Click a company in the map to inspect its score.")
    st.info("Synthetic learning lab · All companies and financial values below are fabricated examples. No live stock recommendations or measured investment returns.")
    saved = st.session_state.setdefault("_stock_visual_inputs", {})
    left, right = st.columns([2,1])
    with left:
        scenarios = {"Balanced universe":"balanced","Sector bottleneck":"sector_bottleneck","Missing financial data":"missing_data"}
        if "sv_scenario" not in st.session_state:
            st.session_state["sv_scenario"] = saved.get("scenario","Balanced universe")
        scenario_label = st.radio("Explore a constraint",list(scenarios),horizontal=True,key="sv_scenario")
        saved["scenario"] = scenario_label
    with right:
        if "sv_budget" not in st.session_state:
            st.session_state["sv_budget"] = saved.get("budget",10000)
        budget = st.slider("Illustrative cash budget ($)",100,100000,step=100,key="sv_budget")
        saved["budget"] = budget
    result = strategy_demo(StrategyDemoRequest(scenario=scenarios[scenario_label],available_cash_cents=budget*100))
    st.session_state["_stock_visual_result"] = result
    points, features, sectors, labels = stock_chart_data(result)
    a,b,c = st.columns(3)
    a.metric("Eligible companies",result["eligible_issuer_count"])
    b.metric("Companies in basket",len(result["selected"]))
    c.metric("Unallocated cash",f"${result['cash_unallocated_cents']/100:,.2f}")
    if not result["selected"]:
        st.warning("No basket satisfies the strategy. The model keeps cash unallocated rather than silently relaxing its constraints.")
    st.caption("Quality 60% + valuation 40% · 10 equal-weight positions · Maximum 3 per sector · Financials and real estate excluded by this strategy")
    if not points:
        st.warning("No companies have enough eligible peer data for the map.")
        return
    plot, inspector = st.columns([1.7,1],gap="large")
    with plot:
        st.subheader("Quality × valuation")
        pick = alt.selection_point(name="company",fields=["security_id"],on="click",nearest=True,toggle=False,empty=False)
        chart = alt.Chart(pd.DataFrame(points)).mark_circle(size=160,stroke="white",strokeWidth=1).encode(
            x=alt.X("quality:Q",title="Quality · sector-relative score",scale=alt.Scale(domain=[-3,103])),
            y=alt.Y("valuation:Q",title="Valuation · sector-relative score",scale=alt.Scale(domain=[-3,103])),
            color=alt.Color("basket:N",scale=alt.Scale(domain=["In basket","Eligible, outside basket"],range=[TEAL,"#b8c5cb"]),legend=alt.Legend(title=None,orient="bottom")),
            opacity=alt.condition(pick,alt.value(1),alt.value(.65)),
            tooltip=["company","security_id","sector",alt.Tooltip("score:Q",format=".1f")]).add_params(pick)
        event = _chart(chart.properties(height=340),key="sv_map_"+scenarios[scenario_label],on_select="rerun",selection_mode=["company"],alt="Synthetic companies by sector-relative quality and valuation. Click a point to inspect five weighted score contributions.")
        selected = event.selection.get("company",[]) if event else []
        if selected and selected != st.session_state.get("_sv_last_pick"):
            st.session_state["_sv_inspect"] = selected[0]["security_id"]
            st.session_state["_sv_last_pick"] = selected
        st.caption("Higher means a stronger relative score among eligible peers in the same sector; it does not predict future returns. Some points overlap; use the company selector to inspect each one.")
    with inspector:
        st.subheader("Inside the score")
        ids = [row["security_id"] for row in points]
        initial = result["selected"][0]["security_id"] if result["selected"] else ids[0]
        chosen = st.session_state.get("_sv_inspect",initial)
        if chosen not in ids:
            chosen = ids[0]
        # A chart click and a keyboard-accessible selector share one inspector.
        if st.session_state.get("sv_inspector") != chosen:
            st.session_state["sv_inspector"] = chosen
        def remember_company():
            st.session_state["_sv_inspect"] = st.session_state["sv_inspector"]
        inspected_id = st.selectbox("Company",ids,format_func=lambda identifier:labels[identifier]+" · "+identifier,key="sv_inspector",on_change=remember_company)
        row = next(item for item in points if item["security_id"]==inspected_id)
        st.caption(row["sector"]+" · "+row["basket"])
        st.metric("Combined score / 100",f"{row['score']:.1f}")
        contribution = alt.Chart(pd.DataFrame(features[inspected_id])).mark_bar(color=TEAL,cornerRadiusEnd=3).encode(
            x=alt.X("contribution:Q",title="Points contributed to total",scale=alt.Scale(domain=[0,20])),
            y=alt.Y("feature:N",title=None,sort=None),
            tooltip=["feature",alt.Tooltip("percentile:Q",format=".1f"),alt.Tooltip("contribution:Q",format=".1f")])
        _chart(contribution.properties(height=210),key="sv_features",alt="Five feature contributions, each worth up to twenty points of the combined score.")
        st.caption("Each feature contributes up to 20 points. A good score can still miss the basket because of sector limits or a higher-ranked peer.")
    if sectors:
        st.subheader("A strong company still needs a balanced basket")
        exposure = alt.Chart(pd.DataFrame(sectors)).mark_bar(color=TEAL,cornerRadiusEnd=3).encode(
            x=alt.X("weight:Q",title="Basket weight (%)",scale=alt.Scale(domain=[0,35])),y=alt.Y("sector:N",title=None),tooltip=["sector","weight"])
        ceiling = alt.Chart(pd.DataFrame([{"cap":30}])).mark_rule(color=GOLD,strokeDash=[5,4]).encode(x="cap:Q")
        _chart((exposure+ceiling).properties(height=190),key="sv_sectors",alt="Sector weights in the synthetic basket, with a thirty percent sector cap.")
        st.caption("Dashed line = 30% sector cap. Diversification here is a constraint, not a measured risk estimate.")
    with st.expander("Basket, excluded companies and calculation details"):
        st.dataframe(pd.DataFrame(result["selected"]),hide_index=True,width="stretch")
        st.dataframe(pd.DataFrame([{"company":labels[row["security_id"]],"id":row["security_id"],"reasons":", ".join(row["reasons"])} for row in result["findings"] if row["reasons"]]),hide_index=True,width="stretch")
        st.json(result)
