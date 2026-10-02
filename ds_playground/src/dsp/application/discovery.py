from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from dsp.application.grants import PROJECT
from dsp.contracts.errors import TrustedContext
from dsp.contracts.schemas import validate
from dsp.ports import Ledger

COLLECTOR = "collector-1.0.0"
PROBE_SECONDS = 2.0
REFUSALS: tuple[tuple[type[BaseException], str, str], ...] = (
    (TimeoutError, "timed_out", "no answer within two seconds"),
    (PermissionError, "permission_denied", "the operating system denied this probe"),
    (FileNotFoundError, "unsupported", "the source this probe reads is not present here"),
    (Exception, "failed", "the probe failed"),
)


def discover(
    ctx: TrustedContext,
    probes: Mapping[str, Callable[[], dict[str, Any]]],
    *,
    ledger: Ledger,
    clock: Callable[[], str],
    new_id: Callable[[], str],
    timer: Callable[[], float],
) -> dict[str, Any]:
    """Run the passive probes and record what they found as a HardwareSnapshot (D19).

    Probes run side by side and each gets two seconds, so the whole discovery takes about two
    seconds at most, inside D19's ten. A probe that is denied, missing, slow or broken leaves its
    fields unknown and a reason in the snapshot; it never becomes "nothing there". The snapshot is
    an observation of one moment: not a reservation, a qualification or an isolation claim.
    """
    snapshot: dict[str, Any] = {
        "id": f"hardware-{new_id()}",
        "revision": "1.0.0",
        "type": "HardwareSnapshot",
        "schema_version": "0.4.0",
        "planning_only": False,
        "tenant_ref": ctx.tenant,
        "project_ref": PROJECT,
        "scope": "assistant_host",
        "compute_binding_ref": None,
        "resource_domain_id": "host-local",
        "parent_resource_domain_id": None,
        "collector_revision": COLLECTOR,
        "system": {"os": None, "architecture": None, "cpu_features": []},
        "cpu": dict.fromkeys(
            ("visible_logical_processors", "effective_cpu_quota", "available_to_plan_cpus")
        ),
        "memory": dict.fromkeys(("total_gib", "available_gib", "effective_limit_gib")),
        "storage": [],
        "accelerators": {"inventory_status": "unknown", "devices": []},
        "isolation_readiness": "unknown",
        "isolation_evidence_ref": None,
        "probes": [],
        "limitations": ["One passive observation; not a reservation or a qualification."],
        "sharing_policy": "local_only",
    }
    pool = ThreadPoolExecutor(max_workers=max(1, len(probes)))
    deadline = timer() + PROBE_SECONDS
    running = {name: pool.submit(probe) for name, probe in probes.items()}
    for name, future in running.items():
        status, summary = "observed", "observed"
        try:
            snapshot.update(future.result(timeout=max(0.0, deadline - timer())))
        except Exception as error:
            status, summary = next(
                (status, summary) for kind, status, summary in REFUSALS if isinstance(error, kind)
            )
            snapshot["limitations"].append(f"{name}: {summary}")
        snapshot["probes"].append({"name": name, "status": status, "safe_summary": summary})
    pool.shutdown(wait=False, cancel_futures=True)

    observed = any(probe["status"] == "observed" for probe in snapshot["probes"])
    snapshot["evidence_source"] = "observed" if observed else "unknown"
    snapshot["observed_at"] = clock() if observed else None
    validate("HardwareSnapshot", snapshot)
    finished = {
        "snapshot": {"id": snapshot["id"], "revision": snapshot["revision"]},
        "evidence_source": snapshot["evidence_source"],
        "probes": {probe["name"]: probe["status"] for probe in snapshot["probes"]},
    }
    aggregate = f"snapshot:{snapshot['id']}"
    event = f"{snapshot['id']}:finished"
    ledger.commit(ctx, aggregate, 0, event, "discovery.finished", finished, [snapshot])
    return snapshot
