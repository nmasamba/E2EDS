from pathlib import Path
from typing import Any

import pytest

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.adapters.store_fs import ContentStore
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext

CTX = TrustedContext.local()
OTHER = TrustedContext("someone", "tenant-other", frozenset())


def _ledger(path: Path) -> SqliteLedger:
    return SqliteLedger(path / "ledger.sqlite", lambda: "2026-10-01T00:00:00+00:00")


def _thing(**extra: Any) -> dict[str, Any]:
    return {"schema_version": "0.1.0", "type": "Thing", "id": "t1", "revision": "1.0.0", **extra}


def test_stale_expected_version_is_rejected(tmp_path: Path) -> None:
    """ADR02: an append at a stale aggregate sequence is a REVISION_CONFLICT and writes nothing."""
    ledger = _ledger(tmp_path)
    ledger.commit(CTX, "job:1", 0, "e1", "job.started", {})
    with pytest.raises(DspError) as raised:
        ledger.commit(CTX, "job:1", 0, "e2", "job.succeeded", {}, [_thing()])
    assert raised.value.code is ErrorCode.REVISION_CONFLICT
    assert [event["event_id"] for event in ledger.events(CTX)] == ["e1"]
    with pytest.raises(DspError):
        ledger.get(CTX, "Thing", "t1", "1.0.0")


def test_retrying_a_committed_event_changes_nothing(tmp_path: Path) -> None:
    """A03: a retry after a lost acknowledgement yields exactly one committed event."""
    ledger = _ledger(tmp_path)
    for _ in range(2):
        ledger.commit(CTX, "job:1", 0, "e1", "job.succeeded", {"artifact": "a"})
    assert len(ledger.events(CTX)) == 1
    with pytest.raises(DspError) as raised:
        ledger.commit(CTX, "job:1", 0, "e1", "job.succeeded", {"artifact": "b"})
    assert raised.value.code is ErrorCode.IDEMPOTENCY_CONFLICT


def test_object_revisions_are_immutable(tmp_path: Path) -> None:
    """A stored revision can be re-put unchanged but never rewritten; the failed event is lost."""
    ledger = _ledger(tmp_path)
    ledger.commit(CTX, "job:1", 0, "e1", "a", {}, [_thing(note="first")])
    ledger.commit(CTX, "job:1", 1, "e2", "b", {}, [_thing(note="first")])
    with pytest.raises(DspError) as raised:
        ledger.commit(CTX, "job:1", 2, "e3", "c", {}, [_thing(note="rewritten")])
    assert raised.value.code is ErrorCode.REVISION_CONFLICT
    assert ledger.get(CTX, "Thing", "t1", "1.0.0")["note"] == "first"
    assert len(ledger.events(CTX)) == 2


def test_another_tenant_sees_nothing(tmp_path: Path) -> None:
    """R05: objects, events and artifacts of one tenant do not exist for another."""
    ledger, store = _ledger(tmp_path), ContentStore(tmp_path / "store")
    ledger.commit(CTX, "job:1", 0, "e1", "a", {}, [_thing()])
    staged = store.staging("attempt") / "f"
    staged.write_bytes(b"data")
    identity = store.commit(CTX, staged)
    assert ledger.events(OTHER) == []
    for lookup in (
        lambda: ledger.get(OTHER, "Thing", "t1", "1.0.0"),
        lambda: store.path(OTHER, identity),
    ):
        with pytest.raises(DspError) as raised:
            lookup()
        assert raised.value.code is ErrorCode.NOT_FOUND


def test_a_projection_rebuilds_from_the_ledger_alone(tmp_path: Path) -> None:
    """ADR02: state derived from events is identical after reopening; a cursor resumes replay."""
    ledger = _ledger(tmp_path)
    for seq, kind in enumerate(("job.started", "job.succeeded")):
        ledger.commit(CTX, "job:1", seq, f"1-{seq}", kind, {})
    ledger.commit(CTX, "job:2", 0, "2-0", "job.started", {})

    def states(events: list[dict[str, Any]]) -> dict[str, str]:
        return {event["aggregate"]: event["type"] for event in events}

    reopened = _ledger(tmp_path)
    assert states(reopened.events(CTX)) == {"job:1": "job.succeeded", "job:2": "job.started"}
    assert [event["aggregate"] for event in reopened.events(CTX, after=2)] == ["job:2"]


def test_identical_bytes_share_one_digest_and_staged_files_are_unreferenced(tmp_path: Path) -> None:
    """Equal bytes are stored once; a file left in staging by a crash is not reachable by digest."""
    store = ContentStore(tmp_path / "store")
    digests = []
    for attempt in ("a", "b"):
        staged = store.staging(attempt) / "f"
        staged.write_bytes(b"same bytes")
        digests.append(store.commit(CTX, staged))
    assert digests[0] == digests[1]
    assert store.path(CTX, digests[0]).read_bytes() == b"same bytes"
    (store.staging("crashed") / "f").write_bytes(b"never committed")
    with pytest.raises(DspError):
        store.path(CTX, "sha256:" + "0" * 64)
    assert len(list((tmp_path / "store" / "cas").rglob("*"))) == 2  # tenant folder + one file
