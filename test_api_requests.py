"""HTTP request/response checks for the FastAPI application.

These use Starlette's synchronous TestClient, which drives an async event loop.
Set RUN_API_REQUEST_TESTS=1 to run them; CI does so on its Linux runners.
"""

import os

import pytest
from fastapi.testclient import TestClient

import main
from main import app


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_API_REQUEST_TESTS") != "1",
    reason="Set RUN_API_REQUEST_TESTS=1 in an async-capable environment",
)

client = TestClient(app)


def test_monthly_preview_uses_server_evidence_and_keeps_cash_private(tmp_path,monkeypatch):
    from test_experimental_basket import research_universe
    screen=research_universe(tmp_path)
    monkeypatch.setattr(main,'stock_screen',lambda *args,**kwargs:screen)
    payload={'acknowledge_experimental':True,'monthly_contribution_cents':100003}
    response=client.post('/research/stock-monthly-contribution',json=payload)
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert response.json()['to_stocks_cents']==100000 and response.json()['cash_unassigned_cents']==3
    assert not response.json()['automatic_schedule_enabled']
    assert client.post('/research/stock-monthly-contribution',json={}).json()['status']=='acknowledgement_required'
    assert client.post('/research/stock-monthly-contribution',json={**payload,'screen':{}}).status_code==422
    screen.universe.fresh=False
    assert client.post('/research/stock-monthly-contribution',json=payload).json()['status']=='unavailable'


def test_stock_decision_workflow_server_evidence_consent_and_privacy(tmp_path,monkeypatch):
    from test_experimental_basket import research_universe
    screen=research_universe(tmp_path)
    monkeypatch.setattr(main,'stock_screen',lambda *args,**kwargs:screen)
    report=client.get('/research/stock-evidence')
    assert report.status_code==200 and report.headers['cache-control']=='no-store'
    assert report.json()['counts']['security_identity']['missing']==20
    assert client.post('/research/stock-decisions',json={}).json()['status']=='acknowledgement_required'
    payload={'acknowledge_experimental':True,'new_cash_cents':100003}
    response=client.post('/research/stock-decisions',json=payload)
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert response.json()['outcome_counts']['buy_candidate']==10
    assert not response.json()['live_recommendations_enabled']
    assert client.post('/research/stock-decisions',json={**payload,'screen':screen.model_dump(mode='json')}).status_code==422
    assert client.post('/research/stock-decisions',json={**payload,'live_recommendations_enabled':True}).status_code==422
    # A second request cannot inherit the prior visitor's holdings or constraints.
    restricted=client.post('/research/stock-decisions',json={**payload,'horizon_years':1}).json()
    assert restricted['outcome_counts']=={'pass':20}
    assert client.post('/research/stock-decisions',json=payload).json()==response.json()


def test_financial_validation_endpoint_is_no_store_and_respects_market_mode(tmp_path,monkeypatch):
    from test_stock_screen import screen_store
    public,history=screen_store(tmp_path)
    monkeypatch.setattr(main,'settings',main.settings.model_copy(update={'market_data_store':public,'market_history_store':history,'market_data_mode':'local_research'}))
    result=client.get('/research/stock-validation')
    assert result.status_code==200 and result.headers['cache-control']=='no-store'
    assert result.json()['checks'] and not result.json()['historical_strategy_evaluation_available']
    assert not result.json()['source_accuracy_verified']
    monkeypatch.setattr(main,'settings',main.settings.model_copy(update={'market_data_mode':'withheld'}))
    assert client.get('/research/stock-validation').json()['status']=='withheld'


def test_experimental_endpoint_opt_in_private_response_and_strict_separation(tmp_path,monkeypatch):
    from test_experimental_basket import research_universe
    screen=research_universe(tmp_path)
    monkeypatch.setattr(main,'stock_screen',lambda *args,**kwargs:screen)
    default=client.post('/research/experimental-basket',json={})
    assert default.status_code==200 and default.json()['status']=='acknowledgement_required'
    result=client.post('/research/experimental-basket',json={'acknowledge_proxy_and_estimates':True,'budget_cents':100003})
    assert result.status_code==200 and result.headers['cache-control']=='no-store'
    body=result.json()
    assert len(body['selected'])==10 and body['cash_unallocated_cents']==3
    assert not body['verified_membership'] and not body['live_recommendations_enabled']
    assert client.post('/research/experimental-basket',json={'verified_membership':True}).status_code==422
    strict=client.post('/research/stock-proposal',json={}).json()
    assert not strict['selected'] and not strict['live_recommendations_enabled']


