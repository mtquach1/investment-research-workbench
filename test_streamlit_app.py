"""Streamlit page smoke tests, enabled by CI in an async-capable environment."""

import os
from pathlib import Path
import socket
from threading import Thread
from time import monotonic, sleep

import pytest
from streamlit.testing.v1 import AppTest
import uvicorn

import config
import main
from api_client import get_json


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_UI_TESTS") != "1",
    reason="Set RUN_UI_TESTS=1 in an environment that supports Streamlit's test runner",
)


@pytest.fixture(autouse=True)
def trusted_local_ui(monkeypatch):
    # Legacy history tests explicitly opt into trusted local storage.
    settings = config.get_settings().model_copy(update={"app_mode": "local"})
    monkeypatch.setattr(config, "get_settings", lambda: settings)


@pytest.mark.parametrize("page", [
    "Goal Explorer", "Tax estimate", "Portfolio scenario", "Goal risk analysis", "Goal sensitivity", "Scenario history", "Rental property", "Fix-and-flip", "Readiness guide", "Debt payoff methods", "Contribution allocator", "Research workbench",
])
def test_calculator_page_renders_without_exceptions(page: str) -> None:
    script = Path(__file__).with_name("streamlit_app.py")
    app = _new_app()
    _open_page(app, page)

    assert not app.exception
    assert app.title[0].value == ("Goal Explorer" if page == "Goal Explorer" else "Tax & Investment Strategy Optimizer")


