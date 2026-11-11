"""Lazy, read-only freshness and recovery details; no network action in the UI."""
from datetime import timezone
import streamlit as st
from config import get_settings
from daily_stock_refresh import read_refresh_status


def render_stock_refresh_status():
    panel=st.expander('Price freshness and refresh status',key='stock_refresh_status',on_change='rerun')
    if not panel.open:return
    with panel:
        settings=get_settings()
        result=read_refresh_status(settings.market_history_store,mode=settings.market_data_mode)
        if result.status!='available':
            st.info('Local price history is withheld or unavailable. This panel never downloads data.')
            return
        a,b=st.columns(2)
        a.metric('Installed prices through',str(result.completed_through))
        b.metric('Installed price series',result.series_count)
        st.caption(f'Snapshot downloaded {result.retrieved_at.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC} · IEX single-exchange history · Refresh runs when the operator requests it; no automatic daily schedule.')
        report=result.last_recorded_attempt
        if report and result.report_matches_snapshot:
            if report.status=='not_published':
                st.warning('The last recorded refresh did not publish. The previous snapshot remains installed at the observation date above.')
                if report.failed_symbol:st.write(f'Needs investigation: {report.failed_symbol}. Missing required sessions: '+', '.join(map(str,report.missing_required_sessions[:10])))
            else:st.success('The last recorded refresh matches the installed snapshot.')
            st.caption(f'Attempt recorded {report.checked_at.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC} · {report.batches_completed} batches completed · {report.batches_resumed} resumed · Reason: {report.reason_code.replace("_"," ")}')
            if report.historical_missing_sessions:
                st.warning('Known historical gaps remain. These series cannot pass complete-history risk requirements until the gaps are resolved.')
                for symbol,days in report.historical_missing_sessions.items():st.write(f'{symbol}: {len(days)} missing session(s)')
            st.download_button('Download refresh audit (JSON)',report.model_dump_json(indent=2),file_name='local-price-refresh-audit.json',mime='application/json')
        else:
            st.caption('No matching refresh report is available for this snapshot. The installed observation date above is authoritative; an older report does not establish freshness.')
        st.caption('This checks snapshot freshness and publication status. Security identity, source accuracy, investment performance and public display permissions have separate requirements.')
