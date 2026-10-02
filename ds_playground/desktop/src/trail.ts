/** Pure projections of the ledger's event log: nothing here is trusted from prose or from a model. */

export type LedgerEvent = {
  seq: number;
  event_id: string;
  type: string;
  recorded_at: string;
  body: Record<string, unknown>;
};

export type StageState =
  | "pending"
  | "running"
  | "waiting_for_user"
  | "failed"
  | "inconclusive"
  | "completed";

export type Stage = { id: string; label: string; state: StageState; note: string };

export const STAGES = [
  ["goal", "Goal and constraints"],
  ["environment", "Environment and context"],
  ["data", "Data and sources"],
  ["plan", "Review the workflow"],
  ["develop", "Develop and optimise"],
  ["self_check", "Development checks"],
  ["evaluate", "Independent evaluation"],
  ["report_release", "Report and release"],
  ["operate", "Install and observe"],
] as const;

export const STALE_AFTER_SECONDS = 60;

/**
 * Add events to the log. The log is keyed by sequence and kept in commit order, so duplicates,
 * replays and any arrival order end in the same log. A reset discards what was known first.
 */
export function merge(log: LedgerEvent[], incoming: LedgerEvent[], reset = false): LedgerEvent[] {
  const bySeq = new Map((reset ? [] : log).map((event) => [event.seq, event]));
  for (const event of incoming) bySeq.set(event.seq, event);
  return [...bySeq.values()].sort((left, right) => left.seq - right.seq);
}

/**
 * Derive the nine stage states from committed events. Only known event types move a stage; a
 * stage is completed only by the event that commits its evidence, never by a message saying so.
 */
export function trail(log: LedgerEvent[]): Stage[] {
  const stages = new Map<string, Stage>(
    STAGES.map(([id, label]) => [id, { id, label, state: "pending", note: "" }]),
  );
  const set = (id: string, state: StageState, note: string) =>
    stages.set(id, { ...stages.get(id)!, state, note });
  const sources = new Set<unknown>();
  for (const { type, body } of log) {
    if (type === "discovery.finished") {
      const observed = body.evidence_source === "observed";
      set("environment", observed ? "completed" : "inconclusive", observed ? "" : "nothing observed");
    } else if (type === "grant.created" && body.purpose === "source_root") {
      sources.add(body.handle);
    } else if (type === "grant.revoked") {
      sources.delete(body.handle);
    } else if (type === "plan.proposed") {
      set("plan", "waiting_for_user", String(body.outcome));
    } else if (type === "job.started") {
      set("develop", "running", "");
    } else if (type === "job.succeeded") {
      set("develop", "completed", "");
    } else if (type === "job.failed") {
      set("develop", "failed", String(body.code));
    }
  }
  if (sources.size)
    set("data", "pending", `${sources.size} source${sources.size === 1 ? "" : "s"} granted`);
  return [...stages.values()];
}

/** How old an observation is, and whether a display of it has gone stale (D19: after 60 s). */
export function freshness(observedAt: string | null, now: number) {
  if (!observedAt) return { seconds: null, stale: true };
  const seconds = Math.max(0, Math.round((now - Date.parse(observedAt)) / 1000));
  return { seconds, stale: seconds > STALE_AFTER_SECONDS };
}