def test_replay_and_proposal_endpoints_use_server_evidence(tmp_path,monkeypatch):
    from test_stock_screen import screen_store
    public,history=screen_store(tmp_path)
    monkeypatch.setattr(main,'settings',main.settings.model_copy(update={'market_data_store':public,'market_history_store':history,'market_data_mode':'local_research'}))
    replay=client.post('/research/stock-replay',json={'issuer_key':'aapl','start':'2026-10-26','end':'2026-10-28','monthly_cents':0})
    assert replay.status_code==200 and replay.json()['status']=='available'
    assert replay.headers['cache-control']=='no-store' and not replay.json()['strategy_performance_evidence']
    proposal=client.post('/research/stock-proposal',json={'budget_cents':100000})
    assert proposal.status_code==200 and not proposal.json()['selected'] and not proposal.json()['live_recommendations_enabled']
    assert proposal.json()['cash_unallocated_cents']==100000
    assert client.post('/research/stock-proposal',json={'budget_cents':100000,'membership_verified':True}).status_code==422
    monkeypatch.setattr(main,'settings',main.settings.model_copy(update={'market_data_mode':'withheld'}))
    assert client.post('/research/stock-replay',json={'issuer_key':'aapl','start':'2026-10-26','end':'2026-10-28'}).json()['status']=='withheld'


def test_stock_filter_api_requires_explicit_estimates_and_rejects_missing_metric(tmp_path,monkeypatch):
    from test_stock_screen import screen_store
    public,history=screen_store(tmp_path)
    monkeypatch.setattr(main,'settings',main.settings.model_copy(update={'market_data_store':public,'market_history_store':history,'market_data_mode':'local_research'}))
    result=client.post('/research/stock-screen/filter',json={'maximum_volatility':0})
    assert result.status_code==200 and result.headers['cache-control']=='no-store'
    assert not result.json()['included_issuer_keys'] and result.json()['exclusions']
    assert not result.json()['live_recommendations_enabled']
    assert client.post('/research/stock-screen/filter',json={'minimum_estimated_earnings_yield':0}).status_code==422


def test_rental_projection_is_reproducible_private_and_rejects_invalid_financing():
    from test_rental_projection import request
    payload=request().model_dump(mode='json')
    result=client.post('/real-estate/rental-projection',json=payload)
    assert result.status_code==200 and result.headers['cache-control']=='no-store'
    assert result.json()['net_profit']=='12000.00'
    assert result.json()==client.post('/real-estate/rental-projection',json=payload).json()
    payload['down_payment']='999999'
    assert client.post('/real-estate/rental-projection',json=payload).status_code==422


def test_stock_screen_exposes_provisional_evidence_without_live_scores(tmp_path,monkeypatch):
    from test_stock_screen import screen_store
    public,history=screen_store(tmp_path)
    monkeypatch.setattr(main,"settings",main.settings.model_copy(update={"market_data_store":public,"market_history_store":history,"market_data_mode":"withheld"}))
    assert client.get("/research/stock-screen").json()["status"]=="withheld"
    monkeypatch.setattr(main,"settings",main.settings.model_copy(update={"market_data_mode":"local_research"}))
    def forbidden(*a,**k):raise AssertionError("Screen serving must not download")
    monkeypatch.setattr("alpaca_history.refresh_history",forbidden)
    response=client.get("/research/stock-screen")
    assert response.status_code==200 and response.headers["cache-control"]=="no-store"
    body=response.json()
    assert body["rows"][0]["score"] is None and not body["rows"][0]["selected"]
    assert not body["live_recommendations_enabled"]
    assert not body["rows"][0]["valuation"]["verified_current_market_cap"]
    ledger=body['rows'][0]['class_share_ledger']
    assert ledger['share_observation']['shares']=='100'
    assert ledger['securities'][0]['assigned_shares'] is None
    assert not ledger['class_quantities_reconciled'] and not ledger['issuer_valuation_verified']


