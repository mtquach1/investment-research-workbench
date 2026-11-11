import os
import pytest
from streamlit.testing.v1 import AppTest
from test_experimental_basket import research_universe


@pytest.mark.skipif(os.getenv('RUN_UI_TESTS')!='1',reason='Enable UI tests')
def test_software_checks_are_explicit_and_evidence_changes_clear_results(tmp_path,monkeypatch):
    import stock_acceptance_ui
    from config import get_settings
    screen=research_universe(tmp_path)
    monkeypatch.setattr(stock_acceptance_ui,'stock_screen',lambda *a,**k:screen)
    monkeypatch.setattr(stock_acceptance_ui,'get_settings',lambda:get_settings().model_copy(update={'market_data_mode':'local_research'}))
    app=AppTest.from_string('from stock_acceptance_ui import render_stock_evaluation\nrender_stock_evaluation()').run()
    assert not app.exception and not app.button
    app.session_state['stock_evaluation_panel']=True;app.run()
    assert not app.metric
    app.button(key='stock_evaluation_run').click().run()
    assert not app.exception and app.metric[0].value=='10'
    assert any('20 companies' in item.value and '10 / 10' in item.value for item in app.caption)
    assert any('Price observations:' in item.value for item in app.caption)
    assert any('Los Angeles' in item.value for item in app.caption)
    assert any('investment returns' in item.value for item in app.info)
    screen.universe.fresh=False;app.run()
    assert not app.metric
    app.button(key='stock_evaluation_run').click().run()
    assert not app.exception and app.metric[1].value=='7'
    assert any('incomplete' in item.value.lower() for item in app.warning)
