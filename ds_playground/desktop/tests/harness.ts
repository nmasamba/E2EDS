import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export type Harness = { base_url: string; token: string; pid: number; home: string };

/** Start a real harness on a DSP_HOME, a new temporary one by default, and wait for its answer. */
export async function startHarness(home = mkdtempSync(join(tmpdir(), "dsp-renderer-"))): Promise<Harness> {
  spawn("uv", ["run", "--frozen", "--project", "..", "python", "-m", "dsp.harness", "--dev"], {
    env: { ...process.env, DSP_HOME: home },
    stdio: "ignore",
  });
  for (let attempt = 0; attempt < 300; attempt++) {
    try {
      const state: { port: number; token: string; pid: number } = JSON.parse(
        readFileSync(join(home, "harness.json"), "utf8"),
      );
      const base_url = `http://127.0.0.1:${state.port}`;
      const harness = { base_url, token: state.token, pid: state.pid, home };
      await fetch(`${harness.base_url}/v1/status`);
      return harness;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error("the harness did not start");
}

export type Pick = (purpose: string) => Promise<unknown>;

/**
 * A browser has no Tauri runtime: answer the shell's two commands the way the shell would. Both
 * run here in Node, outside the page, as Rust does: ``answer`` is read afresh on every call, and
 * the folder picker is played by ``pick``.
 */
export async function open(page: Page, answer: { base_url: string; token: string }, pick?: Pick) {
  await page.exposeFunction("shellPick", pick ?? (async () => null));
  await page.exposeFunction("shellHarness", () => ({ ...answer }));
  await page.addInitScript(() => {
    const shell = window as unknown as {
      shellPick: (purpose: string) => Promise<unknown>;
      shellHarness: () => Promise<unknown>;
    };
    Object.assign(window, {
      __TAURI_INTERNALS__: {
        invoke: async (command: string, args: { purpose: string }) => {
          if (command === "harness") return shell.shellHarness();
          if (command !== "grant_folder") return Promise.reject(`${command} not allowed`);
          return shell.shellPick(args.purpose).catch((error: Error) => Promise.reject(error.message));
        },
      },
    });
  });
  await page.goto("/");
}

/** One request to the harness from Node, which sends no Origin header: the CLI's position. */
export async function native<T = Record<string, unknown>>(harness: Harness, path: string, body?: object) {
  const response = await fetch(`${harness.base_url}${path}`, {
    method: body ? "POST" : "GET",
    headers: { Authorization: `Bearer ${harness.token}`, "Content-Type": "application/json" },
    body: body && JSON.stringify(body),
  });
  const answer: T & { message?: string } = await response.json();
  if (!response.ok) throw new Error(answer.message);
  return answer;
}

export const stage = (page: Page, label: string) =>
  page.getByRole("navigation", { name: "Work trail" }).getByRole("listitem").filter({ hasText: label });

export async function expectNoAxeViolations(page: Page) {
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
}