def test_decision_snapshot_review_uses_server_sources_and_is_private(tmp_path,monkeypatch):
    from test_decision_snapshots import saved
    screen,record=saved(tmp_path)
    monkeypatch.setattr(main,'stock_screen',lambda *a,**k:screen)
    payload={'snapshot_json':record.model_dump_json()}
    assert client.post('/research/stock-decisions/snapshot-review',json=payload).json()['status']=='acknowledgement_required'
    payload['acknowledge_experimental']=True
    response=client.post('/research/stock-decisions/snapshot-review',json=payload)
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert response.json()['current']['context']['new_cash_cents']==100003
    assert not response.json()['current']['live_recommendations_enabled']
    assert not response.json()['recorded_results_attested']
    changed={**payload,'context_override':{**record.assessment.context.model_dump(mode='json'),'horizon_years':1}}
    assert client.post('/research/stock-decisions/snapshot-review',json=changed).json()['current']['outcome_counts']=={'pass':20}
    assert client.post('/research/stock-decisions/snapshot-review',json=payload).json()==response.json()
    assert client.post('/research/stock-decisions/snapshot-review',json={**payload,'screen':screen.model_dump(mode='json')}).status_code==422
    invalid=client.post('/research/stock-decisions/snapshot-review',json={**payload,'snapshot_json':'PRIVATE FINANCIAL MARKER'})
    assert invalid.status_code==422 and 'PRIVATE FINANCIAL MARKER' not in invalid.text
    screen.status='withheld'
    result=client.post('/research/stock-decisions/snapshot-review',json=payload).json()
    assert result['status']=='unavailable' and not result['current']['cards'] and not result['changes']


def test_stock_pdf_is_private_recomputed_and_withheld_when_stale(tmp_path,monkeypatch):
    from test_decision_snapshots import saved
    screen,record=saved(tmp_path)
    monkeypatch.setattr(main,'stock_screen',lambda *a,**k:screen)
    payload={'snapshot_json':record.model_dump_json(),'acknowledge_experimental':True}
    response=client.post('/research/stock-decisions/report',json=payload)
    assert response.status_code==200 and response.content.startswith(b'%PDF-')
    assert response.headers['cache-control']=='no-store' and response.headers['content-type']=='application/pdf'
    assert 'stock-decision-review.pdf' in response.headers['content-disposition']
    assert client.post('/research/stock-decisions/report',json={**payload,'acknowledge_experimental':False}).status_code==422
    screen.universe.fresh=False
    assert client.post('/research/stock-decisions/report',json=payload).status_code==422


def test_owned_holding_review_is_private_and_never_converts_missing_data_to_sell(tmp_path,monkeypatch):
    from test_experimental_basket import research_universe
    from test_holding_research import request
    screen=research_universe(tmp_path)
    monkeypatch.setattr(main,'stock_screen',lambda *a,**k:screen)
    payload=request(reason_state='no_longer_supported',illustrate_full_sale=True,assumed_sale_fee_cents=503).model_dump(mode='json')
    response=client.post('/research/stock-holding-review',json=payload)
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert not response.json()['sale_recommended'] and response.json()['illustration']['cash_before_tax_cents']==99500
    screen.universe.fresh=False
    assert client.post('/research/stock-holding-review',json=payload).json()['status']=='needs_evidence'
    assert client.post('/research/stock-holding-review',json={**payload,'card':{'outcome':'hold'}}).status_code==422


def test_market_endpoint_is_withheld_by_default_and_offline_when_enabled(tmp_path,monkeypatch):
    from test_company_research import research_store
    from test_market_history import bundle
    from market_history import publish_history
    public=research_store(tmp_path);history=tmp_path/"history"
    publish_history(history,bundle())
    def forbidden(*a,**k):raise AssertionError("Market serving must not download")
    monkeypatch.setattr("alpaca_history.refresh_history",forbidden)
    monkeypatch.setattr(main,"settings",main.settings.model_copy(update={"market_data_store":public,"market_history_store":history,"market_data_mode":"withheld"}))
    response=client.get("/research/companies/aapl/market")
    assert response.json()["status"]=="withheld" and response.json()["comparison"] is None
    monkeypatch.setattr(main,"settings",main.settings.model_copy(update={"market_data_mode":"local_research"}))
    response=client.get("/research/companies/aapl/market")
    assert response.status_code==200 and response.headers["cache-control"]=="no-store"
    body=response.json()
    assert body["status"]=="available" and body["raw_close"]=="90"
    assert not body["live_recommendations_enabled"] and not body["public_redistribution_allowed"]
    assert body["comparison"]["points"][0]["company_index"]==100


