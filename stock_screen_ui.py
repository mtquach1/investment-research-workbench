"""Dated sector reference, valuation context and strict selection readiness."""

from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import altair as alt
from decimal import Decimal
from stock_metrics import ScreenFilters,filter_screen
import streamlit as st

from config import get_settings
from stock_screen import stock_screen
from research_language import (FINANCIAL_STATES,PRICE_STATES,HISTORY_STATES,VALUATION_STATES,TERMS,render_term_guide)


@st.cache_data(ttl=60,show_spinner=False)
def _screen(public_root,history_root,public_revision,market_revision,day):
    return stock_screen(public_root,history_root,mode="local_research",today=day)


def _open_company(issuer):
    st.session_state["research_company_query"]=issuer
    st.session_state["stock_research_view"]="Company research"


def open_screen(issuer):
    st.session_state["stock_research_view"]="Research screen"
    st.session_state["screen_sectors"]=[]
    st.session_state["screen_financial_pass"]=False
    st.session_state["screen_inspector"]=issuer
    for key in ("screen_use_quality","screen_use_growth","screen_use_risk","screen_use_estimated_value"):
        st.session_state[key]=False


def render_stock_screen():
    settings=get_settings()
    if settings.market_data_mode!="local_research":
        st.info("This screen combines local-use sector references and market data. Enable personal local research to inspect installed coverage.")
        return
    def revision(root):
        try:return (Path(root)/"CURRENT.json").stat().st_mtime_ns
        except OSError:return None
    result=_screen(str(settings.market_data_store),str(settings.market_history_store),revision(settings.market_data_store),
                   revision(settings.market_history_store),datetime.now(ZoneInfo("America/Los_Angeles")).date())
    if result.status!="available":
        st.warning("Research coverage is unavailable or could not be verified. No ranking is inferred.")
        return
    st.caption('Compare businesses → check the evidence → explore a research basket')
    render_term_guide('screen_term_guide')
    st.caption(f"Reference list: IVV fund holdings dated {result.universe.observed_on}. This is a substitute reference list, not verified official S&P 500 membership.")
    if not result.universe.fresh:st.warning("The sector/universe reference is stale or undated. It cannot pass the current sector gate.")
    from reference_refresh_ui import render_reference_status
    render_reference_status(settings.market_data_store)
    a,b,c=st.columns(3)
    a.metric("Companies with financial data",len(result.rows),help='Companies currently loaded, not complete S&P 500 coverage.')
    b.metric("Meet financial rules",sum(row.financial_status=="pass" for row in result.rows),help='These companies pass the supported financial checks. That does not make them buy recommendations.')
    c.metric("Have valuation estimates",sum(row.valuation.status=="estimated" for row in result.rows),help='Usable estimates based on dated shares and prices. Current market value and all share classes remain unverified.')
    st.info("Use this page to understand a business and its missing data. Passing a check is not a recommendation to buy.")
    explore,coverage=st.tabs(["Explore companies","Coverage & evidence"])
    with explore:_render_explorer(result)
    with coverage:_render_coverage(result)


