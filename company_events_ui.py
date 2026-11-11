"""Source-linked company events, separate from financial scoring and browsing I/O."""

from datetime import datetime, timedelta, timezone

import altair as alt
import pandas as pd
import streamlit as st

from company_events import company_events


@st.cache_data(ttl=60,show_spinner=False)
def _events(root,revision,issuer,minute):
    return company_events(root,issuer,now=datetime.fromtimestamp(minute*60,tz=timezone.utc))


def render_company_events(root,revision,issuer):
    result=_events(str(root),revision,issuer,int(datetime.now(timezone.utc).timestamp()//60))
    st.markdown("#### What is happening around this company?")
    st.caption("Official announcements and SEC filing metadata · Separate from strategy scores · Limited coverage")
    if result.status!="available":
        st.info("Event context is unavailable or could not be verified. This does not mean the company has no news.")
        return
    if result.filings_refresh_due or result.filings_refresh_failed:
        st.warning("The filing snapshot needs refresh or its latest refresh failed. Older verified filings remain visible.")
    if result.context_catalog_status=="unavailable":
        st.warning("Reviewed announcement context is unavailable. Verified SEC filings are shown separately.")
    if result.events:
        for event in result.events:
            with st.container(border=True):
                st.markdown("**"+event.headline+"**")
                st.caption(f"Company announcement · Published {event.published_on} · Manually reviewed {event.reviewed_on}")
                st.write(event.fact)
                if event.scheduled_at:
                    if event.schedule_status=="upcoming":
                        st.info("Upcoming scheduled call: "+event.scheduled_at.strftime("%b %d, %Y · %I:%M %p %z")+" · Source-confirmed schedule; subject to change.")
                    else:
                        st.info("The scheduled call time has passed. Its occurrence and outcome have not been verified here.")
                if event.review_stale:st.warning("This announcement context has not been reviewed within seven days. Check the official source for changes.")
                st.caption("Research consideration · "+event.considerations)
                st.link_button("Read official announcement",event.source_url,key="announcement_"+event.event_id)
    else:
        st.info("No reviewed announcement or upcoming earnings date is installed for this company. This does not establish an absence of news or event risk.")
    st.markdown("**Recent filing timeline**")
    if not result.filings:
        st.info("No verified filing metadata is installed for this issuer. No event calendar is inferred from missing records.")
    else:
        labels=sorted({item.form for item in result.filings})
        forms=st.multiselect("Filing types",labels,default=labels,key="event_forms_"+issuer)
        window=st.radio("Timeline window",["Past 90 days","Past year","All cached"],horizontal=True,key="event_window_"+issuer)
        cutoff=result.checked_at.date()-timedelta(days=90 if window=="Past 90 days" else 365) if window!="All cached" else None
        selected=[item for item in result.filings if item.form in forms and (cutoff is None or item.filed_on>=cutoff)]
        st.caption(f"Snapshot retrieved: {result.filings_retrieved_at.isoformat()} · Showing {len(selected)} of {len(result.filings)} cached recent filings (at most 100). Filing dates are not event occurrence dates.")
        if selected:
            frame=pd.DataFrame([{"Filed":item.filed_on.isoformat(),"Form":item.form,"Topic":item.headline} for item in selected])
            frame["Filing date"]=frame["Filed"]  # Keep tooltip dates untransformed by browser time zones.
            chart=alt.Chart(frame).mark_circle(size=85,opacity=.7).encode(
                x=alt.X("Filed:T",title="SEC filing date",scale=alt.Scale(type="utc"),axis=alt.Axis(format="%b %Y",tickCount=6)),
                y=alt.Y("Form:N",title=None),tooltip=[alt.Tooltip("Filing date:N"),"Form","Topic"]
            ).properties(height=130)
            st.altair_chart(chart,width="stretch",alt="SEC filings grouped by form and filing date. Filing topics are metadata, not sentiment or stock-price explanations.")
            st.dataframe(pd.DataFrame([{"Filed":item.filed_on.isoformat(),"Form":item.form,"Topic":item.headline,
                "Read filing":item.source_url} for item in selected]),hide_index=True,width="stretch",
                column_config={"Read filing":st.column_config.LinkColumn("Read filing",display_text="SEC filing")})
        else:
            st.caption("No filings match this view. Change the time window or filing types; this does not establish an absence of company news.")
    st.caption("8-K topics are based on reported item codes; the filing may include several topics. Company announcements present the issuer's perspective. Independent reporting and complete market news are not covered.")
    with st.expander("Sources, coverage and refresh details"):
        st.write(result.notice)
        st.json({"release_id":result.release_id,"filing_source_sha256":result.filing_source_sha256,
                 "context_catalog_sha256":result.context_catalog_sha256,"checked_at":result.checked_at.isoformat(),
                 "automatic_refresh":"Not scheduled; operator CLI refresh only", "affects_strategy_score":False})
