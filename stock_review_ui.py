"""Decision follow-up and inspectable validation; session-only private state."""
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from collections import Counter
import altair as alt
import pandas as pd
import streamlit as st
import json
from pydantic import ValidationError
from config import get_settings
from stock_decision_review import basket_alternatives,basket_sensitivity,ExistingHolding,HoldingsReviewRequest,review_holdings
from paper_portfolio import PaperRecord,freeze_paper_basket,track_paper_record,restore_paper_record
from market_history import load_history
from financial_validation import validate_installed_financials


def _company(issuer):
    st.session_state['research_company_query']=issuer
    st.session_state['stock_research_view']='Company research'


def render_decision_review(screen,result):
    with st.expander('Alternatives and recommendation stability'):
        st.write('These are feasible one-stock swaps at the current scores. They explain the model’s tradeoff; they are not forecasts or personalized substitutes.')
        st.dataframe(pd.DataFrame(basket_alternatives(result)),hide_index=True,width='stretch')
        shock=st.slider('One-company valuation-yield stress (%)',1,50,10,key='decision_shock')
        signature=(result.model_dump_json(),shock)
        if st.session_state.get('_sensitivity_signature')!=signature:
            st.session_state.pop('_basket_sensitivity',None)
        if st.button('Check basket stability',key='run_basket_stability'):
            st.session_state['_basket_sensitivity']=basket_sensitivity(screen,result,shock=Decimal(shock)/100)
            st.session_state['_sensitivity_signature']=signature
        rows=st.session_state.get('_basket_sensitivity')
        if rows:
            changed=sum(row['Changed positions']>0 for row in rows)
            st.metric('Scenarios changing the basket',f'{changed} / {len(rows)}')
            st.caption('Each scenario changes both estimated valuation yields for one eligible company, holding all other evidence fixed. Scenario counts are not probabilities or confidence intervals; quality inputs and correlated market shocks are not tested here.')
            frame=pd.DataFrame(rows)
            chart=alt.Chart(frame).mark_bar(cornerRadiusEnd=3).encode(
                x=alt.X('Changed positions:O',title='Positions replaced out of ten'),y=alt.Y('count():Q',title='Stress scenarios'),
                color=alt.value('#7cebd3'),tooltip=[alt.Tooltip('Changed positions:O'),alt.Tooltip('count():Q',title='Scenarios')]).properties(height=210).configure_view(stroke=None)
            st.altair_chart(chart,width='stretch',alt='Count of one-company valuation-yield stress scenarios by number of replaced basket positions.')
            st.dataframe(frame,hide_index=True,width='stretch')
    with st.expander('How would this add to your existing holdings?'):
        st.caption('Optional manual amounts. Enter real holdings yourself; the Portfolio illustration is not imported. These values stay in this session.')
        saved=st.session_state.setdefault('_existing_review_rows',[{'Symbol':'','Current value ($)':0.0}])
        if 'existing_research_holdings' not in st.session_state:
            st.session_state['_existing_review_base']=[dict(row) for row in saved]
        entered=st.data_editor(pd.DataFrame(st.session_state['_existing_review_base']),num_rows='dynamic',hide_index=True,width='stretch',
            key='existing_research_holdings',column_config={'Symbol':st.column_config.TextColumn(max_chars=15),
                'Current value ($)':st.column_config.NumberColumn(min_value=0,max_value=1000000,step=1)})
        st.session_state['_existing_review_rows']=entered.to_dict('records')
        try:
            holdings=[]
            for row in entered.to_dict('records'):
                symbol=str(row['Symbol'] or '').strip().upper();amount=Decimal(str(row['Current value ($)'] or 0))
                if not symbol and not amount:continue
                if amount!=amount.quantize(Decimal('.01')):raise ValueError('Use cent amounts')
                holdings.append(ExistingHolding(symbol=symbol,amount_cents=int(amount*100)))
            review=review_holdings(result,HoldingsReviewRequest(holdings=holdings))
        except (ValidationError,ValueError,ArithmeticError):
            st.warning('Use unique ticker symbols and positive values with at most two decimal places, totaling no more than $1 million.')
        else:
            if holdings:
                st.dataframe(pd.DataFrame(review['rows']),hide_index=True,width='stretch')
                st.metric('Largest combined direct position',f"{review['largest_direct_weight']:.1f}%")
                if review['largest_direct_weight']>30:st.warning('A direct position exceeds 30% of the combined entered holdings and new cash. The paper basket does not automatically rebalance existing holdings.')
                st.caption(review['notice'])
            else:st.info('Enter holdings to inspect combined direct exposure. No account connection is needed.')
    with st.expander('Investigate a selected company'):
        lookup={row.issuer_key:row for row in result.selected}
        if st.session_state.get('decision_company') not in lookup:st.session_state.pop('decision_company',None)
        issuer=st.selectbox('Research next',list(lookup),format_func=lambda key:lookup[key].symbol+' · '+lookup[key].company,key='decision_company')
        st.write('Check the annual filing, fiscal period, profitability, valuation assumptions, price history and available event timeline. Missing news coverage does not mean no news or risks exist.')
        st.button('Open company evidence and events',on_click=_company,args=(issuer,),key='decision_open_company')
    with st.expander('Start a dated paper follow-up'):
        st.caption('Freeze today’s selection and assumptions. Entry is the first market session after today’s New York decision date, at its close. Returns appear only after those future sessions are installed. This is a buy-and-hold paper experiment, not brokerage execution.')
        cost=st.slider('Paper entry cost (basis points)',0,1000,10,key='paper_cost')
        st.caption('10 basis points = 0.10% of initial cash. The same portfolio-level entry cost applies to SPY. No future sale cost, slippage or tax is modeled.')
        records=st.session_state.setdefault('_paper_records',[])
        if st.button('Freeze this paper basket',disabled=len(records)>=10,key='freeze_paper'):
            now=datetime.now(ZoneInfo('UTC'))
            ciks={purchase.symbol:next(row.cik for row in screen.rows if row.issuer_key==purchase.issuer_key) for purchase in result.selected}
            try:record=freeze_paper_basket(result,now=now,security_ciks=ciks,entry_cost_bps=cost)
            except ValueError:st.warning('A current, complete basket is required. Refresh the research before freezing.')
            else:
                records.append(record.model_dump(mode='json'))
                st.success(f'Frozen. Earliest entry: {record.earliest_entry_date}. Open Validation & evaluation to follow it.')
        st.caption('Up to ten frozen records stay in this session. Download their JSON in Validation & evaluation to keep a personal copy; clearing the session removes them from the app.')


