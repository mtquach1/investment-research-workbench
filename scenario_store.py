"""Local SQLite persistence for explicitly saved goal-risk simulation runs.

This store is intended for a single-user local app. A hosted or multi-user service
needs authentication and per-user data isolation before enabling these endpoints.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator
from uuid import UUID, uuid4


GOAL_RISK_MODEL_VERSION = "goal-risk-lognormal-v1"


@contextmanager
def _connection(database_path: str | Path) -> Iterator[sqlite3.Connection]:
    path = Path(database_path)
    if path.parent != Path(""):
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS goal_risk_runs (
                run_id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                created_at TEXT NOT NULL,
                model_version TEXT NOT NULL,
                inputs_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            )"""
        )
        yield connection
    finally:
        connection.close()


def _decode_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "run_id": row["run_id"],
        "scenario_type": "goal-risk-analysis",
        "label": row["label"],
        "created_at": row["created_at"],
        "model_version": row["model_version"],
        "inputs": json.loads(row["inputs_json"]),
        "result": json.loads(row["result_json"]),
    }


def save_goal_risk_run(*, label: str, inputs: dict[str, object], result: dict[str, object],
                       database_path: str | Path) -> dict[str, object]:
    run_id = uuid4()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    inputs_json = json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
    result_json = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    with _connection(database_path) as connection:
        connection.execute(
            """INSERT INTO goal_risk_runs
               (run_id, label, created_at, model_version, inputs_json, result_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(run_id), label, created_at, GOAL_RISK_MODEL_VERSION, inputs_json, result_json),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM goal_risk_runs WHERE run_id = ?", (str(run_id),)).fetchone()
    assert row is not None
    return _decode_row(row)


def get_goal_risk_run(run_id: UUID, *, database_path: str | Path) -> dict[str, object] | None:
    with _connection(database_path) as connection:
        row = connection.execute("SELECT * FROM goal_risk_runs WHERE run_id = ?", (str(run_id),)).fetchone()
    return None if row is None else _decode_row(row)


def list_goal_risk_runs(*, database_path: str | Path, limit: int = 50) -> list[dict[str, object]]:
    with _connection(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM goal_risk_runs ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_decode_row(row) for row in rows]
