"""Offline-first, transactional public research data releases.

Transport -> semantic adapter -> immutable normalized artifact -> release
manifest -> atomic pointer. A failed source can retain verified earlier data;
its failure remains visible. No private inputs, credentials, background threads
or network access are required to read a release.
"""

from datetime import date, datetime, timezone, timedelta
import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from data_audit import county_zctas
from market_data import SourceConfigurationError, SourceDownloadError, fetch_source, load_snapshot
from market_sources import SOURCES, source_for_id
from public_data_store import (DataIntegrityError, atomic_bytes, atomic_json,
                               canonical_bytes, file_lock, read_verified, strict_json)
from source_adapters import ADAPTER_VERSION, normalize_source
from source_policy import policy_dict, policy_for


PIPELINE_VERSION="public-release-v1"


class Contract(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)


class Failure(Contract):
    stage: Literal["transport","normalization","cache","configuration"]
    code: Literal["source_unavailable","invalid_dataset","cache_unavailable","operator_contact_required"]
    http_status: int | None = Field(default=None,ge=100,le=599)
    observed_at: datetime | None = None


class PolicyReference(Contract):
    provider: str
    refresh_hours: int = Field(gt=0,le=87600,strict=True)
    observation_max_age_days: int | None = Field(default=None,gt=0,le=36500,strict=True)
    documentation_url: str
    rights_evidence_url: str | None
    public_display_allowed: bool = Field(strict=True)
    rights_status: str
    reviewed_on: date


class TableReference(Contract):
    source_id: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_url: str
    retrieved_at: datetime
    table_as_of: date
    observation_date: date | None
    row_count: int = Field(gt=0,le=1000000,strict=True)
    kind: str
    state: Literal["normalized","cached_after_refresh_failure","retained_previous_release"]
    summary: dict[str,Any]
    policy: dict[str,Any]

    @field_validator("policy")
    @classmethod
    def validate_policy(cls,value):
        return PolicyReference.model_validate(value).model_dump(mode="json")

    @model_validator(mode="after")
    def registered_identity(self):
        if self.source_url!=source_for_id(self.source_id).url:
            raise ValueError("Unregistered artifact source")
        if self.retrieved_at.tzinfo is None:
            raise ValueError("Retrieval timestamp needs a timezone")
        if self.observation_date and self.observation_date>self.table_as_of:
            raise ValueError("Future normalized observation")
        return self


class ReleaseManifest(Contract):
    pipeline_version: Literal["public-release-v1"] = PIPELINE_VERSION
    adapter_version: Literal["public-normalization-v1"] = ADAPTER_VERSION
    as_of: date
    tables: dict[str,TableReference]
    failures: dict[str,Failure]
    stock_recommendations_ready: Literal[False] = False
    rental_discovery_ready: Literal[False] = False

    @model_validator(mode="after")
    def coherent_tables(self):
        if not self.tables:
            raise ValueError("An empty release cannot replace good data")
        for key, table in self.tables.items():
            if key!=table.source_id or table.table_as_of>self.as_of:
                raise ValueError("Incoherent table reference")
        for key in self.failures:
            source_for_id(key)
        return self


def load_release(root, *, verify_tables=True):
    root=Path(root)
    with (root/"CURRENT.json").open("rb") as stream:
        payload=stream.read(65537)
    if len(payload)>65536:
        raise DataIntegrityError("Invalid release pointer size")
    pointer=strict_json(payload)
    if not isinstance(pointer,dict):
        raise DataIntegrityError("Invalid release pointer")
    digest=pointer.get("manifest_sha256","")
    # Validate before constructing a path from an on-disk pointer.
    import re
    if not isinstance(digest,str) or not re.fullmatch(r"[0-9a-f]{64}",digest):
        raise DataIntegrityError("Invalid release pointer")
    try:
        manifest=ReleaseManifest.model_validate(read_verified(root/"releases"/(digest+".json"),digest))
        if verify_tables:
            for reference in manifest.tables.values():
                read_table(root,reference)
    except FileNotFoundError:
        raise DataIntegrityError("Release references a missing artifact") from None
    return digest,manifest


