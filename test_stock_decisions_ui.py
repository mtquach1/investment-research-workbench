import os
import pytest
from streamlit.testing.v1 import AppTest
import stock_decisions_ui
from config import get_settings
from test_experimental_basket import research_universe


@pytest.mark.skipif(os.getenv('RUN_UI_TESTS') != '1', reason='Enable Streamlit UI tests')
def test_decision_journey_evidence_consent_constraints_and_download(tmp_path, monkeypatch):
    screen = research_universe(tmp_path)
    monkeypatch.setattr(stock_decisions_ui, 'stock_screen', lambda *args, **kwargs: screen)
    settings = get_settings().model_copy(update={'market_data_mode': 'local_research'})
    monkeypatch.setattr(stock_decisions_ui, 'get_settings', lambda: settings)
    app = AppTest.from_string('from stock_decisions_ui import render_stock_decisions\nrender_stock_decisions()').run(timeout=30)
    assert not app.exception
    assert len(app.dataframe) == 1  # evidence inventory before consent
    app.checkbox(key='workflow_consent').check().run(timeout=30)
    assert not app.exception
    assert app.metric[0].value == '10'
    assert any('private JSON' in element.label for element in app.get('download_button'))
    app.number_input(key='workflow_horizon').set_value(1).run(timeout=30)
    assert not app.exception and app.metric[0].value == '0'
    assert app.metric[2].value == '$10,000.00'
    app.checkbox(key='workflow_consent').uncheck().run(timeout=30)
    assert not app.exception and not app.metric


@pytest.mark.skipif(os.getenv('RUN_UI_TESTS') != '1', reason='Enable Streamlit UI tests')
def test_named_snapshot_save_compare_invalidation_and_session_isolation(tmp_path,monkeypatch):
    from privacy import clear_financial_session
    screen=research_universe(tmp_path)
    monkeypatch.setattr(stock_decisions_ui,'stock_screen',lambda *a,**k:screen)
    monkeypatch.setattr(stock_decisions_ui,'get_settings',lambda:get_settings().model_copy(update={'market_data_mode':'local_research'}))
    script='from stock_decisions_ui import render_stock_decisions\nrender_stock_decisions()'
    app=AppTest.from_string(script).run(timeout=30)
    app.checkbox(key='workflow_consent').check().run(timeout=30)
    app.session_state['decision_snapshot_panel']=True
    app.run(timeout=30)
    app.button(key='decision_snapshot_save').click().run(timeout=30)
    assert not app.exception and len(app.session_state['_decision_snapshots'])==1
    app.button(key='decision_snapshot_compare').click().run(timeout=30)
    assert not app.exception and app.session_state['_decision_snapshot_review']['review']['changes']==[]
    app.button(key='decision_snapshot_pdf_prepare').click().run(timeout=30)
    assert not app.exception and app.session_state['_decision_snapshot_pdf']['data'].startswith(b'%PDF-')
    app.radio(key='decision_snapshot_mode').set_value('Current editor settings').run(timeout=30)
    app.number_input(key='workflow_horizon').set_value(1).run(timeout=30)
    assert '_decision_snapshot_review' not in app.session_state
    assert '_decision_snapshot_pdf' not in app.session_state
    app.button(key='decision_snapshot_compare').click().run(timeout=30)
    assert app.session_state['_decision_snapshot_review']['review']['current']['outcome_counts']=={'pass':20}
    assert app.session_state['_decision_snapshots'][0]['assessment']['outcome_counts']['buy_candidate']==10
    other=AppTest.from_string(script).run(timeout=30)
    other.checkbox(key='workflow_consent').check().run(timeout=30)
    other.session_state['decision_snapshot_panel']=True;other.run(timeout=30)
    assert not other.exception and not other.session_state['_decision_snapshots']
    screen.universe.fresh=False
    app.run(timeout=30)
    assert not app.exception and '_decision_snapshot_review' not in app.session_state
    app.button(key='decision_snapshot_compare').click().run(timeout=30)
    assert app.session_state['_decision_snapshot_review']['review']['status']=='unavailable'
    clear_financial_session(app.session_state)
    assert '_decision_snapshots' not in app.session_state


@pytest.mark.skipif(os.getenv('RUN_UI_TESTS') != '1', reason='Enable Streamlit UI tests')
def test_restore_snapshot_ui_does_not_automatically_recompute_or_enable_consent(tmp_path,monkeypatch):
    from io import BytesIO
    import decision_snapshots_ui
    from test_decision_snapshots import saved
    screen,record=saved(tmp_path)
    monkeypatch.setattr(stock_decisions_ui,'stock_screen',lambda *a,**k:screen)
    monkeypatch.setattr(stock_decisions_ui,'get_settings',lambda:get_settings().model_copy(update={'market_data_mode':'local_research'}))
    monkeypatch.setattr(decision_snapshots_ui.st,'file_uploader',lambda *a,**k:BytesIO(record.model_dump_json().encode()))
    app=AppTest.from_string('from stock_decisions_ui import render_stock_decisions\nrender_stock_decisions()').run(timeout=30)
    assert not app.checkbox(key='workflow_consent').value and '_decision_snapshots' not in app.session_state
    app.checkbox(key='workflow_consent').check().run(timeout=30)
    app.session_state['decision_snapshot_panel']=True;app.run(timeout=30)
    app.button(key='decision_snapshot_restore').click().run(timeout=30)
    assert not app.exception and len(app.session_state['_decision_snapshots'])==1
    assert '_decision_snapshot_review' not in app.session_state
    app.button(key='decision_snapshot_compare').click().run(timeout=30)
    assert app.session_state['_decision_snapshot_review']['review']['current']['context']['new_cash_cents']==100003


@pytest.mark.skipif(os.getenv('RUN_UI_TESTS') != '1', reason='Enable Streamlit UI tests')
def test_snapshot_actions_keep_the_full_app_in_portfolio_workflow(tmp_path,monkeypatch):
    from pathlib import Path
    # Import every screen consumer before patching the provider. Otherwise a
    # first-time import can retain the fixture function after monkeypatch undo.
    import config,stock_screen,stock_screen_ui,stock_workflows_ui,experimental_basket_ui
    screen=research_universe(tmp_path)
    settings=get_settings().model_copy(update={'market_data_mode':'local_research',
        'market_data_store':tmp_path/'store','market_history_store':tmp_path/'history'})
    for module in (config,stock_decisions_ui,stock_workflows_ui,experimental_basket_ui):
        monkeypatch.setattr(module,'get_settings',lambda:settings)
    for module in (stock_screen,stock_screen_ui,stock_decisions_ui,experimental_basket_ui):
        monkeypatch.setattr(module,'stock_screen',lambda *a,**k:screen)
    app=AppTest.from_file(str(Path(__file__).with_name('streamlit_app.py')),default_timeout=30)
    app.session_state['workspace_section']='Stocks'
    app.session_state['stock_research_view']='Build portfolio'
    app.run()
    app.checkbox(key='workflow_consent').check().run()
    app.session_state['decision_snapshot_panel']=True;app.run()
    app.button(key='decision_snapshot_save').click().run()
    assert not app.exception and app.session_state['stock_research_view']=='Build portfolio'
    app.button(key='decision_snapshot_compare').click().run()
    assert not app.exception and app.session_state['stock_research_view']=='Build portfolio'
    assert app.session_state['_decision_snapshot_review']['review']['status']=='reviewed'
