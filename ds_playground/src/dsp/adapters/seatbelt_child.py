"""Inside the task's process on macOS: confine it with its Seatbelt profile, then run the runner.

``python -m dsp.adapters.seatbelt_child <profile> <attempt>/task.json`` applies the profile with
``sandbox_init``, the call ``sandbox-exec`` makes, but runs the runner in this same process rather
than executing it, because an exec drops the memory limit set when the process was spawned. Only
this module and the interpreter run before the profile applies; a profile that does not compile
ends the process before any task code exists.
"""

import ctypes
import runpy
import sys


def main(profile: str, task: str) -> None:
    """Apply the profile to this process for good, then run ``dsp_runner`` on the task."""
    error = ctypes.c_char_p()
    seatbelt = ctypes.CDLL("/usr/lib/libSystem.B.dylib").sandbox_init
    with open(profile, "rb") as handle:
        if seatbelt(handle.read(), ctypes.c_uint64(0), ctypes.byref(error)):
            raise SystemExit(f"the sandbox profile was refused: {error.value!r}")
    sys.argv = ["dsp_runner", task]
    runpy.run_module("dsp_runner", run_name="__main__")


if __name__ == "__main__":
    main(*sys.argv[1:])
