"""The Linux sandbox: bubblewrap namespaces, a seccomp filter and kernel limits (B26).

Policy (the sandboxed-runner skill), as on macOS. The task's file system holds the runner
environment, the interpreter it was made from (the binary, its standard library and every symlink on
the way), system libraries and the attempt directory, all read-only, and a tmpfs of the scratch size
on scratch, the only writable place; the root and ``/dev`` (whose ``shm`` would otherwise take
writes) are remounted read-only. There is no ``/etc``, home, shell, ``/proc`` or ``/tmp`` (a second
tmpfs would double the scratch size; ``TMPDIR`` is scratch). Every namespace is new, so no network,
not even loopback, and only the task's own processes; the runner is the namespace's first process
(``--as-pid-1``), so its CPU time returns with its exit status. The environment is ``HOME`` and
``TMPDIR`` alone, and only the standard descriptors (and the filter's, which bubblewrap reads and
closes) are passed on.

The seccomp filter refuses sockets other than Unix ones, every way of creating a process except a
thread, memory a task could hold without mapping it (``memfd_create``, System V shared memory),
which ``RLIMIT_AS`` would not count, and kernel interfaces a task never needs. Limits: memory by
``RLIMIT_AS`` (``prlimit``), scratch by the tmpfs size, CPU time by the runner's own limit (the
kernel kills at the hard limit), wall time and output in the shared core. bubblewrap reports a
signal that ended the task as 128 plus its number.
"""

import contextlib
import errno
import os
import shutil
import socket
import struct
from pathlib import Path
from typing import Any

from dsp.adapters.sandbox import FLAGS, Confined, chain, scrubbed
from dsp.contracts.errors import DspError, ErrorCode

AUDIT_ARCH = {"x86_64": 0xC000003E, "aarch64": 0xC00000B7}
SYSCALLS = {  # unistd.h of each architecture
    "x86_64": {
        "socket": 41,
        "clone": 56,
        "fork": 57,
        "vfork": 58,
        "ptrace": 101,
        "personality": 135,
        "pivot_root": 155,
        "chroot": 161,
        "mount": 165,
        "umount2": 166,
        "init_module": 175,
        "delete_module": 176,
        "kexec_load": 246,
        "add_key": 248,
        "request_key": 249,
        "keyctl": 250,
        "unshare": 272,
        "perf_event_open": 298,
        "setns": 308,
        "process_vm_readv": 310,
        "process_vm_writev": 311,
        "finit_module": 313,
        "bpf": 321,
        "userfaultfd": 323,
        "io_uring_setup": 425,
        "io_uring_enter": 426,
        "io_uring_register": 427,
        "clone3": 435,
        "shmget": 29,
        "memfd_create": 319,
    },
    "aarch64": {
        "umount2": 39,
        "mount": 40,
        "pivot_root": 41,
        "chroot": 51,
        "personality": 92,
        "unshare": 97,
        "kexec_load": 104,
        "init_module": 105,
        "delete_module": 106,
        "ptrace": 117,
        "socket": 198,
        "add_key": 217,
        "request_key": 218,
        "keyctl": 219,
        "clone": 220,
        "perf_event_open": 241,
        "setns": 268,
        "process_vm_readv": 270,
        "process_vm_writev": 271,
        "finit_module": 273,
        "bpf": 280,
        "userfaultfd": 282,
        "io_uring_setup": 425,
        "io_uring_enter": 426,
        "io_uring_register": 427,
        "clone3": 435,
        "shmget": 194,
        "memfd_create": 279,
    },
}
CLONE_THREAD = 0x00010000
SYSTEM = [Path(path) for path in ("/usr/lib", "/usr/lib64", "/lib", "/lib64", "/lib32")]
SYSTEM.append(Path("/etc/ld.so.cache"))  # where the loader finds libraries; nothing else of /etc


