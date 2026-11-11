import os
import pytest
from streamlit.testing.v1 import AppTest
from test_experimental_basket import research_universe
from stock_decisions import DecisionContext


@pytest.mark.skipif(os.getenv('RUN_UI_TESTS') != '1', reason='Enable UI tests')
def test_preview_is_explicit_and_edits_invalidate_private_results(tmp_path):
    app = AppTest.from_string('import streamlit as st\nfrom stock_monthly_ui import render_monthly_contribution\nrender_monthly_contribution(st.session_state["screen"],st.session_state["context"])')
    app.session_state['screen'] = research_universe(tmp_path)
    app.session_state['context'] = DecisionContext(acknowledge_experimental=True, monthly_contribution_cents=100003)
    app.run(); assert not app.exception and not app.metric
    app.session_state['monthly_contribution_panel'] = True; app.run()
    app.button(key='monthly_preview').click().run()
    assert not app.exception
    assert [item.value for item in app.metric] == ['$1,000.03', '$1,000.00', '$0.03']
    app.session_state['context'] = DecisionContext(acknowledge_experimental=True, monthly_contribution_cents=50000)
    app.run(); assert not app.metric
    app.button(key='monthly_preview').click().run()
    assert app.metric[0].value == '$500.00'
    screen = app.session_state['screen']; screen.universe.fresh = False
    app.session_state['screen'] = screen; app.run()
    assert not app.metric
    app.button(key='monthly_preview').click().run()
    assert not app.exception and any('stale' in item.value for item in app.warning)
