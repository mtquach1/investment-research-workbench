"""Proposal readiness and observed-history replay, separated from simulations."""
from decimal import Decimal
import altair as alt
import pandas as pd
import streamlit as st
from config import get_settings
from company_research import company_directory
from company_market import company_market
from stock_portfolio import ProposalRequest,stock_proposal
from stock_replay import ReplayRequest,replay_stock


def render_stock_proposal():
    from stock_refresh_ui import render_stock_refresh_status
    render_stock_refresh_status()
    from experimental_basket_ui import render_experimental_basket
    from stock_review_ui import render_validation_workspace
    from stock_decisions_ui import render_stock_decisions
    decisions,experimental,strict,validation=st.tabs(['Decision workflow','Experimental research','Verified recommendations','Validation & evaluation'])
    with strict:_render_verified_proposal()
    with experimental:render_experimental_basket()
    with decisions:render_stock_decisions()
    with validation:render_validation_workspace()


def _render_verified_proposal():
    settings=get_settings();st.subheader('Can the strategy build a verified portfolio?')
    st.caption('The defined strategy requires 10 positions, at most three per sector, with five eligible sector peers for scoring. Budget controls purchase sizing; it does not make a company attractive.')
    budget=st.number_input('Cash available for a proposed basket ($)',0,1000000,10000,100,key='proposal_budget')
    sector=st.slider('Maximum positions per sector',1,3,3,key='proposal_sector')
    # No private inputs are cached with public evidence.
    from stock_screen import stock_screen
    screen=stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)
    request=ProposalRequest(budget_cents=budget*100,maximum_stocks_per_sector=sector)
    result=stock_proposal(screen,request)
    st.session_state['_verified_stock_proposal']=result.model_dump(mode='json')
    st.warning('No verified purchase proposal is available. The research screen and synthetic lab are not substitutes for verified membership, security identity and valuation inputs.')
    st.metric('Cash left uncommitted',f'${result.cash_unallocated_cents/100:,.2f}')
    for blocker in result.global_blockers:st.write(blocker)
    with st.expander('Company exclusions and portfolio constraints'):
        st.dataframe(pd.DataFrame([{'Company':row.company,'Reason':reason} for row in result.findings for reason in row.blockers]),hide_index=True,width='stretch')
        st.json({'strategy_sha256':result.strategy_sha256,'public_release':result.source_release_id,
                 'market_snapshot':result.market_snapshot_sha256,'financial_sector_counts':result.sector_financial_pass_counts,
                 'note':'Financial peer counts do not establish verified eligible peer counts.'})
    st.caption('The existing exact percentile/sector-quota selection engine remains available in the synthetic lab. Real buy recommendations are blocked at the source verification boundary; changing cash or constraints cannot bypass it. No trading or borrowing is performed.')


