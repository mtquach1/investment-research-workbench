"""Transport/cache integrity checks with fake responses; no live network in tests."""

from dataclasses import replace
import io
import json
from urllib.error import HTTPError

import pytest

from market_data import SameHostRedirects, SourceDownloadError, fetch_source, load_snapshot
from market_sources import SOURCES


SOURCE = SOURCES["zillow_sfr_value_zip"]
VALID = b"RegionID,RegionName,RegionType,2026-09-30\n1,01234,zip,100\n"


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "text/csv"}

    def geturl(self):
        return SOURCE.url


def test_content_addressed_snapshot_and_cache_reuse(tmp_path):
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        return Response(VALID)

    first = fetch_source(SOURCE, tmp_path, opener=opener)
    second = fetch_source(SOURCE, tmp_path, opener=opener)
    assert calls == [1]
    assert first.path == second.path
    assert not first.from_cache and second.from_cache
    assert first.path.read_bytes() == VALID
    assert first.metadata["rights_status"] == "public_display_not_cleared"
    assert first.path.name == first.metadata["sha256"] + ".raw"


@pytest.mark.parametrize("payload", [b"<html>Access check</html>", b"", b"unexpected,schema\n1,2\n"])
def test_invalid_refresh_preserves_last_manifest_and_removes_partial_files(tmp_path, payload):
    first = fetch_source(SOURCE, tmp_path, opener=lambda *a, **k: Response(VALID))
    manifest = first.path.parent / "latest.json"
    previous = manifest.read_bytes()
    with pytest.raises(SourceDownloadError):
        fetch_source(SOURCE, tmp_path, refresh=True, opener=lambda *a, **k: Response(payload))
    assert manifest.read_bytes() == previous
    assert load_snapshot(SOURCE.source_id, tmp_path).path == first.path
    assert not list(first.path.parent.glob("*.part"))


def test_transport_retry_and_failure_status_do_not_expose_body(tmp_path):
    calls, delays = [], []

    def opener(*args, **kwargs):
        calls.append(1)
        raise HTTPError(SOURCE.url, 503, "PRIVATE PROVIDER BODY", {}, None)

    with pytest.raises(SourceDownloadError) as error:
        fetch_source(SOURCE, tmp_path, opener=opener, sleep=delays.append)
    assert error.value.status_code == 503
    assert "PRIVATE" not in str(error.value)
    assert len(calls) == 2 and delays == [1]


def test_403_is_not_retried_or_treated_as_valid_data(tmp_path):
    calls = []

    def opener(*args, **kwargs):
        calls.append(1)
        raise HTTPError(SOURCE.url, 403, "Forbidden", {}, None)

    with pytest.raises(SourceDownloadError) as error:
        fetch_source(SOURCE, tmp_path, opener=opener)
    assert error.value.status_code == 403
    assert len(calls) == 1
    assert not (tmp_path / SOURCE.source_id / "latest.json").exists()


def test_byte_limits_and_corrupted_cache_fail_closed(tmp_path):
    with pytest.raises(SourceDownloadError):
        fetch_source(SOURCE, tmp_path, max_bytes=10, opener=lambda *a, **k: Response(VALID))
    first = fetch_source(SOURCE, tmp_path, opener=lambda *a, **k: Response(VALID))
    first.path.write_bytes(b"corrupted")
    with pytest.raises(SourceDownloadError, match="checksum"):
        load_snapshot(SOURCE.source_id, tmp_path)


def test_unregistered_source_and_manifest_traversal_rejected(tmp_path):
    with pytest.raises(ValueError):
        fetch_source(replace(SOURCE, url="https://example.com/private"), tmp_path)
    first = fetch_source(SOURCE, tmp_path, opener=lambda *a, **k: Response(VALID))
    metadata = dict(first.metadata, sha256="../../secret")
    (first.path.parent / "latest.json").write_text(json.dumps(metadata))
    with pytest.raises(SourceDownloadError):
        load_snapshot(SOURCE.source_id, tmp_path)


def test_redirect_is_rejected_before_following_to_a_different_host():
    from urllib.request import Request
    with pytest.raises(SourceDownloadError):
        SameHostRedirects().redirect_request(Request(SOURCE.url), None, 302, "Found", {}, "https://example.com/other")
