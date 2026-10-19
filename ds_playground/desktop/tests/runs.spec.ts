import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import { expectNoAxeViolations, native, open, startHarness, type Harness } from "./harness";

let harness: Harness;
test.beforeAll(async () => {
  harness = await startHarness();
});
test.afterAll(() => {
  process.kill(harness.pid);
});

/** Queue Python as a sandboxed job the way `dsp run-task` does; return the job's ID. */
async function sandboxed(text: string) {
  const { sha256 } = await native<{ sha256: string }>(harness, "/v1/sources", { text });
  const task = { language: "python", source_sha256: sha256, outputs: ["out.json"] };
  const request = { operation: "analyse", idempotency_key: crypto.randomUUID(), task };
  return (await native<{ id: string }>(harness, "/v1/jobs", request)).id;
}

test("B26, A28: sandboxed jobs and the OS's refusal are shown in the activity trail with one wording", async ({ page }) => {
  await native(harness, "/v1/hardware", {});
  const done = await sandboxed("open('out.json', 'w').write('{}')\n");
  const refused = await sandboxed("open('/etc/passwd').read()\n");
  await open(page, harness);
  const activity = page.getByRole("region", { name: "Activity" });
  await expect(activity).toContainText(`Job ${done.slice(-6)}: succeeded (attempt 1, fence 0)`, {
    timeout: 30_000,
  });
  await expect(activity).toContainText(
    `Job ${refused.slice(-6)}: failed (attempt 1, fence 0) · undeclared_read: 1 open(s) outside the declaration; the OS answered`,
    { timeout: 30_000 },
  );
  await expectNoAxeViolations(page);
});

test("D23, A28: a committed table opens from its record, as cells, never from a message", async ({ page }) => {
  await native(harness, "/v1/hardware", {});
  const work = mkdtempSync(join(tmpdir(), "dsp-table-"));
  writeFileSync(join(work, "data.csv"), "order_id,service_level\n1,express\n2,standard\n3,standard\n");
  mkdirSync(join(work, "out"));
  const source = await native<{ handle: string }>(harness, "/v1/grants", { purpose: "source_root", path: join(work, "data.csv") });
  const output = await native<{ handle: string }>(harness, "/v1/grants", { purpose: "output_root", path: join(work, "out") });
  // The file is captured as data through a profile, the way inspect_schema captures it.
  await native(harness, "/v1/profiles", { source_handle: source.handle, relative_path: ".", output_handle: output.handle });
  const events = await native<{ events: { type: string; body: { sha256?: string } }[] }>(harness, "/v1/events");
  const captured = events.events.find((event) => event.type === "data.captured")!.body.sha256!;
  const sql = 'SELECT service_level, count(*) AS orders FROM "data.csv" GROUP BY 1 ORDER BY 1';
  const { sha256 } = await native<{ sha256: string }>(harness, "/v1/sources", { text: sql });
  const task = { language: "sql", source_sha256: sha256, inputs: [{ name: "data.csv", sha256: captured }], outputs: ["table.csv"] };
  const job = (await native<{ id: string }>(harness, "/v1/jobs", { operation: "analyse", idempotency_key: crypto.randomUUID(), task })).id;
  await open(page, harness);
  const results = page.getByRole("region", { name: "Results" });
  await expect(results).toContainText(`Job ${job.slice(-6)}: table.csv`, { timeout: 60_000 });
  await results.getByRole("button", { name: "Open table.csv" }).click();
  const table = page.getByRole("table", { name: `table.csv of job ${job.slice(-6)}` });
  await expect(table.getByRole("row")).toHaveCount(3);
  await expect(table.getByRole("row").nth(1)).toHaveText("express1");
  await expect(table.getByRole("row").nth(2)).toHaveText("standard2");
  await expect(results).not.toContainText("profile.json");  // a profile is a record, not a table to open
  await expectNoAxeViolations(page);
});
