"""The deterministic test worker: Sprint 3's only workload, run as a real separate process.

It leases one attempt of a job from the harness, follows the cue the job's task gives that
attempt (sleep, hang, crash before or after its commit, fail), heartbeats while it works and
reports once. ``--heartbeat-seconds 0`` makes a silent worker whose lease is left to expire.
Exit status 0: reported and accepted; 3: refused by the coordinator (a stale or fenced attempt).
"""

import argparse
import os
import signal
import sys
import time
from typing import Any

import httpx

from dsp.contracts.canonical import canonical_json, digest
from dsp.harness.instance import connect, home


def main(argv: list[str]) -> int:
    """Lease, work and report; return the exit status."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--worker", default=f"worker-{os.getpid()}")
    parser.add_argument("--heartbeat-seconds", type=float, default=15)
    options = parser.parse_args(argv)
    client, route = connect(home()), f"/v1/jobs/{options.job}"
    leased = client.post(f"{route}/lease", json={"worker": options.worker})
    if leased.is_error:
        return 3
    lease, task = leased.json(), leased.json()["task"]
    attempt: dict[str, Any] = {"attempt": lease["attempt"], "fence": lease["fence"]}
    cue = task["cues"][min(lease["attempt"], len(task["cues"])) - 1]

    def report(**fields: Any) -> int:
        return 0 if client.post(f"{route}/report", json=attempt | fields).is_success else 3

    def heartbeat() -> str:
        """Extend the lease; return the job's state, or "" when the coordinator refused us."""
        answer = client.post(f"{route}/heartbeat", json=attempt)
        return "" if answer.is_error else str(answer.json()["state"])

    def work(seconds: float | None) -> str:
        """Sleep for ``seconds`` (forever when None), heartbeating; return why it ended."""
        deadline = None if seconds is None else time.monotonic() + seconds
        while deadline is None or time.monotonic() < deadline:
            if not options.heartbeat_seconds:
                time.sleep(3600 if deadline is None else deadline - time.monotonic())
                continue
            remaining = 3600 if deadline is None else deadline - time.monotonic()
            time.sleep(max(0.0, min(options.heartbeat_seconds, remaining)))
            state = heartbeat()
            if state in ("pause_requested", "cancel_requested"):
                return "stop"
            if not state:
                return "fenced"
        return "done"

    match cue:
        case "crash_before_commit":
            os.kill(os.getpid(), signal.SIGKILL)
        case "fail_transient" | "fail_final":
            return report(outcome="failed", transient=cue == "fail_transient", reason=cue)
        case "hang":
            ended = work(None)
            return report(outcome="stopped") if ended == "stop" else 3
    ended = work(task["seconds"])
    if ended == "stop":
        return report(outcome="stopped")
    if ended == "fenced":
        return 3
    output = {"job": options.job, "attempt": lease["attempt"], "slept": task["seconds"]}
    key = f"{options.job}:{lease['attempt']}"
    status = report(outcome="succeeded", key=key, sha256=digest(canonical_json(output)))
    if cue == "crash_after_commit":
        os.kill(os.getpid(), signal.SIGKILL)
    return status


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except httpx.HTTPError:
        sys.exit(4)
