import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
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
      const state: { port: number; token: string; pid: number } = JSON.parse(
        readFileSync(join(home, "harness.json"), "utf8"),
      );
      const harness = { base_url: `http://127.0.0.1:${state.port}`, token: state.token, pid: state.pid };
      await fetch(`${harness.base_url}/v1/status`);
      return harness;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error("the harness did not start");
}

type Pick = (purpose: string) => Promise<unknown>;

/**
 * A browser has no Tauri runtime: answer the shell's two commands the way the shell would. The
 * folder picker is played by ``pick``, which runs here in Node, outside the page, as Rust does.
 */
async function open(page: Page, answer: { base_url: string; token: string }, pick?: Pick) {
  await page.exposeFunction("shellPick", pick ?? (async () => null));
  await page.addInitScript((harness) => {
    const shell = window as unknown as { shellPick: (purpose: string) => Promise<unknown> };
    Object.assign(window, {
      __TAURI_INTERNALS__: {
        invoke: async (command: string, args: { purpose: string }) => {
          if (command === "harness") return harness;
          if (command !== "grant_folder") return Promise.reject(`${command} not allowed`);
          return shell.shellPick(args.purpose).catch((error: Error) => Promise.reject(error.message));
        },
      },
    });
  }, answer);
  await page.goto("/");
}

type Answer = {
  handle: string;
  message: string;
  id: string;
  grants: { handle: string; label: string }[];
  cpu: { visible_logical_processors: number; effective_cpu_quota: number };
  memory: { total_gib: number };
};

/** One request to the harness from Node, which sends no Origin header: the CLI's position. */
async function native(path: string, body?: object) {
  const response = await fetch(`${harness.base_url}${path}`, {
    method: body ? "POST" : "GET",
    headers: { Authorization: `Bearer ${harness.token}`, "Content-Type": "application/json" },
    body: body && JSON.stringify(body),
  });
  const answer: Answer = await response.json();
  if (!response.ok) throw new Error(answer.message);
  return answer;
}

/** A real folder under a temporary directory, granted the way the shell's picker grants it. */
async function grant(purpose: string, name: string) {
  const folder = join(mkdtempSync(join(tmpdir(), "dsp-folders-")), name);
  mkdirSync(folder);
  return { folder, ...(await native("/v1/grants", { purpose, path: folder })) };
}

const folders = (page: Page) => page.getByRole("region", { name: "Folders" });
const stage = (page: Page, label: string) =>
  page.getByRole("navigation", { name: "Work trail" }).getByRole("listitem").filter({ hasText: label });

