"""Editable allocation dashboard; private assumptions remain in this session."""

from decimal import Decimal, InvalidOperation
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from portfolio_overview import PortfolioComposition, PortfolioHolding, composition_rows, example_composition
from stock_strategy import StrategyDemoRequest, strategy_demo


COLORS=["#7cebd3","#b8b1f1","#6fb4ed","#f2ba80","#ed91b3","#8cd49c","#8eacc4","#d0c780","#a78fc4","#77c8cf"]


def render_portfolio_overview():
    st.session_state.pop("_portfolio_composition_result",None)
    if "portfolio_source" not in st.session_state:
        st.session_state["portfolio_source"]=st.session_state.get("_portfolio_saved_source","Your allocation")
    if "portfolio_composition_budget" not in st.session_state:
        st.session_state["portfolio_composition_budget"]=st.session_state.get("_portfolio_saved_budget",10000)
    editor_control=st.container()
    with editor_control:
        with st.expander("Edit holdings, percentages and allocation source"):
            choice=st.radio("Allocation source",["Your allocation","Synthetic strategy example"],horizontal=True,key="portfolio_source")
            st.session_state["_portfolio_saved_source"]=choice
            if choice=="Your allocation":
                if "_portfolio_editor_rows" not in st.session_state:
                    st.session_state["_portfolio_editor_rows"]=[{"Symbol":row.symbol,"Holding":row.name,"Type":row.kind,
                        "Weight (%)":row.weight_bps/100} for row in example_composition().holdings]
                if "portfolio_holdings_editor" not in st.session_state:
                    st.session_state["_portfolio_editor_base"]=[dict(row) for row in st.session_state["_portfolio_editor_rows"]]
                edited=st.data_editor(pd.DataFrame(st.session_state["_portfolio_editor_base"]),num_rows="dynamic",hide_index=True,width="stretch",
                    key="portfolio_holdings_editor",column_config={"Symbol":st.column_config.TextColumn(required=True,max_chars=30),
                    "Holding":st.column_config.TextColumn(required=True,max_chars=80),
                    "Type":st.column_config.SelectboxColumn(options=["Stock","ETF","Index placeholder"],required=True),
                    "Weight (%)":st.column_config.NumberColumn(min_value=0,max_value=100,step=.25,format="%.2f",required=True)})
                st.session_state["_portfolio_editor_rows"]=edited.to_dict("records")
    a,b,c=st.columns(3)
    with a:
        with st.container(border=True):
            budget=st.number_input("Portfolio amount ($)",min_value=0,max_value=1_000_000,step=1000,key="portfolio_composition_budget")
    st.session_state["_portfolio_saved_budget"]=budget
    if choice=="Your allocation":
        st.caption("Illustrative allocation · Edit to explore. No brokerage balance or algorithm recommendation.")
        try:
            holdings=[]
            for row in edited.to_dict("records"):
                if any(not isinstance(row.get(field),str) or not row[field].strip() for field in ("Symbol","Holding")):
                    raise ValueError("Each holding needs a symbol and name")
                raw=row["Weight (%)"]
                if isinstance(raw,bool):raise ValueError("Use numeric percentages")
                weight=Decimal(str(raw))
                if not weight.is_finite() or weight!=weight.quantize(Decimal(".01")):raise ValueError("Use percentages with at most two decimal places")
                holdings.append(PortfolioHolding(symbol=str(row["Symbol"]).strip().upper(),name=str(row["Holding"]).strip(),
                    kind=row["Type"],weight_bps=int(weight*100)))
            request=PortfolioComposition(budget_cents=budget*100,holdings=holdings)
        except (ValueError,TypeError,KeyError,InvalidOperation):
            st.warning("Review the allocation: use 1–25 unique symbols, valid holding types and numeric weights totaling no more than 100%. Unassigned weight becomes cash; totals over 100% are not silently normalized.")
            return
    else:
        result=strategy_demo(StrategyDemoRequest(available_cash_cents=budget*100))
        if not result["selected"]:
            st.info("This budget does not produce a synthetic basket. No allocation is invented.")
            return
        request=PortfolioComposition(budget_cents=budget*100,origin="synthetic_strategy",holdings=[
            PortfolioHolding(symbol=row["security_id"],name=row["security_id"],kind="Synthetic",weight_bps=1000) for row in result["selected"]])
        st.info("Synthetic strategy output · All ten companies are fabricated. The real recommendation engine remains disabled.")
    rows=composition_rows(request)
    st.session_state["_portfolio_composition_result"]=request.model_dump(mode="json")
    invested=[row for row in rows if row["kind"]!="Cash"]
    b.metric("Holdings",len(invested))
    c.metric("Largest position",f"{max((row['weight_percent'] for row in invested),default=0):g}%")
    allocation,details=st.columns([1.2,1],gap="large")
    with allocation:
        with st.container(border=True):
            st.markdown("**Where your portfolio money goes**")
            frame=pd.DataFrame(rows)
            pick=alt.selection_point(fields=["symbol"],on="click",toggle=False,empty=True)
            chart=alt.Chart(frame).mark_arc(innerRadius=alt.ExprRef(expr="max(0, min(width, height) / 2 - 18) * 0.62"),outerRadius=alt.ExprRef(expr="max(0, min(width, height) / 2 - 18)"),padAngle=.02,cornerRadius=4).encode(
                theta=alt.Theta("weight_bps:Q",stack=True),order=alt.Order("symbol:N"),
                color=alt.Color("symbol:N",scale=alt.Scale(domain=[row["symbol"] for row in rows],range=(COLORS*3)[:len(rows)]),legend=None),
                opacity=alt.condition(pick,alt.value(1),alt.value(.25)),
                tooltip=[alt.Tooltip("name:N",title="Holding"),alt.Tooltip("weight_percent:Q",title="Weight (%)",format=".2f"),alt.Tooltip("amount:Q",title="Allocation ($)",format=",.2f")]).add_params(pick)
            center=alt.Chart(pd.DataFrame([{"text":f"${budget:,.0f}"}])).mark_text(fontSize=20,fontWeight=600,color="#eef4fa").encode(text="text:N")
            st.altair_chart((chart+center).properties(height=260,padding={"top":20,"bottom":20,"left":20,"right":20}),width="stretch",key="portfolio_donut",
                alt="Portfolio doughnut: each slice is exactly proportional to its entered weight, with unallocated weight shown as cash. Exact weights and dollar amounts are also in the table.")
            legend_items=[]
            for index,row in enumerate(rows):
                label="S&P 500*" if row["symbol"]=="SP500_INDEX" else row["symbol"]
                color=COLORS[index % len(COLORS)]
                legend_items.append(f'<span style="display:inline-flex;align-items:center;gap:6px;white-space:nowrap"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{color}"></span>{escape(label)}</span>')
            st.markdown('<div style="display:flex;flex-wrap:wrap;gap:10px 18px;margin:8px 0 16px">'+''.join(legend_items)+'</div>',unsafe_allow_html=True)
            st.caption("Each slice shows its share of your portfolio. Hover for the percentage and dollar amount; click to highlight. Unassigned money appears as cash.")
    with details:
        with st.container(border=True):
            st.markdown("**Allocation detail**")
            st.dataframe(pd.DataFrame([{"Holding":row["symbol"],"Weight":f"{row['weight_percent']:.2f}%","Amount":f"${row['amount']:,.2f}"} for row in rows]),hide_index=True,width="stretch")
            st.caption("Dollar allocations reconcile to the portfolio amount to the cent. Fractional dollar allocations are assumed; these are not executable share quantities.")
        if any(row.kind=="Index placeholder" and row.weight_bps>0 for row in request.holdings):
            st.warning("The S&P 500 placeholder needs a specific fund before a purchase could be sized. An index itself is not a purchasable security.")
        if any(row.symbol=="VOO" and row.weight_bps>0 for row in request.holdings):
            st.info("VOO already tracks the S&P 500. Adding another S&P 500 fund overlaps that exposure; individual stocks can also overlap fund holdings. This view does not calculate look-through exposure.")
    st.caption("Composition is not a diversification score or a return forecast. Your allocation stays in this session and is not sent to Alpaca or saved to the database.")
