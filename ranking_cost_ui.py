"""Beginner-first ranking scenarios and cost-only comparisons."""
import hashlib
import pandas as pd
import streamlit as st
from config import get_settings
from public_data_store import canonical_bytes
from stock_screen import stock_screen
from experimental_basket import ExperimentalRequest
from ranking_cost_evaluation import evaluate_ranking_costs


def render_ranking_cost_evaluation():
    panel=st.expander('How sensitive are the rankings, and what could entry cost?',key='ranking_cost_panel',on_change='rerun')
    if not panel.open:return
    with panel:
        st.caption('Fixed example: $1,000.03 starting cash. Tests ranking behavior and assumed purchase costs; no future prices, returns or trades.')
        settings=get_settings()
        if settings.market_data_mode!='local_research':
            st.info('Enable local research to inspect installed ranking and cost examples.');return
        if not st.checkbox('Use proxy membership and estimated valuations for these examples',key='ranking_cost_consent'):
            st.session_state.pop('_ranking_cost_result',None);return
        screen=stock_screen(settings.market_data_store,settings.market_history_store,mode=settings.market_data_mode)
        request=ExperimentalRequest(acknowledge_proxy_and_estimates=True,budget_cents=100003)
        signature=hashlib.sha256(canonical_bytes({'screen':screen.model_dump(mode='json'),
            'inputs':request.model_dump(mode='json')})).hexdigest()
        if st.session_state.get('_ranking_cost_signature')!=signature:
            st.session_state.pop('_ranking_cost_result',None)
            st.session_state['_ranking_cost_signature']=signature
        if st.button('Evaluate ranking and entry-cost examples',key='ranking_cost_run'):
            try:st.session_state['_ranking_cost_result']=evaluate_ranking_costs(screen,request)
            except (ValueError,ArithmeticError):
                st.session_state.pop('_ranking_cost_result',None)
                st.warning('The examples could not be evaluated. Inspect installed evidence and local tests.')
        result=st.session_state.get('_ranking_cost_result')
        if result is None:return
        if result.status!='evaluated':st.warning(result.reason);return
        a,b=st.columns(2)
        a.metric('Fewest original stocks retained',f'{result.minimum_retained} / 10')
        b.metric('Scenarios changing the basket',f'{result.scenarios_with_changes} / {len(result.sensitivity)}')
        st.caption(f'Checked {result.checked_on} (Los Angeles date). Both valuation-yield estimates move ±10% for one scored company at a time; prices and quality measures stay fixed. These are chosen scenarios, not probabilities or forecasts.')
        if not result.row_order_invariant or not result.uniform_yield_scale_invariant:
            st.error('A ranking consistency check failed. Inspect the detailed checks before relying on this evaluation.')
        st.markdown('**What might entering the basket cost?**')
        st.caption('Same starting cash and fee policy for ten stock purchases versus one SPY purchase. Percentage costs use starting cash and round once to the nearest cent, half up. Assumptions are not broker quotes.')
        st.dataframe(pd.DataFrame([{'Assumption':row.label,
            'Basket entry cost ($)':row.basket_cost_cents/100,
            'SPY entry cost ($)':row.benchmark_cost_cents/100,
            'Basket capital after cost ($)':row.basket_capital_cents/100 if row.basket_capital_cents is not None else None,
            'SPY capital after cost ($)':row.benchmark_capital_cents/100 if row.benchmark_capital_cents is not None else None,
            'Extra basket cost ($)':row.extra_basket_cost_cents/100,'State':row.status} for row in result.costs]),
            hide_index=True,width='stretch')
        st.info('This compares entry costs, not investment gains. Actual fees, spreads, taxes, sale costs and later deposits are not modeled. Original purchase proposals are not rewritten.')
        with st.expander('Ranking checks and exact scenario changes'):
            st.write(f'Company score total (0–10): strategy {result.strategy_score_total:.4f}; alphabetical baseline {result.alphabetical_score_total:.4f}.')
            st.caption('The alphabetical baseline uses the same qualified companies and sector cap, ignoring scores. A higher score total follows the ranking objective; it does not establish higher returns.')
            st.write(f'Input-order check: {"passes" if result.row_order_invariant else "fails"}. Scaling all yield estimates equally by ±10%: {"unchanged basket" if result.uniform_yield_scale_invariant else "changed basket"}.')
            st.dataframe(pd.DataFrame(result.sensitivity),hide_index=True,width='stretch')
        st.download_button('Download ranking and cost evaluation (JSON)',result.model_dump_json(indent=2),
            file_name='experimental-ranking-entry-costs.json',mime='application/json')
        with st.expander('Scope and evidence fingerprints'):
            st.caption(result.notice)
            st.json(result.model_dump(mode='json',include={'model_version','strategy_sha256','public_release_id',
                'market_snapshot_sha256','universe_sha256','listing_reference_hashes'}))