/** Profile a CSV through grants from Node, the way `dsp profile` does. */
async function profile(csv: string) {
  const work = mkdtempSync(join(tmpdir(), "dsp-work-"));
  writeFileSync(join(work, "data.csv"), csv);
  mkdirSync(join(work, "out"));
  const source = await native("/v1/grants", { purpose: "source_root", path: join(work, "data.csv") });
  const output = await native("/v1/grants", { purpose: "output_root", path: join(work, "out") });
  const request = { source_handle: source.handle, relative_path: ".", output_handle: output.handle };
  return native("/v1/profiles", request).catch((error: Error) => error.message);
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
test.afterEach(async () => {
  for (const active of (await native("/v1/grants")).grants) {
    await native(`/v1/grants/${active.handle}/revoke`, {});
  }
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

test("R26: granted folders are listed by name and never by path", async ({ page }) => {
  const source = await grant("source_root", "orders 2026");
  await grant("output_root", "reports");
  await open(page, harness);
  await expect(folders(page).getByRole("listitem")).toHaveText([
    "Source folder: orders 2026Remove",
    "Output folder: reportsRemove",
  ]);
  expect(await page.content()).not.toContain(tmpdir());
  expect(await page.content()).not.toContain(source.handle);
  await expectNoAxeViolations(page);
});

test("R26: a folder picked in the shell's dialog appears in the list", async ({ page }) => {
  const asked: string[] = [];
  await open(page, harness, async (purpose) => {
    asked.push(purpose);
    return grant(purpose, purpose === "source_root" ? "picked data" : "picked out");
  });
  await expect(page.getByText("No folders granted yet.")).toBeVisible();
  await expectNoAxeViolations(page);
  await page.getByRole("button", { name: "Add source folder…" }).click();
  await expect(folders(page).getByRole("listitem")).toHaveText(["Source folder: picked dataRemove"]);
  await page.getByRole("button", { name: "Add output folder…" }).click();
  await expect(folders(page).getByRole("listitem")).toHaveCount(2);
  expect(asked).toEqual(["source_root", "output_root"]);
  expect((await native("/v1/grants")).grants.map((active) => active.label)).toEqual([
    "picked data",
    "picked out",
  ]);
  await expect(page.getByText("No folders granted yet.")).toHaveCount(0);
});

test("R26: a cancelled dialog changes nothing", async ({ page }) => {
  await open(page, harness, async () => null);
  await page.getByRole("button", { name: "Add output folder…" }).click();
  await expect(page.getByText("No folders granted yet.")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect((await native("/v1/grants")).grants).toEqual([]);
});

test("R26: Remove revokes the grant in the harness and keeps focus in the page", async ({ page }) => {
  await grant("source_root", "keep");
  await grant("output_root", "drop");
  await open(page, harness);
  await page.getByRole("button", { name: "Remove output folder drop" }).click();
  await expect(folders(page).getByRole("listitem")).toHaveText(["Source folder: keepRemove"]);
  await expect(page.getByRole("heading", { name: "Folders" })).toBeFocused();
  expect((await native("/v1/grants")).grants.map((active) => active.label)).toEqual(["keep"]);
  await expectNoAxeViolations(page);
});

test("R26: a refused pick shows the harness's reason", async ({ page }) => {
  await open(page, harness, () => native("/v1/grants", { purpose: "source_root", path: "/absent" }));
  await page.getByRole("button", { name: "Add source folder…" }).click();
  await expect(page.getByRole("alert")).toHaveText("Could not update folders: no such folder");
  await expectNoAxeViolations(page);
});

test("R26: a slow earlier refresh does not wipe a newer problem", async ({ page }) => {
  await page.route("**/v1/grants", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 600));
    await route.continue();
  });
  const listed = page.waitForResponse((response) => response.url().endsWith("/v1/grants"));
  await open(page, harness, () => native("/v1/grants", { purpose: "source_root", path: "/absent" }));
  await page.getByRole("button", { name: "Add source folder…" }).click();
  await listed;
  await page.waitForTimeout(300);
  await expect(page.getByRole("alert")).toHaveText("Could not update folders: no such folder");
});

test("C23: the window itself cannot turn a path into a grant", async ({ page }) => {
  const { folder } = await grant("output_root", "already granted");
  await open(page, harness);
  await expect(folders(page).getByRole("listitem")).toHaveCount(1);
  const outcomes = await page.evaluate(
    async ({ base_url, token, path }) => {
      const attempt = (type: string) =>
        fetch(`${base_url}/v1/grants`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": type },
          body: JSON.stringify({ purpose: "source_root", path }),
        }).then(
          (response) => response.status,
          () => "blocked",
        );
      return [await attempt("application/json"), await attempt("text/plain")];
    },
    { ...harness, path: folder },
  );
  expect(outcomes).not.toContain(200);
  expect((await native("/v1/grants")).grants.map((active) => active.label)).toEqual([
    "already granted",
  ]);
});

