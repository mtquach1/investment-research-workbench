"""Chart-first company price/risk research with explicit feed and basis labels."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
from price_checks import load_price_check, freshness_label

import altair as alt
import pandas as pd
import streamlit as st

from company_market import company_market
from company_events import company_events
from config import get_settings
from market_history import HistoryBar, HistorySeries, compare_history, session_dates
from history_chart import range_start,comparison_chart


@st.cache_data(ttl=60,show_spinner=False)
def _market(public_root,history_root,revision,issuer,symbol,day):
    return company_market(public_root,history_root,issuer,mode="local_research",symbol=symbol,today=day)


@st.cache_data(ttl=60,show_spinner=False)
def _announcements(public_root,revision,issuer,minute):
    result=company_events(public_root,issuer,now=datetime.fromtimestamp(minute*60,tz=timezone.utc))
    return [{"day":item.published_on,"label":item.headline,"source_url":item.source_url} for item in result.events]


def _open_history_lab():
    st.session_state["stock_research_view"]="Strategy lab"
    st.session_state["stock_lab_mode"]="Historical comparison"


def render_market_research(public_root,issuer):
    st.markdown("#### What happened to the investment—and how rough was the ride?")
    settings=get_settings()
    if settings.market_data_mode!="local_research":
        st.info("Market history is withheld on this instance. Financial filings and event context remain available.")
        with st.expander("Connect free data for personal local research"):
            st.write("Configure your free Alpaca paper-only keys in local .env, set MARKET_DATA_MODE=local_research, then run the documented operator refresh. Public redistribution is not enabled.")
        st.button("Try an illustrative history comparison",on_click=_open_history_lab,key="history_lab_"+issuer)
        return
    try:revision=(Path(settings.market_history_store)/"CURRENT.json").stat().st_mtime_ns
    except OSError:revision=None
    day=datetime.now(timezone.utc).date()
    result=_market(str(public_root),str(settings.market_history_store),revision,issuer,None,day)
    if result.status=="choose_security":
        symbol=st.selectbox("Security to inspect",result.symbols,key="market_security_"+issuer)
        result=_market(str(public_root),str(settings.market_history_store),revision,issuer,symbol,day)
    if result.status!="available":
        st.info("No verified price history is installed for this company, or the snapshot could not be verified. Other research remains available.")
        st.button("Try an illustrative history comparison",on_click=_open_history_lab,key="history_lab_"+issuer)
        return
    st.markdown(f"**{result.selected_symbol} closing share price: ${result.raw_close:,.2f}** · {result.price_date}")
    st.caption(freshness_label(result.price_date,datetime.now(timezone.utc)))
    downloaded=result.retrieved_at.astimezone(ZoneInfo("America/Los_Angeles"))
    st.caption(f"Source: Alpaca IEX daily data · Downloaded {downloaded:%b %d, %Y at %I:%M %p %Z} · Updates only when refreshed; this is not a live quote.")
    check=load_price_check(settings.market_history_store,result.selected_symbol,result.snapshot_sha256,result.price_date)
    with st.expander("Independent price check"):
        if check is None:
            st.write("No current second-source check is installed for this snapshot. The chart has not been independently confirmed.")
        elif check.status=="unavailable":
            st.write("The last Yahoo Finance check was unavailable. No agreement is inferred and the chart data was preserved.")
        else:
            st.write(rf"Yahoo Finance reported \${check.reference_close:,.2f} for {check.price_date}; Alpaca IEX reported \${check.primary_close:,.2f}. Difference: {check.difference_percent:.3f}%.")
            st.write("Within the diagnostic tolerance." if check.status=="within_tolerance" else "Outside the diagnostic tolerance. Treat this price as needing investigation.")
            st.caption(rf"Checked {check.checked_at:%Y-%m-%d %H:%M UTC}. Tolerance: the larger of \$0.05 or 0.5% of the reference price. Agreement is not proof of an official exchange close or verification of the full history.")
            st.link_button("View Yahoo Finance historical prices",check.source_url)
        st.caption("Checks are an operator refresh, not a request sent whenever you browse. Different trading venues, session definitions and corporate-action adjustments can cause differences.")
    st.caption("Personal IEX research · SPY ETF proxy · Exact reinvested total return unverified · No strategy performance claim")
    for issue in result.issues:st.warning(issue)
    try:public_revision=(Path(public_root)/"CURRENT.json").stat().st_mtime_ns
    except OSError:public_revision=None
    markers=_announcements(str(public_root),public_revision,issuer,int(datetime.now(timezone.utc).timestamp()//60))
    render_history_comparison(result.comparison,key=issuer,markers=markers,company_label=result.selected_symbol,raw_points=result.comparison.points)
    st.caption("The fiscal-year slider changes company financials; this panel inspects the independently dated market history.")
    with st.expander("Price basis, coverage and source evidence"):
        st.write(result.notice)
        st.write("The latest dollar quote above is unadjusted. The Share price chart defaults to split-only adjusted closes; Original prices is a separate explicit option. Value of $100 and risk statistics use provider all-adjusted closes (split, dividend and spin-off adjustments). Do not add dividend cash again in all-adjusted mode. Exact dividend-reinvestment conventions and consolidated closing-price coverage remain unverified.")
        st.write("Current SEC ticker/issuer matching is not a historical security master. Neither the issuer's market capitalization nor its valuation yields are inferred from an arbitrary share count.")
        st.json({"snapshot_sha256":result.snapshot_sha256,"feed":"iex","benchmark":"SPY ETF proxy",
            "missing_requested_sessions":result.missing_requested_sessions,"public_redistribution_allowed":False,
            "strategy_performance_evidence":False})


def render_history_comparison(comparison,*,key,markers=None,company_label="Company",raw_points=None):
    with st.container(border=True):
        _render_history_comparison(comparison,key=key,markers=markers,company_label=company_label,raw_points=raw_points)


def _render_history_comparison(comparison,*,key,markers=None,company_label="Company",raw_points=None):
    options=[point.day for point in comparison.points]
    preset=st.segmented_control("History range",["1W","1M","3M","YTD","1Y","All"],default="All",key="history_range_"+key) or "All"
    cutoff=range_start(preset,options[-1])
    first=next((day for day in options if cutoff is None or day>=cutoff),options[0])
    with st.expander("Custom dates"):
        interval=st.select_slider("Inspect market-history window",options=options,value=(first,options[-1]),
                                  key="history_window_"+key+"_"+preset)
    if interval[0]==interval[1]:
        st.info("Choose at least two dates to compare changes and drawdowns.")
        return
    # Recompute from original decimal observations, not rounded chart indices.
    selected=[point for point in comparison.points if interval[0]<=point.day<=interval[1]]
    def series(name,field):
        return HistorySeries(symbol=name,role="benchmark_proxy" if name=="SPY" else "issuer_security",cik=None if name=="SPY" else 1,
            bars=[HistoryBar(day=point.day,raw_close=Decimal(str(getattr(point,field))),
                adjusted_close=Decimal(str(getattr(point,field)))) for point in selected])
    window=compare_history(series("COMPANY","company_adjusted_close"),series("SPY","benchmark_adjusted_close"))
    company,benchmark=window.company,window.benchmark
    first,second,third=st.columns(3)
    first.metric("Company change",f"{company.cumulative_change:.1%}",help="Change in provider-adjusted value over the selected dates. A 20% gain turns $100 into $120 before your taxes and costs.")
    second.metric("SPY proxy change",f"{benchmark.cumulative_change:.1%}",help="SPY is an exchange-traded fund that tracks the S&P 500. This compares its adjusted history over exactly the same dates.")
    third.metric("Difference (percentage points)",f"{window.endpoint_difference*100:+.1f}",help="Company percentage change minus SPY percentage change. For example, 20% minus 15% is 5 percentage points.")
    st.caption(f"Matched dates: {company.first} through {company.last} · {company.observations} shared closes · {company.return_observations} return observations. Historical single-security comparison, not strategy backtest.")
    options=["Value of $100","Share price ($)","Drawdown"] if raw_points else ["Value of $100","Drawdown"]
    view=st.radio("Chart view",options,horizontal=True,key="history_chart_view_"+key)
    raw_price=False
    if view=="Value of $100":
        st.caption(rf"Start with \$100 on {company.first}. The blue line ends at \${100*(1+company.cumulative_change):,.2f}; SPY ends at \${100*(1+benchmark.cumulative_change):,.2f}. Changing the dates starts both lines at \$100 again. These are adjusted historical values, not share prices or guaranteed returns.")
    elif view=="Share price ($)":
        basis=st.radio("Share-price basis",["Split-adjusted","Original prices (unadjusted)"],horizontal=True,key="history_price_basis_"+key)
        raw_price=basis=="Original prices (unadjusted)"
        st.caption(r"Split-adjusted prices restate earlier prices in current share units. In a 10-for-1 split, one \$1,000 share becomes ten \$100 shares; the split itself changes neither the holding's value nor its return. Dividends are not included in this price view. SPY is hidden because share-price levels do not compare performance." if not raw_price else "Original transaction-date prices include mechanical jumps at stock splits. Use Split-adjusted for a continuous per-share comparison. Return and risk cards still use all-adjusted prices.")
    else:
        st.caption("Drawdown is the drop from an earlier peak within your selected dates. A value of −20% means the investment is 20% below that peak; 0% means it is at a new peak.")
    visible=[dict(Date=item["day"].isoformat(),Publication=item["day"].isoformat(),Announcement=item["label"])
             for item in (markers or []) if interval[0]<=item["day"]<=interval[1]]
    if visible and st.checkbox("Show sourced announcement markers",value=True,key="history_markers_"+key):
        st.caption("Dashed rules mark announcement publication dates. Timing alone does not establish that an announcement caused a price change; inspect the source in News & events.")
    else:visible=[]
    chart_points=[point for point in raw_points if interval[0]<=point.day<=interval[1]] if view=="Share price ($)" else window.points
    missing_split=view=="Share price ($)" and not raw_price and any(point.company_split_adjusted_close is None for point in chart_points)
    if missing_split:st.info("Split-adjusted price evidence is unavailable. Refresh this history or explicitly choose Original prices; no unadjusted fallback is shown.")
    chart=comparison_chart(chart_points,drawdown=view=="Drawdown",company_label=company_label,markers=visible,share_price=view=="Share price ($)",raw_price=raw_price) if not missing_split else None
    if chart is not None:st.altair_chart(chart,width="stretch",alt="Historical daily share price in dollars; basis explicitly selected." if view=="Share price ($)" else "Value of a starting $100 or decline from earlier peak, compared with SPY. Not a forecast.")
    a,b,c=st.columns(3)
    a.metric("Company worst drawdown",f"{company.maximum_drawdown:.1%}",help="Largest fall from an earlier peak within the selected dates. Earlier peaks outside this window are excluded.")
    b.metric("Company annualized volatility",f"{company.annualized_volatility:.1%}" if company.annualized_volatility is not None else "Unavailable",help="How much daily returns fluctuated, expressed on an annual scale. Higher means a bumpier ride; it is not a predicted loss.")
    c.metric("Company annualized change",f"{company.annualized_change:.1%}" if company.annualized_change is not None else "Window under 1 year",help="The constant yearly growth rate that would connect the starting and ending adjusted values. It hides the ups and downs along the way.")
    st.caption("Drawdown is measured from peaks inside the selected window. Volatility uses sample daily-return deviation × √252 and is withheld across missing sessions. Short windows are not annualized.")
    if company.missing_sessions:st.warning(f"{len(company.missing_sessions)} trading sessions are missing inside this window; no prices were filled.")
    with st.expander("Matched values and exclusions"):
        st.write(f"Unmatched dates excluded: company {comparison.excluded_company_dates}; SPY proxy {comparison.excluded_benchmark_dates}. Both series use identical comparison dates.")
        st.dataframe(pd.DataFrame([point.model_dump() for point in window.points]),hide_index=True,width="stretch")


def render_history_lab():
    st.subheader("Learn what a return chart can hide")
    st.info("Illustration only · Every price in this lab is fabricated. These are not Apple, AMD or SPY returns. No market data account is needed.")
    days=session_dates(date(2025,1,2),date(2026,10,28))
    import math
    def example(symbol,role,cik):
        bars=[]
        for index,day in enumerate(days):
            growth=.0005*index if role=="benchmark_proxy" else .00085*index-.32*math.exp(-((index-200)/35)**2)
            value=Decimal(str(100*math.exp(growth)))
            bars.append(HistoryBar(day=day,raw_close=value,adjusted_close=value))
        return HistorySeries(symbol=symbol,role=role,cik=cik,bars=bars)
    render_history_comparison(compare_history(example("SYNTHETIC","issuer_security",1),example("SPY","benchmark_proxy",None)),key="synthetic")
