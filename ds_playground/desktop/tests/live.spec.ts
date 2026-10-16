import { execFileSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { native, open, quitHarness, startHarness, type Harness } from "./harness";

// The sprint's acceptance line on the real local model, in the real window's renderer: run by
// `make live` (tag @live_model), never by `make e2e`. The model loads once for the file.
const MODELS = process.env.DSP_MODEL_DIR ?? join(homedir(), ".local", "share", "dsp", "models");
const INSTRUCTION = "load this CSV and show transit hours by service level";
let harness: Harness;

test.beforeAll(async () => {
  harness = await startHarness(undefined, MODELS);
});
test.afterAll(async () => {
  await quitHarness(harness); // a plain kill left the model server behind, holding its port
});

const activity = (page: Page) => page.getByRole("region", { name: "Activity" });

test("@live_model A28, A24: type the instruction, see real progress, pause mid-run, resume, open the table", async ({
  page,
}) => {
  test.setTimeout(1_200_000);
  await native(harness, "/v1/hardware", {});
  const work = mkdtempSync(join(tmpdir(), "dsp-live-"));
  const data = join(work, "orders.csv");
  const write = `from pathlib import Path; from fixtures.operations import write_orders; write_orders(Path(${JSON.stringify(data)}), orders=500, accounts=50)`;
  execFileSync("uv", ["run", "--frozen", "--project", "..", "python", "-c", write], { cwd: ".." });
  await native(harness, "/v1/grants", { purpose: "source_root", path: data });
  await open(page, harness);
  await expect(page.locator("p.detail")).toContainText("assistant ready (", { timeout: 300_000 });

  await page.getByRole("textbox", { name: "Message" }).fill(INSTRUCTION);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(activity(page)).toContainText(`You: ${INSTRUCTION}`);
  await expect(activity(page)).toContainText("Assistant call 1: inspect_schema", { timeout: 300_000 });

  // Mid-run: the chord pauses the assistant's job (and what it submitted); the loop stops at the
  // end of the call in flight, and nothing it proposes afterwards runs until the owner resumes.
  await page.getByRole("textbox", { name: "Message" }).focus();
  await page.keyboard.press("ControlOrMeta+p");
  await expect(activity(page)).toContainText("You: pause · applied");
  await expect(activity(page)).toContainText(/Job \w+: paused/, { timeout: 300_000 });
  await page.getByRole("button", { name: "Resume" }).click();
  await expect(activity(page)).toContainText("You: resume · applied");

  await expect(activity(page)).toContainText("Assistant (a proposal, not a result):", { timeout: 900_000 });
  const results = page.getByRole("region", { name: "Results" });
  await expect(results).toContainText(/Job \w+: .+\.csv/);
  await results.getByRole("button", { name: /^Open .+\.csv$/ }).first().click();
  const table = page.getByRole("table");
  await expect(table.getByRole("row").nth(1)).toBeVisible();
  await expect(table.getByRole("columnheader").first()).toBeVisible();
});
