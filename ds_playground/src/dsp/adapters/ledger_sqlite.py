import json
import sqlite3
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from dsp.contracts.canonical import canonical_json, digest
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext

SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
    tenant TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL, revision TEXT NOT NULL,
    schema_version TEXT NOT NULL, digest TEXT NOT NULL, body TEXT NOT NULL,
    PRIMARY KEY (tenant, kind, id, revision));
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, tenant TEXT NOT NULL,
    aggregate TEXT NOT NULL, aggregate_seq INTEGER NOT NULL, type TEXT NOT NULL,
    body TEXT NOT NULL, recorded_at TEXT NOT NULL,
    UNIQUE (tenant, aggregate, aggregate_seq));
"""


class SqliteLedger:
    """Single-writer SQLite ledger: immutable object revisions and an event log (the outbox)."""

    def __init__(self, path: Path, clock: Callable[[], str]) -> None:
        self._db = sqlite3.connect(path, isolation_level=None)
        self._db.executescript(SCHEMA)
        self._clock = clock

    def commit(
        self,
        ctx: TrustedContext,
        aggregate: str,
        expected_seq: int,
        event_id: str,
        event_type: str,
        body: dict[str, Any],
        objects: Sequence[dict[str, Any] | tuple[str, dict[str, Any]]] = (),
    ) -> None:
        """Append one event and its objects in one transaction.

        The aggregate must be at ``expected_seq`` (compare-and-swap). Repeating a committed
        ``event_id`` with the same content is a no-op, so a caller that lost the acknowledgement can
        retry safely; the same ``event_id`` with different content is a conflict.
        """
        payload = canonical_json(body).decode()
        with self._db:
            self._db.execute("BEGIN IMMEDIATE")
            prior = self._db.execute(
                "SELECT tenant, aggregate, type, body FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
            if prior:
                if prior != (ctx.tenant, aggregate, event_type, payload):
                    raise DspError(ErrorCode.IDEMPOTENCY_CONFLICT, f"event {event_id} differs")
                return
            (current,) = self._db.execute(
                "SELECT COALESCE(MAX(aggregate_seq), 0) FROM events"
                " WHERE tenant = ? AND aggregate = ?",
                (ctx.tenant, aggregate),
            ).fetchone()
            if current != expected_seq:
                raise DspError(
                    ErrorCode.REVISION_CONFLICT,
                    f"{aggregate} is at {current}, expected {expected_seq}",
                )
            for item in objects:
                kind, obj = item if isinstance(item, tuple) else (item["type"], item)
                self._put(ctx, kind, obj)
            self._db.execute(
                "INSERT INTO events"
                " (event_id, tenant, aggregate, aggregate_seq, type, body, recorded_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    ctx.tenant,
                    aggregate,
                    expected_seq + 1,
                    event_type,
                    payload,
                    self._clock(),
                ),
            )

    def _put(self, ctx: TrustedContext, kind: str, obj: dict[str, Any]) -> None:
        key = (ctx.tenant, kind, obj["id"], obj["revision"])
        body = canonical_json(obj)
        stored = self._db.execute(
            "SELECT digest FROM objects WHERE tenant = ? AND kind = ? AND id = ? AND revision = ?",
            key,
        ).fetchone()
        if stored is None:
            self._db.execute(
                "INSERT INTO objects VALUES (?, ?, ?, ?, ?, ?, ?)",
                (*key, obj["schema_version"], digest(body), body.decode()),
            )
        elif stored[0] != digest(body):
            raise DspError(ErrorCode.REVISION_CONFLICT, f"{key[1]} {key[2]}@{key[3]} is immutable")

    def get(self, ctx: TrustedContext, kind: str, object_id: str, revision: str) -> dict[str, Any]:
        """Return one immutable object revision, or raise NOT_FOUND (also for another tenant's)."""
        row = self._db.execute(
            "SELECT body FROM objects WHERE tenant = ? AND kind = ? AND id = ? AND revision = ?",
            (ctx.tenant, kind, object_id, revision),
        ).fetchone()
        if row is None:
            raise DspError(ErrorCode.NOT_FOUND, f"{kind} {object_id}@{revision} not found")
        loaded: dict[str, Any] = json.loads(row[0])
        return loaded

    def latest(self, ctx: TrustedContext, kind: str, object_id: str) -> dict[str, Any] | None:
        """Return the newest revision of one object, or None when this tenant has none."""
        row = self._db.execute(
            "SELECT body FROM objects WHERE tenant = ? AND kind = ? AND id = ?"
            " ORDER BY rowid DESC LIMIT 1",
            (ctx.tenant, kind, object_id),
        ).fetchone()
        return None if row is None else dict(json.loads(row[0]))

    def seq(self, ctx: TrustedContext, aggregate: str) -> int:
        """Return an aggregate's current sequence: what ``commit`` must be told to expect."""
        (current,) = self._db.execute(
            "SELECT COALESCE(MAX(aggregate_seq), 0) FROM events WHERE tenant = ? AND aggregate = ?",
            (ctx.tenant, aggregate),
        ).fetchone()
        return int(current)

    def current(self, ctx: TrustedContext, kind: str) -> list[dict[str, Any]]:
        """Return the latest revision of every object of one kind in this tenant, oldest first."""
        rows = self._db.execute(
            "SELECT body FROM objects WHERE rowid IN (SELECT MAX(rowid) FROM objects"
            " WHERE tenant = ? AND kind = ? GROUP BY id) ORDER BY rowid",
            (ctx.tenant, kind),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def events(self, ctx: TrustedContext, after: int = 0) -> list[dict[str, Any]]:
        """Return this tenant's events after a cursor, in commit order, for replay."""
        rows = self._db.execute(
            "SELECT seq, event_id, aggregate, aggregate_seq, type, body, recorded_at FROM events"
            " WHERE tenant = ? AND seq > ? ORDER BY seq",
            (ctx.tenant, after),
        ).fetchall()
        names = ("seq", "event_id", "aggregate", "aggregate_seq", "type", "body", "recorded_at")
        return [
            dict(zip(names, (*row[:5], json.loads(row[5]), row[6]), strict=True)) for row in rows
        ]