def test_company_events_http_is_offline_and_keeps_context_out_of_scores(tmp_path,monkeypatch):
    from test_company_events import event_store
    _,store=event_store(tmp_path)
    monkeypatch.setattr(main,"settings",main.settings.model_copy(update={"market_data_store":store}))
    def forbidden(*a,**k):raise AssertionError("Event serving must not download")
    monkeypatch.setattr("market_data.fetch_source",forbidden)
    response=client.get("/research/companies/cik0000002488/events")
    assert response.status_code==200 and response.headers["cache-control"]=="no-store"
    body=response.json()
    assert body["status"]=="available" and len(body["filings"])==1
    assert not body["complete_news_coverage"] and not body["affects_strategy_score"]
    assert client.get("/research/companies/unknown/events").json()["status"]=="unavailable"


def test_company_research_http_is_offline_and_explains_unavailable_valuation(tmp_path,monkeypatch):
    from test_company_research import research_store
    store=research_store(tmp_path)
    monkeypatch.setattr(main,"settings",main.settings.model_copy(update={"market_data_store":store}))
    def forbidden(*a,**k):raise AssertionError("Research serving must not download")
    monkeypatch.setattr("market_data.fetch_source",forbidden)
    directory=client.get("/research/companies")
    assert directory.status_code==200 and directory.json()["entries"][0]["tickers"]==["AAPL"]
    detail=client.get("/research/companies/aapl")
    assert detail.status_code==200 and detail.headers["cache-control"]=="no-store"
    body=detail.json()
    assert len(body["history"])==2 and body["latest"]["metrics"]["earnings_yield"] is None
    assert body["live_recommendations_enabled"] is False
    assert body["strategy_evidence"]["score"] is None
    assert len(body["strategy_evidence"]["features"])==5
    assert body["strategy_evidence"]["recommendation_enabled"] is False
    assert client.get("/research/companies/unknown").json()["status"]=="unavailable"


def test_data_readiness_is_offline_typed_and_withholds_provider_values(tmp_path,monkeypatch):
    from datetime import date, datetime, timezone
    from data_pipeline import build_release
    from test_public_data_pipeline import seed_price, PRICE
    cache,store=tmp_path/"raw",tmp_path/"store"
    seed_price(cache)
    build_release(cache,store,as_of=date(2026,10,28),source_ids=[PRICE],
                  now=datetime(2026,10,28,23,tzinfo=timezone.utc))
    monkeypatch.setattr(main,"settings",main.settings.model_copy(update={"market_data_store":store}))
    def forbidden(*args,**kwargs):raise AssertionError("Serving must not download")
    monkeypatch.setattr("market_data.fetch_source",forbidden)
    response=client.get("/research/data-readiness")
    assert response.status_code==200
    assert response.headers["cache-control"]=="no-store"
    result=response.json()
    assert result["schema_version"]=="data-readiness-v1"
    assert not result["stocks"]["ready"] and not result["rentals"]["ready"]
    assert result["stocks"]["items"][2]["count"]==2
    assert "adjusted_close" not in response.text and '"records"' not in response.text
    assert not any(source["public_display_allowed"] for source in result["sources"])
    assert client.post("/research/data-readiness",json={"available_cash":1000}).status_code==405
    (store/"CURRENT.json").write_text('{"manifest_sha256":"../../private"}')
    invalid=client.get("/research/data-readiness")
    assert invalid.status_code==200 and invalid.json()["status"]=="integrity_error"
    assert str(tmp_path) not in invalid.text


def test_research_demo_cannot_enable_live_recommendations_and_rental_solver_is_typed():
    result = client.post("/research/stock-strategy-demo", json={"available_cash_cents": 100003})
    assert result.status_code == 200
    body = result.json()
    assert body["data_kind"] == "synthetic" and not body["live_recommendations_enabled"]
    assert len(body["selected"]) == 10 and body["cash_unallocated_cents"] == 3
    assert client.post("/research/stock-strategy-demo", json={"data_kind": "live"}).status_code == 422
    response = client.post("/real-estate/rental-feasibility", json={"available_capital": "100000", "monthly_rent": "3000"})
    assert response.status_code == 200
    assert response.json()["model_version"] == "rental-feasibility-v1"
    assert response.json()["status"] == "feasible"


