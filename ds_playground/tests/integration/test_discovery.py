import getpass
import json
import socket
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from dsp.adapters import discovery as adapter
from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.application.discovery import discover
from dsp.contracts.errors import TrustedContext
from dsp.contracts.schemas import validate

CTX = TrustedContext.local()
NOW = "2026-10-02T00:00:00+00:00"
Probes = dict[str, Callable[[], dict[str, Any]]]


def run(tmp_path: Path, probes: Probes) -> dict[str, Any]:
    """Discover with the given probes into a fresh ledger and return the snapshot."""
    ledger = SqliteLedger(tmp_path / "ledger.sqlite", lambda: NOW)
    return discover(
        CTX, probes, ledger=ledger, clock=lambda: NOW, new_id=lambda: "s1", timer=time.monotonic
    )


def statuses(snapshot: dict[str, Any]) -> dict[str, str]:
    """Probe name to status, as recorded in the snapshot."""
    return {probe["name"]: probe["status"] for probe in snapshot["probes"]}


@pytest.mark.disable_socket
def test_real_discovery_observes_this_machine_without_any_network(tmp_path: Path) -> None:
    """A31, D19: with every socket blocked, the real probes observe the core facts in seconds."""
    started = time.monotonic()
    snapshot = run(tmp_path, adapter.probes(tmp_path))
    assert time.monotonic() - started < 10
    validate("HardwareSnapshot", snapshot)
    observed = statuses(snapshot)
    assert {observed[name] for name in ("system", "cpu", "memory", "storage")} == {"observed"}
    assert snapshot["evidence_source"] == "observed"
    assert snapshot["system"]["os"] in ("darwin", "linux")
    assert snapshot["system"]["architecture"]
    assert (
        snapshot["cpu"]["visible_logical_processors"] >= snapshot["cpu"]["effective_cpu_quota"] > 0
    )
    memory = snapshot["memory"]
    assert memory["total_gib"] >= memory["effective_limit_gib"] > 0
    assert 0 < memory["available_gib"] <= memory["total_gib"]
    assert snapshot["storage"][0]["available_gib"] > 0
    gpus = snapshot["accelerators"]
    assert (observed["accelerators"], gpus["inventory_status"]) in (
        ("observed", "observed_present"),
        ("observed", "observed_absent"),
        ("unsupported", "unknown"),
    )
    assert bool(gpus["devices"]) == (gpus["inventory_status"] == "observed_present")


def test_a_snapshot_holds_nothing_that_identifies_the_owner(tmp_path: Path) -> None:
    """A31: no user name, host name, home path or state path appears in the snapshot or event."""
    snapshot = run(tmp_path, adapter.probes(tmp_path))
    events = SqliteLedger(tmp_path / "ledger.sqlite", str).events(CTX)
    text = json.dumps([snapshot, events])
    for private in (getpass.getuser(), socket.gethostname(), str(Path.home()), str(tmp_path)):
        assert private not in text
    assert [event["type"] for event in events] == ["discovery.finished"]
    assert events[0]["body"]["snapshot"] == {"id": "hardware-s1", "revision": "1.0.0"}


def test_a_denied_gpu_probe_is_unknown_not_absent(tmp_path: Path) -> None:
    """A31: a permission failure leaves the accelerator inventory unknown, with the reason."""

    def denied() -> dict[str, Any]:
        raise PermissionError("/dev/secret-gpu for user alice")

    snapshot = run(tmp_path, adapter.probes(tmp_path) | {"accelerators": denied})
    validate("HardwareSnapshot", snapshot)
    assert statuses(snapshot)["accelerators"] == "permission_denied"
    assert snapshot["accelerators"] == {"inventory_status": "unknown", "devices": []}
    assert snapshot["evidence_source"] == "observed"
    assert "accelerators: the operating system denied this probe" in snapshot["limitations"]
    assert "alice" not in json.dumps(snapshot)


