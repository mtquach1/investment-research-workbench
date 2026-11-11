"""Lazy session-only preview of one monthly deposit."""
import hashlib
import pandas as pd
import streamlit as st
from public_data_store import canonical_bytes
from stock_monthly import plan_monthly_contribution


def render_monthly_contribution(screen, context):
    signature = hashlib.sha256(canonical_bytes({'screen': screen.model_dump(mode='json'),
        'context': context.model_dump(mode='json')})).hexdigest()
    if st.session_state.get('_monthly_signature') != signature:
        st.session_state.pop('_monthly_result', None)
        st.session_state['_monthly_signature'] = signature
    panel = st.expander('Preview one monthly contribution', key='monthly_contribution_panel', on_change='rerun')
    if not panel.open:
        return
    with panel:
        st.caption('One deposit, using only the holdings you entered. Initial new cash and earlier proposals are excluded. No automatic schedule or trades.')
        if not context.monthly_contribution_cents:
            st.info('Enter a monthly amount above $0 to preview how one deposit could be split.')
            return
        if st.button('Preview this deposit', key='monthly_preview'):
            st.session_state['_monthly_result'] = plan_monthly_contribution(screen, context)
        result = st.session_state.get('_monthly_result')
        if result is None:
            return
        if result.status not in ('allocated', 'cash_only'):
            st.warning(result.explanation)
            return
        a, b, c = st.columns(3)
        a.metric('Monthly deposit (USD)', f'${result.monthly_amount_cents/100:,.2f}')
        b.metric('Experimental stock additions (USD)', f'${result.to_stocks_cents/100:,.2f}')
        c.metric('Cash left aside (USD)', f'${result.cash_unassigned_cents/100:,.2f}')
        st.caption(f'Evidence checked {result.checked_on} · Entered holdings ${result.entered_holdings_cents/100:,.2f}. Checking does not refresh prices.')
        st.info(result.explanation)
        st.dataframe(pd.DataFrame([{'Stock / holding': row.symbol,
            'Before ($)': row.before_cents/100, 'Add this deposit ($)': row.purchase_cents/100,
            'After ($)': row.after_cents/100, 'Baseline target (%)': float(row.target_weight*100),
            'Why this amount': row.explanation}
            for row in result.positions]), hide_index=True, width='stretch', column_config={
                column: st.column_config.NumberColumn(format='$%.2f') for column in
                ['Before ($)', 'Add this deposit ($)', 'After ($)']})
        with st.expander('Why might money stay in cash?'):
            st.write('Each baseline stock keeps a 10% target. An excluded stock, short time horizon, evidence gap or risk limit can block an addition. An existing position above its target gets no extra money. The planner does not replace blocked stocks or increase other targets.')
            st.caption(result.notice)
        st.download_button('Download monthly preview (private JSON)', result.model_dump_json(indent=2),
            file_name='experimental-monthly-contribution.json', mime='application/json')
        st.caption('Contains entered holding values. Save privately. This separate preview is not part of the decision snapshot/PDF format and cannot be restored there.')
