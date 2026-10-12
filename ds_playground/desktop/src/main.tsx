import { invoke } from "@tauri-apps/api/core";
import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  activity,
  expectedRevision,
  freshness,
  liveJob,
  merge,
  trail,
  type Activity,
  type JobView,
  type LedgerEvent,
  type StageState,
} from "./trail";

type Harness = { base_url: string; token: string };
type Status =
  | { state: "connecting" }
  | { state: "connected"; version: string; pid: number; harness: Harness }
  | { state: "unavailable"; reason: string };
type Grant = { handle: string; purpose: "source_root" | "output_root"; label: string };

type Snapshot = {
  observed_at: string | null;
  system: { os: string | null; architecture: string | null };
  cpu: { visible_logical_processors: number | null; effective_cpu_quota: number | null };
  memory: { total_gib: number | null; available_gib: number | null };
  storage: { available_gib: number | null }[];
  accelerators: { inventory_status: string; devices: { model: string; sharing: string }[] };
  probes: { name: string; status: string; safe_summary: string }[];
};
type Plan = {
  feasibility_outcome: string;
  recommendation: string;
  alternatives: { option_id: string; disposition: string; reason: string }[];
  required_conditions: string[];
};

const CONVERSATION = "conversation-local";
const ENDED = new Set(["succeeded", "failed", "cancelled"]);
/** The native menu's chords, handled here too, so they work wherever the window has focus. */
const SHORTCUTS: Record<string, string> = { p: "pause", ".": "cancel" };
const LABELS: Record<string, string> = { pause: "Pause", resume: "Resume", cancel: "Cancel run" };
/** Shows, in the activity trail, a request the harness never recorded. */
type NotReceived = (what: string) => (error: unknown) => void;

const RETRY_MS = 250;
const GIVE_UP_MS = 15_000;
const POLL_MS = 2_000;
const PURPOSES = { source_root: "Source", output_root: "Output" } as const;
const WORDS: Record<StageState, string> = {
  pending: "○ Not started",
  running: "◐ Running",
  waiting_for_user: "◆ Waiting for you",
  failed: "✕ Failed",
  inconclusive: "◇ Inconclusive",
  completed: "● Completed",
};
const known = (value: number | string | null | undefined) => value ?? "unknown";