def test_a_slow_probe_times_out_and_the_rest_is_kept(tmp_path: Path) -> None:
    """D19: a probe that does not answer in two seconds is timed_out; discovery still returns."""
    release = threading.Event()
    started = time.monotonic()
    snapshot = run(tmp_path, adapter.probes(tmp_path) | {"memory": lambda: release.wait(30) or {}})
    elapsed = time.monotonic() - started
    release.set()
    assert 2 <= elapsed < 4
    assert statuses(snapshot)["memory"] == "timed_out"
    assert snapshot["memory"] == dict.fromkeys(
        ("total_gib", "available_gib", "effective_limit_gib")
    )
    assert statuses(snapshot)["cpu"] == "observed"


def test_missing_and_broken_probes_give_reasons_and_no_detail(tmp_path: Path) -> None:
    """A31: when nothing is observed the snapshot says unknown, stays valid and leaks nothing."""

    def missing() -> dict[str, Any]:
        raise FileNotFoundError("/usr/bin/absent-tool")

    def broken() -> dict[str, Any]:
        raise RuntimeError("stack trace with /Users/alice")

    def subprocess_timeout() -> dict[str, Any]:
        raise TimeoutError

    snapshot = run(tmp_path, {"cpu": missing, "memory": broken, "storage": subprocess_timeout})
    validate("HardwareSnapshot", snapshot)
    assert statuses(snapshot) == {"cpu": "unsupported", "memory": "failed", "storage": "timed_out"}
    assert (snapshot["evidence_source"], snapshot["observed_at"]) == ("unknown", None)
    assert snapshot["accelerators"]["inventory_status"] == "unknown"
    assert "alice" not in json.dumps(snapshot)
    assert "absent-tool" not in json.dumps(snapshot)


def test_linux_sources_are_read_as_the_kernel_writes_them() -> None:
    """A32: cgroup limits cap what the plan may use; an unlimited cgroup leaves the host total."""
    meminfo = (
        "MemTotal:       16384000 kB\nMemFree:         1024000 kB\nMemAvailable:    8192000 kB\n"
    )
    assert adapter.cgroup_limit("max 100000\n") is None
    assert adapter.cgroup_limit("200000 100000\n") == 200000
    assert adapter.linux_memory(meminfo, None) == {
        "total_gib": 15.62,
        "available_gib": 7.81,
        "effective_limit_gib": 15.62,
    }
    assert adapter.linux_memory(meminfo, 4 * 1024**3)["effective_limit_gib"] == 4.0
    devices = adapter.nvidia_devices("NVIDIA RTX A4000, 16376, 15000, 550.54.14\n\n")
    assert [(d["vendor"], d["memory_gib"], d["memory_domain_id"]) for d in devices] == [
        ("NVIDIA", 15.99, "gpu-0")
    ]
    assert adapter.nvidia_devices("") == []


def test_mac_sources_are_read_as_the_system_writes_them() -> None:
    """A32: an Apple GPU shares host memory, so it adds no memory of its own to the plan."""
    vm_stat = (
        "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
        "Pages free:                               89248.\n"
        "Pages active:                           1897181.\n"
        "Pages inactive:                         1846170.\n"
        "Pages speculative:                        50494.\n"
        '"Translation faults":                 123456789.\n'
    )
    assert adapter.mac_memory("68719476736\n", vm_stat) == {
        "total_gib": 64.0,
        "available_gib": 30.3,
        "effective_limit_gib": 64.0,
    }
    profile = json.dumps(
        {
            "SPDisplaysDataType": [
                {
                    "sppci_model": "Apple M1 Max",
                    "spdisplays_vendor": "sppci_vendor_Apple",
                    "spdisplays_mtlgpufamilysupport": "spdisplays_metal4",
                }
            ]
        }
    )
    (device,) = adapter.mac_devices(profile)
    assert (device["vendor"], device["model"], device["memory_gib"]) == (
        "Apple",
        "Apple M1 Max",
        None,
    )
    assert (device["memory_domain_id"], device["sharing"]) == ("host-local", "shared")
