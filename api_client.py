"""Small synchronous HTTP client shared by the Streamlit interface."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


class ApiClientError(RuntimeError):
    """Readable API failure suitable for showing in the local UI."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def request_json(api_base_url: str, path: str, *, method: str = "GET",
                 payload: dict[str, Any] | None = None, timeout_seconds: float = 10.0) -> dict[str, Any]:
    """Send one JSON request and return its decoded object response.

    The timeout keeps a disconnected local backend from freezing the Streamlit
    page indefinitely. Work is bounded by the response size and JSON parsing.
    """
    base = api_base_url.strip().rstrip("/")
    if not base:
        raise ApiClientError("Enter the FastAPI server address first.")
    url = urljoin(base + "/", path.lstrip("/"))
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method.upper())

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
    except HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
            detail = error_body.get("detail", error_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = "The API returned an error response."
        raise ApiClientError(f"API returned HTTP {exc.code}: {detail}", status_code=exc.code) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ApiClientError(
            "Could not reach the FastAPI server. Start it in a separate terminal and check the API URL."
        ) from exc

    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiClientError("The API response was not valid JSON.") from exc
    if not isinstance(decoded, dict):
        raise ApiClientError("The API response was not a JSON object.")
    return decoded


def get_json(api_base_url: str, path: str, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
    return request_json(api_base_url, path, timeout_seconds=timeout_seconds)


def post_json(api_base_url: str, path: str, payload: dict[str, Any], *,
              timeout_seconds: float = 10.0) -> dict[str, Any]:
    return request_json(api_base_url, path, method="POST", payload=payload,
                        timeout_seconds=timeout_seconds)
