"""Privacy policy tests independent of HTTP runtimes and real AI services."""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
import pytest

import ai_service
from config import Settings
import main
from privacy import clear_financial_session, require_ai, require_saved_runs


def test_default_is_ephemeral_even_with_an_api_key():
    settings = Settings(_env_file=None, app_mode="ephemeral", enable_ai=True, openai_api_key="dummy")
    assert not settings.saved_runs_enabled
    assert not settings.ai_enabled
    with pytest.raises(HTTPException):
        require_saved_runs(settings)
    with pytest.raises(HTTPException):
        require_ai(settings)


def test_local_ai_requires_explicit_opt_in_and_a_key():
    settings = Settings(_env_file=None, app_mode="local", enable_ai=False, openai_api_key="dummy")
    assert settings.saved_runs_enabled
    assert not settings.ai_enabled
    assert settings.model_copy(update={"enable_ai": True}).ai_enabled
    assert not settings.model_copy(update={"enable_ai": True, "openai_api_key": None}).ai_enabled


def test_direct_saved_run_handler_is_blocked_without_opening_database(tmp_path, monkeypatch):
    database = tmp_path / "must-not-exist.sqlite3"
    monkeypatch.setattr(main, "settings", Settings(_env_file=None, app_mode="ephemeral", scenario_db_path=database))
    with pytest.raises(HTTPException) as error:
        main.saved_goal_risk_run(uuid4())
    assert error.value.status_code == 404
    assert not database.exists()


def test_ai_client_is_blocked_before_loading_sdk(monkeypatch):
    monkeypatch.setattr(ai_service, "get_settings", lambda: Settings(_env_file=None, app_mode="ephemeral", openai_api_key="dummy", enable_ai=True))
    with pytest.raises(ai_service.AIServiceError, match="disabled"):
        ai_service._client()


def test_clear_drops_all_session_references_including_legacy_history():
    session = {"_explorer_inputs": {"balance": 100}, "_explorer_plans": ["private"],
               "saved_goal_risk_runs": ["legacy"], "explorer_import_test": b"private", "_explorer_risk": "risk"}
    clear_financial_session(session)
    assert session == {}


def test_streamlit_privacy_configuration_is_explicit():
    import tomllib
    config = tomllib.loads(Path(__file__).with_name(".streamlit").joinpath("config.toml").read_text())
    assert config["browser"]["gatherUsageStats"] is False
    assert config["server"]["enableXsrfProtection"] is True
    assert config["server"]["enableStaticServing"] is False
    assert config["server"]["address"] == "127.0.0.1"
    assert config["client"]["showErrorDetails"] == "none"


def test_optional_ai_requests_disable_response_storage(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from schemas import UserFinancialProfile
    from tax_engine import calculate_tax
    captured = []

    async def parse(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(output_parsed=UserFinancialProfile(gross_income=100_000))

    async def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(output_text="Review the supplied deterministic metrics.")

    client = SimpleNamespace(responses=SimpleNamespace(parse=parse, create=create))
    monkeypatch.setattr(ai_service, "_client", lambda: (client, "test-model"))
    profile = asyncio.run(ai_service.parse_financial_profile("Synthetic example"))
    asyncio.run(ai_service.format_strategy_report(calculate_tax(profile)))
    assert len(captured) == 2
    assert all(call["store"] is False for call in captured)