@pytest.fixture
def live_api(tmp_path, monkeypatch):
    """Use the real UI HTTP client and API with an isolated SQLite database."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        base_url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        settings = config.get_settings().model_copy(update={
            "api_base_url": base_url,
            "scenario_db_path": tmp_path / "ui-runs.sqlite3",
        })
        monkeypatch.setattr(main, "settings", settings)
        monkeypatch.setattr(config, "get_settings", lambda: settings)
        server = uvicorn.Server(uvicorn.Config(main.app, log_level="error"))
        worker = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        try:
            deadline = monotonic() + 10
            while not server.started and worker.is_alive() and monotonic() < deadline:
                sleep(0.01)
            assert server.started, "Temporary API failed to start"
            assert get_json(base_url, "/health")["status"] == "ok"
            yield base_url
        finally:
            server.should_exit = True
            worker.join(timeout=10)
            assert not worker.is_alive(), "Temporary API failed to stop"


def _widget(elements, label):
    return next(element for element in elements if element.label == label)


def test_workbench_strategy_and_property_constraints_run_without_api():
    app = _new_app()
    _open_page(app, "Research workbench")
    _widget(app.button, "Run synthetic strategy").click().run()
    assert not app.exception and not app.error
    assert app.session_state["_stock_strategy_demo"]["status"] == "synthetic_proposal"
    _widget(app.button, "Solve property constraints").click().run()
    assert not app.exception and not app.error
    assert app.session_state["_rental_feasibility_result"].candidate_status == "feasible"
    _widget(app.selectbox, "Synthetic scenario").set_value("sector_bottleneck")
    _widget(app.button, "Run synthetic strategy").click().run()
    assert app.session_state["_stock_strategy_demo"]["status"] == "infeasible"
    assert not app.session_state["_stock_strategy_demo"]["selected"]
    _widget(app.number_input, "Illustrative stock cash budget").set_value(1000.001)
    _widget(app.button, "Run synthetic strategy").click().run()
    assert app.error and "_stock_strategy_demo" not in app.session_state
    _widget(app.button, "Clear session workspace").click().run()
    assert "_stock_strategy_demo" not in app.session_state
    assert "_rental_feasibility_result" not in app.session_state


def test_rental_cash_purchase_displays_undefined_debt_ratio_and_new_capital(live_api):
    app = _new_app()
    _open_page(app, "Rental property")
    _widget(app.number_input, "Down payment").set_value(500_000.0)
    _widget(app.number_input, "Initial repairs").set_value(3_000.0)
    _widget(app.number_input, "Initial operating reserves held as cash").set_value(12_000.0)
    _widget(app.button, "Underwrite rental").click().run()
    assert not app.exception and not app.error
    assert any(metric.label == "Debt-service coverage" and metric.value == "Not applicable" for metric in app.metric)
    assert any(metric.label == "Initial cash required" and metric.value == "$525,000.00" for metric in app.metric)


def test_allocation_submit_result_and_clear_without_api(monkeypatch):
    def forbid_http(*args, **kwargs):
        raise AssertionError("Allocator must not call HTTP")
    monkeypatch.setattr("api_client.post_json", forbid_http)
    script = Path(__file__).with_name("streamlit_app.py")
    app = _new_app()
    _open_page(app, "Contribution allocator")
    assert not app.exception
    assert "_allocation_result" not in app.session_state
    _widget(app.button, "Optimize purchases").click().run()
    assert not app.exception
    assert not app.error
    result = app.session_state["_allocation_result"]
    assert result.status == "optimal"
    assert result.absolute_weight_drift == 0
    assert any(metric.label == "Cash allocated" and metric.value == "$4,000.00" for metric in app.metric)
    _widget(app.button, "Clear session workspace").click().run()
    assert "_allocation_result" not in app.session_state
    assert "_allocation_inputs" not in app.session_state


def _goal_page():
    app = _new_app()
    _open_page(app, "Goal risk analysis")
    _widget(app.number_input, "Number of simulated paths").set_value(100)
    _widget(app.number_input, "Years until goal").set_value(2)
    return app


def _save_goal(app, label, return_pct=6.0):
    # Fill both widgets before submission, as a user does in a Streamlit form.
    _widget(app.checkbox, "Save this run to local scenario history").check()
    _widget(app.text_input, "Scenario label").set_value(label)
    _widget(app.number_input, "Expected annual return before fees (%)").set_value(return_pct)
    _widget(app.button, "Simulate goal outcomes").click().run()
    assert not app.exception
    assert not app.error
    assert label in app.success[0].value


def test_goal_save_history_and_compare_through_live_api(live_api):
    app = _goal_page()
    _widget(app.number_input, "Goal cost in today's dollars (optional)").set_value(25_000.0)
    _save_goal(app, "Baseline")
    _save_goal(app, "Higher return", return_pct=8.0)
    runs = get_json(live_api, "/scenario-runs/goal-risk")["runs"]
    assert len(runs) == 2
    by_label = {run["label"]: run for run in runs}
    assert by_label["Baseline"]["inputs"]["annual_return_assumption"] == 0.06
    assert by_label["Higher return"]["inputs"]["annual_return_assumption"] == 0.08
    baseline = by_label["Baseline"]
    assert get_json(live_api, f"/scenario-runs/goal-risk/{baseline['run_id']}") == baseline

    _open_page(app, "Scenario history")
    _widget(app.button, "Refresh saved runs").click().run()
    _widget(app.selectbox, "Baseline run").set_value(baseline["run_id"]).run()
    _widget(app.selectbox, "Compare with").set_value(by_label["Higher return"]["run_id"]).run()
    _widget(app.button, "Compare saved runs").click().run()
    assert not app.exception
    assert not app.error
    delta = (by_label["Higher return"]["result"]["ending_balance_median_in_today_dollars"]
             - baseline["result"]["ending_balance_median_in_today_dollars"])
    assert _widget(app.metric, "Median balance change").value == f"${delta:,.2f}"
    assert _widget(app.metric, "Goal-reaching share change").value

    # A changed contribution makes the third run incompatible with the baseline.
    _open_page(app, "Goal risk analysis")
    _widget(app.number_input, "Monthly contribution").set_value(750.0)
    _save_goal(app, "Different contribution")
    _open_page(app, "Scenario history")
    _widget(app.button, "Refresh saved runs").click().run()
    runs = get_json(live_api, "/scenario-runs/goal-risk")["runs"]
    different = next(run for run in runs if run["label"] == "Different contribution")
    _widget(app.selectbox, "Baseline run").set_value(baseline["run_id"]).run()
    _widget(app.selectbox, "Compare with").set_value(different["run_id"]).run()
    _widget(app.button, "Compare saved runs").click().run()
    assert not app.exception
    assert "HTTP 422" in app.error[0].value
    assert "Align starting balance" in app.error[0].value


def test_goal_simulation_without_save_does_not_persist(live_api):
    app = _goal_page()
    _widget(app.button, "Simulate goal outcomes").click().run()
    assert not app.exception
    assert not app.error
    assert _widget(app.metric, "Median · today's dollars").value
    assert get_json(live_api, "/scenario-runs/goal-risk")["runs"] == []


def test_blank_save_label_shows_warning_without_persisting(live_api):
    app = _goal_page()
    _widget(app.checkbox, "Save this run to local scenario history").check()
    _widget(app.text_input, "Scenario label").set_value(" ")
    _widget(app.button, "Simulate goal outcomes").click().run()
    assert not app.exception
    assert "at least two characters" in app.warning[0].value
    assert get_json(live_api, "/scenario-runs/goal-risk")["runs"] == []


def test_explorer_controls_update_inspection_and_survive_navigation():
    app = _new_app()
    assert not app.exception
    _widget(app.slider, "Adjust monthly contribution ($)").set_value(1500.0).run()
    assert _widget(app.number_input, "Monthly contribution ($)").value == 1500.0
    _widget(app.slider, "Inspect year").set_value(0).run()
    assert _widget(app.metric, "Modeled balance").value == "$10,000.00"
    assert _widget(app.metric, "Modeled growth / loss").value == "$0.00"
    _widget(app.slider, "Goal deadline (years)").set_value(2).run()
    _widget(app.slider, "Inspect year").set_value(2).run()
    _widget(app.radio, "Show amounts in").set_value("Future dollars").run()
    assert _widget(app.metric, "Starting balance + deposits").value == "$46,000.00"
    _open_page(app, "Tax estimate")
    _open_page(app, "Goal Explorer")
    assert not app.exception
    assert _widget(app.number_input, "Monthly contribution ($)").value == 1500.0
    assert _widget(app.slider, "Goal deadline (years)").value == 2


def test_explorer_session_comparison_restore_and_delete():
    app = _new_app()
    _widget(app.button, "Keep plan in this session").click().run()
    assert len(app.session_state["_explorer_plans"]) == 1
    _widget(app.number_input, "Monthly contribution ($)").set_value(1200.0).run()
    assert not app.exception
    assert _widget(app.metric, "Base balance change · today's $").value != "$0.00"
    _widget(app.slider, "Goal deadline (years)").set_value(1).run()
    assert _widget(app.slider, "Inspect year").value <= 1
    _widget(app.button, "Restore baseline inputs").click().run()
    assert _widget(app.number_input, "Monthly contribution ($)").value == 1000.0
    assert _widget(app.slider, "Goal deadline (years)").value == 10
    _widget(app.button, "Delete selected session plan").click().run()
    assert app.session_state["_explorer_plans"] == []
    assert not app.exception


def test_explorer_invalid_inputs_replace_previous_results():
    app = _new_app()
    _widget(app.number_input, "Low annual return (%)").set_value(20.0).run()
    assert not app.exception
    assert any("ordered" in warning.value for warning in app.warning)
    assert len(app.metric) == 0


def test_explorer_simulation_is_reproducible_and_stale_results_are_hidden():
    app = _new_app()
    _widget(app.slider, "Goal deadline (years)").set_value(1).run()
    _widget(app.button, "Run uncertainty simulation").click().run()
    assert not app.exception
    first = _widget(app.metric, "Simulated paths reaching goal").value
    _widget(app.slider, "Inspect year").set_value(0).run()
    assert _widget(app.metric, "Simulated paths reaching goal").value == first
    _widget(app.button, "Run uncertainty simulation").click().run()
    assert _widget(app.metric, "Simulated paths reaching goal").value == first
    _widget(app.number_input, "Monthly contribution ($)").set_value(1200.0).run()
    assert any("Inputs changed" in info.value for info in app.info)
    assert not any(metric.label == "Simulated paths reaching goal" for metric in app.metric)


def test_ephemeral_ui_hides_history_and_disables_database_save(monkeypatch):
    settings = config.get_settings().model_copy(update={"app_mode": "ephemeral"})
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    app = _new_app()
    _widget(app.radio, "Explore").set_value("Tools").run()
    assert "Scenario history" not in _widget(app.selectbox, "Choose a calculator").options
    _open_page(app, "Goal risk analysis")
    assert _widget(app.checkbox, "Save this run to local scenario history").disabled
    assert not app.exception


def test_workspace_clear_removes_plans_inputs_risk_and_legacy_history():
    app = _new_app()
    _widget(app.button, "Keep plan in this session").click().run()
    _widget(app.number_input, "Monthly contribution ($)").set_value(1200.0).run()
    _widget(app.button, "Run uncertainty simulation").click().run()
    old_upload = app.session_state["_explorer_upload_token"]
    app.session_state["saved_goal_risk_runs"] = [{"synthetic_private": True}]
    _widget(app.button, "Clear session workspace").click().run()
    assert not app.exception
    assert _widget(app.number_input, "Monthly contribution ($)").value == 1000.0
    assert "_explorer_plans" not in app.session_state
    assert "_explorer_risk" not in app.session_state
    assert "saved_goal_risk_runs" not in app.session_state
    assert app.session_state["_explorer_upload_token"] != old_upload
    assert any("workspace reset" in success.value for success in app.success)


def test_explorer_sessions_do_not_share_financial_state():
    script = str(Path(__file__).with_name("streamlit_app.py"))
    first = _new_app()
    _widget(first.number_input, "Starting balance ($)").set_value(22_000.0).run()
    _widget(first.button, "Keep plan in this session").click().run()
    second = _new_app()
    assert _widget(second.number_input, "Starting balance ($)").value == 10_000.0
    assert "_explorer_plans" not in second.session_state
    assert first.session_state["_explorer_plans"][0]["inputs"]["current_balance"] == 22_000.0


def test_contribution_action_and_common_year_comparison():
    app = _new_app()
    assert _widget(app.radio, "Workspace layout").value == "Chart first"
    required = float(_widget(app.metric, "Monthly amount needed · base").value.replace("$", "").replace(",", ""))
    _widget(app.button, "Use base monthly estimate").click().run()
    assert _widget(app.number_input, "Monthly contribution ($)").value == required
    _widget(app.button, "Keep plan in this session").click().run()
    _widget(app.slider, "Goal deadline (years)").set_value(2).run()
    assert _widget(app.radio, "Compare at").value == "Same elapsed year"
    comparison = next(table.value for table in app.table if "Evaluated year" in table.value.columns)
    assert list(comparison["Evaluated year"]) == [2, 2]
    _widget(app.radio, "Compare at").set_value("Each plan's deadline").run()
    comparison = next(table.value for table in app.table if "Evaluated year" in table.value.columns)
    assert list(comparison["Evaluated year"]) == [10, 2]
    assert any("Different deadlines" in warning.value for warning in app.warning)
    _widget(app.radio, "Workspace layout").set_value("Side by side").run()
    assert not app.exception
    assert _widget(app.slider, "Goal deadline (years)").value == 2


def test_subcent_rounded_estimate_is_not_offered_as_zero_deposit_solution():
    app = _new_app()
    _widget(app.number_input, "Starting balance ($)").set_value(0.0)
    _widget(app.number_input, "Monthly contribution ($)").set_value(0.0)
    _widget(app.number_input, "High annual return (%)").set_value(100.0)
    _widget(app.number_input, "Base annual return (%)").set_value(100.0)
    _widget(app.slider, "Goal deadline (years)").set_value(60).run()
    assert not app.exception
    assert _widget(app.metric, "Monthly amount needed · base").value == "$0.00"
    assert _widget(app.button, "Use base monthly estimate").disabled
    assert any("rounded deposit estimate still leaves" in info.value for info in app.info)


def test_pdf_preparation_is_explicit_current_and_cleared_with_workspace():
    from io import BytesIO
    from pypdf import PdfReader
    app = _new_app()
    assert "_explorer_pdf" not in app.session_state
    _widget(app.button, "Prepare PDF report").click().run()
    assert not app.exception
    signature, pdf = app.session_state["_explorer_pdf"]
    assert len(PdfReader(BytesIO(pdf)).pages) == 2
    assert _widget(app.get("download_button"), "Download PDF report")
    _widget(app.slider, "Inspect year").set_value(0).run()
    assert app.session_state["_explorer_pdf"] == (signature, pdf)
    _widget(app.number_input, "Monthly contribution ($)").set_value(1200.0).run()
    assert "_explorer_pdf" not in app.session_state
    assert not any(button.label == "Download PDF report" for button in app.get("download_button"))
    _widget(app.button, "Prepare PDF report").click().run()
    _widget(app.button, "Clear session workspace").click().run()
    assert "_explorer_pdf" not in app.session_state
    assert not app.exception


def test_pdf_can_include_the_selected_comparison_and_currency_changes_invalidate_it():
    from io import BytesIO
    from pypdf import PdfReader
    app = _new_app()
    assert _widget(app.checkbox, "Include selected baseline in PDF").disabled
    _widget(app.button, "Keep plan in this session").click().run()
    _widget(app.number_input, "Monthly contribution ($)").set_value(1200.0).run()
    _widget(app.checkbox, "Include selected baseline in PDF").check().run()
    _widget(app.button, "Prepare PDF report").click().run()
    assert len(PdfReader(BytesIO(app.session_state["_explorer_pdf"][1])).pages) == 3
    _widget(app.radio, "Show amounts in").set_value("Future dollars").run()
    assert "_explorer_pdf" not in app.session_state
    _widget(app.button, "Prepare PDF report").click().run()
    text = PdfReader(BytesIO(app.session_state["_explorer_pdf"][1])).pages[0].extract_text()
    assert "Future dollars" in text
    _widget(app.number_input, "Goal cost today ($)").set_value(100_000.0).run()
    assert _widget(app.checkbox, "Include selected baseline in PDF").disabled
    assert "_explorer_pdf" not in app.session_state


def test_invalid_report_label_and_financial_inputs_do_not_offer_stale_pdf():
    app = _new_app()
    _widget(app.button, "Prepare PDF report").click().run()
    _widget(app.text_input, "Plan label").set_value(" ").run()
    assert _widget(app.button, "Prepare PDF report").disabled
    assert "_explorer_pdf" not in app.session_state
    _widget(app.text_input, "Plan label").set_value("Valid label").run()
    _widget(app.button, "Prepare PDF report").click().run()
    _widget(app.number_input, "Low annual return (%)").set_value(20.0).run()
    assert "_explorer_pdf" not in app.session_state
    assert not any(button.label == "Download PDF report" for button in app.get("download_button"))


def test_pdf_failure_is_generic_and_preserves_the_plan(monkeypatch):
    import goal_explorer_ui
    secret = "SYNTHETIC-PRIVATE-ERROR"

    def fail(*args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(goal_explorer_ui, "build_goal_report", fail)
    app = _new_app()
    _widget(app.button, "Prepare PDF report").click().run()
    assert not app.exception
    assert any("Could not prepare" in error.value for error in app.error)
    assert all(secret not in error.value for error in app.error)
    assert _widget(app.number_input, "Monthly contribution ($)").value == 1000.0
    assert "_explorer_pdf" not in app.session_state


def _new_app():
    app = AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py")), default_timeout=30)
    app.session_state["workspace_section"] = "Goals"
    return app.run()


def _open_page(app, page):
    _widget(app.radio, "Explore").set_value("Goals" if page == "Goal Explorer" else "Tools").run()
    if page != "Goal Explorer":
        _widget(app.selectbox, "Choose a calculator").set_value(page).run()
    return app


def test_rental_holding_stress_funding_and_navigation():
    app=AppTest.from_file(str(Path(__file__).with_name('streamlit_app.py')),default_timeout=30).run()
    assert not app.exception
    assert len(app.session_state['_rental_hold_result']['Base']['months'])==120
    _widget(app.slider,'Hold for (years)').set_value(2).run()
    _widget(app.number_input,'One-time repair bill ($)').set_value(1000000).run()
    assert app.session_state['_rental_hold_result']['Base']['status']=='funding_shortfall'
    assert app.session_state['_rental_hold_result']['Base']['net_profit'] is None
    _widget(app.radio,'Explore').set_value('Stocks').run()
    _widget(app.radio,'Explore').set_value('Real estate').run()
    assert _widget(app.slider,'Hold for (years)').value==2
    assert _widget(app.number_input,'One-time repair bill ($)').value==1000000
    _widget(app.number_input,'Repair month').set_value(24).run()
    _widget(app.slider,'Hold for (years)').set_value(1).run()
    assert _widget(app.number_input,'Repair month').value<=12 and not app.exception
    _widget(app.button,'Clear session workspace').click().run()
    assert _widget(app.number_input,'One-time repair bill ($)').value==0


def test_visual_workspace_reacts_compares_preserves_and_clears():
    app = AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py")), default_timeout=30).run()
    assert not app.exception

    assert app.title[0].value == "Find the room in a rental deal"
    initial = app.session_state["_rental_visual_result"].annual_pre_tax_cash_flow
    _widget(app.button, "Pin this scenario for comparison").click().run()
    _widget(app.slider, "Monthly rent ($)").set_value(3500).run()
    assert not app.exception
    assert app.session_state["_rental_visual_result"].annual_pre_tax_cash_flow > initial
    assert app.session_state["_rental_visual_baseline"]["cashflow"] == initial
    _widget(app.radio, "Explore").set_value("Stocks").run()
    _widget(app.radio, "Stock workspace").set_value("Strategy lab").run()
    assert not app.exception
    assert app.session_state["_stock_visual_result"]["data_kind"] == "synthetic"
    before = app.session_state["_stock_visual_result"]
    _widget(app.slider, "Illustrative cash budget ($)").set_value(20000).run()
    after = app.session_state["_stock_visual_result"]
    assert [row["security_id"] for row in before["selected"]] == [row["security_id"] for row in after["selected"]]
    assert after["selected"][0]["purchase_cents"] == 2*before["selected"][0]["purchase_cents"]
    _widget(app.selectbox, "Company").set_value("SYN_4_0").run()
    assert _widget(app.metric, "Combined score / 100").value == "70.0"
    _widget(app.radio, "Explore a constraint").set_value("Sector bottleneck").run()
    assert app.session_state["_stock_visual_result"]["status"] == "infeasible"
    _widget(app.radio, "Explore").set_value("Real estate").run()
    assert _widget(app.slider, "Monthly rent ($)").value == 3500
    _widget(app.slider, "Purchase price ($)").set_value(50000).run()
    assert _widget(app.slider, "Down payment ($)").value <= 50000
    assert not app.exception
    _widget(app.button, "Clear session workspace").click().run()
    assert "_rental_visual_baseline" not in app.session_state
    assert _widget(app.slider, "Monthly rent ($)").value == 3000
    assert "_stock_visual_result" not in app.session_state
    assert not app.exception


def test_coverage_panel_discloses_scope_and_does_not_change_scenario(tmp_path,monkeypatch):
    from datetime import date, datetime, timezone
    from data_pipeline import build_release
    from test_public_data_pipeline import seed_rentals, GEO, VALUE
    import data_readiness_ui
    cache,store=tmp_path/"raw",tmp_path/"published"
    seed_rentals(cache)
    build_release(cache,store,as_of=date(2026,10,28),source_ids=[GEO,VALUE],
                  now=datetime(2026,10,28,23,tzinfo=timezone.utc))
    settings=config.get_settings().model_copy(update={"market_data_store":store})
    monkeypatch.setattr(config,"get_settings",lambda:settings)
    monkeypatch.setattr(data_readiness_ui,"get_settings",lambda:settings)
    app=AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py")),default_timeout=30).run()
    assert not app.exception
    app.session_state['data_coverage_rentals']=True
    app.run()
    assert _widget(app.metric,"Dated geographic candidates").value=="2"
    assert any("Not current USPS ZIP membership" in item.value for item in app.markdown)
    before=app.session_state["_rental_visual_result"].annual_pre_tax_cash_flow
    _widget(app.slider,"Monthly rent ($)").set_value(3500).run()
    assert _widget(app.metric,"Dated geographic candidates").value=="2"
    assert app.session_state["_rental_visual_result"].annual_pre_tax_cash_flow>before
    assert not app.exception


def test_real_company_research_search_and_period_inspection(tmp_path,monkeypatch):
    from test_company_research import research_store
    import company_research_ui
    store=research_store(tmp_path)
    settings=config.get_settings().model_copy(update={"market_data_store":store})
    monkeypatch.setattr(config,"get_settings",lambda:settings)
    monkeypatch.setattr(company_research_ui,"get_settings",lambda:settings)
    app=AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py")),default_timeout=30)
    app.session_state["workspace_section"]="Stocks"
    app.session_state["stock_research_view"]="Company research"
    app.run()
    assert not app.exception
    assert _widget(app.radio,"Stock workspace").value=="Company research"
    assert _widget(app.select_slider,"Inspect fiscal period").value=="2025-12-31"
    assert any("What does this tell our strategy?" in item.value for item in app.markdown)
    assert any("Selection score unavailable" in item.value for item in app.info)
    _widget(app.select_slider,"Inspect fiscal period").set_value("2024-12-31").run()
    assert not app.exception
    assert any("Selected fiscal year: 2024-12-31" in item.value for item in app.caption)
    _widget(app.text_input,"Find a supported company").set_value("unmatched company").run()
    assert any("No supported company matches" in info.value for info in app.info)
    _widget(app.text_input,"Find a supported company").set_value("AAPL").run()
    assert _widget(app.selectbox,"Research company").value=="aapl"
    assert not app.exception


def test_news_only_issuer_shows_confirmed_schedule_and_filterable_filings(tmp_path,monkeypatch):
    from test_company_events import event_store, CLOCK
    from company_events import company_events
    import company_research_ui
    import company_events_ui
    _,store=event_store(tmp_path,2023554)
    settings=config.get_settings().model_copy(update={"market_data_store":store})
    monkeypatch.setattr(config,"get_settings",lambda:settings)
    monkeypatch.setattr(company_research_ui,"get_settings",lambda:settings)
    monkeypatch.setattr(company_events_ui,"_events",lambda root,revision,issuer,minute:company_events(root,issuer,now=CLOCK))
    app=AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py")),default_timeout=30)
    app.session_state["workspace_section"]="Stocks"
    app.session_state["stock_research_view"]="Company research"
    app.run()
    assert not app.exception
    assert any("Upcoming scheduled call" in item.value for item in app.info)
    assert any("financial snapshot is unavailable" in item.value for item in app.warning)
    assert _widget(app.selectbox,"Research company").value=="cik0002023554"
    _widget(app.multiselect,"Filing types").set_value([]).run()
    assert any("No filings match this view" in item.value for item in app.caption)
    _widget(app.radio,"Timeline window").set_value("All cached").run()
    assert not app.exception


def test_portfolio_overview_preserves_weights_budget_and_navigation():
    app=AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py")),default_timeout=30)
    app.session_state["workspace_section"]="Stocks"
    app.run()
    assert not app.exception and _widget(app.radio,"Stock workspace").value=="Portfolio"
    result=app.session_state["_portfolio_composition_result"]
    assert [row["weight_bps"] for row in result["holdings"]]==[2000,1500,2500,1500,1000,1500]
    _widget(app.number_input,"Portfolio amount ($)").set_value(20000).run()
    assert app.session_state["_portfolio_composition_result"]["budget_cents"]==2000000
    assert _widget(app.metric,"Largest position").value=="25%"
    _widget(app.radio,"Stock workspace").set_value("Company research").run()
    _widget(app.radio,"Stock workspace").set_value("Portfolio").run()
    assert _widget(app.number_input,"Portfolio amount ($)").value==20000
    assert app.session_state["_portfolio_composition_result"]["holdings"]==result["holdings"]
    _widget(app.button,"Clear session workspace").click().run()
    assert _widget(app.number_input,"Portfolio amount ($)").value==10000
    assert not app.exception


def test_source_panel_loads_only_when_opened(tmp_path,monkeypatch):
    from test_stock_screen import screen_store
    import data_readiness_ui
    from market_catalog import load_catalog
    public,_=screen_store(tmp_path)
    catalog=load_catalog(public)
    calls=[]
    monkeypatch.setattr(data_readiness_ui,'_public_coverage',lambda *args:calls.append(args) or catalog)
    app=AppTest.from_string("from data_readiness_ui import render_data_readiness\nrender_data_readiness('stocks')",default_timeout=30)
    app.run()
    assert not app.exception and not calls
    app.session_state['data_coverage_stocks']=True
    app.run()
    assert not app.exception and len(calls)==1
    assert any('Research release' in item.value for item in app.caption)


def test_portfolio_overallocation_is_not_silently_normalized():
    app=AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py")),default_timeout=30)
    app.session_state["workspace_section"]="Stocks"
    app.session_state["_portfolio_editor_rows"]=[{"Symbol":"AAA","Holding":"A","Type":"Stock","Weight (%)":60.0},
        {"Symbol":"BBB","Holding":"B","Type":"Stock","Weight (%)":60.0}]
    app.run()
    assert any("totals over 100% are not silently normalized" in item.value for item in app.warning)
    assert "_portfolio_composition_result" not in app.session_state and not app.exception


def test_stock_screen_filters_and_company_navigation(tmp_path,monkeypatch):
    from test_stock_screen import screen_store
    import stock_screen_ui,company_research_ui,market_history_ui
    from types import SimpleNamespace
    from test_company_research import NOW
    # Exercise navigation at the fixture's date; the real clock would eventually
    # make its October 26 proxy stale and correctly remove sector-filter matches.
    monkeypatch.setattr(stock_screen_ui,'datetime',SimpleNamespace(now=lambda tz:NOW.astimezone(tz)))
    public,history=screen_store(tmp_path)
    settings=config.get_settings().model_copy(update={"market_data_store":public,"market_history_store":history,"market_data_mode":"local_research"})
    for module in (config,stock_screen_ui,company_research_ui,market_history_ui):
        monkeypatch.setattr(module,"get_settings",lambda:settings)
    app=AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py")),default_timeout=30)
    app.session_state["workspace_section"]="Stocks";app.session_state["stock_research_view"]="Research screen"
    app.run()
    assert not app.exception
    assert _widget(app.metric,"Companies with financial data").value=="1"
    assert _widget(app.metric,"Have valuation estimates").value=="1"
    assert _widget(app.metric,"Reported issuer count (shares)").value=="100"
    assert any('Class quantities are not reconciled' in item.value for item in app.markdown)
    _widget(app.checkbox,"Apply historical risk thresholds").set_value(True).run()
    assert not app.session_state['_stock_filter_result']['included_issuer_keys']
    assert app.session_state['_stock_filter_result']['exclusions'] and not app.exception
    _widget(app.checkbox,"Apply historical risk thresholds").set_value(False).run()
    _widget(app.checkbox,"Apply profitability and leverage thresholds").set_value(True).run()
    _widget(app.slider,"Minimum return on assets (%)").set_value(100.0).run()
    assert not app.session_state['_stock_filter_result']['included_issuer_keys']
    _widget(app.checkbox,"Apply profitability and leverage thresholds").set_value(False).run()
    _widget(app.multiselect,"Business sector").set_value(["Information Technology"]).run()
    _widget(app.checkbox,"Only companies meeting financial rules").set_value(True).run()
    assert _widget(app.selectbox,"Choose a company to understand").value=="aapl"
    _widget(app.button,"Open full company research").click().run()
    assert _widget(app.radio,"Stock workspace").value=="Company research"
    _widget(app.button,"Inspect sector and valuation context").click().run()
    assert _widget(app.radio,"Stock workspace").value=="Research screen" and not app.exception


def test_filing_share_panel_distinguishes_latest_period_rounding_and_dimensions():
    from copy import deepcopy
    from class_share_ledger import build_class_share_ledger
    from filing_share_evidence import filing_point_shares
    from market_sources import COVER_FILINGS
    from test_filing_share_evidence import evidence
    from test_class_share_ledger import inputs,REF
    values=inputs();values.update(cik=320193,directory={'AAPL':{320193}},class_tables=[(REF,[dict(
        cik=320193,symbol='AAPL',class_title='Common Stock',exchange='NASDAQ',context_ref='class',
        accession='cover',period_end='2025-09-27',filed_on='2025-10-31')])])
    point=filing_point_shares(evidence(),COVER_FILINGS['sec_cover_aapl_2025'])[0]
    older=deepcopy(point);older.update(measured_on='2024-09-28',dimensions={'custom:ClassAxis':'custom:A'},scope='dimensional_unassigned')
    ledger=build_class_share_ledger(**values,filing_share_tables=[(REF,[point,older])])
    app=AppTest.from_string('from stock_screen_ui import render_class_share_ledger\nimport streamlit as st\nrender_class_share_ledger(st.session_state["ledger"])',default_timeout=30)
    app.session_state['ledger']=ledger
    app.run()
    assert not app.exception
    assert _widget(app.metric,'Class quantities reconciled').value=='Not yet'
    table=app.dataframe[1].value
    assert len(table)==1 and table.iloc[0]['Reported count (shares)']=='14,773,260,000'
    assert table.iloc[0]['Rounding (shares)']=='1,000'
    _widget(app.checkbox,'Include older periods and dimensional observations').set_value(True).run()
    assert not app.exception and len(app.dataframe[1].value)==2


def test_historical_class_match_panel_keeps_dates_and_current_assignment_separate():
    from test_class_quantity_review import ledger_with_review
    app=AppTest.from_string('from stock_screen_ui import render_class_share_ledger\nimport streamlit as st\nrender_class_share_ledger(st.session_state["ledger"])',default_timeout=30)
    app.session_state['ledger']=ledger_with_review()
    app.run()
    assert not app.exception
    assert _widget(app.metric,'Historical statement count (shares)').value=='14,773,260,000'
    assert _widget(app.metric,'Reported issuer count (shares)').value=='100'
    assert _widget(app.metric,'Class quantities reconciled').value=='Not yet'
    assert app.dataframe[0].value.iloc[0]['Current shares assigned']=='Unknown'
    assert any('2025-09-27' in item.value and '2026-11-03' in item.value for item in app.caption)
    assert any('does not replace' in item.value for item in app.caption)


def test_reference_health_panel_is_lazy_and_discloses_failed_candidate(tmp_path,monkeypatch):
    import reference_refresh_ui
    from test_reference_refresh import installed,fetcher
    from reference_refresh import refresh_references
    from test_company_research import DAY,NOW
    from datetime import timedelta
    root=installed(tmp_path)
    now=NOW+timedelta(hours=1)
    result=refresh_references(tmp_path/'raw',root,as_of=DAY,now=now,
        fetch=fetcher(now=now,failed='ivv_holdings_proxy'))
    calls=[];original=reference_refresh_ui.load_release
    def counted(*a,**k):calls.append(1);return original(*a,**k)
    monkeypatch.setattr(reference_refresh_ui,'load_release',counted)
    app=AppTest.from_string('from reference_refresh_ui import render_reference_status\nimport streamlit as st\nrender_reference_status(st.session_state["root"])',default_timeout=30)
    app.session_state['root']=root
    app.run()
    assert not app.exception and not calls
    app.session_state['reference_health']=True
    app.run()
    assert not app.exception and len(calls)==1
    assert _widget(app.metric,'Official index membership').value=='Not verified'
    assert any('did not publish' in item.value for item in app.warning)
    assert len(app.dataframe[0].value)==4
    assert result.previous_release_id==result.installed_release_id


def test_market_history_window_and_drawdown_view_react(tmp_path,monkeypatch):
    from datetime import date
    from test_company_research import research_store
    from test_market_history import bundle
    from market_history import publish_history
    import company_research_ui,market_history_ui
    public=research_store(tmp_path);history=tmp_path/"history"
    publish_history(history,bundle())
    settings=config.get_settings().model_copy(update={"market_data_store":public,"market_history_store":history,"market_data_mode":"local_research"})
    monkeypatch.setattr(config,"get_settings",lambda:settings)
    monkeypatch.setattr(company_research_ui,"get_settings",lambda:settings)
    monkeypatch.setattr(market_history_ui,"get_settings",lambda:settings)
    app=AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py")),default_timeout=30)
    app.session_state["workspace_section"]="Stocks";app.session_state["stock_research_view"]="Company research"
    app.run()
    assert not app.exception and _widget(app.metric,"Company change").value=="-10.0%"
    _widget(app.select_slider,"Inspect market-history window").set_value((date(2026,10,27),date(2026,10,28))).run()
    assert _widget(app.metric,"Company change").value=="-25.0%"
    _widget(app.radio,"Chart view").set_value("Drawdown").run()
    assert _widget(app.metric,"Company worst drawdown").value=="-25.0%" and not app.exception
    _widget(app.radio,"Chart view").set_value("Share price ($)").run()
    assert not app.exception
    assert any("Split-adjusted prices" in item.value for item in app.caption)
    _widget(app.radio,"Chart view").set_value("Value of $100").run()
    assert any("Start with" in item.value and "$100" in item.value for item in app.caption)


def test_real_replay_and_proposal_readiness_workflows(tmp_path,monkeypatch):
    from test_stock_screen import screen_store
    import stock_workflows_ui
    public,history=screen_store(tmp_path)
    settings=config.get_settings().model_copy(update={'market_data_store':public,'market_history_store':history,'market_data_mode':'local_research'})
    monkeypatch.setattr(config,'get_settings',lambda:settings)
    monkeypatch.setattr(stock_workflows_ui,'get_settings',lambda:settings)
    app=AppTest.from_file(str(Path(__file__).with_name('streamlit_app.py')),default_timeout=30)
    app.session_state['workspace_section']='Stocks';app.session_state['stock_research_view']='Historical replay'
    app.run()
    assert not app.exception and app.session_state['_stock_replay_result']['status']=='available'
    _widget(app.number_input,'Starting investment ($)').set_value(2000).run()
    assert app.session_state['_stock_replay_result']['total_deposits_cents']==200000
    assert app.session_state['_stock_replay_result']['company_ending_value']=='1800.00'
    _widget(app.radio,'Stock workspace').set_value('Build portfolio').run()
    assert not app.exception and not app.session_state['_verified_stock_proposal']['selected']
    assert not app.session_state['_verified_stock_proposal']['live_recommendations_enabled']
    assert app.session_state['_verified_stock_proposal']['cash_unallocated_cents']==1000000


def test_experimental_basket_opt_in_budget_and_no_stale_selection(tmp_path,monkeypatch):
    from test_experimental_basket import research_universe
    import experimental_basket_ui
    screen=research_universe(tmp_path)
    settings=config.get_settings().model_copy(update={'market_data_mode':'local_research'})
    monkeypatch.setattr(experimental_basket_ui,'get_settings',lambda:settings)
    monkeypatch.setattr(experimental_basket_ui,'stock_screen',lambda *args,**kwargs:screen)
    app=AppTest.from_string('from experimental_basket_ui import render_experimental_basket\nrender_experimental_basket()',default_timeout=30)
    app.run()
    assert not app.exception and '_experimental_stock_basket' not in app.session_state
    _widget(app.checkbox,'I understand this uses proxy membership and valuation estimates').check().run()
    assert not app.exception and len(app.session_state['_experimental_stock_basket']['selected'])==10
    _widget(app.number_input,'Experimental cash budget ($)').set_value(20000).run()
    assert sum(row['purchase_cents'] for row in app.session_state['_experimental_stock_basket']['selected'])==2000000
    _widget(app.slider,'Experimental sector position cap').set_value(2).run()
    assert not app.exception and not app.session_state['_experimental_stock_basket']['selected']
    assert app.session_state['_experimental_stock_basket']['status']=='infeasible'
    _widget(app.checkbox,'I understand this uses proxy membership and valuation estimates').uncheck().run()
    assert '_experimental_stock_basket' not in app.session_state and not app.exception


def test_decision_review_stability_freeze_and_pending_follow_up(tmp_path,monkeypatch):
    from test_experimental_basket import research_universe
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import experimental_basket_ui,stock_review_ui
    screen=research_universe(tmp_path)
    screen.checked_on=datetime.now(ZoneInfo('America/Los_Angeles')).date()
    settings=config.get_settings().model_copy(update={'market_data_mode':'local_research'})
    for module in (experimental_basket_ui,stock_review_ui):monkeypatch.setattr(module,'get_settings',lambda:settings)
    monkeypatch.setattr(experimental_basket_ui,'stock_screen',lambda *args,**kwargs:screen)
    app=AppTest.from_string('from experimental_basket_ui import render_experimental_basket\nfrom stock_review_ui import render_validation_workspace\nrender_experimental_basket()\nrender_validation_workspace()',default_timeout=45)
    app.run()
    _widget(app.checkbox,'I understand this uses proxy membership and valuation estimates').check().run()
    _widget(app.button,'Check basket stability').click().run()
    assert not app.exception and app.session_state['_basket_sensitivity']
    _widget(app.slider,'One-company valuation-yield stress (%)').set_value(20).run()
    assert '_basket_sensitivity' not in app.session_state
    _widget(app.button,'Freeze this paper basket').click().run()
    assert not app.exception and len(app.session_state['_paper_records'])==1
    frozen=app.session_state['_paper_records'][0]
    _widget(app.number_input,'Experimental cash budget ($)').set_value(20000).run()
    assert app.session_state['_paper_records'][0]==frozen and not app.exception
    from types import SimpleNamespace
    import json
    payload=json.dumps(frozen).encode()
    monkeypatch.setattr(stock_review_ui.st,'file_uploader',lambda *args,**kwargs:SimpleNamespace(getvalue=lambda:payload))
    app.session_state['_paper_records']=[]
    app.run()
    _widget(app.button,'Restore paper record').click().run()
    assert not app.exception and len(app.session_state['_paper_records'])==1
    assert frozen['fingerprint'] in app.session_state['_paper_imported_fingerprints']
