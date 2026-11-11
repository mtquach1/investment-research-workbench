"""Lazy public-source health panel. Browsing never starts a download."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from data_pipeline import load_release
from reference_refresh import reference_observations,read_reference_report

LABELS={'sec_ticker_exchange':'Issuer directory','nasdaq_listed_directory':'Nasdaq listings',
    'nasdaq_other_directory':'Other exchange listings','ivv_holdings_proxy':'Fund holdings reference'}


def render_reference_status(root):
    panel=st.expander('Are the stock reference sources up to date?',key='reference_health',on_change='rerun')
    if not panel.open:return
    with panel:
        try:
            digest,manifest=load_release(root,verify_tables=False)
            # Check the hashes of every consumed reference artifact.
            from data_pipeline import read_table
            for key in LABELS:read_table(root,manifest.tables[key])
            observations=reference_observations(manifest)
        except (OSError,ValueError,KeyError,TypeError):
            st.info('The complete four-source reference cohort is unavailable. No evidence is inferred.')
            return
        today=datetime.now(ZoneInfo('America/Los_Angeles')).date()
        def fresh(item):
            age=(today-item.retrieved_at.astimezone(ZoneInfo('America/Los_Angeles')).date()).days
            return 0<=age<=7 and (item.source_id=='sec_ticker_exchange' or
                item.observed_on is not None and 0<=(today-item.observed_on).days<=7)
        a,b=st.columns(2)
        a.metric('Reference sources within age policy',f'{sum(fresh(item) for item in observations)} / 4')
        b.metric('Official index membership','Not verified')
        st.caption('Recent source data can still be incomplete or wrong. A fund’s holdings remain a substitute reference list, not official S&P 500 membership.')
        st.caption('Age checks use Los Angeles calendar dates. Download times below use UTC, which can show the following date during a Los Angeles evening.')
        st.dataframe(pd.DataFrame([{'Source':LABELS[item.source_id],
            'Age check':'Within 7-day policy' if fresh(item) else 'Needs newer evidence',
            'Source receipt':'Retained after source failure' if item.source_id in manifest.failures else 'Installed',
            'Observed':str(item.observed_on) if item.observed_on else 'Not provided by source',
            'Downloaded (UTC)':item.retrieved_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M'),
            'Records':item.rows} for item in observations]),hide_index=True,width='stretch')
        report=read_reference_report(root)
        if report and report.installed_release_id==digest:
            if report.status=='published':st.success('The last coordinated reference refresh published all four sources together.')
            else:st.warning('The last coordinated refresh did not publish. The installed release was preserved or another writer advanced it.')
            if report.failed_sources:st.caption('Sources needing attention: '+', '.join(LABELS.get(key,key) for key in report.failed_sources))
            with st.expander('Compare source receipts before and after the attempt'):
                previous={item.source_id:item for item in report.before}
                st.dataframe(pd.DataFrame([{'Source':LABELS[item.source_id],
                    'Source bytes changed':item.source_sha256!=previous[item.source_id].source_sha256,
                    'Previous observation':str(previous[item.source_id].observed_on or 'Unavailable'),
                    'Candidate observation':str(item.observed_on or 'Unavailable'),
                    'Previous records':previous[item.source_id].rows,'Candidate records':item.rows} for item in report.candidate]),hide_index=True,width='stretch')
                st.caption('Candidate receipts are not installed evidence when publication failed.')
            st.download_button('Download reference refresh audit',report.model_dump_json(indent=2),file_name='stock-reference-refresh.json',mime='application/json')
        else:st.caption('No matching coordinated refresh report is available for this release.')
        st.caption('This panel is read-only. Refresh is operator-run, has no automatic schedule, and does not update prices or financial statements.')
