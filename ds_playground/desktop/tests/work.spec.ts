import { spawn, type ChildProcess } from "node:child_process";
import { expect, test, type Page } from "@playwright/test";
import { expectNoAxeViolations, native, open, stage, startHarness, type Harness } from "./harness";

let harness: Harness;
test.beforeAll(async () => {
  harness = await startHarness();
});
test.afterAll(() => {
  process.kill(harness.pid);
});

/** The test worker as a real process on the harness's profile, heartbeating every 200 ms. */
function worker(job: string): ChildProcess {
  const args = ["--frozen", "--project", "..", "python", "-m", "fixtures.worker", "--job", job];
  return spawn("uv", ["run", ...args, "--heartbeat-seconds", "0.2"], {
    cwd: "..",
    env: { ...process.env, DSP_HOME: harness.home },
    stdio: "ignore",
  });
}

const composer = (page: Page) => page.getByRole("form", { name: "Composer" });
const activity = (page: Page) => page.getByRole("region", { name: "Activity" });
const develop = (page: Page) => stage(page, "Develop and optimise");

async function say(page: Page, text: string) {
  await page.getByRole("textbox", { name: "Message" }).fill(text);
  await page.getByRole("button", { name: "Send" }).click();
}

/** Reach a button with the keyboard alone, from wherever focus is, and press it. */
async function pressByKeyboard(page: Page, name: string) {
  for (let step = 0; step < 40; step++) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => document.activeElement?.textContent?.trim() ?? "");
    if (focused === name) {
      await page.keyboard.press("Enter");
      return;
    }
  }
  throw new Error(`${name} was not reached by Tab`);
}

