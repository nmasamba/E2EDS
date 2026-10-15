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

/** The develop stage as each job state leaves it; the note is what the owner needs to know. */
const DEVELOP: Record<string, [StageState, string]> = {
  queued: ["pending", "queued, waiting for a worker"],
  running: ["running", ""],
  checkpointed: ["running", "checkpointed"],
  pause_requested: ["running", "pausing"],
  paused: ["waiting_for_user", "paused"],
  cancel_requested: ["running", "cancelling"],
  cancelled: ["inconclusive", "cancelled"],
  succeeded: ["completed", ""],
  failed: ["failed", ""],
};
const ENDED = new Set(["succeeded", "failed", "cancelled"]);
/** The coordinator's event types; a job state is read from these and from nothing else. */
const JOB_EVENTS = new Set(
  [
    "queued", "started", "heartbeat", "checkpointed", "succeeded", "failed", "requeued", "expired",
    "cancel_requested", "cancelled", "pause_requested", "paused", "resumed", "result_rejected",
  ].map((name) => `job.${name}`),
);
const jobState = (type: string, body: Record<string, unknown>) =>
  JOB_EVENTS.has(type) && typeof body.job === "string" && typeof body.state === "string"
    ? body.state
    : null;

export type JobView = { id: string; state: string; attempt: number; fence: number };
export type Activity = { seq: number; at: string; text: string; state: string };

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
    } else if (jobState(type, body) && String(body.state) in DEVELOP) {
      const [state, note] = DEVELOP[String(body.state)];
      const input = (body.input ?? {}) as Record<string, unknown>;
      set("develop", state, body.state === "failed" ? String(input.reason ?? "") : note);
    } else if (type === "job.started") {
      set("develop", "running", "");
    } else if (type === "job.succeeded") {
      set("develop", "completed", "");
    } else if (type === "job.failed") {
      set("develop", "failed", String(body.code));
    } else if (type === "workload.revised") {
      set("goal", stages.get("goal")!.state, `requirements at ${body.to}`);
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

/** Every job's latest state from its own events, the most recently queued first. */
export function jobs(log: LedgerEvent[]): JobView[] {
  const seen = new Map<string, JobView>();
  const parents = new Map<string, string>();
  for (const { type, body } of log) {
    const state = jobState(type, body);
    if (!state) continue;
    const input = (body.input ?? {}) as Record<string, unknown>;
    if (type === "job.queued" && typeof input.parent === "string") parents.set(String(body.job), input.parent);
    seen.set(String(body.job), {
      id: String(body.job),
      state,
      attempt: Number(body.attempt),
      fence: Number(body.fence),
    });
  }
  // A job the assistant submitted is addressed through its parent while that parent is live.
  const live = (id: string) => seen.has(id) && !ENDED.has(seen.get(id)!.state);
  return [...seen.values()].filter((job) => !live(parents.get(job.id) ?? "")).reverse();
}

/** The job the header's controls act on: the most recent one that has not ended. */
export const liveJob = (log: LedgerEvent[]) => jobs(log).find((job) => !ENDED.has(job.state)) ?? null;

/** The requirement revision a new message must name: the last revision applied, else the first. */
export const expectedRevision = (log: LedgerEvent[]) =>
  String(log.filter((event) => event.type === "workload.revised").at(-1)?.body.to ?? "1.0.0");

const tail = (id: unknown) => String(id).slice(-6);

/**
 * The activity trail, the one place an outcome is shown: what the owner said (typed, a button, a
 * shortcut or the menu) with the state each command reached and its reason, every job
 * transition except heartbeats, with the reason the coordinator recorded for a failure (a sandboxed
 * task's failure kind and message) and the code that refused a late result, requirement
 * revisions, refused admissions and the workspace's own events, in commit order. Nothing here is
 * a model's narration; every line is a committed event.
 */
export function activity(log: LedgerEvent[]): Activity[] {
  const settled = new Map<string, string>();
  for (const { type, body } of log)
    if (type.startsWith("command."))
      settled.set(String(body.command), [body.state, body.reason ?? body.because].filter(Boolean).join(" · "));
  const items: Activity[] = [];
  for (const { seq, recorded_at: at, type, body } of log) {
    const add = (text: string, state = "") => items.push({ seq, at, text, state });
    if (type === "message.received") add(`You: ${body.text}`, settled.get(String(body.command)) ?? "received");
    else if (type === "job.heartbeat" || type.startsWith("command.")) continue;
    else if (jobState(type, body)) {
      // A refused result is about the attempt that sent it, not the job's state now.
      const input = (body.input ?? {}) as Record<string, unknown>;
      const refused = type === "job.result_rejected";
      const [number, fence] = refused ? [input.attempt, input.fence] : [body.attempt, body.fence];
      const attempt = Number(number) ? ` (attempt ${number}, fence ${fence})` : "";
      const said = refused ? `${input.outcome} result refused` : String(body.state).replace("_", " ");
      add(`Job ${tail(body.job)}: ${said}${attempt}`, String(input.reason ?? input.because ?? ""));
    } else if (type === "workload.revised") {
      const impact = body.impact as { stale: unknown[]; holds: unknown[] };
      const changed = (body.patch as { path: string }[]).map((op) => op.path.split("/").at(-1)).join(", ");
      add(`Requirements ${body.from} → ${body.to}: ${changed}; ${impact.stale.length} stale, ${impact.holds.length} held`);
    } else if (type === "admission.rejected") add(`Admission refused: ${body.reason}`);
    else if (type === "discovery.finished") add(`Environment observed: ${body.evidence_source}`);
    else if (type === "plan.proposed") add(`Plan proposed: ${body.outcome}`);
    else if (type === "grant.created") add(`Folder granted: ${body.label}`);
    else if (type === "grant.revoked") add("Folder removed");
    else if (type === "export.committed") add(`Export committed: ${body.version}`);
    else if (type === "assistant.ready") add(`Assistant ready: ${body.profile}`);
    else if (type === "assistant.unavailable") add(`Assistant unavailable: ${body.reason}`);
    else if (type === "assistant.call_dispatched") add(`Assistant call ${body.n}: ${body.tool}`);
    else if (type === "assistant.call_refused") add(`Assistant call ${body.n}: ${body.tool}`, `refused · ${body.reason}`);
    else if (type === "assistant.answered") add(`Assistant (a proposal, not a result): ${body.text}`);
  }
  return items;
}

export type AssistantView = { state: string; reason: string; profile: string };

/** The assistant as its last committed event left it: never ready on a message's say-so. */
export function assistant(log: LedgerEvent[]): AssistantView {
  let view: AssistantView = { state: "unavailable", reason: "not started", profile: "" };
  for (const { type, body } of log) {
    if (type === "assistant.ready") view = { state: "ready", reason: "", profile: String(body.profile) };
    else if (type === "assistant.unavailable") view = { state: "unavailable", reason: String(body.reason), profile: "" };
  }
  return view;
}
