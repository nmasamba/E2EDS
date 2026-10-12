"""The macOS sandbox: Seatbelt, a fatal jetsam memory limit and a size-capped scratch volume (B26).

Policy (the sandboxed-runner skill), deny by default. Reads: the runner environment, the Python it
was made from and every symlink on the way to it, system libraries and the attempt directory, with
the metadata of their ancestors and the root's listing. Writes: scratch and ``/dev/null``. Also
sysctl reads. Nothing else: no network, no process creation or execution, no IPC, no Mach services.

Limits: memory by the kernel (a fatal jetsam limit on the spawn, which an exec would drop, hence
``seatbelt_child`` instead of ``sandbox-exec``), scratch by the kernel (a sparse disk image of the
scratch size mounted on scratch), CPU time by the runner's own limit (SIGXCPU) and, because Darwin
does not kill at the hard limit, by polling the kernel's account of the process here; wall time
and output in the shared core. The descriptors the task inherits are its three standard ones.
"""

import ctypes
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

from dsp.adapters.sandbox import FLAGS, Confined, scrubbed

SETSID, CLOEXEC_DEFAULT = 0x0400, 0x4000  # spawn.h
JETSAM_SET, MEMLIMIT_FATAL, JETSAM_PRIORITY = 0x8000, 0x04 | 0x08, 180  # spawn_private.h


class _Usage(ctypes.Structure):
    """``rusage_info_v0`` (libproc.h): times in Mach absolute-time units."""

    _fields_ = [
        ("uuid", ctypes.c_uint8 * 16),
        *((field, ctypes.c_uint64) for field in ("user", "system", "wakeups", "interrupts")),
        *((field, ctypes.c_uint64) for field in ("pageins", "wired", "resident", "footprint")),
        *((field, ctypes.c_uint64) for field in ("started", "exited")),
    ]


class _Timebase(ctypes.Structure):
    _fields_ = [("numer", ctypes.c_uint32), ("denom", ctypes.c_uint32)]


def _chain(path: Path) -> list[Path]:
    """Every symlink met on the way from ``path`` to the file it names, then that file."""
    found: list[Path] = []
    for _ in range(40):
        link = next((p for p in [*reversed(path.parents), path] if p.is_symlink()), None)
        if link is None:
            break
        found.append(link)
        path = Path(os.path.normpath(link.parent / os.readlink(link))) / path.relative_to(link)
    return [*found, path]


class Seatbelt(Confined):
    """Runs the runner under Seatbelt on macOS with its memory, scratch and CPU limits."""

    killed = "memory_limit"  # jetsam is what kills with SIGKILL here

    def __init__(self, environment: Path) -> None:
        super().__init__(environment)
        self.system = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
        timebase = _Timebase()
        self.system.mach_timebase_info(ctypes.byref(timebase))
        self.tick: float = timebase.numer / timebase.denom / 1e9  # seconds per Mach time unit

    def profile(self, work: Path) -> str:
        """The attempt's Seatbelt profile: what is not allowed here is denied."""
        python = _chain(self.environment / "bin" / "python")
        reads = [self.environment.resolve(), python[-1].parents[1], Path("/usr/lib")]
        reads += [Path("/System/Library"), work]
        ancestors = {path for read in [*reads, *python] for path in [read, *read.parents]}

        def paths(kind: str, chosen: set[Path] | list[Path]) -> str:
            return " ".join(f"({kind} {json.dumps(str(p), ensure_ascii=False)})" for p in chosen)

        return "\n".join(
            [
                "(version 1)",
                "(deny default)",
                f"(allow file-read* {paths('subpath', reads)})",
                '(allow file-read-data (literal "/"))',
                f"(allow file-read-metadata {paths('literal', sorted(ancestors))})",
                f"(allow file-write* {paths('subpath', [work / 'scratch'])})",
                '(allow file-read* file-write* (literal "/dev/null"))',
                "(allow sysctl-read)",
            ]
        )

    def start(self, task: dict[str, Any], work: Path, channel: int) -> int:
        """Mount the capped scratch volume, write the profile and spawn the confined runner."""
        limits, scratch = task["limits"], work / "scratch"
        size = f"{math.ceil(limits['scratch_bytes'] / 1024)}k"
        image = ["hdiutil", "create", "-quiet", "-type", "SPARSE", "-fs", "HFS+", "-size", size]
        subprocess.run([*image, "-volname", "scratch", str(scratch)], check=True)
        attach = ["hdiutil", "attach", "-quiet", "-nobrowse", "-noautoopen", "-mountpoint"]
        subprocess.run([*attach, str(scratch), f"{scratch}.sparseimage"], check=True)
        (work / "profile.sb").write_text(self.profile(work))
        python = str(self.environment / "bin" / "python")
        argv = [python, *FLAGS, "-m", "dsp.adapters.seatbelt_child", str(work / "profile.sb")]
        argv.append(str(work / "task.json"))
        environ = [f"{name}={value}" for name, value in scrubbed(work).items()]
        actions, attributes, pid = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_int()
        system = self.system
        system.posix_spawn_file_actions_init(ctypes.byref(actions))
        system.posix_spawn_file_actions_addopen(ctypes.byref(actions), 0, b"/dev/null", 0, 0)
        system.posix_spawn_file_actions_adddup2(ctypes.byref(actions), channel, 1)
        system.posix_spawn_file_actions_addopen(
            ctypes.byref(actions), 2, b"/dev/null", os.O_WRONLY, 0
        )
        system.posix_spawnattr_init(ctypes.byref(attributes))
        system.posix_spawnattr_setflags(
            ctypes.byref(attributes), ctypes.c_short(SETSID | CLOEXEC_DEFAULT)
        )
        try:
            if system.posix_spawnattr_setjetsam_ext(
                ctypes.byref(attributes),
                ctypes.c_short(JETSAM_SET | MEMLIMIT_FATAL),
                JETSAM_PRIORITY,
                limits["memory_mib"],
                limits["memory_mib"],
            ):
                raise OSError("the memory limit could not be set on the spawn")
            refused = system.posix_spawn(
                ctypes.byref(pid),
                os.fsencode(python),
                ctypes.byref(actions),
                ctypes.byref(attributes),
                (ctypes.c_char_p * (len(argv) + 1))(*map(os.fsencode, argv), None),
                (ctypes.c_char_p * (len(environ) + 1))(*map(os.fsencode, environ), None),
            )
        finally:
            system.posix_spawn_file_actions_destroy(ctypes.byref(actions))
            system.posix_spawnattr_destroy(ctypes.byref(attributes))
        if refused:
            raise OSError(refused, os.strerror(refused))
        return pid.value

    def exceeded(self, pid: int, task: dict[str, Any]) -> bool:
        """True once the kernel has counted the task's CPU time past its limit."""
        usage = _Usage()
        if self.system.proc_pid_rusage(pid, 0, ctypes.byref(usage)):
            return False  # it has already ended; its exit status says how
        ticks: int = usage.user + usage.system
        limit: int = task["limits"]["cpu_seconds"]
        return ticks * self.tick >= limit

    def end(self, work: Path) -> None:
        """Detach the scratch volume and delete its image: scratch is never a result."""
        if os.path.ismount(work / "scratch"):
            detach = ["hdiutil", "detach", "-quiet", "-force", str(work / "scratch")]
            subprocess.run(detach, check=True)
        (work / "scratch.sparseimage").unlink(missing_ok=True)