def _render_explorer(result):
    left,right=st.columns([2,1])
    with left:
        sectors=st.multiselect("Business sector",sorted({row.sector for row in result.rows if row.sector}),key="screen_sectors",help=TERMS['sector'][1])
    with right:
        passed=st.checkbox("Only companies meeting financial rules",key="screen_financial_pass")
    with st.expander("Financial and risk filters"):
        st.caption("Only active thresholds exclude companies. Missing or stale values cannot pass an active filter. These research filters do not change strategy weights or enable recommendations.")
        quality=st.checkbox("Apply profitability and leverage thresholds",key="screen_use_quality")
        roa=st.slider("Minimum return on assets (%)",-100.0,100.0,0.0,1.0,key="screen_roa",help="Annual profit divided by average beginning/end assets. This measures accounting profitability, not stock returns.")
        margin=st.slider("Minimum operating margin (%)",-100.0,100.0,0.0,1.0,key="screen_margin",help="Operating income divided by annual revenue.")
        fcf=st.slider("Minimum free cash flow margin (%)",-100.0,100.0,0.0,1.0,key="screen_fcf",help="Operating cash flow minus cash capital expenditure, divided by revenue.")
        leverage=st.slider("Maximum liabilities / assets (%)",0.0,200.0,85.0,1.0,key="screen_leverage",help="All reported liabilities divided by ending assets; this is broader than interest-bearing debt.")
        growth=st.checkbox("Apply annual revenue growth threshold",key="screen_use_growth")
        revenue=st.slider("Minimum annual revenue growth (%)",-100.0,200.0,0.0,1.0,key="screen_growth",help="Latest reported annual revenue versus the prior comparable year in the current snapshot. Not TTM or point-in-time backtest data.")
        risk=st.checkbox("Apply historical risk thresholds",key="screen_use_risk")
        volatility=st.slider("Maximum annualized volatility (%)",0.0,200.0,50.0,1.0,key="screen_vol",help="Historical daily fluctuations on an annual scale. A threshold is not a forecast or a guaranteed loss limit.")
        loss=st.slider("Maximum historical drawdown loss (%)",0.0,100.0,50.0,1.0,key="screen_drawdown",help="Largest peak-to-trough decline within the installed window. This uses the full installed history, independent of the company chart's selected dates.")
        value=st.checkbox("Use estimated valuation as a research filter",key="screen_use_estimated_value")
        earnings=st.slider("Minimum estimated annual earnings yield (%)",-100.0,100.0,2.0,.5,key="screen_earnings",help="Reported annual net income / filing-based estimated equity value. It is not a verified current yield, a dividend payment or a forecast return.")
    pct=lambda number:Decimal(str(number))/100
    criteria=ScreenFilters(sectors=sectors,financial_pass_only=passed,
        minimum_roa=pct(roa) if quality else None,minimum_operating_margin=pct(margin) if quality else None,
        minimum_fcf_margin=pct(fcf) if quality else None,maximum_liabilities_to_assets=pct(leverage) if quality else None,
        minimum_revenue_growth=pct(revenue) if growth else None,maximum_volatility=pct(volatility) if risk else None,
        maximum_drawdown_loss=pct(loss) if risk else None,minimum_estimated_earnings_yield=pct(earnings) if value else None,
        allow_valuation_estimates=value)
    filtered=filter_screen(result,criteria)
    st.session_state['_stock_filter_result']=filtered.model_dump(mode='json')
    included=set(filtered.included_issuer_keys)
    rows=[row for row in result.rows if row.issuer_key in included]
    sort_fields={"Company":None,"Return on assets":"return_on_assets","Operating margin":"operating_margin",
        "FCF margin":"free_cashflow_margin","Revenue growth":"revenue_growth","Liabilities / assets":"liabilities_to_assets",
        "Historical volatility":"annualized_volatility"}
    sort=st.selectbox("Sort research results",list(sort_fields),key="screen_sort")
    field=sort_fields[sort]
    def ordering(row):
        metric=row.metrics.get(field) if field else None
        amount=metric.value if metric and metric.status=='available' else None
        return (amount is None,(amount if field in ('liabilities_to_assets','annualized_volatility') else -amount) if amount is not None else 0,row.company)
    rows.sort(key=ordering if field else lambda row:row.company)
    if filtered.exclusions:
        with st.expander(f"Why {len(filtered.exclusions)} companies were excluded"):
            names={row.issuer_key:row.company for row in result.rows}
            st.dataframe(pd.DataFrame([{'Company':names[item.issuer_key],'Reason':reason} for item in filtered.exclusions for reason in item.reasons]),hide_index=True,width='stretch')
    def metric_value(row,key):
        metric=row.metrics.get(key)
        return float(metric.value) if metric and metric.status=='available' and metric.value is not None else None
    st.caption(f"Showing {len(rows)} of {len(result.rows)} loaded companies. Other entries in the reference list have not all been analyzed.")
    st.dataframe(pd.DataFrame([{"Company":row.company,"Sector":row.sector or "Unverified","Annual period":str(row.financial_period or "Unavailable"),
        "Financial checks":FINANCIAL_STATES[row.financial_status],"Price data":PRICE_STATES[row.price_status],"Price history":HISTORY_STATES[row.history_count_status],
        "Return on assets":metric_value(row,"return_on_assets"),"Operating margin":metric_value(row,"operating_margin"),
        "FCF margin":metric_value(row,"free_cashflow_margin"),"Revenue growth":metric_value(row,"revenue_growth"),"Valuation basis":VALUATION_STATES[row.valuation.status][0],"Annual earnings yield estimate":float(row.valuation.annual_earnings_yield_estimate) if row.valuation.annual_earnings_yield_estimate is not None else None}
        for row in rows]),hide_index=True,width="stretch",column_config={name:st.column_config.NumberColumn(format="percent") for name in ("Annual earnings yield estimate","Return on assets","Operating margin","FCF margin","Revenue growth")})
    st.caption('Need help with a column? Open “Explain a term” above. Missing data is not the same as failing a financial rule.')
    with st.expander('Compare up to three companies'):
        choices={item.issuer_key:item for item in rows}
        if 'screen_compare' in st.session_state:
            st.session_state['screen_compare']=[key for key in st.session_state['screen_compare'] if key in choices]
        selected_comparison=st.multiselect('Companies to compare',list(choices),format_func=lambda key:choices[key].company,max_selections=3,key='screen_compare')
        if selected_comparison:
            st.caption('Same metric definitions and snapshot date; latest annual fiscal periods can differ. Period ends and availability are shown. This is descriptive company research, not a ranking or a matched-period performance test.')
            comparison_rows=[]
            for key in selected_comparison:
                item=choices[key]
                comparison_rows.append({'Company':item.company,'Annual period':str(item.financial_period),'Sector':item.sector or 'Unavailable',
                    **{name.replace('_',' '):f'{metric.value:.2%}' if metric.value is not None and metric.status=='available' else metric.status for name,metric in item.metrics.items()},
                    'Valuation basis':item.valuation.status,'Financial checks':item.financial_status})
            st.dataframe(pd.DataFrame(comparison_rows),hide_index=True,width='stretch')
    plot=[{"Company":row.company,"Operating margin":metric_value(row,"operating_margin"),"Return on assets":metric_value(row,"return_on_assets"),"Sector":row.sector or 'Unverified'} for row in rows]
    plot=[item for item in plot if item['Operating margin'] is not None and item['Return on assets'] is not None]
    if plot:
        with st.expander("Compare profitability visually"):
            st.caption("Each dot is a company matching your filters. Higher/right means more accounting profit—not a predicted stock return. Hover to identify a company.")
            chart=alt.Chart(pd.DataFrame(plot)).mark_circle(size=110,opacity=.8).encode(
                x=alt.X('Operating margin:Q',axis=alt.Axis(format='.0%',gridOpacity=.1)),
                y=alt.Y('Return on assets:Q',axis=alt.Axis(format='.0%',gridOpacity=.1)),color=alt.Color('Sector:N',legend=alt.Legend(orient='bottom',columns=2,title=None,labelLimit=240)),
                tooltip=['Company','Sector',alt.Tooltip('Operating margin:Q',format='.2%'),alt.Tooltip('Return on assets:Q',format='.2%')]).properties(height=300).configure_view(stroke=None)
            st.altair_chart(chart,width='stretch',alt='Accounting profitability comparison for the filtered company sample, not expected stock returns.')
    if not rows:
        st.info("No installed issuer matches these research filters. No constraints were relaxed.")
        return
    lookup={row.issuer_key:row for row in rows}
    if st.session_state.get("screen_inspector") not in lookup:
        st.session_state.pop("screen_inspector",None)
    selected=st.selectbox("Choose a company to understand",list(lookup),format_func=lambda key:lookup[key].company,key="screen_inspector")
    row=lookup[selected];estimate=row.valuation
    with st.container(border=True):
        st.subheader(row.company)
        st.caption(f"Financial year ended {row.financial_period or 'date unavailable'} · {row.sector or 'Business sector unavailable'}")
        checks=st.columns(3)
        for column,title,label in zip(checks,('Business checks','Price data','Price history'),
            (FINANCIAL_STATES[row.financial_status],PRICE_STATES[row.price_status],HISTORY_STATES[row.history_count_status])):
            with column:
                with st.container(border=True):st.caption(title);st.markdown('**'+label+'**')
        state_title,state_meaning=VALUATION_STATES[estimate.status]
        st.markdown('**'+state_title+'**')
        st.caption(state_meaning)
        if estimate.status=="estimated":
            first,second,third=st.columns(3)
            first.metric("Estimated total share value",f"${estimate.market_cap_estimate/1000000000:,.1f}B",help='Estimated company-wide value of reported common shares, not the price of one share. Share-class coverage remains unverified. B means billion dollars.')
            second.metric("Profit relative to estimated value",f"{estimate.annual_earnings_yield_estimate:.2%}" if estimate.annual_earnings_yield_estimate is not None else "Unavailable",help=TERMS['earnings_yield'][1]+' '+TERMS['earnings_yield'][3])
            third.metric("Cash relative to estimated value",f"{estimate.annual_fcf_yield_estimate:.2%}" if estimate.annual_fcf_yield_estimate is not None else "Unavailable",help=TERMS['free_cashflow_yield'][1]+' '+TERMS['free_cashflow_yield'][3])
        with st.expander("Metric values, availability and definitions"):
            st.caption(f'{row.eligible_financial_sector_peers} financially passing sector peers in the installed sample; this is not a count of fully verified investment candidates.')
            if row.provider_sector!=row.sector:st.caption(f'Provider sector label: {row.provider_sector or "Unavailable"} · Application mapping: {result.universe.sector_mapping_version}')
            st.dataframe(pd.DataFrame([{'Metric':name.replace('_',' '),'Value':f'{item.value:.2%}' if item.value is not None else 'Unavailable','Status':item.status,'Basis':item.basis} for name,item in row.metrics.items()]),hide_index=True,width='stretch')
            st.write(estimate.reason)
        if estimate.measured_on:
            st.caption(f"Shares counted {estimate.measured_on} · Price dated {estimate.price_date or 'unavailable'}")
            if estimate.price_date:
                st.caption(f'The share count describes {(estimate.price_date-estimate.measured_on).days} days before this price. It may have changed since then.')
        with st.expander('Trace the dates behind this estimate'):
            st.caption('Each date answers a different question. Downloading today does not update an older report or share count.')
            st.caption(f'Source download timestamp (UTC): {row.financial_source_retrieved_at.astimezone(timezone.utc).isoformat() if row.financial_source_retrieved_at else "Unavailable"}')
            st.write(f'Share filing date: {estimate.filed_on or "Unavailable"} · Split factor: {estimate.split_factor or "Unavailable"}')
            clocks=[('Fiscal year ended',row.financial_period,'Annual accounting period; not TTM.'),
                ('Shares measured',estimate.measured_on,'Date the reported point share count describes.'),
                ('Share filing published',estimate.filed_on,'Filing date; precise intraday release time is not established.'),
                ('Market quote observed',estimate.price_date,'Installed daily price observation.'),
                ('Source downloaded (UTC)',row.financial_source_retrieved_at.astimezone(timezone.utc).date() if row.financial_source_retrieved_at else None,'Retrieval date; cannot refresh an older observation.')]
            date_frame=pd.DataFrame([{'Evidence':label,'Date':str(day),'Date label':str(day),'Meaning':meaning} for label,day,meaning in clocks if day])
            if not date_frame.empty:
                timeline=alt.Chart(date_frame).mark_point(filled=True,size=100,color='#7cebd3').encode(
                    x=alt.X('Date:T',scale=alt.Scale(type='utc'),title='Evidence date',axis=alt.Axis(format='%b %Y',gridOpacity=.1)),
                    y=alt.Y('Evidence:N',sort=[item[0] for item in clocks],title=None,axis=alt.Axis(labelLimit=200)),
                    tooltip=['Evidence:N',alt.Tooltip('Date label:N',title='Date'),'Meaning:N']).properties(height=205).configure_view(stroke=None)
                st.altair_chart(timeline,width='stretch',alt='Dates of annual financials, share measurement, filing, market quote and source retrieval. New retrieval does not make old observations fresh.')
                st.dataframe(date_frame[['Evidence','Date','Meaning']],hide_index=True,width='stretch')
        with st.expander('Listing and share-class evidence'):
            st.caption('Independent listing metadata checks exact source symbols and exchange agreement. It does not establish official S&P membership, legal issuer/share-class identity or current issuer-wide equity value.')
            st.dataframe(pd.DataFrame([{'Ticker':symbol,'Listing check':item.status.replace('_',' '),'Security name':item.security_name or 'Unavailable',
                'Listing exchange':item.exchange or 'Unavailable','Reference date':str(item.observed_on or 'Unavailable'),'Type hint':item.security_kind_hint or 'Unavailable',
                'Reason':item.reason} for symbol,item in row.listing_evidence.items()]),hide_index=True,width='stretch')
            st.json({symbol:item.model_dump(mode='json') for symbol,item in row.listing_evidence.items()})
        with st.expander('What registered share class does the filing disclose?'):
            st.caption('A dated 10-K cover can corroborate a registered class. It does not establish every economic class, current share quantities, issuer-wide valuation or index membership.')
            st.dataframe(pd.DataFrame([{'Symbol':symbol,'Status':item.status.replace('_',' '),
                'Registered class':item.class_title or 'Unavailable','Filed':str(item.filed_on or 'Unavailable')}
                for symbol,item in row.filing_class_evidence.items()]),hide_index=True,width='stretch')
            for item in row.filing_class_evidence.values():
                if item.source_url:
                    st.caption(item.reason)
                    st.link_button('Open primary filing · '+item.symbol,item.source_url)
            with st.expander('Filing source hashes and evidence metadata'):
                st.json({symbol:item.model_dump(mode='json') for symbol,item in row.filing_class_evidence.items()})
        if row.class_share_ledger:
            render_class_share_ledger(row.class_share_ledger)
        with st.expander('Requirements for a verified recommendation'):
            st.caption('These checks describe evidence readiness. They do not predict returns.')
            st.dataframe(pd.DataFrame([{"Requirement":"Financial evidence","Result":FINANCIAL_STATES[row.financial_status]},
                {"Requirement":"Business sector in the substitute reference list","Result":{"pass":"Meets sector rule","fail":"Does not meet sector rule","unavailable":"Needs sector evidence"}[row.sector_status]},
                {"Requirement":"Recent price","Result":PRICE_STATES[row.price_status]},
                {"Requirement":"756 complete daily return observations","Result":HISTORY_STATES[row.history_count_status]},
                {"Requirement":"Verified current company share value","Result":"Not verified"},
                {"Requirement":"Official index membership and security identity","Result":"Not verified"}]),hide_index=True,width="stretch")
        if row.financial_reasons:
            with st.expander("Financial exclusions and missing evidence"):
                for reason in row.financial_reasons:st.write(reason)
        st.button("Open full company research",on_click=_open_company,args=(row.issuer_key,),key="screen_open_company")
        st.link_button("SEC issuer filings",f"https://www.sec.gov/edgar/browse/?CIK={row.cik}")
    with st.expander("Why the selection engine remains blocked"):
        for blocker in result.blockers:st.write(blocker)
        st.json({"strategy":result.strategy_id,"strategy_sha256":result.strategy_sha256,
            "public_release_id":result.public_release_id,"market_snapshot_sha256":result.market_snapshot_sha256,
            "universe_source_sha256":result.universe.source_sha256,"valuation_evidence":estimate.model_dump(mode="json")})


