import { expect, test } from "vitest";
import {
  activity,
  expectedRevision,
  freshness,
  jobs,
  liveJob,
  merge,
  trail,
  type LedgerEvent,
} from "./trail";

const event = (seq: number, type: string, body: Record<string, unknown> = {}): LedgerEvent => ({
  seq,
  event_id: `e${seq}`,
  type,
  recorded_at: "2026-10-02T00:00:00+00:00",
  body,
});

const history = [
  event(1, "grant.created", { handle: "grant-a", purpose: "source_root", label: "data" }),
  event(2, "grant.created", { handle: "grant-b", purpose: "output_root", label: "out" }),
  event(3, "discovery.finished", { evidence_source: "observed" }),
  event(4, "plan.proposed", { outcome: "INSUFFICIENT_EVIDENCE" }),
  event(7, "job.started", {}),
  event(8, "job.succeeded", {}),
  event(9, "export.committed", {}),
];

const states = (log: LedgerEvent[]) =>
  Object.fromEntries(trail(log).map((stage) => [stage.id, [stage.state, stage.note]]));

test("R20: the nine stages come from committed events, in the suite's order", () => {
  expect(trail([]).map((stage) => [stage.id, stage.state])).toEqual([
    ["goal", "pending"],
    ["environment", "pending"],
    ["data", "pending"],
    ["plan", "pending"],
    ["develop", "pending"],
    ["self_check", "pending"],
    ["evaluate", "pending"],
    ["report_release", "pending"],
    ["operate", "pending"],
  ]);
  expect(states(history)).toMatchObject({
    environment: ["completed", ""],
    data: ["pending", "1 source granted"],
    plan: ["waiting_for_user", "INSUFFICIENT_EVIDENCE"],
    develop: ["completed", ""],
    evaluate: ["pending", ""],
  });
});

test("R20: duplicate, out-of-order and replayed events converge on the same log", () => {
  const shuffled = [history[5], history[0], history[3], history[0], history[6], history[2]];
  const late = [history[4], history[1], history[4]];
  const converged = merge(merge([], shuffled), late);
  expect(converged).toEqual(history);
  expect(merge(converged, history)).toEqual(history);
  expect(trail(converged)).toEqual(trail(history));
});

test("R20: a reset replaces what was known instead of adding to it", () => {
  const other = [event(1, "job.failed", { code: "INPUT_INVALID" })];
  expect(merge(history, other, true)).toEqual(other);
  expect(states(merge(history, other, true)).develop).toEqual(["failed", "INPUT_INVALID"]);
});

test("R20: a job that starts again is running again, and a revoked source is not counted", () => {
  const rerun = [...history, event(10, "job.started"), event(11, "grant.revoked", { handle: "grant-a" })];
  expect(states(rerun)).toMatchObject({ develop: ["running", ""], data: ["pending", ""] });
  const second = event(12, "grant.created", { handle: "grant-c", purpose: "source_root" });
  expect(states([...history, second]).data).toEqual(["pending", "2 sources granted"]);
  expect(states([...rerun, event(12, "job.failed", { code: "FORBIDDEN" })]).develop).toEqual([
    "failed",
    "FORBIDDEN",
  ]);
});

test("R20: prose or unknown events claiming completion change nothing", () => {
  const spoofed = [
    event(1, "stage.completed", { stage: "evaluate", outcome: "PASS" }),
    event(2, "assistant.message", { text: "The evaluation is completed and passed." }),
    event(3, "job.succeeded.fake", {}),
    event(4, "discovery.finished", { evidence_source: "unknown" }),
  ];
  expect(states(spoofed)).toMatchObject({
    evaluate: ["pending", ""],
    develop: ["pending", ""],
    environment: ["inconclusive", "nothing observed"],
  });
});

test("D19: an observation is stale after 60 seconds, and never fresh when there is none", () => {
  const at = "2026-10-02T00:00:00+00:00";
  const base = Date.parse(at);
  expect(freshness(at, base + 12_400)).toEqual({ seconds: 12, stale: false });
  expect(freshness(at, base + 60_000)).toEqual({ seconds: 60, stale: false });
  expect(freshness(at, base + 61_000)).toEqual({ seconds: 61, stale: true });
  expect(freshness(at, base - 5_000)).toEqual({ seconds: 0, stale: false });
  expect(freshness(null, base)).toEqual({ seconds: null, stale: true });
});

const job = (seq: number, type: string, id: string, state: string, attempt = 0, fence = 0, extra = {}) =>
  event(seq, type, { job: id, action: type.slice(4), at: "t", input: {}, state, attempt, fence, ...extra });

