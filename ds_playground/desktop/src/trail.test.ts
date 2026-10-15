import { expect, test } from "vitest";
import {
  activity,
  assistant,
  expectedRevision,
  freshness,
  jobs,
  liveJob,
  results,
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

test("R18: the assistant is ready only by its own committed event, and unavailable says why", () => {
  expect(assistant([])).toEqual({ state: "unavailable", reason: "not started", profile: "" });
  const down = [event(1, "assistant.unavailable", { reason: "model missing" })];
  expect(assistant(down)).toEqual({ state: "unavailable", reason: "model missing", profile: "" });
  const up = [...down, event(2, "assistant.ready", { profile: "assistant-local-cpu-v1", model_sha256: "sha256:d9" })];
  expect(assistant(up)).toMatchObject({ state: "ready", profile: "assistant-local-cpu-v1" });
  const said = [...up, event(3, "assistant.message", { text: "I am ready" }), event(4, "assistant.unavailable", { reason: "the model server stopped" })];
  expect(assistant(said)).toMatchObject({ state: "unavailable", reason: "the model server stopped" });
  expect(activity(up).map((item) => item.text)).toEqual([
    "Assistant unavailable: model missing",
    "Assistant ready: assistant-local-cpu-v1",
  ]);
});

test("B24, A24: a child job is addressed through its live parent; assistant lines are proposals", () => {
  const parent = job(1, "job.queued", "job-p", "queued");
  const child = job(3, "job.queued", "job-c", "queued", 0, 0, { input: { parent: "job-p" } });
  const log = [parent, job(2, "job.started", "job-p", "running", 1), child, job(4, "job.started", "job-c", "running", 1)];
  expect(liveJob(log)?.id).toBe("job-p");
  expect(jobs(log).map((view) => view.id)).toEqual(["job-p"]);
  const ended = [...log, job(5, "job.succeeded", "job-p", "succeeded", 1)];
  expect(liveJob(ended)?.id).toBe("job-c");
  const said = [
    event(6, "assistant.call_dispatched", { job: "job-p", n: 1, tool: "inspect_schema" }),
    event(7, "assistant.call_refused", { job: "job-p", n: 2, tool: "request_trial", code: "INPUT_INVALID", reason: "arguments" }),
    event(8, "assistant.answered", { job: "job-p", n: 3, text: "The evaluation passed." }),
  ];
  expect(activity(said).map((item) => [item.text, item.state])).toEqual([
    ["Assistant call 1: inspect_schema", ""],
    ["Assistant call 2: request_trial", "refused · arguments"],
    ["Assistant (a proposal, not a result): The evaluation passed.", ""],
  ]);
  expect(trail(said).find((stage) => stage.id === "evaluate")!.state).toBe("pending");
});

test("D23, A28: a result is the record a job's success names, never a message's claim", () => {
  const log = [
    job(1, "job.queued", "job-a", "queued"),
    job(2, "job.succeeded", "job-a", "succeeded", 1, 0, { input: { key: "job-a.1", sha256: "sha256:a" } }),
    event(3, "assistant.answered", { job: "job-b", text: "the table is ready: sha256:fake" }),
    job(4, "job.succeeded", "job-c", "succeeded", 1, 0, { input: { key: "job-c.1", sha256: "sha256:c" } }),
    job(5, "job.failed", "job-d", "failed", 1, 0, { input: { reason: "crash" } }),
  ];
  expect(results(log)).toEqual([
    { job: "job-c", sha256: "sha256:c" },
    { job: "job-a", sha256: "sha256:a" },
  ]);
  expect(results([])).toEqual([]);
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

test("A27, R20: the activity trail is the committed events with each command's reached state and one wording", () => {
  const log = [
    event(1, "discovery.finished", { evidence_source: "observed" }),
    event(2, "message.received", { command: "c1", text: "pause now", state: "received" }),
    event(3, "command.rejected", { command: "c1", state: "rejected", because: "no job is live", reason: "no job is live" }),
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
    event(12, "message.received", { command: "c4", text: "summarise it", state: "received" }),
    event(13, "command.rejected", {
      command: "c4",
      state: "rejected",
      because: "ASSISTANT_UNAVAILABLE",
      reason: "no assistant is bound yet",
    }),
    event(14, "message.received", { command: "c5", text: "resume", state: "received" }),
    event(15, "command.rejected", { command: "c5", state: "rejected", because: "PAUSED" }),
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
    [12, "You: summarise it", "rejected · no assistant is bound yet"],
    [14, "You: resume", "rejected · PAUSED"],
  ]);
});

test("B26, A04: a sandboxed job's failure and a refused late result read in one wording", () => {
  const reason = "undeclared_read: 1 open(s) outside the declaration; the OS answered PermissionError";
  const log = [
    job(1, "job.started", "job-123456", "running", 1),
    job(2, "job.failed", "job-123456", "failed", 1, 0, { input: { attempt: 1, fence: 0, reason } }),
    job(3, "job.expired", "job-abcdef", "queued", 1, 1),
    job(4, "job.result_rejected", "job-abcdef", "queued", 1, 1, {
      input: { attempt: 1, fence: 0, outcome: "succeeded", because: "REVISION_CONFLICT" },
    }),
    job(5, "job.succeeded", "job-fedcba", "succeeded", 1),
  ];
  expect(activity(log).map((item) => [item.text, item.state])).toEqual([
    ["Job 123456: running (attempt 1, fence 0)", ""],
    ["Job 123456: failed (attempt 1, fence 0)", reason],
    ["Job abcdef: queued (attempt 1, fence 1)", ""],
    ["Job abcdef: succeeded result refused (attempt 1, fence 0)", "REVISION_CONFLICT"],
    ["Job fedcba: succeeded (attempt 1, fence 0)", ""],
  ]);
});