def render_class_share_ledger(ledger):
    with st.expander('Can this share count be matched to each share class?'):
        st.write('Class quantities are not reconciled. Verified company valuation remains unavailable.')
        point=ledger.share_observation
        label={'reported_unallocated':'Reported count · class assignment unknown','stale':'Old share measurement',
               'ambiguous':'Conflicting share counts','unavailable':'Share count unavailable'}[point.status]
        st.metric('Reported issuer count (shares)',f'{point.shares:,.0f}' if point.shares is not None else 'Unavailable')
        classes,assignment=st.columns(2)
        classes.metric('Tickers with filing-class evidence',sum(bool(item.filing_observations) for item in ledger.securities),
            help='Count of observed tickers with a filing title. This is not the number of all economic classes.')
        assignment.metric('Class quantities reconciled','Not yet')
        st.caption(f'{label} · Measured {point.measured_on or "unknown"} · Filed {point.filed_on or "unknown"} · Checked {ledger.checked_on}')
        st.caption('This count is shown once for the issuer. It is not assigned to every ticker or added again for each class. The 120-day age check here uses the check date; valuation estimates use the price date.')
        st.caption('Directory securities can include preferred shares, debt or warrants. Their presence does not establish another common-stock class.')
        historical_states={'matched_historical_statement':'Dated statement matches review','not_reviewed':'Not reviewed',
            'review_not_yet_available':'Review not available on check date','evidence_unavailable':'Needs corroborating evidence',
            'evidence_conflict':'Evidence differs from review'}
        st.dataframe(pd.DataFrame([{'Ticker':item.symbol,
            'Directory match':{'unique_issuer':'One issuer match','ambiguous_issuer':'Multiple issuer matches','filing_only':'Filing only'}[item.directory_status],
            'Registered class observations':'; '.join(observation.class_title+' (filed '+str(observation.filed_on)+')' for observation in item.filing_observations) or 'No filing evidence',
            'Current shares assigned':'Unknown',
            'Historical statement link':historical_states[item.historical_quantity.status] if item.historical_quantity else 'Not reviewed'} for item in ledger.securities],
            columns=['Ticker','Directory match','Registered class observations','Current shares assigned','Historical statement link']),hide_index=True,width='stretch')
        reviewed=[item for item in ledger.securities if item.historical_quantity and item.historical_quantity.review]
        if reviewed:
            with st.expander('What historical count has been matched to a class?'):
                st.caption('A dated statement link does not verify today’s class count or complete company valuation.')
                for item in reviewed:
                    match=item.historical_quantity;review=match.review
                    st.markdown('**'+item.symbol+' · '+historical_states[match.status]+'**')
                    if match.status=='matched_historical_statement':
                        st.metric('Historical statement count (shares)',f'{review.shares:,.0f}')
                        st.caption(f'Historical measurement: {review.measured_on} · Filed: {review.filed_on} · Review available: {review.reviewed_on}')
                        st.caption(f'This count describes {(ledger.checked_on-review.measured_on).days} days before the check date. It does not replace the latest issuer count above.')
                        st.link_button('Open matched primary filing · '+item.symbol,match.matched_source_url)
                    else:st.warning(match.reason)
                    with st.expander('Why this statement was linked · '+item.symbol):
                        st.write(review.review_basis.replace('$',r'\$'))
                        st.caption(review.statement_location)
                        st.caption('Economic rights, all economic/nontraded classes and intervening corporate actions still need review.')
        if ledger.filing_point_observations:
            with st.expander('Compare share counts reported inside the filings'):
                st.caption('These are older filing observations, not replacements for the latest issuer count above. Different dates, rounding or dimensions can explain different counts; no class quantities are added together.')
                show_all=st.checkbox('Include older periods and dimensional observations',key=f'ledger_share_history_{ledger.cik}')
                periods=[item.period_end for security in ledger.securities for item in security.filing_observations]
                cutoff=max(periods) if periods else ledger.checked_on
                observations=[item for item in ledger.filing_point_observations if show_all or (item.measured_on>=cutoff and not item.dimensions)]
                st.dataframe(pd.DataFrame([{'Count basis':'Filing cover' if item.tag.startswith('dei:') else 'Common shares outstanding',
                    'Measured':str(item.measured_on),'Reported count (shares)':f'{item.shares:,.0f}',
                    'Rounding (shares)':'Exact as tagged' if item.decimals=='INF' else f'{Decimal(10)**-int(item.decimals):,.0f}' if int(item.decimals)<=0 else '<1',
                    'Scope':'Dimensions present · unassigned' if item.dimensions else 'Issuer count · unassigned',
                    'Filed':str(item.filed_on)} for item in observations]),hide_index=True,width='stretch')
                st.caption('Rounding is the reported precision increment, not an error estimate. Optional source details retain exact tags, dimensions, scales and source hashes.')
        with st.expander('Why class coverage matters'):
            st.write(r'Example: if class A has 60 shares at \$10 and class B has 40 shares at \$20, their combined value is \$1,400. Multiplying all 100 shares by class A’s \$10 price gives \$1,000. A single ticker cannot establish which calculation applies.')
            for gap in ledger.gaps:st.write(gap)
        with st.expander('Share ledger sources and dates'):
            st.json(ledger.model_dump(mode='json'))


