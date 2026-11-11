import os
import pytest
from streamlit.testing.v1 import AppTest
from test_experimental_basket import research_universe


@pytest.mark.skipif(os.getenv('RUN_UI_TESTS')!='1',reason='Enable UI tests')
def test_ranking_cost_panel_requires_consent_and_invalidates_on_source_edits(tmp_path,monkeypatch):
    import ranking_cost_ui
    from config import get_settings
    screen=research_universe(tmp_path)
    monkeypatch.setattr(ranking_cost_ui,'stock_screen',lambda *a,**k:screen)
    monkeypatch.setattr(ranking_cost_ui,'get_settings',lambda:get_settings().model_copy(update={'market_data_mode':'local_research'}))
    app=AppTest.from_string('from ranking_cost_ui import render_ranking_cost_evaluation\nrender_ranking_cost_evaluation()',default_timeout=30).run()
    assert not app.checkbox and not app.metric
    app.session_state['ranking_cost_panel']=True;app.run()
    assert not app.button and not app.metric
    app.checkbox(key='ranking_cost_consent').check().run()
    app.button(key='ranking_cost_run').click().run()
    assert not app.exception and app.metric
    assert any('not probabilities' in item.value for item in app.caption)
    costs=next(item.value for item in app.dataframe if 'Basket entry cost ($)' in item.value.columns)
    assert costs.iloc[-1]['Extra basket cost ($)']==9
    screen.universe.fresh=False;app.run()
    assert not app.metric
    app.button(key='ranking_cost_run').click().run()
    assert not app.exception and not app.metric and app.warning
    app.checkbox(key='ranking_cost_consent').uncheck().run()
    assert '_ranking_cost_result' not in app.session_state