/** One authenticated request to the harness. The token is held in memory only. */
async function call<T>(harness: Harness, path: string, method = "GET", payload?: unknown): Promise<T> {
  const response = await fetch(`${harness.base_url}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${harness.token}`,
      ...(payload === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  const body: T & { message?: string } = await response.json();
  if (!response.ok) throw new Error(body.message);
  return body;
}

/**
 * Ask the shell where the harness is, then ask the harness for its status. The harness may still
 * be starting, so an unreadable state file or an unanswered port is retried until the deadline;
 * an answer from the harness, good or bad, is final.
 */
async function connect(): Promise<Status> {
  let reason = "";
  for (const start = Date.now(); Date.now() - start < GIVE_UP_MS; ) {
    try {
      const harness = await invoke<Harness>("harness");
      const response = await fetch(`${harness.base_url}/v1/status`, {
        headers: { Authorization: `Bearer ${harness.token}` },
      });
      const body: { version: string; pid: number; message: string } = await response.json();
      return response.ok
        ? { state: "connected", version: body.version, pid: body.pid, harness }
        : { state: "unavailable", reason: body.message };
    } catch (error) {
      reason = error instanceof TypeError ? "the harness did not answer" : String(error);
      await new Promise((resolve) => setTimeout(resolve, RETRY_MS));
    }
  }
  return { state: "unavailable", reason };
}

/**
 * The folders the owner has granted. Picking happens in the shell's native dialog, which gives
 * the path to the harness directly; this view only ever holds handles and folder names.
 */
function Folders({ harness, revision }: { harness: Harness; revision: number }) {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [problem, setProblem] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const queue = useRef(Promise.resolve());

  // One at a time, in order, so a refresh that finishes late cannot undo a newer change. Only
  // the owner's own action sets or clears the problem; a background refresh leaves it alone.
  const attempt = (change?: () => Promise<unknown>) =>
    (queue.current = queue.current.then(async () => {
      try {
        await change?.();
        setGrants((await call<{ grants: Grant[] }>(harness, "/v1/grants")).grants);
        if (change) setProblem("");
      } catch (error) {
        if (change) setProblem(error instanceof Error ? error.message : String(error));
      }
    }));
  useEffect(() => {
    void attempt();
  }, [revision]);

  return (
    <section aria-labelledby="folders">
      <h2 id="folders" tabIndex={-1} ref={heading}>
        Folders
      </h2>
      {grants.length === 0 && <p>No folders granted yet.</p>}
      <ul>
        {grants.map((grant) => (
          <li key={grant.handle}>
            <span>
              {PURPOSES[grant.purpose]} folder: {grant.label}
            </span>
            <button
              type="button"
              aria-label={`Remove ${PURPOSES[grant.purpose].toLowerCase()} folder ${grant.label}`}
              onClick={async () => {
                await attempt(() => call(harness, `/v1/grants/${grant.handle}/revoke`, "POST"));
                heading.current?.focus();
              }}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <p>
        {(["source_root", "output_root"] as const).map((purpose) => (
          <button
            key={purpose}
            type="button"
            onClick={() => attempt(() => invoke("grant_folder", { purpose }))}
          >
            Add {PURPOSES[purpose].toLowerCase()} folder…
          </button>
        ))}
      </p>
      {problem && <p role="alert">Could not update folders: {problem}</p>}
    </section>
  );
}

/** What discovery observed, with what it could not observe said plainly, and how old it is. */
function Environment(props: { snapshot: Snapshot | null; now: number; observe: () => void }) {
  const { snapshot, now, observe } = props;
  const age = freshness(snapshot?.observed_at ?? null, now);
  const gpus = snapshot?.accelerators;
  const unobserved = snapshot?.probes.filter((probe) => probe.status !== "observed") ?? [];
  return (
    <section aria-labelledby="environment">
      <h2 id="environment">Environment</h2>
      {snapshot ? (
        <dl>
          <dt>System</dt>
          <dd>
            {known(snapshot.system.os)} {known(snapshot.system.architecture)}
          </dd>
          <dt>Processors</dt>
          <dd>
            {known(snapshot.cpu.visible_logical_processors)} visible,{" "}
            {known(snapshot.cpu.effective_cpu_quota)} usable
          </dd>
          <dt>Memory</dt>
          <dd>
            {known(snapshot.memory.total_gib)} GiB total, {known(snapshot.memory.available_gib)} GiB
            available
          </dd>
          <dt>Storage</dt>
          <dd>{known(snapshot.storage[0]?.available_gib)} GiB free</dd>
          <dt>Accelerators</dt>
          <dd>
            {gpus?.inventory_status === "observed_present" &&
              gpus.devices
                .map((device) => `${device.model} (${device.sharing} memory, not checked)`)
                .join(", ")}
            {gpus?.inventory_status === "observed_absent" && "none observed"}
            {gpus?.inventory_status === "unknown" && "unknown"}
          </dd>
          {unobserved.map((probe) => (
            <div key={probe.name}>
              <dt>Not observed</dt>
              <dd>
                {probe.name}: {probe.safe_summary}
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <p>Not observed yet.</p>
      )}
      <p>
        {snapshot &&
          (age.seconds === null
            ? "Nothing could be observed. "
            : `${age.stale ? "Stale: observed" : "Observed"} ${age.seconds} s ago. `)}
        <button type="button" onClick={observe}>
          Observe again
        </button>
      </p>
    </section>
  );
}

/** The provisional plan as the rule table derived it; it authorises nothing. */
function ProposedPlan({ plan }: { plan: Plan | null }) {
  return (
    <section aria-labelledby="plan">
      <h2 id="plan">Provisional plan</h2>
      {plan ? (
        <>
          <p>
            Outcome: {plan.feasibility_outcome}. {plan.recommendation}
          </p>
          <ul>
            {plan.alternatives.map((option) => (
              <li key={option.option_id}>
                {option.option_id} is {option.disposition}: {option.reason}
              </li>
            ))}
            {plan.required_conditions.map((condition) => (
              <li key={condition}>Needs: {condition}</li>
            ))}
          </ul>
        </>
      ) : (
        <p>No plan yet.</p>
      )}
    </section>
  );
}

/**
 * Pause, resume and cancel for the live job: each press is one command with its own ID, sent on
 * the fast path. The outcome is the command's committed state, shown in the activity trail.
 * Cmd+P and Cmd+. (Ctrl elsewhere) press Pause and Cancel run from anywhere in the window.
 */
function Controls(props: { harness: Harness; job: JobView | null; notReceived: NotReceived }) {
  const { harness, job, notReceived } = props;
  const send = (action: string) => {
    if (!job) return;
    const body = { command_id: crypto.randomUUID(), action };
    call(harness, `/v1/jobs/${job.id}/control`, "POST", body).catch(notReceived(LABELS[action]));
  };
  useEffect(() => {
    const press = (event: KeyboardEvent) => {
      const command = /Mac/.test(navigator.platform) ? event.metaKey : event.ctrlKey;
      const action = command && !event.shiftKey && !event.altKey && SHORTCUTS[event.key.toLowerCase()];
      if (!action || !job) return;
      event.preventDefault();
      send(action);
    };
    document.addEventListener("keydown", press);
    return () => document.removeEventListener("keydown", press);
  });
  const paused = job?.state === "paused";
  return (
    <p className="controls">
      <button type="button" onClick={() => send(paused ? "resume" : "pause")} disabled={!job}>
        {paused ? "Resume" : "Pause"}
      </button>
      <button type="button" onClick={() => send("cancel")} disabled={!job || ENDED.has(job.state)}>
        Cancel run
      </button>
    </p>
  );
}

/**
 * The composer keeps its draft and its message ID until the harness has the message, so a retry
 * after a lost answer is the same message, not a second one. Its receipt is in the activity trail.
 */
function Composer(props: { harness: Harness; revision: string; notReceived: NotReceived }) {
  const { harness, revision, notReceived } = props;
  const [draft, setDraft] = useState("");
  const messageId = useRef(crypto.randomUUID());
  const send = async () => {
    if (!draft.trim()) return;
    const body = { client_message_id: messageId.current, text: draft, expected_revision: revision };
    try {
      await call(harness, `/v1/conversations/${CONVERSATION}/messages`, "POST", body);
      setDraft("");
      messageId.current = crypto.randomUUID();
    } catch (error) {
      notReceived(`You: ${draft}`)(error);
    }
  };
  return (
    <form
      className="composer"
      aria-label="Composer"
      onSubmit={(event) => {
        event.preventDefault();
        void send();
      }}
    >
      <textarea
        aria-label="Message"
        rows={2}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) void send();
        }}
      />
      <button type="submit">Send</button>
    </form>
  );
}

/**
 * The one workload that exists: the hung test job, queued here and run by a worker process. A
 * queued job and a refused admission are both committed events, so the trail shows the result.
 */
function Run({ harness, notReceived }: { harness: Harness; notReceived: NotReceived }) {
  const start = () => {
    const body = {
      operation: "analyse",
      idempotency_key: crypto.randomUUID(),
      task: { cues: ["hang"], seconds: 0 },
    };
    call(harness, "/v1/jobs", "POST", body).catch(
      (error) => error instanceof TypeError && notReceived("Start the hung test job")(error),
    );
  };
  return (
    <section aria-labelledby="run">
      <h2 id="run">Run</h2>
      <p>
        <button type="button" onClick={start}>
          Start the hung test job
        </button>
      </p>
    </section>
  );
}

/**
 * Every outcome, in one place: each committed event the owner would want to see with the state
 * each command reached, then any request this window sent that the harness never recorded.
 */
function ActivityTrail({ items, unheard }: { items: Activity[]; unheard: string[] }) {
  return (
    <section aria-labelledby="activity">
      <h2 id="activity">Activity</h2>
      {items.length + unheard.length === 0 && <p>Nothing has happened yet.</p>}
      <ol className="activity" aria-live="polite">
        {items.map((item) => (
          <li key={item.seq}>
            <span>
              {item.at.slice(11, 19)} {item.text}
              {item.state && ` · ${item.state}`}
            </span>
          </li>
        ))}
        {unheard.map((line, index) => (
          <li key={`unheard-${index}`}>
            <span>{line}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

/**
 * The workspace is a projection of the harness's ledger: it polls for events after its cursor
 * and derives everything shown from them. When a poll fails it keeps the last known state and
 * says so; it never assumes work stopped. It reconnects, and replays from its cursor, when the
 * harness answers again.
 */
function Workspace(props: { harness: Harness; version: string; pid: number }) {
  const { version, pid } = props;
  const [harness, setHarness] = useState(props.harness);
  const address = useRef(harness);
  address.current = harness;
  const [log, setLog] = useState<LedgerEvent[]>([]);
  const [lostAt, setLostAt] = useState("");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [now, setNow] = useState(Date.now());
  const cursor = useRef(0);
  const started = useRef(false);
  const [unheard, setUnheard] = useState<string[]>([]);
  const notReceived: NotReceived = (what) => (error) => {
    const why = error instanceof TypeError ? "the harness did not answer" : String((error as Error).message);
    setUnheard((lines) => [...lines, `${what} · not received · ${why}`]);
  };

  const observe = () => void call(address.current, "/v1/hardware", "POST").catch(() => undefined);
  useEffect(() => {
    const poll = async () => {
      try {
        type Batch = { events: LedgerEvent[]; cursor: number; reset: boolean };
        const batch = await call<Batch>(address.current, `/v1/events?after=${cursor.current}`);
        cursor.current = batch.cursor;
        setLog((log) => merge(log, batch.events, batch.reset));
        setLostAt("");
        if (!started.current && !batch.events.some((event) => event.type === "discovery.finished"))
          observe();
        started.current = true;
      } catch {
        setLostAt((since) => since || new Date().toLocaleTimeString());
        // The harness may have been restarted on a new port: ask the shell where it is now.
        void invoke<Harness>("harness").then(setHarness, () => undefined);
      }
      setNow(Date.now());
    };
    void poll();
    const timer = setInterval(poll, POLL_MS);
    return () => clearInterval(timer);
  }, []);

  const latest = (type: string) => log.filter((event) => event.type === type).at(-1)?.seq ?? 0;
  const [discovered, planned] = [latest("discovery.finished"), latest("plan.proposed")];
  useEffect(() => {
    if (discovered) void call<Snapshot>(harness, "/v1/hardware").then(setSnapshot, () => undefined);
  }, [discovered]);
  useEffect(() => {
    if (planned) void call<Plan>(harness, "/v1/plan").then(setPlan, () => undefined);
  }, [planned]);

  const age = freshness(snapshot?.observed_at ?? null, now);
  const live = liveJob(log);
  return (
    <>
      <p role="status">
        {lostAt ? `○ Connection lost; last known state as of ${lostAt}` : "● Harness connected"}
      </p>
      <p className="detail">
        version {version} · process {pid}
        {live && ` · job ${live.id.slice(-6)} ${live.state.replace("_", " ")}`}
      </p>
      <Controls harness={harness} job={live} notReceived={notReceived} />
      <div className="workspace">
        <nav aria-label="Work trail">
          <ol>
            {trail(log).map((stage) => (
              <li key={stage.id}>
                <span>{stage.label}</span>
                <span>
                  {WORDS[stage.state]}
                  {stage.note && ` · ${stage.note}`}
                </span>
              </li>
            ))}
          </ol>
        </nav>
        <div>
          <Environment snapshot={snapshot} now={now} observe={observe} />
          <ProposedPlan plan={plan} />
          <Folders
            harness={harness}
            revision={log.filter((event) => event.type.startsWith("grant.")).length}
          />
          <Run harness={harness} notReceived={notReceived} />
          <ActivityTrail items={activity(log)} unheard={unheard} />
        </div>
      </div>
      <Composer harness={harness} revision={expectedRevision(log)} notReceived={notReceived} />
      <section className="resources" aria-label="Resource status">
        {snapshot && age.seconds !== null
          ? `${known(snapshot.cpu.effective_cpu_quota)} processors · ` +
            `${known(snapshot.memory.available_gib)} of ${known(snapshot.memory.total_gib)} GiB ` +
            `memory available · ${known(snapshot.storage[0]?.available_gib)} GiB free · ` +
            `${age.stale ? "stale, " : ""}observed ${age.seconds} s ago`
          : "Resources not observed"}
      </section>
    </>
  );
}

function App() {
  const [status, setStatus] = useState<Status>({ state: "connecting" });
  useEffect(() => {
    void connect().then(setStatus);
  }, []);
  return (
    <main>
      <h1>DS Playground</h1>
      {status.state === "connected" ? (
        <Workspace harness={status.harness} version={status.version} pid={status.pid} />
      ) : (
        <>
          <p role="status">
            {status.state === "connecting" ? "… Connecting to the harness" : "○ Harness unavailable"}
          </p>
          {status.state === "unavailable" && <p className="detail">{status.reason}</p>}
        </>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
