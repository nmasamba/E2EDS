import { invoke } from "@tauri-apps/api/core";
import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

type Harness = { base_url: string; token: string };
type Status =
  | { state: "connecting" }
  | { state: "connected"; version: string; pid: number; harness: Harness }
  | { state: "unavailable"; reason: string };
type Grant = { handle: string; purpose: "source_root" | "output_root"; label: string };

const RETRY_MS = 250;
const GIVE_UP_MS = 15_000;
const PURPOSES = { source_root: "Source", output_root: "Output" } as const;

/** One authenticated request to the harness. The token is held in memory only. */
async function call<T>(harness: Harness, path: string, method = "GET"): Promise<T> {
  const response = await fetch(`${harness.base_url}${path}`, {
    method,
    headers: { Authorization: `Bearer ${harness.token}` },
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
function Folders({ harness }: { harness: Harness }) {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [problem, setProblem] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);

  const attempt = async (change?: () => Promise<unknown>) => {
    try {
      await change?.();
      setGrants((await call<{ grants: Grant[] }>(harness, "/v1/grants")).grants);
      setProblem("");
    } catch (error) {
      setProblem(error instanceof Error ? error.message : String(error));
    }
  };
  useEffect(() => {
    void attempt();
  }, []);

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

function App() {
  const [status, setStatus] = useState<Status>({ state: "connecting" });
  useEffect(() => {
    void connect().then(setStatus);
  }, []);
  return (
    <main>
      <h1>DS Playground</h1>
      <p role="status">
        {status.state === "connecting" && "… Connecting to the harness"}
        {status.state === "connected" && "● Harness connected"}
        {status.state === "unavailable" && "○ Harness unavailable"}
      </p>
      {status.state === "connected" && (
        <p className="detail">
          version {status.version} · process {status.pid}
        </p>
      )}
      {status.state === "unavailable" && <p className="detail">{status.reason}</p>}
      {status.state === "connected" && <Folders harness={status.harness} />}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
