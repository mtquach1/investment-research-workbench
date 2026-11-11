"""Compact, public-only evidence panels shared by the two decision workspaces."""

from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from config import get_settings
from market_catalog import load_catalog


SOURCE_LABELS={
    'sec_cover_aapl_2025':'Apple FY2025 registered security classes (SEC filing)',
    'sec_cover_nvda_2026':'NVIDIA FY2026 registered security classes (SEC filing)',
    "census_zcta_county_2020":"2020 geographic areas (Census)",
    "zillow_sfr_value_zip":"Single-family values (Zillow)",
    "zillow_mixed_rent_zip":"Mixed-home rents (Zillow)",
    "zillow_sfr_rent_metro":"Regional single-family rents (Zillow)",
    "hud_safmr_2027":"ZIP rent benchmarks (HUD)",
    "ivv_holdings_proxy":"Fund holdings proxy (iShares)",
    "alphavantage_ibm_daily_demo":"One-stock price demo (Alpha Vantage)",
    "sec_ticker_exchange":"Issuer/ticker mapping (SEC)",
    'nasdaq_listed_directory':'Nasdaq listing directory',
    'nasdaq_other_directory':'Other-exchange listing directory (Nasdaq Trader)',
    **{f"sec_companyfacts_{ticker.lower()}":ticker+" annual sample (SEC)" for ticker in ("AAPL","MSFT","KO","JPM")},
}


def _source_display(row):
    stamp=row.get("retrieved_at")
    fetched=datetime.fromisoformat(stamp).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M") if stamp else "Unavailable"
    states={"normalized":"Loaded","cached_after_refresh_failure":"Earlier data retained",
            "retained_previous_release":"Earlier release retained","unavailable":"Unavailable"}
    issues={"source_unavailable":"Provider did not supply data","operator_contact_required":"Operator setup required",
            "cache_unavailable":"No cached data","invalid_dataset":"Dataset failed validation"}
    return {"Dataset":SOURCE_LABELS.get(row["source_id"],row["source_id"]),
        "Observation":row.get("observation_date") or ("2020 geography vintage" if row["source_id"]=="census_zcta_county_2020" else "Not supplied"),
        "Downloaded (UTC)":fetched,"Availability":states.get(row["state"],row["state"]),
        "Latest issue":issues.get(row.get("failure_code"),"None")}


@st.cache_data(ttl=30,show_spinner=False)
def _public_coverage(root, pointer_version, today):
    # Public metadata only. Never add budgets, holdings, uploads or session state.
    return load_catalog(root)


def render_data_readiness(domain):
    root=get_settings().market_data_store
    try:
        marker=(Path(root)/"CURRENT.json").stat().st_mtime_ns
    except OSError:
        marker=None
    today=datetime.now(timezone.utc).date()
    panel=st.expander('Data coverage and sources',expanded=False,key='data_coverage_'+domain,on_change='rerun')
    if not panel.open:return
    with panel:
        catalog=_public_coverage(str(root),marker,today)
        if catalog.status!="partial":
            st.info(catalog.notice)
            return
        evidence=catalog.stocks if domain=="stocks" else catalog.rentals
        st.caption(f"Research release: {catalog.normalized_as_of} · Observation age checked: {catalog.checked_on}")
        st.write("These checks show what evidence is available. They do not certify an investment recommendation.")
        overview, sources, meaning=st.tabs(["Coverage", "Sources and dates", "What this means"])
        with overview:
            columns=st.columns(2)
            for index,item in enumerate(evidence.items):
                with columns[index%2]:
                    amount=f"{item.count:,}"+(f" / {item.denominator:,}" if item.denominator else "")
                    st.metric(item.label,amount)
                    st.caption(item.unit+" · "+item.status.replace("_"," "))
            if domain=="stocks":
                item=evidence.items[1]
                chart_rows=[{"status":"Complete annual sample","count":item.count},
                            {"status":"Incomplete annual sample","count":(item.denominator or 0)-item.count}]
                chart_title="Annual samples · not full-universe coverage"
            else:
                item=evidence.items[1]
                chart_rows=[{"status":"Within observation age limit","count":item.count},
                            {"status":"Missing or older observation","count":max(0,(item.denominator or 0)-item.count)}]
                chart_title="Value context · dated geographic candidates"
            if sum(row["count"] for row in chart_rows):
                chart=alt.Chart(pd.DataFrame(chart_rows)).mark_bar(cornerRadiusEnd=3).encode(
                    x=alt.X("count:Q",title="Count",axis=alt.Axis(tickMinStep=1)),
                    y=alt.Y("status:N",title=None,sort=None,axis=alt.Axis(labelLimit=240)),
                    color=alt.Color("status:N",scale=alt.Scale(domain=[row["status"] for row in chart_rows],range=["#087f83","#d79736"]),legend=None),
                    tooltip=["status","count"])
                st.altair_chart(chart.properties(height=220,title=chart_title).configure_view(strokeWidth=0),width="stretch",
                    alt=chart_title+". Counts describe audited samples or context, not recommendation coverage.")
        with meaning:
            for item in evidence.items:
                st.markdown(f"**{item.label}:** {item.explanation}")
            st.markdown("**What still needs evidence**")
            for blocker in evidence.blockers:
                st.write("• "+blocker)
        with sources:
            source_rows=[row for row in catalog.sources if (row["source_id"].startswith(("sec_","ivv_","alphavantage_","nasdaq_"))
                if domain=="stocks" else row["source_id"].startswith(("zillow_","census_","hud_")))]
            st.markdown("**Source dates and recovery status**")
            st.dataframe(pd.DataFrame([_source_display(row) for row in source_rows]),hide_index=True,width="stretch")
            st.caption("A retrieval date says when a file was fetched. An observation date says which period it describes. Old data does not become current when re-downloaded.")
            st.caption("An unavailable or incompatible dataset is excluded from supported calculations. A failed refresh retains verified earlier data with visible recovery status.")
            st.caption("Public-data coverage is cached for at most 30 seconds; private scenario inputs are not part of this cache.")
            st.caption("Display permissions are source-specific. Exact metadata includes each review decision, full timestamps, source IDs, age checks and fingerprints.")
            if st.checkbox("Show exact source metadata",key="source_metadata_"+domain):
                st.json(source_rows)
            st.markdown("**Method and source documentation**")
            for row in source_rows:
                if row.get("documentation_url"):
                    st.link_button(SOURCE_LABELS.get(row["source_id"],row["source_id"]),row["documentation_url"])
            st.caption("Release fingerprint: "+catalog.release_id)