def render_validation_workspace():
    settings=get_settings()
    st.subheader('Evidence before performance claims')
    from stock_acceptance_ui import render_stock_evaluation
    render_stock_evaluation()
    from ranking_cost_ui import render_ranking_cost_evaluation
    render_ranking_cost_evaluation()
    st.info('Historical strategy evaluation is withheld: the installed sample lacks historical membership, delisted coverage and contemporaneous filing/valuation vintages. Today’s winners are never projected backward as strategy performance.')
    checks,tracking=st.tabs(['Calculation checks','Dated paper follow-up'])
    with checks:
        if settings.market_data_mode!='local_research':
            st.info('Enable personal local market research to inspect calculation checks and paper tracking.')
            return
        st.caption('An independent formula implementation checks arithmetic against the same installed normalized facts and prices. A pass does not verify the original source, tag mapping or financial assumptions.')
        if st.button('Reconcile installed calculations',key='reconcile_financials'):
            st.session_state['_financial_validation']=validate_installed_financials(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode).model_dump(mode='json')
        report=st.session_state.get('_financial_validation')
        if report:
            st.write('Available inputs reconcile.' if report['status']=='reconciled_available_inputs' else 'Some calculations disagree; inspect the mismatches.' if report['status']=='mismatch' else 'The installed evidence could not be reconciled. Refresh and try again.')
            st.caption('Audit as of '+str(report.get('checked_on'))+' · Rerun after refreshing data to check a new snapshot.')
            st.caption('Official-reference rows compare selected published Apple and Microsoft annual statement amounts. Other rows reconcile arithmetic over installed inputs. Neither establishes full-universe source verification.')
            counts=Counter(row['status'] for row in report['checks'])
            a,b,c=st.columns(3)
            a.metric('Arithmetic passes',counts['pass']);b.metric('Mismatches',counts['mismatch']);c.metric('Unavailable checks',counts['unavailable'])
            attention=st.checkbox('Show unavailable checks and mismatches only',value=True,key='audit_attention')
            issuers=sorted({row['issuer_key'] for row in report['checks']})
            issuer=st.selectbox('Audit issuer',['All issuers']+issuers,format_func=lambda key:report.get('company_names',{}).get(key,key),key='audit_issuer')
            visible=[row for row in report['checks'] if (not attention or row['status']!='pass') and (issuer=='All issuers' or row['issuer_key']==issuer)]
            st.dataframe(pd.DataFrame([{'Company':report.get('company_names',{}).get(row['issuer_key'],row['issuer_key']),'Check':row['metric'].replace('official_reference:','Official statement: ').replace('_',' '),
                'Result':row['status'].capitalize(),'Expected':row['expected'] if row['expected'] is not None else 'Unavailable',
                'Actual':row['actual'] if row['actual'] is not None else 'Unavailable','Formula':row['formula']} for row in visible]),hide_index=True,width='stretch')
            with st.expander('Calculation inputs and snapshot identifiers'):
                st.json({'public_release_id':report['public_release_id'],'market_snapshot_sha256':report['market_snapshot_sha256'],
                    'reference_cases_sha256':report.get('reference_cases_sha256'),'visible_checks':visible})
            for notice in report['limitations']:st.caption(notice)
            st.download_button('Download calculation audit',json.dumps(report,indent=2),'stock-calculation-audit.json','application/json')
    with tracking:
        records=st.session_state.setdefault('_paper_records',[])
        with st.expander('Restore a downloaded paper record'):
            st.caption('Restore your own JSON to this session. Imported timestamps are user-supplied and cannot prove when the basket was created. No file is sent to market providers.')
            upload=st.file_uploader('Frozen paper record JSON',type=['json'],key='paper_record_upload')
            if st.button('Restore paper record',disabled=upload is None or len(records)>=10,key='restore_paper_record'):
                payload=upload.getvalue()
                try:
                    restored=restore_paper_record(payload,now=datetime.now(ZoneInfo('UTC')),known_fingerprints=[item['fingerprint'] for item in records])
                except (ValueError,ValidationError):st.warning('Record could not be restored: check its format, checksum, creation date, size and whether it is already in this session.')
                else:
                    records.append(restored.model_dump(mode='json'))
                    st.session_state.setdefault('_paper_imported_fingerprints',[]).append(restored.fingerprint)
                    st.success('Restored as an unverified user-supplied record. Its creation time is not attested.')
        if not records:
            st.info('No frozen paper basket yet. Construct an experimental basket, then use Start a dated paper follow-up. No performance curve is invented while we wait for future prices.')
            return
        index=st.selectbox('Frozen paper basket',range(len(records)),format_func=lambda i:records[i]['created_at']+' · '+records[i]['fingerprint'][:8],key='paper_record_choice')
        record=PaperRecord.model_validate(records[index])
        if record.fingerprint in st.session_state.get('_paper_imported_fingerprints',[]):st.warning('Imported paper record: creation time and original selection are not independently attested. Treat results as a user-supplied scenario.')
        st.caption(f'Created {record.created_at.isoformat()} · Entry no earlier than {record.earliest_entry_date} · Model {record.basket.strategy_sha256[:12]}')
        st.download_button('Download frozen paper record',record.model_dump_json(indent=2),'frozen-paper-basket.json','application/json')
        st.caption('The export includes your paper budget and allocations. It is not uploaded or saved to the app database. Its checksum detects edits, but does not attest creation time.')
        if settings.market_data_mode!='local_research':st.info('Local market research must be enabled.');return
        try:
            digest,bundle=load_history(settings.market_history_store)
            result=track_paper_record(record,bundle,today=datetime.now(ZoneInfo('America/New_York')).date())
        except (ValueError,OSError):st.warning('Installed market history could not be verified.');return
        st.session_state['_paper_tracking_result']=result
        st.write(result['reason']);st.caption(result['notice']);st.caption('Evaluation snapshot: '+digest)
        if result['status']!='available':return
        a,b,c=st.columns(3)
        a.metric('Basket net gain / loss',f"${Decimal(result['basket_gain']):,.2f}")
        b.metric('SPY net gain / loss',f"${Decimal(result['benchmark_gain']):,.2f}")
        c.metric('Difference versus SPY',f"${Decimal(result['difference_dollars']):,.2f}")
        values=[{'Date':row['day'],'Series':name,'Value ($)':float(Decimal(row[key]))} for row in result['points'] for name,key in [('Paper basket after entry cost','basket_net'),('SPY after entry cost','benchmark_net')]]
        chart=alt.Chart(pd.DataFrame(values)).mark_line(strokeWidth=2.5).encode(x=alt.X('Date:T',title=None),y=alt.Y('Value ($):Q',scale=alt.Scale(zero=False)),
            color=alt.Color('Series:N',scale=alt.Scale(range=['#7cebd3','#b8b1f1']),legend=alt.Legend(orient='bottom',title=None)),tooltip=['Date:T','Series:N',alt.Tooltip('Value ($):Q',format=',.2f')]).properties(height=300).configure_view(stroke=None)
        st.altair_chart(chart,width='stretch',alt='Prospective frozen paper basket and matched SPY values after identical entry costs.')
        st.dataframe(pd.DataFrame(result['points']),hide_index=True,width='stretch')
