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
