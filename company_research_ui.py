"""Interactive real filing research. Browsing never triggers provider downloads."""

from datetime import datetime, timezone
from pathlib import Path
import re

import altair as alt
import pandas as pd
import streamlit as st

from company_research import company_directory, company_research
from company_strategy import explain_company_strategy
from company_events_ui import render_company_events
from market_history_ui import render_market_research
from stock_screen_ui import open_screen
from config import get_settings


@st.cache_data(ttl=30, show_spinner=False)
def _directory(root, revision, day):
    return company_directory(root, today=day)


@st.cache_data(ttl=30, show_spinner=False)
def _research(root, revision, issuer, day):
    return company_research(root, issuer, today=day)


def _money(value):
    if value is None:
        return "Unavailable"
    return f"${float(value)/1e9:,.2f}B"


def _chart(rows, measures, title, *, percentage=False, key, inspected_period):
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.info("No aligned observations are available for this chart.")
        return
    frame["fiscal_date"] = frame["period"]
    # A missing ratio creates a gap; never draw through unavailable observations.
    frame["segment"] = frame.groupby("measure", sort=False)["value"].transform(lambda values: values.isna().cumsum())
    legend = alt.selection_point(fields=["measure"], bind="legend")
    chart = alt.Chart(frame).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("period:T", title="Fiscal year end", scale=alt.Scale(type="utc"), axis=alt.Axis(format="%Y",tickCount="year")),
        y=alt.Y("value:Q", title="Percent (%)" if percentage else "USD billions", scale=alt.Scale(zero=True)),
        color=alt.Color("measure:N", title=None, scale=alt.Scale(domain=measures, range=["#7cebd3", "#b8b1f1", "#93b6d6"][:len(measures)]), legend=alt.Legend(orient="bottom")),
        detail="segment:N", opacity=alt.condition(legend, alt.value(1), alt.value(.15)),
        tooltip=[alt.Tooltip("fiscal_date:N", title="Fiscal period end"), "measure", alt.Tooltip("value:Q", format=",.2f")],
    ).add_params(legend)
    marker = alt.Chart(pd.DataFrame([{"period":inspected_period,"fiscal_date":inspected_period}])).mark_rule(color="#899ca5",strokeDash=[4,4]).encode(
        x=alt.X("period:T",scale=alt.Scale(type="utc")),tooltip=[alt.Tooltip("fiscal_date:N",title="Inspected fiscal year")])
    st.altair_chart((chart+marker).properties(height=300).configure_view(strokeWidth=0), width="stretch", key=key,
        alt=title + ". Sourced annual filing observations; gaps mean unavailable data, not zero.")
    st.caption("Click a legend item to highlight it. Figures describe the business, not stock investment returns.")