test("R20, R19: the trail, environment and plan are projections of the ledger", async ({ page }) => {
  await open(page, harness);
  const trail = page.getByRole("navigation", { name: "Work trail" }).getByRole("listitem");
  await expect(trail).toHaveCount(9);
  await expect(stage(page, "Environment and context")).toContainText("● Completed");
  await expect(stage(page, "Review the workflow")).toContainText(
    "◆ Waiting for you · INSUFFICIENT_EVIDENCE",
  );
  await expect(stage(page, "Independent evaluation")).toContainText("○ Not started");
  const observed = await native("/v1/hardware");
  const environment = page.getByRole("region", { name: "Environment" });
  await expect(environment).toContainText(
    `${observed.cpu.visible_logical_processors} visible, ${observed.cpu.effective_cpu_quota} usable`,
  );
  await expect(environment).toContainText(`${observed.memory.total_gib} GiB total`);
  await expect(environment).toContainText(/Observed \d+ s ago/);
  await expect(page.getByRole("region", { name: "Provisional plan" })).toContainText(
    "Outcome: INSUFFICIENT_EVIDENCE. local-native-draft is unqualified",
  );
  await expect(page.getByRole("region", { name: "Resource status" })).toContainText(
    `${observed.cpu.effective_cpu_quota} processors`,
  );
  await expectNoAxeViolations(page);
  await page.reload();
  await expect(stage(page, "Environment and context")).toContainText("● Completed");
  await expect(environment).toContainText(`${observed.memory.total_gib} GiB total`);
});

test("R20: work done through the CLI reaches the open window", async ({ page }) => {
  await open(page, harness);
  await expect(stage(page, "Develop and optimise")).toContainText("○ Not started");
  expect(await profile("a,b\n1,2\n")).toMatchObject({ version: "v1", files: 3 });
  await expect(stage(page, "Develop and optimise")).toContainText("● Completed");
  await expect(stage(page, "Data and sources")).toContainText("1 source granted");
  await expect(folders(page).getByRole("listitem")).toHaveText([
    "Source folder: data.csvRemove",
    "Output folder: outRemove",
  ]);
  const wide = Array.from({ length: 201 }, (_, column) => `c${column}`).join(",");
  expect(await profile(`${wide}\n`)).toContain("columns");
  await expect(stage(page, "Develop and optimise")).toContainText("✕ Failed · INPUT_INVALID");
  await expectNoAxeViolations(page);
});

test("D19: the environment display goes stale after 60 seconds and can be observed again", async ({
  page,
}) => {
  await page.clock.install();
  await open(page, harness);
  const environment = page.getByRole("region", { name: "Environment" });
  await expect(environment).toContainText(/Observed \d+ s ago/);
  const before = await native("/v1/hardware");
  await page.clock.fastForward(61_000);
  await expect(environment).toContainText(/Stale: observed \d+ s ago/);
  await expect(page.getByRole("region", { name: "Resource status" })).toContainText("stale");
  await expectNoAxeViolations(page);
  await environment.getByRole("button", { name: "Observe again" }).click();
  await expect.poll(async () => (await native("/v1/hardware")).id).not.toBe(before.id);
});

test("A31: what could not be observed is shown as unknown with its reason", async ({ page }) => {
  const real = await native("/v1/hardware", {});
  const partial = {
    ...real,
    memory: { total_gib: null, available_gib: null, effective_limit_gib: null },
    accelerators: { inventory_status: "unknown", devices: [] },
    probes: [
      {
        name: "accelerators",
        status: "permission_denied",
        safe_summary: "the operating system denied this probe",
      },
    ],
  };
  await page.route("**/v1/hardware", (route) =>
    route.request().method() === "GET"
      ? route.fulfill({ json: partial, headers: { "access-control-allow-origin": "*" } })
      : route.continue(),
  );
  await open(page, harness);
  const environment = page.getByRole("region", { name: "Environment" });
  await expect(environment).toContainText("unknown GiB total, unknown GiB available");
  await expect(environment).toContainText("Acceleratorsunknown");
  await expect(environment).toContainText(
    "Not observedaccelerators: the operating system denied this probe",
  );
  await expectNoAxeViolations(page);
});

test("R20: a lost connection keeps the last known state and says so", async ({ page }) => {
  const own = await startHarness();
  await open(page, own);
  await expect(stage(page, "Environment and context")).toContainText("● Completed");
  process.kill(own.pid);
  await expect(page.getByRole("status")).toHaveText(/○ Connection lost; last known state as of /, {
    timeout: 15_000,
  });
  await expect(stage(page, "Environment and context")).toContainText("● Completed");
  await expect(page.getByRole("region", { name: "Environment" })).toContainText("GiB total");
  await expectNoAxeViolations(page);
});
