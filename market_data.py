"""Bounded, content-addressed downloads for the local public-data audit.

No private inputs or credentials. Not wired to a public endpoint. Sources are
fixed in market_sources, including the canonical SEC CIK template; user-supplied
URLs cannot become download destinations.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from email.utils import parsedate_to_datetime
from math import isfinite
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from market_sources import PublicSource, source_for_id
from public_data_store import file_lock, provider_turn, atomic_json, strict_json


class SourceDownloadError(RuntimeError):
    def __init__(self, message, *, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class SourceConfigurationError(SourceDownloadError):
    pass


class SameHostRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        target, original = urlparse(new_url), urlparse(request.full_url)
        if target.scheme != "https" or target.hostname != original.hostname or target.username or target.password:
            raise SourceDownloadError("Unexpected source redirect")
        return super().redirect_request(request, response, code, message, headers, new_url)


@dataclass(frozen=True)
class SourceSnapshot:
    path: Path
    metadata: dict
    from_cache: bool


def _safe_source(source):
    if source != source_for_id(source.source_id):
        raise ValueError("Only registered public sources may be downloaded")
    url = urlparse(source.url)
    if url.scheme != "https" or url.username or url.password:
        raise ValueError("Invalid public source URL")


def _validate_payload(path, kind):
    if kind == 'sec_filing_html':
        body=path.read_text(encoding='utf-8-sig')
        if '<html' not in body.lower() or 'dei:DocumentType'.lower() not in body.lower():
            raise SourceDownloadError('Expected an inline-XBRL filing, not a challenge or error page')
        return
    if kind == "hud_xlsx":
        from zipfile import ZipFile, BadZipFile
        try:
            with ZipFile(path) as archive:
                if "xl/workbook.xml" not in archive.namelist() or sum(info.file_size for info in archive.infolist()) > 100*1024*1024:
                    raise SourceDownloadError("Unexpected or oversized workbook")
        except BadZipFile:
            raise SourceDownloadError("Invalid workbook") from None
        return
    if kind in ("json", "companyfacts_json", "adjusted_daily_json", "submissions_json"):
        with path.open(encoding="utf-8-sig") as stream:
            value = strict_json(stream.read())
        if kind == "json":
            if not isinstance(value, dict) or not value.get("fields") or not isinstance(value.get("data"), list):
                raise SourceDownloadError("Unexpected issuer mapping schema")
        elif kind == "adjusted_daily_json":
            if not isinstance(value, dict) or not value.get("Meta Data") or not value.get("Time Series (Daily)"):
                raise SourceDownloadError("Provider returned no adjusted daily dataset")
        elif kind == "submissions_json":
            if not isinstance(value,dict) or not value.get("cik") or not isinstance(value.get("filings",{}).get("recent"),dict):
                raise SourceDownloadError("Unexpected submissions schema")
        elif not isinstance(value, dict) or not value.get("cik") or not value.get("entityName") or not isinstance(value.get("facts"), dict):
            raise SourceDownloadError("Unexpected company facts schema")
        return
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        prefix = stream.read(32_000)
    if "<html" in prefix.lower() or "<!doctype" in prefix.lower() or not prefix.strip():
        raise SourceDownloadError("Source returned HTML or empty data")
    if kind == "pipe" and "GEOID_ZCTA5_20" not in prefix.splitlines()[0]:
        raise SourceDownloadError("Unexpected geographic relationship schema")
    if kind == 'symbol_directory_pipe' and not {'Security Name','Test Issue','ETF'}.issubset(prefix.splitlines()[0].split('|')):
        raise SourceDownloadError('Unexpected security listing directory schema')
    if kind == "csv" and not {"RegionID", "RegionName", "RegionType"}.issubset(prefix.splitlines()[0].split(",")):
        raise SourceDownloadError("Unexpected housing source schema")
    if kind == "holdings_csv" and not all(value in prefix for value in ("Ticker", "Asset Class", "Market Value")):
        raise SourceDownloadError("Unexpected holdings source schema")


def load_snapshot(source_id, cache_root) -> SourceSnapshot:
    source = source_for_id(source_id)
    directory = Path(cache_root) / source_id
    metadata = strict_json((directory / "latest.json").read_text(encoding="utf-8"))
    if not isinstance(metadata,dict):
        raise SourceDownloadError("Invalid snapshot manifest")
    checksum = metadata.get("sha256", "")
    if (not isinstance(checksum,str) or not re.fullmatch(r"[0-9a-f]{64}", checksum)
            or metadata.get("source_url") != source.url or metadata.get("source_id")!=source_id):
        raise SourceDownloadError("Invalid snapshot manifest")
    path = directory / f"{checksum}.raw"
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    if digest.hexdigest() != checksum:
        raise SourceDownloadError("Snapshot checksum mismatch")
    return SourceSnapshot(path, metadata, True)


def fetch_source(source: PublicSource, cache_root, **kwargs) -> SourceSnapshot:
    _safe_source(source)
    with file_lock(Path(cache_root)/".source_locks"/(source.source_id+".lock")):
        return _fetch_source(source, cache_root, **kwargs)


def _fetch_source(source: PublicSource, cache_root, *, refresh=False, max_bytes=200*1024*1024,
                 timeout=20, attempts=2, opener=None, sleep=time.sleep, validator=None) -> SourceSnapshot:
    _safe_source(source)
    opener = opener or build_opener(SameHostRedirects()).open
    if not 1 <= attempts <= 3 or not 0 < timeout <= 60 or not 0 < max_bytes <= 200*1024*1024:
        raise ValueError("Invalid download bounds")
    if source.format in ("json","companyfacts_json","adjusted_daily_json","hud_xlsx","submissions_json"):
        max_bytes=min(max_bytes,25*1024*1024)
    if source.format=='sec_filing_html':max_bytes=min(max_bytes,8*1024*1024)
    if not refresh:
        try:
            return load_snapshot(source.source_id, cache_root)
        except FileNotFoundError:
            pass
    directory = Path(cache_root) / source.source_id
    directory.mkdir(parents=True, exist_ok=True)
    user_agent="InvestmentResearchAudit/0.2 (educational public-data coverage inspection)"
    if source.source_id.startswith("sec_"):
        from source_policy import SourceAccessSettings
        user_agent=SourceAccessSettings().sec_user_agent or ""
        if (not 10<=len(user_agent)<=200 or "\n" in user_agent or "\r" in user_agent
                or not re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+",user_agent)):
            raise SourceConfigurationError("SEC downloads require SEC_USER_AGENT with an operator contact email")
    for attempt in range(attempts):
        temporary = directory / f"{uuid4().hex}.part"
        try:
            request = Request(source.url, headers={
                "User-Agent": user_agent,
                "Accept": "text/csv,text/plain,application/octet-stream,*/*",
            })
            digest, count = hashlib.sha256(), 0
            started = time.monotonic()
            host = urlparse(source.url).hostname
            provider = "sec.gov" if host.endswith("sec.gov") else host
            with provider_turn(cache_root, provider, 1 if provider == "sec.gov" else .5), opener(request, timeout=timeout) as response:
                if response.status != 200:
                    raise SourceDownloadError("Source did not return HTTP 200", status_code=response.status)
                # No provider redirect may silently change the data authority.
                if urlparse(response.geturl()).hostname != urlparse(source.url).hostname:
                    raise SourceDownloadError("Unexpected source redirect")
                with temporary.open("wb") as stream:
                    while block := response.read(64*1024):
                        count += len(block)
                        if count > max_bytes or time.monotonic()-started > 120:
                            raise SourceDownloadError("Source exceeded download bounds")
                        stream.write(block)
                        digest.update(block)
                metadata = {
                    "source_id": source.source_id, "source_url": source.url,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "sha256": digest.hexdigest(), "bytes": count,
                    "content_type": response.headers.get("Content-Type"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "role": source.role, "rights_status": source.rights_status,
                }
            _validate_payload(temporary, source.format)
            if validator:
                validator(temporary)
            destination = directory / f"{metadata['sha256']}.raw"
            temporary.replace(destination)
            # Retain retrieval evidence even when identical bytes are downloaded again.
            atomic_json(directory / "receipts" / (uuid4().hex+".json"), metadata)
            atomic_json(directory / "latest.json", metadata)
            return SourceSnapshot(destination, metadata, False)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            retry = not isinstance(error, HTTPError) or error.code == 429 or error.code >= 500
            if not retry or attempt+1 >= attempts:
                raise SourceDownloadError("Public source download failed; previous snapshot preserved",
                                          status_code=error.code if isinstance(error, HTTPError) else None) from None
            delay = min(2 ** attempt, 4)
            if isinstance(error, HTTPError):
                requested_delay=0
                retry_after=(error.headers or {}).get("Retry-After",0)
                try:
                    requested_delay=float(retry_after)
                except (ValueError, TypeError):
                    try:
                        requested=parsedate_to_datetime(retry_after)
                        requested_delay=(requested-datetime.now(timezone.utc)).total_seconds()
                    except (ValueError,TypeError,OverflowError):
                        pass
                if isfinite(requested_delay):
                    if requested_delay>60:
                        raise SourceDownloadError("Provider retry delay exceeds local budget; previous snapshot preserved",
                                                  status_code=error.code) from None
                    delay=max(delay,requested_delay)
            sleep(delay)
        finally:
            temporary.unlink(missing_ok=True)
    raise SourceDownloadError("No download attempt completed")
