"""Passive hardware probes for the local machine (D19): fixed sources, no install, no elevation.

Each probe returns the part of a HardwareSnapshot it observed, or raises: PermissionError when
the OS denies it, FileNotFoundError when its source does not exist here, TimeoutError when it
overruns. Nothing here reads a serial number, a user name, a host name or a home path.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

PROBE_SECONDS = 2.0
GIB = 1024**3
HOST = "host-local"


def _run(*argv: str) -> str:
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=PROBE_SECONDS)
    except subprocess.TimeoutExpired as error:
        raise TimeoutError from error
    if done.returncode:
        raise RuntimeError
    return done.stdout


def _gib(count: float) -> float:
    return round(count / GIB, 2)


def cgroup_limit(text: str) -> float | None:
    """Return the first field of a cgroup v2 limit file, or None when it says ``max``."""
    first = text.split()[0]
    return None if first == "max" else float(first)


def linux_memory(meminfo: str, limit: float | None) -> dict[str, Any]:
    """Read total and available memory from ``/proc/meminfo`` text, capped by a cgroup limit."""
    kib = {line.split(":")[0]: int(line.split()[1]) for line in meminfo.splitlines() if line}
    total = kib["MemTotal"] * 1024
    return {
        "total_gib": _gib(total),
        "available_gib": _gib(kib["MemAvailable"] * 1024),
        "effective_limit_gib": _gib(min(total, limit) if limit else total),
    }


def mac_memory(memsize: str, vm_stat: str) -> dict[str, Any]:
    """Read total memory from ``hw.memsize`` and estimate available memory from ``vm_stat``."""
    page = int(vm_stat.split("page size of ")[1].split()[0])
    pages = {
        line.split(":")[0]: int(line.split(":")[1].strip().rstrip("."))
        for line in vm_stat.splitlines()[1:]
        if line.split(":")[1].strip().rstrip(".").isdigit()
    }
    free = pages["Pages free"] + pages["Pages inactive"] + pages["Pages speculative"]
    total = _gib(int(memsize))
    return {"total_gib": total, "available_gib": _gib(free * page), "effective_limit_gib": total}


def _device(index: int, **fields: Any) -> dict[str, Any]:
    return {"logical_device_id": f"gpu-{index}", "runtime_check": "not_run", **fields}


def nvidia_devices(csv: str) -> list[dict[str, Any]]:
    """Read devices from ``nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version``."""
    devices = []
    for index, line in enumerate(line for line in csv.splitlines() if line.strip()):
        name, total, free, driver = (field.strip() for field in line.split(","))
        devices.append(
            _device(
                index,
                vendor="NVIDIA",
                model=name,
                memory_gib=round(float(total) / 1024, 2),
                available_memory_gib=round(float(free) / 1024, 2),
                driver_runtime_label=f"driver {driver}",
                memory_domain_id=f"gpu-{index}",
                sharing="unknown",
            )
        )
    return devices


def mac_devices(profile: str) -> list[dict[str, Any]]:
    """Read devices from ``system_profiler SPDisplaysDataType -json``.

    An Apple GPU has no memory of its own: it shares the host's, so it is placed in the host's
    memory domain and never counted as extra capacity.
    """
    return [
        _device(
            index,
            vendor=gpu.get("spdisplays_vendor", "unknown").removeprefix("sppci_vendor_"),
            model=gpu.get("sppci_model", "unknown"),
            memory_gib=None,
            available_memory_gib=None,
            driver_runtime_label=gpu.get("spdisplays_mtlgpufamilysupport"),
            memory_domain_id=HOST,
            sharing="shared",
        )
        for index, gpu in enumerate(json.loads(profile)["SPDisplaysDataType"])
    ]


def _system() -> dict[str, Any]:
    names = {"os": platform.system().lower(), "architecture": platform.machine()}
    return {"system": {**names, "cpu_features": []}}


def _cpu() -> dict[str, Any]:
    visible = os.cpu_count()
    quota: float | None = visible
    if sys.platform == "linux":
        quota = len(os.sched_getaffinity(0))
        limit = Path("/sys/fs/cgroup/cpu.max")
        if limit.exists() and (budget := cgroup_limit(limit.read_text())):
            quota = min(quota, budget / float(limit.read_text().split()[1]))
    return {
        "cpu": {
            "visible_logical_processors": visible,
            "effective_cpu_quota": quota,
            "available_to_plan_cpus": None,
        }
    }


def _memory() -> dict[str, Any]:
    if sys.platform == "linux":
        limit = Path("/sys/fs/cgroup/memory.max")
        cap = cgroup_limit(limit.read_text()) if limit.exists() else None
        return {"memory": linux_memory(Path("/proc/meminfo").read_text(), cap)}
    memsize = _run("/usr/sbin/sysctl", "-n", "hw.memsize")
    return {"memory": mac_memory(memsize, _run("/usr/bin/vm_stat"))}


def _accelerators() -> dict[str, Any]:
    if sys.platform == "linux":
        query = "--query-gpu=name,memory.total,memory.free,driver_version"
        devices = nvidia_devices(_run("nvidia-smi", query, "--format=csv,noheader,nounits"))
    else:
        devices = mac_devices(_run("/usr/sbin/system_profiler", "SPDisplaysDataType", "-json"))
    status = "observed_present" if devices else "observed_absent"
    return {"accelerators": {"inventory_status": status, "devices": devices}}


def probes(state_dir: Path) -> dict[str, Callable[[], dict[str, Any]]]:
    """Return the allowlisted probes, by name; storage is measured where the app keeps its state."""

    def storage() -> dict[str, Any]:
        free = _gib(shutil.disk_usage(state_dir).free)
        volume = {"role": "combined", "domain_id": "state-volume", "available_gib": free}
        return {"storage": [{**volume, "effective_quota_gib": None}]}

    return {
        "system": _system,
        "cpu": _cpu,
        "memory": _memory,
        "storage": storage,
        "accelerators": _accelerators,
    }