def test_rental_v2_cash_purchase_and_reserve_accounting_http():
    from test_rental_underwriting import inputs
    response = client.post("/real-estate/rental-underwriting", json=inputs(down_payment=200_000))
    assert response.status_code == 200
    result = response.json()
    assert result["model_version"] == "rental-underwriting-v2"
    assert result["dscr"] is None
    assert result["annual_noi"] == 14_640
    assert result["initial_cash_required"] == 220_000
    assert result["annual_pre_tax_cash_flow"] == 13_440
    no_capacity = client.post("/real-estate/rental-underwriting", json=inputs(vacancy_rate=1))
    assert no_capacity.status_code == 200
    assert no_capacity.json()["break_even_monthly_rent_per_unit"] is None


def test_contribution_allocation_http_contract_and_invalid_input_privacy():
    from allocation_ui import example_allocation
    response = client.post("/portfolio/contribution-allocation", json=example_allocation())
    assert response.status_code == 200
    assert response.json()["status"] == "optimal"
    assert response.json()["absolute_weight_drift"] == 0
    assert response.headers["cache-control"] == "no-store"
    data = example_allocation()
    data["accounts"][0]["available_cash"] = "PRIVATE-INVALID-AMOUNT"
    invalid = client.post("/portfolio/contribution-allocation", json=data)
    assert invalid.status_code == 422
    assert "PRIVATE-INVALID-AMOUNT" not in invalid.text