def _render_coverage(result):
    rows=result.security_coverage
    st.subheader('What has actually been checked?')
    st.caption('Every security in the dated ETF reference appears here, including unanalysed and unresolved rows. Exact ticker-to-issuer matching is not proof of a share class or S&P membership.')
    a,b,c=st.columns(3)
    a.metric('Reference securities',len(rows))
    b.metric('With financial research',sum(row.financials_installed for row in rows))
    c.metric('Exact ticker price series',sum(row.exact_symbol_history_installed for row in rows))
    st.caption('These counts refer to securities; multiple share classes can share one issuer’s financial statements. Price-series totals elsewhere include the SPY benchmark.')
    if result.listing_reference_hashes:
        from collections import Counter
        counts=Counter(row.listing.status.replace('_',' ') for row in rows)
        st.markdown('**Which listings agree with the issuer directory?**')
        chart=alt.Chart(pd.DataFrame([{'Listing check':key,'Securities':value} for key,value in counts.items()])).mark_bar(color='#7cebd3',cornerRadiusEnd=3).encode(
            x=alt.X('Securities:Q',axis=alt.Axis(tickMinStep=1,tickCount=6,gridOpacity=.12)),y=alt.Y('Listing check:N',sort='-x',title=None),tooltip=['Listing check:N','Securities:Q']).properties(height=200).configure_view(stroke=None)
        st.altair_chart(chart,width='stretch',alt='Independent listing cross-check coverage. A corroborated listing is not verified index membership or legal share-class identity.')
        st.caption('Exact official source aliases only; no punctuation replacements. Listing status concerns and source conflicts exclude experimental candidates when observed. Missing or stale listing coverage remains disclosed and cannot establish verified recommendations.')
    missing=st.checkbox('Show coverage gaps only',value=False,key='screen_coverage_gaps')
    visible=[row for row in rows if not missing or not (row.financials_installed and row.exact_symbol_history_installed and row.mapping_status=='exact_issuer_match')]
    st.dataframe(pd.DataFrame([{'Ticker':row.symbol,'Provider sector':row.provider_sector,'Issuer mapping':row.mapping_status,
        'CIK':str(row.cik) if row.cik else 'Unresolved','Financials installed':row.financials_installed,
        'Exact ticker history':row.exact_symbol_history_installed,'Listing cross-check':row.listing.status.replace('_',' '),
        'Listing name':row.listing.security_name or 'Unavailable','Listing date':str(row.listing.observed_on or 'Unavailable'),
        'Official membership':'Unverified','Current issuer valuation':'Unverified'} for row in visible]),hide_index=True,width='stretch')
    st.caption('Installed is a coverage flag, not a passing financial/risk result. Two share classes can share issuer statements while needing separate price/security evidence. Valuation estimates never satisfy verified-current-valuation gates.')
    for blocker in result.blockers:st.write(blocker)
    st.json({'checked_on':str(result.checked_on),'universe_observed_on':str(result.universe.observed_on),
        'universe_sha256':result.universe.source_sha256,'public_release_id':result.public_release_id,
        'market_snapshot_sha256':result.market_snapshot_sha256,'strategy_sha256':result.strategy_sha256,
        'listing_reference_hashes':result.listing_reference_hashes,
        'public_market_data_redistribution_allowed':False})
