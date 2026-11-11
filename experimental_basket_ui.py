"""Opt-in paper basket; private budget is never cached or sent to providers."""
import altair as alt
import pandas as pd
import streamlit as st
from config import get_settings
from stock_screen import stock_screen
from experimental_basket import ExperimentalRequest,experimental_basket


def render_experimental_basket():
    settings=get_settings()
    st.subheader('Experimental paper-research basket')
    st.warning('Uses a limited ETF holdings proxy and estimated valuations. This is a separate experiment; verified recommendation gates remain unchanged. No evidence of outperformance or suitability is implied.')
    st.session_state.pop('_experimental_stock_basket',None)
    if settings.market_data_mode!='local_research':st.info('Personal local market research must be enabled.');return
    accepted=st.checkbox('I understand this uses proxy membership and valuation estimates',value=False,key='experimental_ack')
    if not accepted:
        st.info('Acknowledge the assumptions to inspect algorithm-selected research positions. The app will still refuse a basket if financial, peer, sector or funding constraints fail.')
        return
    screen=stock_screen(settings.market_data_store,settings.market_history_store,mode='local_research')
    a,b=st.columns(2)
    budget=a.number_input('Experimental cash budget ($)',0,1000000,10000,100,key='experimental_budget')
    sector=b.slider('Experimental sector position cap',1,3,3,key='experimental_sector')
    with st.expander('Purchase restrictions and historical risk'):
        symbols=sorted({ticker for row in screen.rows for ticker in row.tickers})
        excluded=st.multiselect('Exclude from the research basket',symbols,key='experimental_excluded')
        risk_limit=st.checkbox('Limit historical volatility',key='experimental_risk_on')
        volatility=st.slider('Experimental volatility ceiling (%)',0,200,50,1,key='experimental_volatility')
        st.caption('Restrictions apply before scoring and can change sector peer populations. The fixed strategy still needs ten stocks, at least five eligible sector peers, and no more than three positions per sector. No automatic relaxation.')
    from decimal import Decimal
    request=ExperimentalRequest(acknowledge_proxy_and_estimates=accepted,budget_cents=budget*100,
        maximum_stocks_per_sector=sector,excluded_symbols=excluded,maximum_volatility=Decimal(volatility)/100 if risk_limit else None)
    result=experimental_basket(screen,request)
    st.session_state['_experimental_stock_basket']=result.model_dump(mode='json')
    st.caption(f'ETF reference {result.universe_observed_on} · Research as of {result.checked_on} · Cash affects sizing, not the quality/value score.')
    if result.status!='research_basket':st.info(result.reason)
    else:
        st.success('Experimental basket constructed under the disclosed research assumptions.')
        a,b,c=st.columns(3)
        a.metric('Paper positions',len(result.selected))
        b.metric('Sector count',len({row.sector for row in result.selected}))
        c.metric('Cash unassigned',f'${result.cash_unallocated_cents/100:,.2f}')
        st.dataframe(pd.DataFrame([{'Stock':row.symbol,'Company':row.company,'Sector':row.sector,'Research score / 100':row.score*100,
            'Weight (%)':float(row.weight)*100,'Paper purchase ($)':row.purchase_cents/100,'Price date':row.price_date,
            'Indicative fractional shares':float(row.illustrative_fractional_shares)} for row in result.selected]),hide_index=True,width='stretch',
            column_config={'Research score / 100':st.column_config.NumberColumn(format='%.2f'),'Paper purchase ($)':st.column_config.NumberColumn(format='$%.2f'),
                'Indicative fractional shares':st.column_config.NumberColumn(format='%.6f')})
        st.caption('Scores measure relative accounting quality and estimated valuation within eligible sectors, not expected percentage returns. Purchases assume fractional-dollar positions, no fees and no existing holdings. Indicative shares are not executable orders.')
        selected={row.issuer_key for row in result.selected}
        contributions=pd.DataFrame([{'Stock':row.symbol,'Feature':name.replace('_',' '),'Score points':value*100}
            for row in result.findings if row.issuer_key in selected for name,value in row.contributions.items()])
        st.markdown('**What contributes to each stock’s score?**')
        chart=alt.Chart(contributions).mark_bar(cornerRadiusEnd=3).encode(
            y=alt.Y('Stock:N',title=None,sort='-x',axis=alt.Axis(labelOverlap=False)),x=alt.X('Score points:Q',stack='zero',scale=alt.Scale(domain=[0,100]),axis=alt.Axis(gridOpacity=.1)),
            color=alt.Color('Feature:N',scale=alt.Scale(range=['#7cebd3','#b8b1f1','#6fb4ed','#f2ba80','#ed91b3']),legend=alt.Legend(orient='bottom',columns=2,title=None,labelLimit=240)),
            tooltip=['Stock:N','Feature:N',alt.Tooltip('Score points:Q',format='.2f')]).properties(height=310).configure_view(stroke=None)
        st.altair_chart(chart,width='stretch',alt='Experimental score contributions from five equally weighted quality/value percentile features. Score points are not returns.')
        st.download_button('Download research snapshot (JSON)',result.model_dump_json(indent=2),file_name='experimental-paper-basket.json',mime='application/json')
        from stock_review_ui import render_decision_review
        render_decision_review(screen,result)
    with st.expander('Selection, exclusions and assumptions'):
        st.write('Five features each receive 20% weight: return on assets, operating margin, free cash flow margin, estimated earnings yield and estimated free cash flow yield. Exact tied-rank percentiles are computed within qualifying sectors. The algorithm maximizes total score under the sector quota; ties use issuer and security identifiers.')
        st.dataframe(pd.DataFrame([{'Company':row.company,'Stock':row.symbol or 'Unresolved','Score':row.score,'Selected':row.selected,
            'Reason':'; '.join(row.reasons) or 'Meets the research rules'} for row in result.findings]),hide_index=True,width='stretch')
        st.json({'research_qualified_sector_counts':result.qualified_sector_counts,'strategy_sha256':result.strategy_sha256,
            'public_release_id':result.public_release_id,'market_snapshot_sha256':result.market_snapshot_sha256,
            'universe_sha256':result.universe_sha256,'inputs':request.model_dump(mode='json')})
    st.caption(result.notice)