def render_company_research():
    st.subheader("Explore a real company's financials")
    st.info("Real SEC filing data · Supported cached issuers. No live price, buy recommendation or verified S&P membership is inferred.")
    root = get_settings().market_data_store
    try:
        revision = (Path(root)/"CURRENT.json").stat().st_mtime_ns
    except OSError:
        revision = None
    day = datetime.now(timezone.utc).date()
    directory = _directory(str(root), revision, day)
    if directory.status != "available":
        st.info(directory.notice)
        st.caption("Run the documented public-data refresh to install supported SEC snapshots. The Strategy lab remains available without them.")
        return
    query = st.text_input("Find a supported company", placeholder="Try Apple, NVIDIA, Amazon, Alphabet or a ticker", key="research_company_query").strip().casefold()
    tokens = [token for token in re.sub(r"[^a-z0-9]+"," ",query).split() if token not in ("stock","stocks","shares")]
    entries = [entry for entry in sorted(directory.entries,key=lambda item:item.name.casefold()) if all(token in
        re.sub(r"[^a-z0-9]+"," ",(entry.name+" "+" ".join(entry.tickers)+" "+entry.issuer_key).casefold()) for token in tokens)]
    st.caption(f"{len(directory.entries)} supported cached issuers · Search covers these snapshots, not the whole market.")
    if not entries:
        st.info("No supported company matches. This search does not substitute a different company or invent missing data.")
        return
    by_key = {entry.issuer_key: entry for entry in entries}
    issuer = st.selectbox("Research company", list(by_key), format_func=lambda key: by_key[key].name+(" · Events only" if not by_key[key].financials_available else ""),
                          key="research_issuer")
    result = _research(str(root), revision, issuer, day)
    if result.status != "available":
        st.warning(result.notice)
        if not by_key[issuer].financials_available:
            st.markdown("### "+by_key[issuer].name)
            render_company_events(root,revision,issuer)
            render_market_research(root,issuer)
        return
    st.markdown("### " + result.company.name)
    st.caption(f"Latest supported fiscal year: {result.latest.period_end or 'Unavailable'} · Snapshot retrieved: {result.retrieved_at[:10]} · SEC CIK: {result.company.cik}")
    if result.company.ticker_mapping == "matched_sec_directory":
        st.caption("SEC directory ticker associations: " + ", ".join(result.company.tickers))
        if len(result.company.tickers)>1:
            st.caption("An issuer can have common shares, preferred shares and notes. These associations do not make those securities interchangeable; the charts describe the filing issuer.")
    else:
        st.caption("Current ticker associations are unavailable; this view identifies the filing issuer by CIK.")
    if not result.current_strategy_period_gate_passed:
        st.warning("The financial period does not pass the strategy's current-data age requirement. Historical research remains available.")
    history = result.history or [result.latest]
    periods = [item.period_end for item in history if item.period_end]
    if not periods:
        st.warning("No supported annual revenue period was found for this issuer.")
        return
    selected_period = st.select_slider("Inspect fiscal period", options=periods, value=periods[-1], key="research_period_"+issuer) if len(periods)>1 else periods[0]
    selected = next(item for item in history if item.period_end == selected_period)
    fact_value = lambda name: selected.facts[name].value if name in selected.facts else None
    first, second, third = st.columns(3)
    first.metric("Reported revenue", _money(fact_value("revenue")))
    second.metric("Reported net income", _money(fact_value("net_income")))
    third.metric("Free cash flow · OCF minus cash capex", _money(fact_value("free_cashflow")))
    overview,business,market,news,evidence=st.tabs(["Investment case","Business financials","Price & risk","News & events","Sources"])
    with overview:
        st.button("Inspect sector and valuation context",on_click=open_screen,args=(issuer,),key="company_screen_"+issuer)
        st.caption("Filing-based estimates are kept separate from the strategy's verified valuation requirements.")
        render_strategy_evidence(explain_company_strategy(selected,as_of=day))
    with news:
        render_company_events(root,revision,issuer)
        st.caption("Events use their actual announcement/filing dates and are independent of the fiscal-year slider above.")
    with market:
        render_market_research(root,issuer)
    def rows(names, *, metric=False):
        output = []
        for item in history:
            for field, label in names.items():
                value = item.metrics.get(field) if metric else item.facts[field].value if field in item.facts else None
                output.append({"period": item.period_end, "measure": label,
                               "value": float(value)*(100 if metric else 1e-9) if value is not None else None})
        return output
    with business:
        business_chart,cash,margins=st.tabs(["Revenue & earnings","Cash generation","Profitability"])
    with business_chart:
        names = {"revenue":"Revenue", "net_income":"Net income"}
        _chart(rows(names), list(names.values()), "Annual revenue and net income", key="research_business_"+issuer,inspected_period=selected_period)
    with cash:
        names = {"operating_cashflow":"Operating cash flow", "capital_expenditures":"Cash capital expenditure", "free_cashflow":"Free cash flow"}
        _chart(rows(names), list(names.values()), "Annual operating cash flow and cash capital expenditure", key="research_cash_"+issuer,inspected_period=selected_period)
        st.caption("Free cash flow here equals reported operating cash flow minus cash property/plant/equipment expenditure. It is a defined research measure, not necessarily the company's own adjusted FCF measure.")
    with margins:
        names = {"operating_margin":"Operating margin", "free_cashflow_margin":"FCF margin", "return_on_assets":"Return on assets"}
        _chart(rows(names, metric=True), list(names.values()), "Annual profitability ratios", percentage=True, key="research_margins_"+issuer,inspected_period=selected_period)
        st.caption("Return on assets uses average beginning/end assets. Each point uses aligned inputs within one filing accession. Missing bank/sector inputs remain unavailable.")
    with evidence:
        st.write("History shows reported fiscal years available in this snapshot and may include later restatements. It is not a point-in-time strategy backtest or a price chart.")
        st.dataframe(pd.DataFrame([{"Fact": name.replace("_", " "), "Value (USD)":str(fact.value), "Filed":fact.filed,
            "Accession":fact.accession, "Source tag":fact.tag} for name,fact in selected.facts.items()]), hide_index=True, width="stretch")
        if selected.issues:
            st.write("Data notes: " + "; ".join(selected.issues))
        st.caption("Valuation yields and buy recommendations remain unavailable until market capitalization, security identity, price history and portfolio requirements are supported.")
        st.link_button("SEC company filings", f"https://www.sec.gov/edgar/browse/?CIK={result.company.cik}")
        st.link_button("Source financial facts", result.source_url)
        st.json({"selected_period":selected.model_dump(mode="json"), "source_sha256":result.source_sha256,
            "release_id":result.release_id, "retrieved_at":result.retrieved_at, "source_as_of":result.source_as_of})


