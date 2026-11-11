"""Small filesystem transactions for public data only; no user financial state.

OS locks are released on process death. Readers follow one atomic pointer into
immutable, hash-verified files; a partially built release is never served.
"""

from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import time
from uuid import uuid4


class DataIntegrityError(ValueError):
    pass


def strict_json(payload):
    def unique_pairs(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise DataIntegrityError("Duplicate JSON field")
            result[key]=value
        return result
    def reject_constant(value):
        raise DataIntegrityError("Non-finite JSON number")
    return json.loads(payload,object_pairs_hook=unique_pairs,parse_constant=reject_constant)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def atomic_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(uuid4().hex+".part")
    try:
        with temporary.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path, value):
    atomic_bytes(path, canonical_bytes(value))


def read_verified(path, checksum, *, maximum_bytes=32*1024*1024):
    if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise DataIntegrityError("Invalid artifact checksum")
    with Path(path).open("rb") as stream:
        size=os.fstat(stream.fileno()).st_size
        if size>maximum_bytes:
            raise DataIntegrityError('Artifact exceeds byte budget')
        # A maximum-sized read allocated a 32 MiB buffer for every tiny JSON
        # artifact on Windows. Read only its measured size plus a growth sentinel;
        # every payload still receives the full checksum and strict JSON checks.
        payload=stream.read(size+1)
        if len(payload)!=size:
            raise DataIntegrityError('Artifact changed size while being read')
    if len(payload) > maximum_bytes or hashlib.sha256(payload).hexdigest() != checksum:
        raise DataIntegrityError("Artifact integrity check failed")
    return strict_json(payload)


@contextmanager
def file_lock(path, *, timeout=15):
    if not 0 <= timeout <= 60:
        raise ValueError("Invalid lock timeout")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic()+timeout
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError("Public data writer is busy") from None
                time.sleep(.025)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def provider_turn(root, provider, interval, *, clock=time.time, sleep=time.sleep):
    """Serialize and space requests across cooperating processes sharing a cache."""
    if not re.fullmatch(r"[a-z0-9._-]+", provider) or not .1 <= interval <= 10:
        raise ValueError("Invalid provider policy")
    directory = Path(root)/".provider_locks"
    with file_lock(directory/(provider+".lock")):
        stamp = directory/(provider+".json")
        previous = json.loads(stamp.read_text()) if stamp.exists() else {}
        delay = min(interval, max(0, float(previous.get("requested_at", 0))+interval-clock()))
        if delay:
            sleep(delay)
        atomic_json(stamp, {"requested_at":clock()})
        yield