def render_stock_replay():
    settings=get_settings();st.subheader('What if I had invested regularly?')
    st.caption('Replay installed historical observations. This evaluates a chosen security, not the recommendation strategy and not future returns.')
    if settings.market_data_mode!='local_research':st.info('Personal local market research must be enabled.');return
    directory=company_directory(settings.market_data_store)
    entries={row.issuer_key:row for row in directory.entries}
    if not entries:st.info('No installed companies are available.');return
    issuer=st.selectbox('Replay company',list(entries),format_func=lambda key:entries[key].name,key='replay_company')
    market=company_market(settings.market_data_store,settings.market_history_store,issuer,mode='local_research')
    if market.status=='choose_security':
        symbol=st.selectbox('Replay security',market.symbols,key='replay_security')
        market=company_market(settings.market_data_store,settings.market_history_store,issuer,symbol=symbol,mode='local_research')
    if market.status!='available':st.info('No unambiguous installed price history is available for this company.');return
    dates=[point.day for point in market.comparison.points]
    start,end=st.select_slider('Replay dates',options=dates,value=(dates[0],dates[-1]),key='replay_dates_'+issuer)
    a,b=st.columns(2)
    initial=a.number_input('Starting investment ($)',0,1000000,1000,100,key='replay_initial')
    monthly=b.number_input('Monthly deposit ($)',0,100000,100,50,key='replay_monthly')
    with st.expander('Return basis and fee assumptions'):
        basis=st.radio('Replay return basis',['Price only · split-adjusted','Provider-adjusted proxy · distributions included'],key='replay_basis')
        buy_fee=st.number_input('Fee per deposit (%)',0.0,5.0,0.0,.1,key='replay_buy_fee')
        account_fee=st.number_input('Additional annual account fee (%)',0.0,10.0,0.0,.1,key='replay_account_fee')
    if start==end or initial+monthly==0:st.info('Choose at least two dates and a nonzero investment amount.');return
    request=ReplayRequest(issuer_key=issuer,symbol=market.selected_symbol,start=start,end=end,initial_cents=initial*100,
        monthly_cents=monthly*100,basis='split_adjusted_price_only' if basis.startswith('Price') else 'provider_all_adjusted_proxy',
        purchase_fee_rate=Decimal(str(buy_fee))/100,annual_account_fee_rate=Decimal(str(account_fee))/100)
    result=replay_stock(settings.market_data_store,settings.market_history_store,request,mode='local_research')
    st.session_state['_stock_replay_result']=result.model_dump(mode='json')
    if result.status!='available':st.warning(result.reason);return
    a,b,c=st.columns(3)
    a.metric('Money deposited',f'${result.total_deposits_cents/100:,.0f}')
    b.metric(market.selected_symbol+' ending value',f'${result.company_ending_value:,.0f}')
    c.metric('SPY ending value',f'${result.benchmark_ending_value:,.0f}')
    st.caption('Starting cash buys at the first selected trading close. Monthly deposits start the following calendar month and buy at its first shared trading close. Fees are identical policies for both alternatives. Split-only mode excludes dividends; all-adjusted mode is an approximate distribution-adjusted proxy.')
    frame=pd.DataFrame([{'Date':str(row.day),'Company':float(row.company_value),'SPY':float(row.benchmark_value),'Deposits':row.cumulative_deposits_cents/100} for row in result.points])
    chart=alt.Chart(frame).transform_fold(['Company','SPY','Deposits'],as_=['Series','Value']).mark_line(strokeWidth=2.5,interpolate='linear').encode(
        x=alt.X('Date:T',scale=alt.Scale(type='utc'),title=None,axis=alt.Axis(grid=False)),
        y=alt.Y('Value:Q',title='Account value ($)',axis=alt.Axis(gridOpacity=.1)),
        color=alt.Color('Series:N',scale=alt.Scale(domain=['Company','SPY','Deposits'],range=['#289dff','#b8b1f1','#9aa9bd'])),
        strokeDash=alt.StrokeDash('Series:N',scale=alt.Scale(domain=['Company','SPY','Deposits'],range=[[],[6,4],[2,4]]),legend=None),
        tooltip=[alt.Tooltip('Date:T',format='%Y-%m-%d'),'Series:N',alt.Tooltip('Value:Q',format='$,.2f')]).properties(height=320).configure_view(stroke=None)
    st.altair_chart(chart,width='stretch',alt='Historical stock and SPY account values under matched deposits, with money deposited shown separately. Not a forecast.')
    st.caption(f'Net growth after modeled fees: {market.selected_symbol} {result.company_net_growth:,.2f} dollars; SPY {result.benchmark_net_growth:,.2f} dollars. Contributions are not investment returns.')
    with st.expander('Deposit ledger and evidence'):
        st.dataframe(pd.DataFrame([row.model_dump() for row in result.points]),hide_index=True,width='stretch')
        st.json({'inputs':request.model_dump(mode='json'),'snapshot_sha256':result.snapshot_sha256,'model_version':result.model_version})
    st.caption(result.notice)
