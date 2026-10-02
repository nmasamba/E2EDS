import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

type Harness = { base_url: string; token: string; pid: number };

/** Start a real harness on a temporary DSP_HOME and wait until it answers. */
async function startHarness(): Promise<Harness> {
  const home = mkdtempSync(join(tmpdir(), "dsp-renderer-"));
  spawn("uv", ["run", "--frozen", "--project", "..", "python", "-m", "dsp.harness", "--dev"], {
    env: { ...process.env, DSP_HOME: home },
    stdio: "ignore",
  });
  for (let attempt = 0; attempt < 300; attempt++) {
    try {
      const state = JSON.parse(readFileSync(join(home, "harness.json"), "utf8"));
      const harness = { base_url: `http://127.0.0.1:${state.port}`, token: state.token, pid: state.pid };
      await fetch(`${harness.base_url}/v1/status`);
      return harness;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error("the harness did not start");
}

/** A browser has no Tauri runtime: answer the shell's one command the way the shell would. */
async function open(page: Page, answer: { base_url: string; token: string }) {
  await page.addInitScript((harness) => {
    Object.assign(window, {
      __TAURI_INTERNALS__: {
        invoke: async (command: string) =>
          command === "harness" ? harness : Promise.reject(`${command} not allowed`),
      },
    });
  }, answer);
  await page.goto("/");
}

async function expectNoAxeViolations(page: Page) {
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
}

let harness: Harness;
test.beforeAll(async () => {
  harness = await startHarness();
});
test.afterAll(() => {
  process.kill(harness.pid);
});

test("R26: shows connected with the harness version and pid", async ({ page }) => {
  await open(page, harness);
  await expect(page.getByRole("status")).toHaveText("● Harness connected");
  await expect(page.getByText(`version 0.1.0 · process ${harness.pid}`)).toBeVisible();
  await expectNoAxeViolations(page);
});

test("C23: a wrong token shows unavailable with the harness's reason", async ({ page }) => {
  await open(page, { ...harness, token: "wrong" });
  await expect(page.getByRole("status")).toHaveText("○ Harness unavailable");
  await expect(page.getByText("missing or wrong credential")).toBeVisible();
  await expectNoAxeViolations(page);
});

test("R26: a stopped harness shows connecting, then unavailable with the reason", async ({ page }) => {
  const stopped = await startHarness();
  process.kill(stopped.pid);
  const answers = () => fetch(stopped.base_url).then(() => true, () => false);
  await expect.poll(answers).toBe(false);
  await open(page, stopped);
  await expect(page.getByRole("status")).toHaveText("… Connecting to the harness");
  await expectNoAxeViolations(page);
  await expect(page.getByRole("status")).toHaveText("○ Harness unavailable", { timeout: 20_000 });
  await expect(page.getByText("the harness did not answer")).toBeVisible();
  await expectNoAxeViolations(page);
});

test("C23: the token is never stored, logged or rendered", async ({ page }) => {
  const logged: string[] = [];
  page.on("console", (message) => logged.push(message.text()));
  await open(page, harness);
  await expect(page.getByRole("status")).toHaveText("● Harness connected");
  const kept = await page.evaluate(() =>
    JSON.stringify([{ ...localStorage }, { ...sessionStorage }, document.cookie, document.body.innerHTML]),
  );
  expect(kept + logged.join()).not.toContain(harness.token);
});