def read_table(root, reference):
    data=read_verified(Path(root)/"artifacts"/(reference.artifact_sha256+".json"),reference.artifact_sha256)
    if (not isinstance(data,dict) or not isinstance(data.get("records"),list)
            or data.get("source_id")!=reference.source_id or data.get("source_sha256")!=reference.source_sha256
            or data.get("as_of")!=reference.table_as_of.isoformat()
            or data.get("adapter_version")!=ADAPTER_VERSION
            or len(data.get("records",[]))!=reference.row_count):
        raise DataIntegrityError("Normalized table disagrees with release manifest")
    return data


def _due(snapshot, source_id, now):
    if not isinstance(snapshot.metadata.get("retrieved_at"),str):
        raise DataIntegrityError("Invalid snapshot retrieval timestamp")
    stamp=datetime.fromisoformat(snapshot.metadata["retrieved_at"])
    if stamp.tzinfo is None or stamp>now+timedelta(minutes=5):
        raise DataIntegrityError("Invalid snapshot retrieval timestamp")
    return (now-stamp).total_seconds()>=policy_for(source_id).refresh_hours*3600


def build_release(cache_root, root, *, as_of, download=False, force_refresh=False,
                  source_ids=None, now=None, fetch=fetch_source, expected_directory_sha=None,
                  expected_release_id=None, progress=None, receipt_clock=None, publication_check=None):
    if force_refresh and not download:
        raise ValueError("Refresh requires explicit download permission")
    selective=source_ids is not None
    source_ids=sorted(SOURCES if source_ids is None else source_ids)
    if not source_ids or len(source_ids)!=len(set(source_ids)):
        raise ValueError("Invalid registered-source selection")
    for key in source_ids:
        source_for_id(key)
    if type(as_of) is not date:
        raise ValueError("A calculation date is required")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None or as_of>now.date():
        raise ValueError("Invalid publication clock")
    root=Path(root)
    with file_lock(root/"writer.lock"):
        try:
            previous_id,previous=load_release(root)
        except FileNotFoundError:
            previous_id,previous=None,None
        if expected_release_id is not None and previous_id!=expected_release_id:
            raise ValueError('Public release changed; re-plan before refreshing sources')
        if previous and previous.as_of>as_of:
            raise ValueError("Use a separate store for an older as-of date")
        if expected_directory_sha is not None:
            reference=previous.tables.get("sec_ticker_exchange") if previous else None
            if reference is None or reference.source_sha256!=expected_directory_sha:
                raise ValueError("SEC directory changed; create a new import plan")
        if not selective and previous:
            source_ids=sorted(set(source_ids)|set(previous.tables)|set(previous.failures))
        geography=set()
        try:
            geography=set(county_zctas(load_snapshot("census_zcta_county_2020",cache_root).path))
        except (OSError,ValueError,SourceDownloadError):
            if previous and "census_zcta_county_2020" in previous.tables:
                geography={row["zcta"] for row in read_table(root,previous.tables["census_zcta_county_2020"])["records"]}
        # Geometry must be established before dependent housing adapters run.
        source_ids.sort(key=lambda name:(name!="census_zcta_county_2020",name))
        tables=dict(previous.tables) if selective and previous else {}
        failures={key:value for key,value in previous.failures.items() if key not in source_ids} if selective and previous else {}
        for source_index,source_id in enumerate(source_ids):
            snapshot,normalized=None,None
            try:
                snapshot=load_snapshot(source_id,cache_root)
                _due(snapshot,source_id,now)
            except (OSError,ValueError,SourceDownloadError):
                snapshot=None
            failure=None
            if previous and source_id in previous.failures and previous.failures[source_id].stage in ("transport","configuration"):
                failure=previous.failures[source_id]
            if download and (snapshot is None or force_refresh or _due(snapshot,source_id,now)):
                prepared=[]
                def validate(path):
                    prepared.append(normalize_source(source_id,path,as_of=as_of,geography=geography))
                try:
                    candidate=fetch(source_for_id(source_id),cache_root,refresh=True,validator=validate)
                    receipt_now=receipt_clock() if receipt_clock else now
                    if receipt_now.tzinfo is None or receipt_now<now:raise ValueError('Invalid receipt assessment clock')
                    _due(candidate,source_id,receipt_now)
                    snapshot=candidate
                    normalized=prepared[0] if prepared else None
                    failure=None
                except SourceConfigurationError:
                    failure=Failure(stage="configuration",code="operator_contact_required",observed_at=now)
                except SourceDownloadError as error:
                    failure=Failure(stage="transport",code="source_unavailable",http_status=error.status_code,observed_at=now)
                except (OSError,ValueError,KeyError,TypeError):
                    failure=Failure(stage="normalization",code="invalid_dataset")
            if snapshot is None:
                failure=failure or Failure(stage="cache",code="cache_unavailable")
            elif normalized is None:
                try:
                    normalized=normalize_source(source_id,snapshot.path,as_of=as_of,geography=geography)
                except (OSError,ValueError,KeyError,TypeError):
                    failure=Failure(stage="normalization",code="invalid_dataset")
            if normalized is not None:
                if source_id=="census_zcta_county_2020":
                    geography={row["zcta"] for row in normalized["records"]}
                artifact={**normalized,"as_of":as_of.isoformat(),"source_id":source_id,
                    "source_sha256":snapshot.metadata["sha256"],"source_url":source_for_id(source_id).url,
                    "retrieved_at":snapshot.metadata["retrieved_at"]}
                payload=canonical_bytes(artifact)
                digest=hashlib.sha256(payload).hexdigest()
                destination=root/"artifacts"/(digest+".json")
                if destination.exists():
                    read_verified(destination,digest)
                else:
                    atomic_bytes(destination,payload)
                tables[source_id]=TableReference(source_id=source_id,artifact_sha256=digest,
                    source_sha256=artifact["source_sha256"],source_url=artifact["source_url"],
                    retrieved_at=artifact["retrieved_at"],table_as_of=as_of,observation_date=normalized["observation_date"],
                    row_count=len(normalized["records"]),kind=normalized["kind"],summary=normalized["summary"],
                    state="cached_after_refresh_failure" if failure else "normalized",policy=policy_dict(source_id))
            elif previous and source_id in previous.tables:
                reference=previous.tables[source_id]
                read_table(root,reference)
                tables[source_id]=reference.model_copy(update={"state":"retained_previous_release"})
            if failure:
                failures[source_id]=failure
            if progress:progress({'completed_sources':source_index+1,'total_sources':len(source_ids),
                'source_id':source_id,'retained_after_failure':failure is not None})
        attempt={"attempted_at":now.isoformat(),"as_of":as_of.isoformat(),
                 "source_count":len(source_ids),"table_count":len(tables),
                 "failures":{key:value.model_dump(mode="json") for key,value in failures.items()}}
        if not tables:
            atomic_json(root/"last_attempt.json",dict(attempt,status="no_release_published"))
            raise DataIntegrityError("No validated tables; existing release preserved")
        manifest=ReleaseManifest(as_of=as_of,tables=tables,failures=failures)
        if publication_check is not None:
            try:
                publication_check(manifest)
            except ValueError:
                atomic_json(root/"last_attempt.json",dict(attempt,status="rejected_before_publication"))
                raise
        payload=canonical_bytes(manifest.model_dump(mode="json"))
        digest=hashlib.sha256(payload).hexdigest()
        destination=root/"releases"/(digest+".json")
        if destination.exists():
            read_verified(destination,digest)
        else:
            atomic_bytes(destination,payload)
        # Validate every artifact before publishing the only serving pointer.
        for reference in manifest.tables.values():
            read_table(root,reference)
        if digest!=previous_id:
            atomic_json(root/"CURRENT.json",{"manifest_sha256":digest})
        atomic_json(root/"last_attempt.json",dict(attempt,status="degraded" if failures else "normalized",release_id=digest))
        return digest,manifest
