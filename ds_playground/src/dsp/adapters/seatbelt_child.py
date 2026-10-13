"""Inside the task's process on macOS: confine it with its Seatbelt profile, then run the runner.

``python -m dsp.adapters.seatbelt_child <profile> <attempt>/task.json`` applies the profile with
``sandbox_init``, the call ``sandbox-exec`` makes, but runs the runner in this same process rather
than executing it, because an exec drops the memory limit set when the process was spawned. Only
this module and the interpreter run before the profile applies; a profile that does not compile
ends the process before any task code exists. A watcher thread ends the task if the harness dies.
"""

import ctypes
import os
import runpy
import sys
import threading
import time


def main(profile: str, task: str) -> None:
    """Apply the profile to this process for good, then run ``dsp_runner`` on the task."""
    threading.Thread(target=orphaned, daemon=True).start()
    error = ctypes.c_char_p()
    seatbelt = ctypes.CDLL("/usr/lib/libSystem.B.dylib").sandbox_init
    with open(profile, "rb") as handle:
        if seatbelt(handle.read(), ctypes.c_uint64(0), ctypes.byref(error)):
            raise SystemExit(f"the sandbox profile was refused: {error.value!r}")
    sys.argv = ["dsp_runner", task]
    runpy.run_module("dsp_runner", run_name="__main__")


def orphaned() -> None:
    """End the task when the harness that supervises it ends: macOS has no parent-death signal.

    The harness enforces wall and CPU time from outside; without it they would not hold. This runs
    in the task's own process, so a hostile task could starve it: a mitigation, not a boundary.
    """
    while os.getppid() != 1:
        time.sleep(1)
    os._exit(137)


if __name__ == "__main__":
    main(*sys.argv[1:])