def seccomp_filter(machine: str) -> bytes:
    """The classic BPF program the task runs under, for this machine's system-call table."""
    calls = SYSCALLS[machine]
    load, equal, at_least, any_bit, answer = 0x20, 0x15, 0x35, 0x45, 0x06
    allow, kill = 0x7FFF0000, 0x80000000

    def op(code: int, k: int, true: int = 0, false: int = 0) -> bytes:
        return struct.pack("<HBBI", code, true, false, k)

    def refuse(number: int) -> int:
        return 0x00050000 | number

    program = [op(load, 4), op(equal, AUDIT_ARCH[machine], 1), op(answer, kill), op(load, 0)]
    if machine == "x86_64":  # the x32 ABI shares the architecture; refuse all of it
        program += [op(at_least, 0x40000000, 0, 1), op(answer, kill)]
    for name, number in calls.items():
        if name not in ("socket", "clone", "clone3"):
            program += [op(equal, number, 0, 1), op(answer, refuse(errno.EPERM))]
    program += [op(equal, calls["clone3"], 0, 1), op(answer, refuse(errno.ENOSYS))]  # use clone
    program += [op(equal, calls["socket"], 0, 4), op(load, 16), op(equal, socket.AF_UNIX, 0, 1)]
    program += [op(answer, allow), op(answer, refuse(errno.EACCES))]
    program += [op(equal, calls["clone"], 0, 4), op(load, 16), op(any_bit, CLONE_THREAD, 0, 1)]
    program += [op(answer, allow), op(answer, refuse(errno.EPERM)), op(answer, allow)]
    return b"".join(program)


class Bubblewrap(Confined):
    """Runs the runner in bubblewrap on Linux with its seccomp filter and limits."""

    relays_signals = True

    def __init__(self, environment: Path) -> None:
        super().__init__(environment)
        prlimit, bwrap = shutil.which("prlimit"), shutil.which("bwrap")
        if not (prlimit and bwrap):
            raise DspError(ErrorCode.DEPENDENCY_UNAVAILABLE, "bubblewrap or prlimit is missing")
        self.tools = prlimit, bwrap

    def arguments(self, task: dict[str, Any], work: Path) -> list[str]:
        """The fixed argument vector from ``prlimit`` to the runner; no string is a shell's."""
        limits, python = task["limits"], chain(self.environment / "bin" / "python")
        argv = [self.tools[0], f"--as={limits['memory_mib'] * 2**20}", "--", self.tools[1]]
        argv += ["--unshare-all", "--as-pid-1", "--die-with-parent", "--new-session"]
        for path in SYSTEM:
            if path.is_symlink():
                argv += ["--symlink", os.readlink(path), str(path)]
            elif path.exists():
                argv += ["--ro-bind", str(path), str(path)]
        for link in python[:-1]:
            if not link.is_relative_to(self.environment):
                argv += ["--symlink", os.readlink(link), str(link)]
        for path in (python[-1], python[-1].parents[1] / "lib", self.environment, work):
            argv += ["--ro-bind", str(path), str(path)]
        argv += ["--size", str(limits["scratch_bytes"]), "--tmpfs", str(work / "scratch")]
        argv += ["--dev", "/dev", "--remount-ro", "/dev", "--remount-ro", "/"]  # and no /proc
        argv += ["--chdir", str(work / "scratch"), "--seccomp", "3", "--"]
        return [*argv, str(self.environment / "bin" / "python"), *FLAGS, "-m", "dsp_runner"]

    def start(self, task: dict[str, Any], work: Path, channel: int) -> int:
        """Write the filter, then spawn ``prlimit`` and bubblewrap with fixed arguments."""
        argv = [*self.arguments(task, work), str(work / "task.json")]
        (work / "seccomp.bpf").write_bytes(seccomp_filter(os.uname().machine))
        program, inherited = os.open(work / "seccomp.bpf", os.O_RDONLY), []
        for name in os.listdir("/proc/self/fd"):
            with contextlib.suppress(OSError):  # the listing's own descriptor is closed by now
                if int(name) > 3 and int(name) != program and os.get_inheritable(int(name)):
                    inherited.append(int(name))
        try:
            return os.posix_spawn(
                argv[0],
                argv,
                scrubbed(work),
                file_actions=[
                    (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
                    (os.POSIX_SPAWN_DUP2, channel, 1),
                    (os.POSIX_SPAWN_OPEN, 2, os.devnull, os.O_WRONLY, 0),
                    (os.POSIX_SPAWN_DUP2, program, 3),
                    *((os.POSIX_SPAWN_CLOSE, fd) for fd in inherited),
                ],
                setsid=True,
            )
        finally:
            os.close(program)
