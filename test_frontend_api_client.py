"""Request construction and error handling for the Streamlit API client."""

from io import BytesIO
from urllib.error import HTTPError

import pytest

import api_client
from api_client import ApiClientError


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_post_json_encodes_payload_and_decodes_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(api_client, "urlopen", fake_urlopen)
    result = api_client.post_json("http://localhost:8000/", "/calculate", {"gross_income": 100_000})

    request = captured["request"]
    assert request.full_url == "http://localhost:8000/calculate"
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert request.data == b'{"gross_income": 100000}'
    assert captured["timeout"] == 10.0
    assert result == {"ok": True}


def test_http_error_surfaces_api_validation_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(*_: object, **__: object) -> None:
        raise HTTPError("http://localhost/calculate", 422, "Invalid input", {},
                        BytesIO(b'{"detail": "gross_income must be positive"}'))

    monkeypatch.setattr(api_client, "urlopen", fake_urlopen)
    with pytest.raises(ApiClientError, match="HTTP 422: gross_income must be positive") as error:
        api_client.post_json("http://localhost:8000", "/calculate", {"gross_income": -1})
    assert error.value.status_code == 422


def test_connection_failure_returns_local_backend_guidance(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(*_: object, **__: object) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(api_client, "urlopen", fake_urlopen)
    with pytest.raises(ApiClientError, match="Start it in a separate terminal"):
        api_client.get_json("http://127.0.0.1:8000", "/health")


def test_blank_api_address_is_rejected_before_network_call() -> None:
    with pytest.raises(ApiClientError, match="Enter the FastAPI server address"):
        api_client.get_json("  ", "/health")