def test_infeasible_allocation_is_a_model_result_not_an_http_failure():
    from allocation_ui import example_allocation
    data = example_allocation()
    data["accounts"][0]["allowed_assets"] = []
    response = client.post("/portfolio/contribution-allocation", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "infeasible"
    assert response.json()["trades"] == []


def test_ephemeral_mode_blocks_storage_and_ai_before_body_parsing(tmp_path, monkeypatch):
    database = tmp_path / "blocked.sqlite3"
    monkeypatch.setattr(main, "settings", main.get_settings().model_copy(update={
        "app_mode": "ephemeral", "enable_ai": True, "openai_api_key": "dummy",
        "scenario_db_path": database,
    }))
    routes = [
        ("GET", "/scenario-runs/goal-risk"),
        ("GET", "/scenario-runs/goal-risk/not-a-valid-id"),
        ("POST", "/scenario-runs/goal-risk"),
        ("POST", "/scenario-runs/goal-risk/compare"),
        ("POST", "/optimize"),
        ("POST", "/optimize/"),
    ]
    for method, path in routes:
        response = client.request(method, path, content=b"not valid JSON")
        assert response.status_code == 404
        assert response.headers["cache-control"] == "no-store"
    assert not database.exists()
    assert client.get("/health").json()["ai_enabled"] is False
    assert client.post("/calculate", json={"gross_income": 100_000}).status_code == 200


def test_financial_validation_does_not_echo_input_or_log_payload(caplog):
    secret = "PRIVATE-FINANCIAL-INPUT-12345"
    response = client.post("/calculate", json={"gross_income": secret, "unexpected": secret})
    assert response.status_code == 422
    assert secret not in response.text
    assert secret not in caplog.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_unexpected_api_failure_does_not_log_financial_exception(monkeypatch, caplog):
    from test_goal_explorer import inputs
    secret = "PRIVATE-EXCEPTION-12345"

    def fail(_):
        raise RuntimeError(secret)

    monkeypatch.setattr(main, "explore_goal", fail)
    response = client.post("/scenarios/goal-explorer", json=inputs().model_dump(mode="json"))
    assert response.status_code == 500
    assert secret not in response.text
    assert secret not in caplog.text
    assert response.headers["cache-control"] == "no-store"


def test_ephemeral_mode_cannot_read_existing_local_database(tmp_path, monkeypatch):
    from test_goal_explorer import inputs
    database = tmp_path / "existing.sqlite3"
    settings = main.get_settings().model_copy(update={"app_mode": "local", "scenario_db_path": database})
    monkeypatch.setattr(main, "settings", settings)
    payload = inputs().model_dump(mode="json")
    analysis = {name: value for name, value in payload.items() if name not in ("goal_name", "return_assumptions")}
    analysis.update(annual_return_assumption=0.06, annual_volatility_assumption=0.15, simulation_count=100)
    saved = client.post("/scenario-runs/goal-risk", json={"label": "Local only", "analysis": analysis})
    assert saved.status_code == 200
    before = database.read_bytes()
    monkeypatch.setattr(main, "settings", settings.model_copy(update={"app_mode": "ephemeral"}))
    assert client.get(f"/scenario-runs/goal-risk/{saved.json()['run_id']}").status_code == 404
    assert client.get("/scenario-runs/goal-risk").status_code == 404
    assert database.read_bytes() == before


def test_goal_explorer_request_returns_timeline_and_rejects_invalid_rates():
    from test_goal_explorer import inputs
    payload = inputs().model_dump(mode="json")
    response = client.post("/scenarios/goal-explorer", json=payload)
    assert response.status_code == 200
    base = response.json()["scenarios"][1]
    assert base["timeline"][-1]["balance_nominal"] == 22_000
    assert base["summary"]["required_monthly_contribution"] == 1666.67
    payload["return_assumptions"] = {"low": 0.1, "base": 0, "high": 0.2}
    assert client.post("/scenarios/goal-explorer", json=payload).status_code == 422


def test_health_request_returns_declared_response() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert isinstance(response.json()["tax_year"], int)


def test_calculate_request_returns_tax_metrics() -> None:
    response = client.post("/calculate", json={"gross_income": 100_000})

    assert response.status_code == 200
    payload = response.json()
    assert payload["gross_income"] == 100_000
    assert payload["total_estimated_tax"] > 0
    assert "assumptions" in payload


@pytest.mark.parametrize(
    "payload",
    [
        {"gross_income": -1},
        {"gross_income": 100_000, "unrecognized_field": "reject me"},
    ],
)
def test_calculate_request_rejects_invalid_payloads(payload: dict[str, object]) -> None:
    response = client.post("/calculate", json=payload)

    assert response.status_code == 422


def test_portfolio_request_reports_time_budget_fit() -> None:
    response = client.post(
        "/scenarios/portfolio",
        json={
            "monthly_contribution": 500,
            "years": 10,
            "annual_return_assumption": 0.06,
            "estimated_monthly_hours": 6,
            "available_monthly_hours": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fits_time_budget"] is True
    assert payload["time_budget_utilization"] == 0.6


def test_goal_risk_request_returns_reproducible_distribution() -> None:
    payload = {
        "current_balance": 10_000,
        "monthly_contribution": 500,
        "years": 10,
        "annual_return_assumption": 0.06,
        "annual_volatility_assumption": 0.15,
        "annual_fee_assumption": 0.002,
        "annual_inflation_assumption": 0.03,
        "target_amount_today": 100_000,
        "simulation_count": 500,
        "random_seed": 21,
    }
    first = client.post("/scenarios/goal-risk-analysis", json=payload)
    second = client.post("/scenarios/goal-risk-analysis", json=payload)

    assert first.status_code == 200
    assert first.json() == second.json()
    result = first.json()
    assert 0 <= result["probability_of_reaching_goal"] <= 1
    assert result["ending_balance_p10_in_today_dollars"] <= result["ending_balance_median_in_today_dollars"]
    assert result["ending_balance_median_in_today_dollars"] <= result["ending_balance_p90_in_today_dollars"]


def test_goal_risk_request_rejects_out_of_range_simulation() -> None:
    response = client.post("/scenarios/goal-risk-analysis", json={
        "monthly_contribution": 500,
        "years": 10,
        "annual_return_assumption": 0.06,
        "annual_volatility_assumption": 0.15,
        "simulation_count": 10_000,
    })

    assert response.status_code == 422


def test_goal_sensitivity_request_returns_ranked_factor_spans() -> None:
    response = client.post("/scenarios/goal-sensitivity", json={
        "goal_name": "Down payment",
        "current_balance": 10_000,
        "monthly_contribution": 500,
        "years": 15,
        "annual_return_assumption": 0.06,
        "annual_fee_assumption": 0.002,
        "annual_inflation_assumption": 0.03,
        "target_amount_today": 150_000,
        "sensitivity_ranges": {
            "monthly_contribution": {"low": 400, "high": 600},
            "annual_return": {"low": 0.04, "high": 0.08},
            "annual_fee": {"low": 0.001, "high": 0.003},
            "annual_inflation": {"low": 0.02, "high": 0.04},
        },
    })

    assert response.status_code == 200
    result = response.json()
    assert len(result["factors"]) == 4
    assert [factor["impact_rank"] for factor in result["factors"]] == [1, 2, 3, 4]
    spans = [factor["balance_span_today_dollars"] for factor in result["factors"]]
    assert spans == sorted(spans, reverse=True)


def test_saved_goal_risk_runs_are_persisted_and_compared(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "settings", main.get_settings().model_copy(update={
        "scenario_db_path": tmp_path / "api-runs.sqlite3", "app_mode": "local",
    }))
    common = {
        "current_balance": 10_000,
        "monthly_contribution": 500,
        "years": 10,
        "annual_volatility_assumption": 0.15,
        "annual_fee_assumption": 0.002,
        "annual_inflation_assumption": 0.03,
        "target_amount_today": 100_000,
        "simulation_count": 200,
        "random_seed": 42,
    }
    first = client.post("/scenario-runs/goal-risk", json={
        "label": "Baseline", "analysis": {**common, "annual_return_assumption": 0.05},
    })
    second = client.post("/scenario-runs/goal-risk", json={
        "label": "Higher-return scenario", "analysis": {**common, "annual_return_assumption": 0.07},
    })

    assert first.status_code == 200
    assert second.status_code == 200
    saved = first.json()
    assert saved["model_version"] == "goal-risk-lognormal-v1"
    assert saved["inputs"]["annual_return_assumption"] == 0.05
    listed = client.get("/scenario-runs/goal-risk")
    assert listed.status_code == 200
    assert len(listed.json()["runs"]) == 2
    fetched = client.get(f"/scenario-runs/goal-risk/{saved['run_id']}")
    assert fetched.status_code == 200
    comparison = client.post("/scenario-runs/goal-risk/compare", json={
        "baseline_run_id": first.json()["run_id"],
        "comparison_run_id": second.json()["run_id"],
    })
    assert comparison.status_code == 200
    assert comparison.json()["comparison"]["label"] == "Higher-return scenario"


def test_readiness_request_returns_transparent_review_prompts() -> None:
    response = client.post(
        "/scenarios/readiness-check",
        json={
            "strategy_category": "rental_property",
            "emergency_savings": 8_000,
            "monthly_essential_expenses": 2_000,
            "emergency_fund_target_months": 6,
            "debt_balance_at_highest_apr": 5_000,
            "highest_debt_apr": 0.24,
            "user_debt_apr_comparison": 0.10,
            "liquidity_horizon_months": 36,
            "available_monthly_hours": 4,
            "estimated_strategy_monthly_hours": 6,
            "risk_tolerance_rating": 5,
            "risk_capacity_rating": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["debt_apr_above_user_threshold"] is True
    assert payload["fits_time_budget"] is False
    assert len(payload["review_prompts"]) == 5
    assert "score" not in payload


def test_readiness_request_rejects_invalid_risk_rating() -> None:
    response = client.post(
        "/scenarios/readiness-check",
        json={
            "strategy_category": "portfolio",
            "emergency_savings": 2_000,
            "monthly_essential_expenses": 2_000,
            "emergency_fund_target_months": 3,
            "available_monthly_hours": 2,
            "risk_tolerance_rating": 6,
            "risk_capacity_rating": 2,
        },
    )

    assert response.status_code == 422


def test_debt_payoff_request_returns_both_methods() -> None:
    response = client.post(
        "/scenarios/debt-payoff",
        json={
            "debts": [{
                "name": "No-interest balance",
                "balance": 1_200,
                "annual_apr": 0,
                "minimum_monthly_payment": 100,
            }],
            "extra_monthly_payment": 100,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["avalanche"]["payoff_months"] == 6
    assert payload["snowball"]["payoff_months"] == 6
    assert payload["avalanche"]["total_interest"] == 0


def test_debt_payoff_request_rejects_invalid_minimum_payment() -> None:
    response = client.post(
        "/scenarios/debt-payoff",
        json={
            "debts": [{"name": "Card", "balance": 1_000, "annual_apr": 0.24,
                       "minimum_monthly_payment": 0}],
            "extra_monthly_payment": 100,
        },
    )

    assert response.status_code == 422
