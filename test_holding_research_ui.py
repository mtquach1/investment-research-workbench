import os
import pytest
from streamlit.testing.v1 import AppTest
from test_experimental_basket import research_universe
from test_holding_research import request


@pytest.mark.skipif(os.getenv('RUN_UI_TESTS')!='1',reason='Enable UI tests')
def test_guided_review_shows_exact_money_and_preserves_missing_evidence(tmp_path):
    screen=research_universe(tmp_path)
    app=AppTest.from_string('import streamlit as st\nfrom holding_research_ui import render_owned_holdings\nrender_owned_holdings(st.session_state["screen"],st.session_state["context"])')
    app.session_state['screen']=screen;app.session_state['context']=request().context
    app.run();assert not app.exception and not app.metric
    app.session_state['owned_holding_panel']=True;app.run()
    app.selectbox(key='owned_T00_reason').set_value('still_supported').run()
    app.checkbox(key='owned_T00_simulate').check().run()
    app.number_input(key='owned_T00_fee').set_value(5.03).run()
    app.checkbox(key='owned_T00_know_cost').check().run()
    app.number_input(key='owned_T00_cost').set_value(1200.0).run()
    assert not app.exception
    assert app.metric[1].value=='995.00' and app.metric[2].value=='-205.00'
    screen.universe.fresh=False;app.session_state['screen']=screen;app.run()
    assert not app.exception and any('Company evidence needed' in item.value for item in app.markdown)
    assert app.metric[1].value=='995.00'


@pytest.mark.skipif(os.getenv('RUN_UI_TESTS')!='1',reason='Enable UI tests')
def test_note_restore_is_explicit_resets_costs_and_survives_holding_switch(tmp_path, monkeypatch):
    from io import BytesIO
    import holding_research_ui
    from holding_notes import save_holding_note
    from holding_research import HoldingReviewInputs
    from stock_decisions import DecisionHolding
    from privacy import clear_financial_session
    screen=research_universe(tmp_path);ctx=request().context
    ctx.holdings.append(DecisionHolding(symbol='T01',value_cents=10000))
    note=save_holding_note(ctx,'T00',HoldingReviewInputs(reason_state='concerns',notes='Check next filing'),saved_on=screen.checked_on)
    monkeypatch.setattr(holding_research_ui.st,'file_uploader',lambda *a,**k:BytesIO(note.model_dump_json().encode()))
    app=AppTest.from_string('import streamlit as st\nfrom holding_research_ui import render_owned_holdings\nrender_owned_holdings(st.session_state["screen"],st.session_state["context"])')
    app.session_state['screen']=screen;app.session_state['context']=ctx
    app.session_state['owned_holding_panel']=True;app.run()
    assert app.text_area(key='owned_T00_notes').value==''  # uploading is not restoring
    app.checkbox(key='owned_T00_simulate').check().run()
    app.button(key='holding_note_restore').click().run()
    assert not app.exception
    assert app.text_area(key='owned_T00_notes').value=='Check next filing'
    assert app.selectbox(key='owned_T00_reason').value=='concerns'
    assert not app.checkbox(key='owned_T00_simulate').value
    assert any('unverified' in item.value for item in app.success)
    app.selectbox(key='owned_holding_symbol').set_value('T01').run()
    app.text_area(key='owned_T01_notes').set_value('Second holding').run()
    app.selectbox(key='owned_holding_symbol').set_value('T00').run()
    assert app.text_area(key='owned_T00_notes').value=='Check next filing'
    assert any(item.label=='Download personal note (restorable JSON)' for item in app.get('download_button'))
    # Current company conclusions are recomputed, never imported from the note.
    screen.universe.fresh=False;app.session_state['screen']=screen;app.run()
    assert any('Company evidence needed' in item.value for item in app.markdown)
    assert app.text_area(key='owned_T00_notes').value=='Check next filing'
    clear_financial_session(app.session_state)
    assert '_holding_note_drafts' not in app.session_state
