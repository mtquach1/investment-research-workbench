"""One session-only evidence -> constraints -> decision investigation workflow."""
from decimal import Decimal
import json
import altair as alt
import pandas as pd
from pydantic import ValidationError
import streamlit as st
from config import get_settings
from stock_screen import stock_screen
from stock_evidence import evidence_inventory
from stock_decisions import POLICY, POLICY_HASH, DecisionContext, DecisionHolding, assess_decisions
from decision_snapshots_ui import render_decision_snapshots

LABELS = {'buy_candidate': 'Buy candidate · experimental', 'hold': 'Hold · limited rules pass',
    'review_for_trim_or_sell': 'Review for trim/sell · no sale instruction', 'pass': 'Pass · research criteria',
    'insufficient_evidence': 'Insufficient evidence'}


def render_stock_decisions():
    st.subheader('Find stocks to research, or review what you own')
    st.caption('Check the data → set your limits → understand the results → save or download. Your settings do not change the company quality/value score.')
    st.info('Experimental research only: the company list is a substitute reference and valuations are estimates. Verified buy/sell recommendations remain unavailable.')
    settings = get_settings()
    if settings.market_data_mode != 'local_research':
        st.info('Enable personal local market research to use the decision workspace.')
        return
    screen = stock_screen(settings.market_data_store, settings.market_history_store, mode=settings.market_data_mode)
    inventory = evidence_inventory(screen)
    with st.expander('1 · Check the data and its limits', expanded=False):
        st.caption(f'Checked {screen.checked_on} · ETF observations {screen.universe.observed_on or "unavailable"} · Checking does not download fresh prices.')
        if screen.status != 'available':
            st.warning('Installed evidence is unavailable or failed integrity checks. Decisions are withheld.')
        else:
            frame = pd.DataFrame([{'Requirement': code.replace('_', ' '), 'State': state, 'Companies': count}
                for code, counts in inventory.counts.items() for state, count in counts.items()])
            chart = alt.Chart(frame).mark_bar(cornerRadiusEnd=3).encode(
                y=alt.Y('Requirement:N', title=None, axis=alt.Axis(labelLimit=200)),
                x=alt.X('Companies:Q', title='Installed companies', axis=alt.Axis(tickMinStep=1, gridOpacity=.1)),
                color=alt.Color('State:N', scale=alt.Scale(domain=['pass', 'fail', 'missing', 'provisional'],
                    range=['#7cebd3', '#ed91b3', '#74849b', '#f2ba80']), legend=alt.Legend(orient='bottom', title=None)),
                tooltip=['Requirement:N', 'State:N', 'Companies:Q']).properties(height=300).configure_view(stroke=None)
            st.altair_chart(chart, width='stretch', alt='Company counts for each evidence requirement, split into passing, failed, missing and provisional evidence. Counts do not measure recommendation confidence.')
            st.dataframe(pd.DataFrame(inventory.counts).T.rename_axis('Requirement').reset_index(), hide_index=True, width='stretch')
        st.info('Verified recommendations remain blocked. This workspace can only apply the separate experimental policy. Automatic daily refresh and verified share-class/index/valuation coverage are still unfinished.')
        st.download_button('Download evidence inventory', inventory.model_dump_json(indent=2), file_name='stock-evidence-inventory.json', mime='application/json')
    st.markdown('**2 · Your research constraints**')
    accepted = st.checkbox('Use experimental decisions with proxy membership and estimated valuations', value=False, key='workflow_consent')
    if not accepted:
        st.info('Read the evidence report first. Opt in to inspect experimental assessments; nothing is purchased or sold.')
        return
    a, b, c = st.columns(3)
    cash = a.number_input('New cash to consider ($)', 0, 1000000, 10000, 100, key='workflow_cash')
    horizon = b.number_input('Time invested (years)', 0, 60, 5, key='workflow_horizon',help='How long could you leave this money invested? The experimental policy uses a five-year preference, not a validated suitability test.')
    weight = c.slider('Largest direct position (%)', 1, 100, 30, key='workflow_weight',help=r'For example, \$300 of \$1,000 is 30%. Underlying fund holdings are not included.')
    monthly = st.number_input('Monthly amount to preview ($)', 0, 100000, 0, 100, key='workflow_monthly',
        help='Use 0 to skip. Preview one deposit below; this does not set up recurring payments.')
    with st.expander('Holdings and optional restrictions'):
        excluded = st.multiselect('Purchase exclusions', sorted({symbol for row in screen.rows for symbol in row.tickers}), key='workflow_exclusions')
        risk_on = st.checkbox('Apply a historical volatility ceiling', key='workflow_risk_on')
        volatility = st.slider('Annualized historical volatility ceiling (%)', 0, 200, 50, key='workflow_volatility')
        st.caption('Optional exact-symbol holdings. Values stay in this session; no account connection. Include all holdings you want in the denominator. Funds retain unresolved underlying exposure.')
        entered = st.data_editor(pd.DataFrame([{'Symbol': '', 'Current value ($)': 0.0}]), num_rows='dynamic', hide_index=True,
            width='stretch', key='workflow_holdings', column_config={
                'Symbol': st.column_config.TextColumn(max_chars=15),
                'Current value ($)': st.column_config.NumberColumn(min_value=0, max_value=1000000, step=1)})
    try:
        holdings = []
        for row in entered.to_dict('records'):
            symbol = str(row['Symbol'] or '').strip().upper()
            value = Decimal(str(row['Current value ($)'] or 0))
            if not symbol and not value: continue
            if not value.is_finite() or value != value.quantize(Decimal('.01')):
                raise ValueError('Use finite cent amounts')
            holdings.append(DecisionHolding(symbol=symbol, value_cents=int(value * 100)))
        context = DecisionContext(acknowledge_experimental=True, new_cash_cents=cash * 100, horizon_years=horizon,
            maximum_direct_weight=Decimal(weight) / 100, monthly_contribution_cents=monthly * 100,
            maximum_volatility=Decimal(volatility) / 100 if risk_on else None, excluded_symbols=excluded, holdings=holdings)
    except (ValidationError, ValueError, ArithmeticError):
        st.warning('Enter unique ticker symbols and positive cent amounts, at most 25 holdings and $1 million combined.')
        return
    result = assess_decisions(screen, context)
    from stock_monthly_ui import render_monthly_contribution
    render_monthly_contribution(screen, context)
    from holding_research_ui import render_owned_holdings
    render_owned_holdings(screen,context)
    st.markdown('**3 · Investigate the assessment**')
    if result.status != 'experimental':
        st.warning('The research data needs updating or could not be verified. Your settings stay in this session. Checking this page does not download new data.')
        st.caption('To inspect data dates, open Stocks → Research screen. A holding-cost illustration can still use your own entered amounts above.')
        render_decision_snapshots(screen,context,result)
        return
    a, b, c = st.columns(3)
    a.metric('Experimental candidates', result.outcome_counts.get('buy_candidate', 0))
    b.metric('Holdings needing review', result.outcome_counts.get('review_for_trim_or_sell', 0))
    c.metric('New cash unassigned', f'${result.cash_unassigned_cents / 100:,.2f}')
    st.caption('Candidate amounts retain the original equal-weight baseline. Held, blocked or constrained amounts stay cash; this is not a reoptimized complete portfolio. Current holding concentration excludes new cash; candidate concentration includes it.')
    groups = st.multiselect('Show assessments', list(LABELS), default=list(LABELS), format_func=LABELS.get, key='workflow_groups')
    cards = [card for card in result.cards if card.outcome in groups]
    st.dataframe(pd.DataFrame([{'Company': card.company, 'Symbols': ', '.join(card.symbols), 'Assessment': LABELS[card.outcome],
        'Score / 100': card.research_score * 100 if card.research_score is not None else None,
        'Paper addition ($)': card.paper_addition_cents / 100, 'Why': '; '.join(reason.detail for reason in card.reasons)} for card in cards]),
        hide_index=True, width='stretch', column_config={
            'Score / 100': st.column_config.NumberColumn(format='%.2f'),
            'Paper addition ($)': st.column_config.NumberColumn(format='$%.2f')})
    if cards:
        indexes = list(range(len(cards)))
        if st.session_state.get('workflow_company', 0) not in indexes:
            st.session_state.pop('workflow_company', None)
        index = st.selectbox('Investigate a company decision', indexes, format_func=lambda i: cards[i].company, key='workflow_company')
        card = cards[index]
        st.markdown(f'**{LABELS[card.outcome]}**')
        for item in card.reasons: st.write(item.detail)
        positive, contrary = st.columns(2)
        with positive:
            st.markdown('**Supporting evidence**')
            for item in card.supporting_evidence: st.write(item)
        with contrary:
            st.markdown('**Concerns and unknowns**')
            for item in card.contrary_evidence: st.write(item)
            for item in card.review_flags: st.caption(f'{item.code}: {item.detail}')
        st.markdown('**Revisit when**')
        for item in card.revisit_when: st.write(item)
        if card.evidence:
            st.dataframe(pd.DataFrame([check.model_dump() for check in card.evidence.checks]), hide_index=True, width='stretch')
        if card.issuer_key and st.button('Open financials, price history and events', key='workflow_open_company'):
            st.session_state['research_company_query'] = card.issuer_key
            st.session_state['stock_research_view'] = 'Company research'
            st.rerun()
    st.download_button('Download this decision assessment (private JSON)', result.model_dump_json(indent=2),
        file_name='experimental-stock-decisions.json', mime='application/json')
    st.caption('This raw export contains your entered holdings and constraints. Use the saved-record panel below for validated restore and a recomputed PDF summary. A complete thesis/cost/tax review remains unfinished.')
    render_decision_snapshots(screen,context,result)
    with st.expander('Exact decision policy and reproducibility'):
        st.json(POLICY)
        st.code(json.dumps({'policy_sha256': POLICY_HASH, 'strategy_sha256': result.strategy_sha256,
            'public_release_id': result.public_release_id, 'market_snapshot_sha256': result.market_snapshot_sha256,
            'universe_sha256': result.universe_sha256, 'listing_reference_hashes': result.listing_reference_hashes}, indent=2))
    st.caption(result.notice)