def render_strategy_evidence(result):
    st.markdown("#### What does this tell our strategy?")
    st.caption(f"Selected fiscal year: {result.period_end} · Assessed as of {result.evaluated_as_of} · {result.strategy_id}")
    st.info("Research only · Selection score unavailable. Business profitability alone does not establish a good purchase price.")
    st.write("The strategy combines three profitability measures and two valuation measures, each with a 20% weight. It ranks eligible companies within their sectors; these raw ratios are not percentile scores.")
    labels={"return_on_assets":"Return on assets","operating_margin":"Operating margin",
            "free_cashflow_margin":"Free cash flow margin","earnings_yield":"Earnings yield",
            "free_cashflow_yield":"Free cash flow yield"}
    available=[{"Measure":labels[item.key],"Percent":float(item.value)*100}
               for item in result.features if item.status=="available"]
    if available:
        chart=alt.Chart(pd.DataFrame(available)).mark_bar(color="#7cebd3").encode(
            y=alt.Y("Measure:N",sort=list(labels.values()),title=None,axis=alt.Axis(labelLimit=200)),
            x=alt.X("Percent:Q",title="Reported ratio (%)",scale=alt.Scale(zero=True)),
            tooltip=["Measure",alt.Tooltip("Percent:Q",format=".2f")]).properties(height=150)
        st.altair_chart(chart,width="stretch",alt="Available raw profitability ratios for the inspected fiscal year. These are not scores or expected returns.")
    st.dataframe(pd.DataFrame([{"Measure":labels[item.key],"Reported value":
        f"{item.value:.2%}" if item.value is not None else "Unavailable",
        "Strategy weight":f"{item.weight:.0%}","Definition":item.formula} for item in result.features]),
        hide_index=True,width="stretch")
    failed=[item for item in result.financial_checks if item.status=="fail"]
    missing=[item for item in result.financial_checks if item.status=="unavailable"]
    if failed:
        st.warning("Observed financial rule failures: "+"; ".join(item.explanation for item in failed))
    if missing:
        st.warning("Financial checks awaiting evidence: "+"; ".join(item.explanation for item in missing))
    if not failed and not missing:
        st.success("The inspected filing passes the supported financial checks. Overall investment eligibility remains undetermined.")
    with st.expander("Inspect financial rules and evidence"):
        st.dataframe(pd.DataFrame([{"Rule":item.explanation,"Result":item.status} for item in result.financial_checks]),
                     hide_index=True,width="stretch")
    st.markdown("**What still prevents a recommendation?**")
    for requirement in result.unresolved_requirements:
        st.markdown("- "+requirement)
    st.caption(result.notice)
