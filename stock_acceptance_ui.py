"""Optional evidence-bound software evaluation, separate from investment returns."""
import hashlib
import pandas as pd
import streamlit as st
from config import get_settings
from public_data_store import canonical_bytes
from stock_screen import stock_screen
from stock_acceptance import evaluate_stock_workflow

FINDINGS={
    'financials':'Financial rules not met', 'financial_inputs':'Financial inputs missing',
    'financial_basis':'Financial dates or filing evidence need review',
    'quality_features':'Profitability measures missing', 'valuation':'Valuation estimate unavailable',
    'valuation_yields':'Positive valuation measures unavailable',
    'peer_evidence':'Too few comparable companies', 'ambiguous_identity':'Stock identifier not uniquely matched',
    'filing_class_conflict':'Share-class evidence conflicts', 'risk_history':'Price history incomplete',
    'basket_infeasible':'Ten-stock rules cannot be satisfied', 'price':'Price evidence unavailable',
}


def render_stock_evaluation():
    panel=st.expander('Check the connected stock workflow',key='stock_evaluation_panel',on_change='rerun')
    if not panel.open:return
    with panel:
        st.caption('Runs ten software checks with fixed example amounts, not your holdings. No source refreshes, database writes or trades. This is separate from investment performance.')
        settings=get_settings()
        if settings.market_data_mode!='local_research':
            st.info('Enable local research to check the installed stock workflow.')
            return
        screen=stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)
        signature=hashlib.sha256(canonical_bytes(screen.model_dump(mode='json'))).hexdigest()
        if st.session_state.get('_stock_evaluation_signature')!=signature:
            st.session_state.pop('_stock_evaluation',None)
            st.session_state['_stock_evaluation_signature']=signature
        if st.button('Run example workflow checks',key='stock_evaluation_run'):
            st.session_state['_stock_evaluation']=evaluate_stock_workflow(screen)
        report=st.session_state.get('_stock_evaluation')
        if report is None:return
        passed=sum(item.status=='passed' for item in report.checks)
        blocked=sum(item.status=='blocked' for item in report.checks)
        failed=sum(item.status=='failed' for item in report.checks)
        a,b,c=st.columns(3)
        a.metric('Checks passed',passed)
        b.metric('Checks blocked by missing inputs',blocked)
        c.metric('Software checks failed',failed)
        st.caption(f'Checked {report.checked_on} (Los Angeles calendar date) · A check date does not make installed observations fresh.')
        inputs=report.input_summary
        candidates=str(inputs.candidate_count)+' / 10' if inputs.candidate_count is not None else 'not assessed'
        st.caption(f'Reference age policy: {"current" if inputs.references_fresh else "needs newer evidence"} · {inputs.company_count} companies · Experimental candidates: {candidates}.')
        st.caption(f'Price observations: {inputs.oldest_price_date or "unavailable"} to {inputs.newest_price_date or "unavailable"}. Dates cover available company prices; the range does not verify every company’s evidence.')
        if inputs.blocking_reason_counts:
            with st.expander('What is limiting the candidate list?'):
                st.dataframe(pd.DataFrame([{'Evidence or policy finding':FINDINGS.get(key,key.replace('_',' ')),
                    'Company count':value} for key,value in inputs.blocking_reason_counts.items()]),
                    hide_index=True,width='stretch')
                st.caption('A company can have multiple findings. Counts are not investment confidence or probabilities. Inspect the company assessment for the full explanation.')
                st.caption('The current strategy needs ten stocks, at most three per sector, and at least five qualified companies within a scored sector. Fresh prices alone do not guarantee enough candidates.')
        if report.status=='incomplete':
            st.warning('Workflow evaluation incomplete. Inspect reference dates and missing company evidence in the Research screen, then rerun. Passing safety checks does not complete the blocked paths.')
        elif report.status=='failed':
            st.error('A software check failed. Do not treat this workflow evaluation as accepted; inspect local test results.')
        else:st.success('All ten example checks passed for this installed evidence. Broader release acceptance remains unfinished.')
        st.info('These checks measure software behavior, not investment returns. Source accuracy, public-data rights, real beginner tasks and deployment still need separate acceptance.')
        st.dataframe(pd.DataFrame([{'Check':item.title,'Result':item.status.capitalize(),
            'What this means':item.detail} for item in report.checks]),hide_index=True,width='stretch')
        st.download_button('Download workflow checks (JSON)',report.model_dump_json(indent=2),
            file_name='stock-workflow-checks.json',mime='application/json')
        with st.expander('Scope and evidence fingerprints'):
            st.caption(report.notice)
            st.json(report.model_dump(mode='json',exclude={'checks','notice'}))
