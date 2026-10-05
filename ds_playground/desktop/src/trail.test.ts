import { expect, test } from "vitest";
import { freshness, merge, trail, type LedgerEvent } from "./trail";

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