test("A07, A25: the develop stage follows the job's committed state, never a label", () => {
  const states = (log: LedgerEvent[]) => trail(log).find((stage) => stage.id === "develop")!;
  expect(states([job(1, "job.queued", "job-a", "queued")])).toMatchObject({
    state: "pending",
    note: "queued, waiting for a worker",
  });
  expect(states([job(1, "job.started", "job-a", "running", 1)]).state).toBe("running");
  expect(states([job(1, "job.pause_requested", "job-a", "pause_requested", 1, 1)])).toMatchObject({
    state: "running",
    note: "pausing",
  });
  expect(states([job(1, "job.paused", "job-a", "paused", 1, 1)])).toMatchObject({
    state: "waiting_for_user",
    note: "paused",
  });
  expect(states([job(1, "job.cancelled", "job-a", "cancelled", 1, 2)])).toMatchObject({
    state: "inconclusive",
    note: "cancelled",
  });
  expect(states([job(1, "job.succeeded", "job-a", "succeeded", 1)]).state).toBe("completed");
  const failed = job(1, "job.failed", "job-a", "failed", 3, 0, { input: { reason: "io" } });
  expect(states([failed])).toMatchObject({ state: "failed", note: "io" });
  expect(states([job(1, "job.heartbeat", "job-a", "running", 1)]).state).toBe("running");
  expect(states([job(1, "job.result_rejected", "job-a", "succeeded", 1)]).state).toBe("completed");
  expect(states([event(1, "job.started", { recipe: "profile-csv" })]).state).toBe("running");
  expect(states([event(1, "job.succeeded.fake", { state: "succeeded" })]).state).toBe("pending");
  const revised = event(2, "workload.revised", { from: "1.0.0", to: "2.0.0", patch: [], impact: { stale: [], holds: [] } });
  expect(trail([revised]).find((stage) => stage.id === "goal")).toMatchObject({
    state: "pending",
    note: "requirements at 2.0.0",
  });
});

test("A24: the live job is the newest that has not ended; the revision is the last applied", () => {
  const log = [
    job(1, "job.queued", "job-a", "queued"),
    job(2, "job.started", "job-a", "running", 1),
    job(3, "job.queued", "job-b", "queued"),
    job(4, "job.cancelled", "job-b", "cancelled"),
    job(5, "job.heartbeat", "job-a", "running", 1),
  ];
  expect(jobs(log).map((view) => [view.id, view.state])).toEqual([
    ["job-b", "cancelled"],
    ["job-a", "running"],
  ]);
  expect(liveJob(log)).toEqual({ id: "job-a", state: "running", attempt: 1, fence: 0 });
  expect(liveJob([...log, job(6, "job.succeeded", "job-a", "succeeded", 1)])).toBeNull();
  expect(liveJob([job(1, "job.paused", "job-c", "paused")])?.state).toBe("paused");
  expect(expectedRevision(log)).toBe("1.0.0");
  const revised = event(7, "workload.revised", { from: "1.0.0", to: "2.0.0", patch: [], impact: { stale: [], holds: [] } });
  expect(expectedRevision([...log, revised])).toBe("2.0.0");
});

test("A27, R20: the activity trail is the committed events with each command's reached state", () => {
  const log = [
    event(1, "discovery.finished", { evidence_source: "observed" }),
    event(2, "message.received", { command: "c1", text: "pause now", state: "received" }),
    event(3, "command.rejected", { command: "c1", state: "rejected", because: "no job is live" }),
    job(4, "job.queued", "job-abcdef", "queued"),
    job(5, "job.heartbeat", "job-abcdef", "running", 1),
    job(6, "job.started", "job-abcdef", "running", 1),
    event(7, "message.received", { command: "c2", text: "exclude field region", state: "received" }),
    event(8, "workload.revised", {
      from: "1.0.0",
      to: "2.0.0",
      patch: [{ path: "/intent_constraints/features/allowed_fields" }, { path: "/intent_constraints/features/excluded_fields" }],
      impact: { stale: [{}], holds: ["job-abcdef"] },
    }),
    event(9, "command.applied", { command: "c2", state: "applied" }),
    event(10, "admission.rejected", { reason: "needs 1 processors; 0 free" }),
    event(11, "message.received", { command: "c3", text: "status", state: "received" }),
  ];
  expect(activity(log).map((item) => [item.seq, item.text, item.state])).toEqual([
    [1, "Environment observed: observed", ""],
    [2, "You: pause now", "rejected · no job is live"],
    [4, "Job abcdef: queued", ""],
    [6, "Job abcdef: running (attempt 1, fence 0)", ""],
    [7, "You: exclude field region", "applied"],
    [8, "Requirements 1.0.0 → 2.0.0: allowed_fields, excluded_fields; 1 stale, 1 held", ""],
    [10, "Admission refused: needs 1 processors; 0 free", ""],
    [11, "You: status", "received"],
  ]);
});