test("A27, R15: the composer's receipts, and a message the harness never had, are shown in the activity trail only", async ({
  page,
}) => {
  await open(page, harness);
  await expect(page.getByRole("status")).toHaveText("● Harness connected");
  await expect(activity(page)).toContainText("Environment observed: observed");
  await say(page, "status");
  await expect(activity(page)).toContainText("You: status · rejected · no job is live");
  await say(page, "please summarise the data");
  await expect(activity(page)).toContainText("You: please summarise the data · rejected · model missing");
  await expect(page.getByRole("textbox", { name: "Message" })).toHaveValue("");
  await page.route("**/v1/conversations/**", (route) => route.abort());
  await say(page, "hello");
  await expect(activity(page)).toContainText("You: hello · no answer");
  await expect(page.getByRole("textbox", { name: "Message" })).toHaveValue("hello");
  await page.unrouteAll();
  await expect(composer(page)).not.toContainText("received");
  await expect(page.getByRole("button", { name: "Pause" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Cancel run" })).toBeDisabled();
  await expectNoAxeViolations(page);
  const events = await native<{ events: { type: string; body: { text?: string } }[] }>(harness, "/v1/events");
  expect(events.events.filter((event) => event.type === "message.received").map((event) => event.body.text)).toEqual([
    "status",
    "please summarise the data",
  ]);
});

test("A24, A25, A26, R15: pause and cancel by shortcut, change, resume by keyboard; the trail survives a reload", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await open(page, harness);
  await expect(stage(page, "Environment and context")).toContainText("● Completed");
  await page.getByRole("button", { name: "Start the hung test job" }).click();
  await expect(develop(page)).toContainText("○ Not started · queued, waiting for a worker");
  const queued = await native<{ events: { type: string; body: { job?: string } }[] }>(harness, "/v1/events");
  const job = queued.events.filter((event) => event.type === "job.queued").at(-1)?.body.job;
  expect(job).toBeTruthy();
  await expect(page.getByRole("region", { name: "Run" })).toHaveText("RunStart the hung test job");
  const first = worker(job!);
  await expect(develop(page)).toContainText("◐ Running", { timeout: 30_000 });
  await expect(page.getByText(`job ${job!.slice(-6)} running`)).toBeVisible();

  await page.keyboard.press("ControlOrMeta+p");
  await expect(activity(page)).toContainText("You: pause · applied");
  await expect(develop(page)).toContainText("◆ Waiting for you · paused", { timeout: 30_000 });
  await expect.poll(() => first.exitCode, { timeout: 30_000 }).toBe(0);
  await expect(activity(page)).toContainText(`Job ${job!.slice(-6)}: pause requested (attempt 1, fence 1)`);
  await expect(activity(page)).toContainText(`Job ${job!.slice(-6)}: paused`);

  await say(page, "exclude field region");
  await expect(activity(page)).toContainText("You: exclude field region · applied");
  await expect(activity(page)).toContainText(
    "Requirements 1.0.0 → 2.0.0: allowed_fields, excluded_fields; 0 stale, 0 held",
  );
  await expect(stage(page, "Goal and constraints")).toContainText("requirements at 2.0.0");

  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await pressByKeyboard(page, "Resume");
  await expect(activity(page)).toContainText("You: resume · applied");
  await expect(develop(page)).toContainText("queued, waiting for a worker");
  const second = worker(job!);
  await expect(develop(page)).toContainText("◐ Running", { timeout: 30_000 });
  await expect(activity(page)).toContainText(`Job ${job!.slice(-6)}: running (attempt 2, fence 1)`);

  await page.getByRole("textbox", { name: "Message" }).focus();
  await page.keyboard.press("ControlOrMeta+Shift+K");
  await expect(activity(page)).toContainText("You: cancel this run · applied");
  await expect(develop(page)).toContainText("◇ Inconclusive · cancelled", { timeout: 30_000 });
  await expect.poll(() => second.exitCode, { timeout: 30_000 }).toBe(0);
  await expect(page.getByRole("button", { name: "Cancel run" })).toBeDisabled();
  await expectNoAxeViolations(page);

  await page.reload();
  await expect(develop(page)).toContainText("◇ Inconclusive · cancelled");
  await expect(stage(page, "Goal and constraints")).toContainText("requirements at 2.0.0");
  const lines = [
    "You: pause · applied",
    "pause requested (attempt 1, fence 1)",
    "paused (attempt 1, fence 1)",
    "You: exclude field region · applied",
    "You: resume · applied",
    "queued (attempt 1, fence 1)",
    "running (attempt 2, fence 1)",
    "You: cancel this run · applied",
    "cancel requested (attempt 2, fence 2)",
    "cancelled (attempt 2, fence 2)",
  ];
  for (const line of lines) await expect(activity(page)).toContainText(line);
  await say(page, "status");
  await expect(activity(page).getByRole("listitem").last()).toContainText("You: status · rejected · no job is live");
  const events = await native<{ events: { type: string; body: { text?: string; expected_revision?: string } }[] }>(
    harness,
    "/v1/events",
  );
  const messages = events.events.filter((event) => event.type === "message.received").map((event) => event.body);
  expect(messages.slice(-5).map((body) => [body.text, body.expected_revision])).toEqual([
    ["pause", "1.0.0"],
    ["exclude field region", "1.0.0"],
    ["resume", "2.0.0"],
    ["cancel this run", "2.0.0"],
    ["status", "2.0.0"],
  ]);
  const job_states = events.events.filter((event) => event.type.startsWith("job.") && event.type !== "job.heartbeat");
  expect(job_states.map((event) => event.type)).toEqual([
    "job.queued",
    "job.started",
    "job.pause_requested",
    "job.paused",
    "job.resumed",
    "job.started",
    "job.cancel_requested",
    "job.cancelled",
  ]);
  await expectNoAxeViolations(page);
});

test("A08, R20: the Run button's result and a refused admission are shown in the activity trail only", async ({ page }) => {
  await open(page, harness);
  await expect(stage(page, "Environment and context")).toContainText("● Completed");
  test.setTimeout(180_000);
  const lines = activity(page).getByRole("listitem");
  // Queued jobs hold their reservations, so pressing Run again and again exhausts the machine.
  for (let press = 0; press < 64 && !(await activity(page).textContent())?.includes("Admission refused"); press++) {
    const before = await lines.count();
    await page.getByRole("button", { name: "Start the hung test job" }).click();
    await expect.poll(() => lines.count()).toBeGreaterThan(before);
  }
  await expect(activity(page)).toContainText(/Job [0-9a-f]{6}: queued/);
  await expect(activity(page)).toContainText(/Admission refused: needs .+ free after what live jobs hold/);
  await expect(activity(page)).not.toContainText("no answer");
  await expect(page.getByRole("region", { name: "Run" })).toHaveText("RunStart the hung test job");
  await expectNoAxeViolations(page);
});
