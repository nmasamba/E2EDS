import { invoke } from "@tauri-apps/api/core";
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type Status =
  | { state: "connecting" }
  | { state: "connected"; version: string; pid: number }
  | { state: "unavailable"; reason: string };

const RETRY_MS = 250;
const GIVE_UP_MS = 15_000;

/**
 * Ask the shell where the harness is, then ask the harness for its status. The harness may still
 * be starting, so an unreadable state file or an unanswered port is retried until the deadline;
 * an answer from the harness, good or bad, is final. The token lives only inside one attempt.
 */
async function connect(): Promise<Status> {
  let reason = "";
  for (const start = Date.now(); Date.now() - start < GIVE_UP_MS; ) {
    try {
      const { base_url, token } = await invoke<{ base_url: string; token: string }>("harness");
      const response = await fetch(`${base_url}/v1/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = await response.json();
      return response.ok
        ? { state: "connected", version: body.version, pid: body.pid }
        : { state: "unavailable", reason: body.message };
    } catch (error) {
      reason = error instanceof TypeError ? "the harness did not answer" : String(error);
      await new Promise((resolve) => setTimeout(resolve, RETRY_MS));
    }
  }
  return { state: "unavailable", reason };
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
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
